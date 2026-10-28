from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('companies', views.CompanyViewSet, basename='company')
router.register('jobs', views.JobViewSet, basename='job')
router.register('applications', views.ApplicationViewSet, basename='application')
router.register('drives', views.DriveViewSet, basename='drive')
router.register('notifications', views.NotificationViewSet, basename='notification')
router.register('reports', views.ReportViewSet, basename='report')
router.register('tasks', views.TaskViewSet, basename='task')

urlpatterns = [path('placed-students/', views.PlacedStudentsView.as_view())] + router.urls
