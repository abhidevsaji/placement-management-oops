from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework import status as http
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import ActivityLog
from accounts.permissions import (IsAdminRole, IsAnyApprovedUser, IsOfficerOrAdmin, IsPlacementOfficer, IsStudent)
from .models import Application, Company, JobPosting, Notification, PlacementDrive, Report, Task
from .serializers import (ApplicationSerializer, CompanySerializer, DriveSerializer, JobSerializer,
                          NotificationSerializer, ReportSerializer, TaskSerializer)


def as_api_error(exc):
    """Turn a Django ValidationError (from model rules) into a DRF 400 response."""
    return ValidationError(exc.messages)


class CompanyViewSet(viewsets.ModelViewSet):
    """Placement Officer (or Admin) manages company information."""
    serializer_class = CompanySerializer
    permission_classes = [IsOfficerOrAdmin]

    def get_queryset(self):
        qs = Company.objects.all()
        q = self.request.query_params.get('q')
        return qs.filter(name__icontains=q) if q else qs

    def perform_create(self, serializer):
        company = serializer.save(created_by=self.request.user)
        ActivityLog.record(self.request.user, 'ADD_COMPANY', company.name)

    def perform_update(self, serializer):
        company = serializer.save()
        ActivityLog.record(self.request.user, 'UPDATE_COMPANY', company.name)


class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAnyApprovedUser()]
        if self.action == 'apply':
            return [IsStudent()]
        return [IsOfficerOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        qs = JobPosting.objects.select_related('company')
        if user.role == 'student':
            # Student only sees open, not-expired jobs they are eligible for.
            student = user.get_profile()
            qs = qs.filter(status='open', company__status='active')
            ids = [j.pk for j in qs if j.is_accepting and student.is_eligible_for(j)]
            return qs.filter(pk__in=ids)
        params = self.request.query_params
        if params.get('company'):
            qs = qs.filter(company_id=params['company'])
        if params.get('status'):
            qs = qs.filter(status=params['status'])
        return qs

    def perform_create(self, serializer):
        job = serializer.save(posted_by=self.request.user)
        job.notify_eligible_students()
        ActivityLog.record(self.request.user, 'POST_JOB', str(job))

    def perform_update(self, serializer):
        job = serializer.save()
        ActivityLog.record(self.request.user, 'UPDATE_JOB', str(job))

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        job = self.get_object()
        try:
            application = Application.apply(request.user.get_profile(), job)
        except DjangoValidationError as exc:
            raise as_api_error(exc)
        ActivityLog.record(request.user, 'APPLY_JOB', str(job))
        return Response(ApplicationSerializer(application).data, status=http.HTTP_201_CREATED)


class ApplicationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ApplicationSerializer

    def get_permissions(self):
        if self.action == 'set_status':
            return [IsPlacementOfficer()]
        return [IsAnyApprovedUser()]

    def get_queryset(self):
        user = self.request.user
        qs = Application.objects.select_related('student', 'job__company', 'result')
        if user.role == 'student':
            return qs.filter(student_id=user.pk)
        p = self.request.query_params
        if p.get('job'):
            qs = qs.filter(job_id=p['job'])
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        if p.get('q'):
            qs = qs.filter(Q(student__name__icontains=p['q']) | Q(student__roll_no__icontains=p['q']))
        return qs

    @action(detail=True, methods=['patch'], url_path='status')
    def set_status(self, request, pk=None):
        application = self.get_object()
        try:
            application.update_status(request.data.get('status', ''))
        except DjangoValidationError as exc:
            raise as_api_error(exc)
        ActivityLog.record(request.user, 'UPDATE_APPLICATION', f'{application} ')
        return Response(self.get_serializer(application).data)


class PlacedStudentsView(APIView):
    permission_classes = [IsOfficerOrAdmin]

    def get(self, request):
        qs = Application.objects.filter(status=Application.PLACED).select_related('student', 'job__company', 'result')
        return Response(ApplicationSerializer(qs, many=True).data)


class DriveViewSet(viewsets.ModelViewSet):
    serializer_class = DriveSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAnyApprovedUser()]
        return [IsPlacementOfficer()]

    def get_queryset(self):
        qs = PlacementDrive.objects.select_related('job__company')
        user = self.request.user
        if user.role == 'student':
            return qs.filter(job__applications__student_id=user.pk).exclude(job__applications__status='rejected').distinct()
        return qs

    def perform_create(self, serializer):
        drive = serializer.save(scheduled_by=self.request.user)
        drive.notify_students()
        ActivityLog.record(self.request.user, 'SCHEDULE_DRIVE', str(drive.job))


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAnyApprovedUser]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        n = self.get_object()
        n.is_read = True
        n.save(update_fields=['is_read'])
        return Response(self.get_serializer(n).data)

    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        self.get_queryset().update(is_read=True)
        return Response(status=http.HTTP_204_NO_CONTENT)


class ReportViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Admin generates and views placement reports."""
    serializer_class = ReportSerializer
    permission_classes = [IsAdminRole]
    queryset = Report.objects.select_related('generated_by')

    def create(self, request, *args, **kwargs):
        report_type = request.data.get('report_type', Report.SUMMARY)
        if report_type not in dict(Report.TYPE_CHOICES):
            raise ValidationError({'report_type': 'Unknown report type.'})
        report = Report.generate(report_type, request.user)
        ActivityLog.record(request.user, 'GENERATE_REPORT', report_type)
        return Response(self.get_serializer(report).data, status=http.HTTP_201_CREATED)


class TaskViewSet(viewsets.ModelViewSet):
    """Admin assigns tasks to officers; each officer sees and updates only their own."""
    serializer_class = TaskSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsOfficerOrAdmin()]
        if self.action == 'progress':
            return [IsPlacementOfficer()]
        return [IsAdminRole()]

    def get_queryset(self):
        qs = Task.objects.select_related('assigned_to', 'assigned_by', 'company')
        user = self.request.user
        if user.role == 'officer':
            return qs.filter(assigned_to_id=user.pk)
        p = self.request.query_params
        if p.get('officer'):
            qs = qs.filter(assigned_to_id=p['officer'])
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        return qs

    def perform_create(self, serializer):
        data = dict(serializer.validated_data)
        serializer.instance = Task.assign(self.request.user, **data)
        ActivityLog.record(self.request.user, 'ASSIGN_TASK', str(serializer.instance))

    @action(detail=True, methods=['post'])
    def progress(self, request, pk=None):
        task = self.get_object()
        try:
            task.progress(request.data.get('status', ''), str(request.data.get('officer_note', '')))
        except DjangoValidationError as exc:
            raise as_api_error(exc)
        ActivityLog.record(request.user, 'TASK_PROGRESS', f'{task.title}: {task.status}')
        return Response(self.get_serializer(task).data)
