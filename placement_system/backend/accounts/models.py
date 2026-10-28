"""
Accounts app - implements the UML classes:  User  ->  Student / PlacementOfficer / Admin

OOP concepts used here
  * Inheritance   : Student, PlacementOfficer and Admin extend User (multi-table inheritance,
                    exactly like the UML generalisation arrow).
  * Encapsulation : business rules live inside the classes (register, approve, update_profile,
                    is_eligible_for ...) so views stay thin.
  * Polymorphism  : every subclass overrides get_dashboard_summary() and EDITABLE_FIELDS;
                    callers just call user.get_profile().get_dashboard_summary().
"""
from django.apps import apps
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

phone_validator = RegexValidator(r'^\d{10}$', 'Phone number must be exactly 10 digits.')


MAX_RESUME_MB = 2


def resume_path(instance, filename):
    return f'resumes/student_{instance.pk}.pdf'


def validate_resume_file(file):
    """Only real PDF files up to 2 MB are accepted."""
    if not file.name.lower().endswith('.pdf'):
        raise ValidationError('Resume must be a PDF file.')
    if file.size > MAX_RESUME_MB * 1024 * 1024:
        raise ValidationError(f'Resume must be smaller than {MAX_RESUME_MB} MB.')
    head = file.read(5)
    file.seek(0)
    if head != b'%PDF-':
        raise ValidationError('This file is not a valid PDF.')


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('Email is required')
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.update(role=User.ADMIN, status=User.APPROVED, is_staff=True, is_superuser=True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """UML: User (user_id, name, email, password, role, status)."""
    STUDENT, OFFICER, ADMIN = 'student', 'officer', 'admin'
    ROLE_CHOICES = [(STUDENT, 'Student'), (OFFICER, 'Placement Officer'), (ADMIN, 'Admin')]
    PENDING, APPROVED, REJECTED = 'pending', 'approved', 'rejected'
    STATUS_CHOICES = [(PENDING, 'Pending'), (APPROVED, 'Approved'), (REJECTED, 'Rejected')]

    ROLE = None  # each subclass sets its own role
    # name of the reverse one-to-one accessor Django creates for each child class
    _CHILD_ACCESSOR = {STUDENT: 'student', OFFICER: 'placementofficer', ADMIN: 'admin'}

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    # verification trail (filled when an Admin approves / rejects the account)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    rejection_reason = models.CharField(max_length=255, blank=True)

    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    # fields a user may change through updateProfile(); subclasses extend this list
    EDITABLE_FIELDS = ['name']

    def __str__(self):
        return f'{self.name} ({self.role})'

    # ---------- construction ----------
    @classmethod
    def register(cls, password, **data):
        """Create an account in 'pending' state; an Admin must approve it before login."""
        user = cls(role=cls.ROLE, status=cls.PENDING, **data)
        user.email = user.email.lower()
        user.set_password(password)
        user.save()
        return user

    # ---------- account state ----------
    @property
    def is_approved(self):
        return self.status == self.APPROVED

    def approve(self, by=None):
        self.status = self.APPROVED
        self.rejection_reason = ''
        self.verified_at = timezone.now()
        self.verified_by = by
        self.save(update_fields=['status', 'rejection_reason', 'verified_at', 'verified_by'])
        apps.get_model('placement', 'Notification').send(self, 'Your account has been verified. Welcome aboard!')

    def reject(self, reason='', by=None):
        self.status = self.REJECTED
        self.rejection_reason = reason[:255]
        self.verified_at = timezone.now()
        self.verified_by = by
        self.save(update_fields=['status', 'rejection_reason', 'verified_at', 'verified_by'])

    # ---------- UML methods ----------
    def update_profile(self, **data):
        """Only whitelisted fields can be changed (encapsulation / security)."""
        for field in self.EDITABLE_FIELDS:
            if field in data:
                setattr(self, field, data[field])
        self.full_clean(exclude=['password'], validate_unique=False)
        self.save()
        return self

    def get_profile(self):
        """Return the most specific object (Student / PlacementOfficer / Admin)."""
        try:
            return getattr(self, self._CHILD_ACCESSOR.get(self.role, ''))
        except (ObjectDoesNotExist, AttributeError):
            return self

    def get_dashboard_summary(self):
        """Polymorphic: overridden by each subclass."""
        return {}


class Student(User):
    """UML: Student (student_id, roll_no, branch, cgpa, phone, address)."""
    ROLE = User.STUDENT
    EDITABLE_FIELDS = ['name', 'branch', 'cgpa', 'phone', 'address']

    roll_no = models.CharField(max_length=30, unique=True)
    branch = models.CharField(max_length=50)
    cgpa = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    phone = models.CharField(max_length=10, validators=[phone_validator])
    address = models.TextField(blank=True)
    resume = models.FileField(upload_to=resume_path, blank=True)
    resume_updated = models.DateTimeField(null=True, blank=True)

    @property
    def has_resume(self):
        return bool(self.resume)

    def attach_resume(self, file):
        """Validate and store the resume (replaces any older one)."""
        validate_resume_file(file)
        if self.resume:
            self.resume.delete(save=False)
        self.resume.save(file.name, file, save=False)
        self.resume_updated = timezone.now()
        self.save(update_fields=['resume', 'resume_updated'])

    def remove_resume(self):
        if self.resume:
            self.resume.delete(save=False)
        self.resume = ''
        self.resume_updated = None
        self.save(update_fields=['resume', 'resume_updated'])

    def is_eligible_for(self, job):
        return job.allows(self.cgpa, self.branch)

    def get_dashboard_summary(self):
        apps_qs = self.applications.all()
        return {
            'applications_total': apps_qs.count(),
            'applied': apps_qs.filter(status='applied').count(),
            'shortlisted': apps_qs.filter(status='shortlisted').count(),
            'rejected': apps_qs.filter(status='rejected').count(),
            'placed': apps_qs.filter(status='placed').count(),
            'unread_notifications': self.notifications.filter(is_read=False).count(),
        }


class PlacementOfficer(User):
    """UML: PlacementOfficer (officer_id, department, phone)."""
    ROLE = User.OFFICER
    EDITABLE_FIELDS = ['name', 'department', 'phone']

    department = models.CharField(max_length=100)
    phone = models.CharField(max_length=10, validators=[phone_validator])

    def get_dashboard_summary(self):
        Company = apps.get_model('placement', 'Company')
        Job = apps.get_model('placement', 'JobPosting')
        Application = apps.get_model('placement', 'Application')
        return {
            'companies': Company.objects.count(),
            'open_jobs': Job.objects.filter(status='open').count(),
            'applications_total': Application.objects.count(),
            'pending_review': Application.objects.filter(status='applied').count(),
            'shortlisted': Application.objects.filter(status='shortlisted').count(),
            'placed': Application.objects.filter(status='placed').count(),
            'open_tasks': self.tasks.exclude(status='completed').count(),
            'unread_notifications': self.notifications.filter(is_read=False).count(),
        }


class Admin(User):
    """UML: Admin (admin_id)."""
    ROLE = User.ADMIN

    def get_dashboard_summary(self):
        Task = apps.get_model('placement', 'Task')
        return {
            'pending_users': User.objects.filter(status=User.PENDING).count(),
            'open_tasks': Task.objects.exclude(status='completed').count(),
            'overdue_tasks': Task.objects.exclude(status='completed').filter(due_date__lt=timezone.localdate()).count(),
            'unread_notifications': self.notifications.filter(is_read=False).count(),
            'students': User.objects.filter(role=User.STUDENT).count(),
            'officers': User.objects.filter(role=User.OFFICER).count(),
            'recent_activity': ActivityLog.objects.count(),
        }


class ActivityLog(models.Model):
    """Used by Admin.monitorActivities() (see sequence diagram)."""
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='activities')
    action = models.CharField(max_length=60)
    details = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    @classmethod
    def record(cls, user, action, details=''):
        return cls.objects.create(user=user, action=action, details=details[:255])
