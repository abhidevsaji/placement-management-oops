from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import ActivityLog, Admin, PlacementOfficer, Student, User


class _RegisterBase(serializers.ModelSerializer):
    """Shared registration logic (inheritance): validates password + email, then calls Model.register()."""
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('This email is already registered.')
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        return self.Meta.model.register(password, **validated_data)


class StudentRegisterSerializer(_RegisterBase):
    class Meta:
        model = Student
        fields = ['name', 'email', 'password', 'roll_no', 'branch', 'cgpa', 'phone', 'address']


class OfficerRegisterSerializer(_RegisterBase):
    class Meta:
        model = PlacementOfficer
        fields = ['name', 'email', 'password', 'department', 'phone']


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


# ---- profile serializers (one per role -> polymorphic lookup in PROFILE_SERIALIZERS) ----
class _ProfileBase(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'role', 'status']
        read_only_fields = ['id', 'email', 'role', 'status']


class StudentProfileSerializer(_ProfileBase):
    has_resume = serializers.BooleanField(read_only=True)
    resume_updated = serializers.DateTimeField(read_only=True)

    class Meta(_ProfileBase.Meta):
        model = Student
        fields = _ProfileBase.Meta.fields + ['roll_no', 'branch', 'cgpa', 'phone', 'address', 'has_resume', 'resume_updated']
        read_only_fields = _ProfileBase.Meta.read_only_fields + ['roll_no']


class OfficerProfileSerializer(_ProfileBase):
    class Meta(_ProfileBase.Meta):
        model = PlacementOfficer
        fields = _ProfileBase.Meta.fields + ['department', 'phone']


class AdminProfileSerializer(_ProfileBase):
    class Meta(_ProfileBase.Meta):
        model = Admin


PROFILE_SERIALIZERS = {
    User.STUDENT: StudentProfileSerializer,
    User.OFFICER: OfficerProfileSerializer,
    User.ADMIN: AdminProfileSerializer,
}


def serialize_profile(user):
    profile = user.get_profile()
    serializer_class = PROFILE_SERIALIZERS.get(user.role, _ProfileBase)
    return serializer_class(profile).data


class UserListSerializer(serializers.ModelSerializer):
    details = serializers.SerializerMethodField()
    has_resume = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'role', 'status', 'date_joined', 'details', 'has_resume', 'rejection_reason']

    def get_has_resume(self, obj):
        p = obj.get_profile()
        return p.has_resume if isinstance(p, Student) else None

    def get_details(self, obj):
        p = obj.get_profile()
        if isinstance(p, Student):
            return f'{p.roll_no} | {p.branch} | CGPA {p.cgpa}'
        if isinstance(p, PlacementOfficer):
            return p.department
        return ''


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', default='System', read_only=True)

    class Meta:
        model = ActivityLog
        fields = ['id', 'user_name', 'action', 'details', 'created_at']


class UserDetailSerializer(UserListSerializer):
    """Everything the Admin needs to decide on a registration."""
    profile = serializers.SerializerMethodField()
    verified_by_name = serializers.CharField(source='verified_by.name', default='', read_only=True)

    class Meta(UserListSerializer.Meta):
        fields = UserListSerializer.Meta.fields + ['profile', 'verified_at', 'verified_by_name']

    def get_profile(self, obj):
        return serialize_profile(obj)
