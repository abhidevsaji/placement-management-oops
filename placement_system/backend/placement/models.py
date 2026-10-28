"""
Placement app - implements the UML classes:
Company, JobPosting, Application, Result, PlacementDrive, Report (+ Notification, from the sequence diagram).
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone

from accounts.models import Student, User


class Notification(models.Model):
    """In-app notification shown to a user (students are told about new jobs, status changes, drives)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    @classmethod
    def send(cls, user, message):
        return cls.objects.create(user=user, message=message[:255])

    @classmethod
    def send_many(cls, users, message):
        cls.objects.bulk_create([cls(user=u, message=message[:255]) for u in users])


class Company(models.Model):
    """UML: Company. Managed by the Placement Officer (company has no login of its own)."""
    ACTIVE, INACTIVE = 'active', 'inactive'
    STATUS_CHOICES = [(ACTIVE, 'Active'), (INACTIVE, 'Inactive')]

    name = models.CharField(max_length=150, unique=True)
    hr_email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'companies'

    def __str__(self):
        return self.name


class JobPosting(models.Model):
    """UML: JobPosting. Company 1 --- 0..* JobPosting ("offers")."""
    OPEN, CLOSED = 'open', 'closed'
    STATUS_CHOICES = [(OPEN, 'Open'), (CLOSED, 'Closed')]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=150)
    description = models.TextField()
    package = models.CharField(max_length=50, help_text='e.g. 6 LPA')
    eligibility_criteria = models.TextField(blank=True, help_text='Free text shown to students')
    min_cgpa = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(10)])
    allowed_branches = models.CharField(max_length=255, blank=True, help_text='Comma separated; empty = all branches')
    last_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=OPEN)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.title} @ {self.company.name}'

    def clean(self):
        if self.last_date and self.last_date < timezone.localdate() and not self.pk:
            raise ValidationError({'last_date': 'Last date cannot be in the past.'})

    # ---- behaviour ----
    @property
    def branch_list(self):
        return [b.strip().lower() for b in self.allowed_branches.split(',') if b.strip()]

    def allows(self, cgpa, branch):
        """Eligibility rule: CGPA at least min_cgpa AND branch in the allowed list (if one is given)."""
        if cgpa < self.min_cgpa:
            return False
        return not self.branch_list or branch.strip().lower() in self.branch_list

    @property
    def is_accepting(self):
        return self.status == self.OPEN and self.last_date >= timezone.localdate()

    def eligible_students(self):
        return [s for s in Student.objects.filter(status=User.APPROVED) if s.is_eligible_for(self)]

    def notify_eligible_students(self):
        Notification.send_many(self.eligible_students(),
                               f'New job: {self.title} at {self.company.name} ({self.package}). Apply before {self.last_date}.')


class Application(models.Model):
    """UML: Application. JobPosting 1 --- 0..* Application ("receives")."""
    APPLIED, SHORTLISTED, REJECTED, PLACED = 'applied', 'shortlisted', 'rejected', 'placed'
    STATUS_CHOICES = [(APPLIED, 'Applied'), (SHORTLISTED, 'Shortlisted'), (REJECTED, 'Rejected'), (PLACED, 'Placed')]
    # Allowed status changes. Anything else is refused (encapsulated business rule).
    TRANSITIONS = {
        APPLIED: {SHORTLISTED, REJECTED},
        SHORTLISTED: {PLACED, REJECTED},
        REJECTED: set(),
        PLACED: set(),
    }

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    applied_date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=APPLIED)

    class Meta:
        unique_together = ('student', 'job')
        ordering = ['-applied_date', '-id']

    def __str__(self):
        return f'{self.student.name} -> {self.job.title} [{self.status}]'

    @classmethod
    def apply(cls, student, job):
        """UML: apply(). Validates every rule before saving."""
        if not job.is_accepting:
            raise ValidationError('This job is closed or the last date has passed.')
        if not student.has_resume:
            raise ValidationError('Upload your resume in My profile before applying.')
        if not student.is_eligible_for(job):
            raise ValidationError('You do not meet the eligibility criteria for this job.')
        if cls.objects.filter(student=student, job=job).exists():
            raise ValidationError('You have already applied for this job.')
        application = cls.objects.create(student=student, job=job)
        Notification.send(student, f'Application submitted for {job.title} at {job.company.name}.')
        return application

    def update_status(self, new_status):
        """UML: updateStatus(). Officer moves an application forward; student is notified."""
        if new_status not in self.TRANSITIONS.get(self.status, set()):
            raise ValidationError(f'Cannot change status from {self.status} to {new_status}.')
        self.status = new_status
        self.save(update_fields=['status'])
        if new_status in (self.PLACED, self.REJECTED):
            Result.publish(self)
        else:
            Notification.send(self.student, f'You have been shortlisted for {self.job.title} at {self.job.company.name}.')


class Result(models.Model):
    """UML: Result. Application 1 --- 0..1 Result ("generates")."""
    SELECTED, NOT_SELECTED = 'selected', 'not_selected'
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='result')
    status = models.CharField(max_length=15)
    selected_date = models.DateField(default=timezone.localdate)

    @classmethod
    def publish(cls, application):
        """UML: publishResult(). Creates the result and tells the student."""
        selected = application.status == Application.PLACED
        result, _ = cls.objects.update_or_create(
            application=application,
            defaults={'status': cls.SELECTED if selected else cls.NOT_SELECTED})
        job = application.job
        msg = (f'Congratulations! You are placed at {job.company.name} ({job.title}).' if selected
               else f'Your application for {job.title} at {job.company.name} was not selected.')
        Notification.send(application.student, msg)
        return result


class PlacementDrive(models.Model):
    """UML: PlacementDrive. Scheduled by a Placement Officer for a job."""
    SCHEDULED, COMPLETED, CANCELLED = 'scheduled', 'completed', 'cancelled'
    STATUS_CHOICES = [(SCHEDULED, 'Scheduled'), (COMPLETED, 'Completed'), (CANCELLED, 'Cancelled')]

    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='drives')
    drive_date = models.DateField()
    venue = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=SCHEDULED)
    scheduled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        ordering = ['drive_date', 'id']

    def notify_students(self):
        """UML: notifyStudents(). Tell every applicant who has not been rejected."""
        students = Student.objects.filter(applications__job=self.job).exclude(applications__status=Application.REJECTED)
        Notification.send_many(set(students),
                               f'Placement drive for {self.job.title} at {self.job.company.name} on {self.drive_date}, venue: {self.venue}.')


class Report(models.Model):
    """UML: Report. generateReport() builds the data, viewReport() is the API read."""
    SUMMARY, COMPANY_WISE, BRANCH_WISE = 'summary', 'company_wise', 'branch_wise'
    TYPE_CHOICES = [(SUMMARY, 'Placement summary'), (COMPANY_WISE, 'Company wise'), (BRANCH_WISE, 'Branch wise')]

    report_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    generated_date = models.DateField(default=timezone.localdate)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    data = models.JSONField(default=dict)

    class Meta:
        ordering = ['-id']

    @classmethod
    def generate(cls, report_type, user):
        builder = {cls.SUMMARY: cls._summary, cls.COMPANY_WISE: cls._company_wise, cls.BRANCH_WISE: cls._branch_wise}[report_type]
        return cls.objects.create(report_type=report_type, generated_by=user, data=builder())

    # one small builder per report type
    @staticmethod
    def _summary():
        students = Student.objects.filter(status=User.APPROVED).count()
        placed = Student.objects.filter(applications__status=Application.PLACED).distinct().count()
        return {
            'total_students': students,
            'placed_students': placed,
            'placement_percentage': round(placed * 100 / students, 1) if students else 0,
            'companies': Company.objects.count(),
            'jobs': JobPosting.objects.count(),
            'applications': Application.objects.count(),
            'shortlisted': Application.objects.filter(status=Application.SHORTLISTED).count(),
        }

    @staticmethod
    def _company_wise():
        rows = Company.objects.annotate(
            jobs_count=Count('jobs', distinct=True),
            applications=Count('jobs__applications', distinct=True),
            placed=Count('jobs__applications', filter=Q(jobs__applications__status=Application.PLACED), distinct=True),
        )
        return {'rows': [{'company': c.name, 'jobs': c.jobs_count, 'applications': c.applications, 'placed': c.placed} for c in rows]}

    @staticmethod
    def _branch_wise():
        out = []
        for b in Student.objects.filter(status=User.APPROVED).values_list('branch', flat=True).distinct():
            total = Student.objects.filter(status=User.APPROVED, branch=b).count()
            placed = Student.objects.filter(branch=b, applications__status=Application.PLACED).distinct().count()
            out.append({'branch': b, 'students': total, 'placed': placed})
        return {'rows': out}


class Task(models.Model):
    """Work the Admin assigns to a Placement Officer. The task types map to the officer's UML operations."""
    TASK_TYPES = [
        ('add_company', 'Add / update company details'), ('post_job', 'Post a job opening'),
        ('set_eligibility', 'Set eligibility criteria'), ('review_applications', 'Review student applications'),
        ('shortlist', 'Shortlist students'), ('schedule_drive', 'Schedule a placement drive'),
        ('notify_students', 'Notify eligible students'), ('publish_results', 'Publish placement results'),
        ('other', 'Other'),
    ]
    LOW, MEDIUM, HIGH = 'low', 'medium', 'high'
    PRIORITY_CHOICES = [(LOW, 'Low'), (MEDIUM, 'Medium'), (HIGH, 'High')]
    PENDING, IN_PROGRESS, COMPLETED = 'pending', 'in_progress', 'completed'
    STATUS_CHOICES = [(PENDING, 'Pending'), (IN_PROGRESS, 'In progress'), (COMPLETED, 'Completed')]
    # What an officer may do (forward only). The Admin can change anything.
    OFFICER_TRANSITIONS = {PENDING: {IN_PROGRESS, COMPLETED}, IN_PROGRESS: {COMPLETED}, COMPLETED: set()}

    title = models.CharField(max_length=150)
    task_type = models.CharField(max_length=25, choices=TASK_TYPES, default='other')
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey('accounts.PlacementOfficer', on_delete=models.CASCADE, related_name='tasks')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    priority = models.CharField(max_length=6, choices=PRIORITY_CHOICES, default=MEDIUM)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=PENDING)
    officer_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['status', 'due_date', '-id']

    def __str__(self):
        return f'{self.title} -> {self.assigned_to.name}'

    @property
    def is_overdue(self):
        return self.status != self.COMPLETED and bool(self.due_date) and self.due_date < timezone.localdate()

    @classmethod
    def assign(cls, admin_user, **data):
        task = cls.objects.create(assigned_by=admin_user, **data)
        due = f' Due {task.due_date}.' if task.due_date else ''
        Notification.send(task.assigned_to, f'New task from admin: {task.title} ({task.priority} priority).{due}')
        return task

    def progress(self, new_status, note=''):
        """Officer reports progress; the Admin is notified."""
        if new_status not in self.OFFICER_TRANSITIONS.get(self.status, set()):
            raise ValidationError(f'Cannot change a {self.status} task to {new_status}.')
        self.status = new_status
        self.officer_note = note[:255]
        self.completed_at = timezone.now() if new_status == self.COMPLETED else None
        self.save()
        if self.assigned_by_id:
            Notification.send(self.assigned_by, f'{self.assigned_to.name} marked "{self.title}" as {new_status.replace("_", " ")}.')
