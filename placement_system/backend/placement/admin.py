from django.contrib import admin

from .models import Application, Company, JobPosting, Notification, PlacementDrive, Report, Result, Task

admin.site.register([Company, JobPosting, Application, Result, PlacementDrive, Report, Notification, Task])
