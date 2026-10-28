from rest_framework import serializers

from .models import Application, Company, JobPosting, Notification, PlacementDrive, Report, Result, Task


class CompanySerializer(serializers.ModelSerializer):
    open_jobs = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = ['id', 'name', 'hr_email', 'phone', 'address', 'description', 'status', 'open_jobs']

    def get_open_jobs(self, obj):
        return obj.jobs.filter(status='open').count()


class JobSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    applications_count = serializers.SerializerMethodField()
    has_applied = serializers.SerializerMethodField()

    class Meta:
        model = JobPosting
        fields = ['id', 'company', 'company_name', 'title', 'description', 'package', 'eligibility_criteria',
                  'min_cgpa', 'allowed_branches', 'last_date', 'status', 'applications_count', 'has_applied']

    def get_applications_count(self, obj):
        return obj.applications.count()

    def get_has_applied(self, obj):
        user = self.context['request'].user
        return user.role == 'student' and obj.applications.filter(student_id=user.pk).exists()

    def validate_company(self, company):
        if company.status != Company.ACTIVE:
            raise serializers.ValidationError('Jobs can only be posted for active companies.')
        return company

    def validate_last_date(self, value):
        from django.utils import timezone
        if not self.instance and value < timezone.localdate():
            raise serializers.ValidationError('Last date cannot be in the past.')
        return value


class ApplicationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    roll_no = serializers.CharField(source='student.roll_no', read_only=True)
    branch = serializers.CharField(source='student.branch', read_only=True)
    cgpa = serializers.FloatField(source='student.cgpa', read_only=True)
    email = serializers.CharField(source='student.email', read_only=True)
    has_resume = serializers.BooleanField(source='student.has_resume', read_only=True)
    phone = serializers.CharField(source='student.phone', read_only=True)
    address = serializers.CharField(source='student.address', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    company_name = serializers.CharField(source='job.company.name', read_only=True)
    package = serializers.CharField(source='job.package', read_only=True)
    result = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ['id', 'job', 'job_title', 'company_name', 'package', 'student', 'student_name', 'roll_no',
                  'branch', 'cgpa', 'email', 'phone', 'address', 'has_resume', 'applied_date', 'status', 'result']

    def get_result(self, obj):
        r = getattr(obj, 'result', None)
        return {'status': r.status, 'selected_date': r.selected_date} if r else None


class DriveSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    company_name = serializers.CharField(source='job.company.name', read_only=True)

    class Meta:
        model = PlacementDrive
        fields = ['id', 'job', 'job_title', 'company_name', 'drive_date', 'venue', 'description', 'status']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'is_read', 'created_at']


class ReportSerializer(serializers.ModelSerializer):
    generated_by_name = serializers.CharField(source='generated_by.name', default='', read_only=True)
    type_label = serializers.CharField(source='get_report_type_display', read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'report_type', 'type_label', 'generated_date', 'generated_by_name', 'data']
        read_only_fields = ['generated_date', 'data']


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.name', default='', read_only=True)
    company_name = serializers.CharField(source='company.name', default='', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = ['id', 'title', 'task_type', 'description', 'assigned_to', 'assigned_to_name', 'assigned_by_name',
                  'company', 'company_name', 'priority', 'due_date', 'status', 'officer_note', 'is_overdue',
                  'created_at', 'completed_at']
        read_only_fields = ['officer_note', 'completed_at']

    def validate_assigned_to(self, officer):
        if officer.status != 'approved':
            raise serializers.ValidationError('Tasks can only be assigned to approved placement officers.')
        return officer

    def validate_due_date(self, value):
        from django.utils import timezone
        if value and not self.instance and value < timezone.localdate():
            raise serializers.ValidationError('Due date cannot be in the past.')
        return value
