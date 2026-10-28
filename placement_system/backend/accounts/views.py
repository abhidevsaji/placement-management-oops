from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.http import FileResponse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework import status as http
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ActivityLog, Student, User
from .permissions import IsAdminRole
from .serializers import (UserDetailSerializer, ActivityLogSerializer, LoginSerializer, OfficerRegisterSerializer,
                          PROFILE_SERIALIZERS, StudentRegisterSerializer, UserListSerializer,
                          serialize_profile)

REGISTRATION_MESSAGE = 'Registration submitted. You can log in once an admin approves your account.'


class RegisterStudentView(APIView):
    permission_classes = [AllowAny]
    serializer_class = StudentRegisterSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        ActivityLog.record(user, 'REGISTER', f'{user.role} registered: {user.email}')
        return Response({'detail': REGISTRATION_MESSAGE}, status=http.HTTP_201_CREATED)


class RegisterOfficerView(RegisterStudentView):
    serializer_class = OfficerRegisterSerializer


class LoginView(APIView):
    """Activity diagram: Valid login? -> Account approved? -> identify role."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower()
        user = authenticate(request, username=email, password=serializer.validated_data['password'])
        if user is None:
            return Response({'detail': 'Invalid email or password.'}, status=http.HTTP_400_BAD_REQUEST)
        if user.status == User.PENDING:
            return Response({'detail': 'Your account is waiting for admin approval.', 'code': 'pending'},
                            status=http.HTTP_403_FORBIDDEN)
        if user.status == User.REJECTED:
            reason = f' Reason: {user.rejection_reason}' if user.rejection_reason else ''
            return Response({'detail': 'Your registration was rejected by the admin.' + reason, 'code': 'rejected'},
                            status=http.HTTP_403_FORBIDDEN)
        token, _ = Token.objects.get_or_create(user=user)
        ActivityLog.record(user, 'LOGIN', user.email)
        return Response({'token': token.key, 'user': serialize_profile(user)})


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        ActivityLog.record(request.user, 'LOGOUT', request.user.email)
        return Response(status=http.HTTP_204_NO_CONTENT)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(serialize_profile(request.user))

    def put(self, request):
        profile = request.user.get_profile()
        serializer_class = PROFILE_SERIALIZERS[request.user.role]
        serializer = serializer_class(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            profile.update_profile(**serializer.validated_data)
        except DjangoValidationError as e:
            return Response(e.message_dict, status=http.HTTP_400_BAD_REQUEST)
        ActivityLog.record(request.user, 'UPDATE_PROFILE', request.user.email)
        return Response(serialize_profile(request.user))


class DashboardView(APIView):
    """Polymorphism in action: the same call returns different data per role."""
    def get(self, request):
        return Response(request.user.get_profile().get_dashboard_summary())


# ------------------------- Admin only -------------------------
class UserListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = User.objects.exclude(pk=request.user.pk).order_by('-date_joined')
        for field in ('role', 'status'):
            if request.query_params.get(field):
                qs = qs.filter(**{field: request.query_params[field]})
        q = request.query_params.get('q')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q))
        return Response(UserListSerializer(qs, many=True).data)


class UserActionView(APIView):
    """POST /api/admin/users/<id>/approve|reject/   DELETE /api/admin/users/<id>/"""
    permission_classes = [IsAdminRole]

    def _target(self, request, pk):
        user = User.objects.filter(pk=pk).first()
        if user is None or user.pk == request.user.pk:
            return None
        return user

    def get(self, request, pk, action=None):
        user = self._target(request, pk)
        if user is None:
            return Response({'detail': 'User not found.'}, status=http.HTTP_404_NOT_FOUND)
        return Response(UserDetailSerializer(user).data)

    def post(self, request, pk, action):
        user = self._target(request, pk)
        if user is None or action not in ('approve', 'reject'):
            return Response({'detail': 'User not found.'}, status=http.HTTP_404_NOT_FOUND)
        if action == 'approve':
            user.approve(by=request.user)
        else:
            reason = str(request.data.get('reason', '')).strip()
            if len(reason) < 3:
                return Response({'reason': ['Please give a short reason for rejecting this account.']},
                                status=http.HTTP_400_BAD_REQUEST)
            user.reject(reason, by=request.user)
        ActivityLog.record(request.user, action.upper() + '_USER', user.email)
        return Response(UserListSerializer(user).data)

    def delete(self, request, pk, action=None):
        user = self._target(request, pk)
        if user is None:
            return Response({'detail': 'User not found.'}, status=http.HTTP_404_NOT_FOUND)
        ActivityLog.record(request.user, 'DELETE_USER', user.email)
        user.delete()
        return Response(status=http.HTTP_204_NO_CONTENT)


class ActivityLogView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(ActivityLogSerializer(ActivityLog.objects.select_related('user')[:100], many=True).data)


# ------------------------- Resume -------------------------
class ResumeView(APIView):
    """A student uploads / replaces / removes their own resume (multipart form, field name: resume)."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def _student(self, request):
        return request.user.get_profile() if request.user.role == User.STUDENT else None

    def post(self, request):
        student = self._student(request)
        file = request.FILES.get('resume')
        if student is None:
            return Response({'detail': 'Only students can upload a resume.'}, status=http.HTTP_403_FORBIDDEN)
        if file is None:
            return Response({'resume': ['Choose a PDF file to upload.']}, status=http.HTTP_400_BAD_REQUEST)
        try:
            student.attach_resume(file)
        except DjangoValidationError as e:
            return Response({'resume': e.messages}, status=http.HTTP_400_BAD_REQUEST)
        ActivityLog.record(request.user, 'UPLOAD_RESUME', request.user.email)
        return Response(serialize_profile(request.user))

    def delete(self, request):
        student = self._student(request)
        if student is None:
            return Response(status=http.HTTP_403_FORBIDDEN)
        student.remove_resume()
        return Response(serialize_profile(request.user))


class ResumeDownloadView(APIView):
    """Private download: a student sees only their own resume, officers/admins can see any."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        if not user.is_approved or (user.role == User.STUDENT and user.pk != pk):
            return Response(status=http.HTTP_403_FORBIDDEN)
        student = Student.objects.filter(pk=pk).first()
        if student is None or not student.has_resume:
            return Response({'detail': 'No resume uploaded.'}, status=http.HTTP_404_NOT_FOUND)
        return FileResponse(student.resume.open('rb'), content_type='application/pdf',
                            headers={'Content-Disposition': f'inline; filename="resume_{student.roll_no}.pdf"'})
