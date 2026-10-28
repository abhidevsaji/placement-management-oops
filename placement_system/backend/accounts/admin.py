from django.contrib import admin

from .models import ActivityLog, Admin as AdminUser, PlacementOfficer, Student, User

admin.site.register([User, Student, PlacementOfficer, AdminUser, ActivityLog])
