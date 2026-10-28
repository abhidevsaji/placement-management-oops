from django.urls import path

from . import views

urlpatterns = [
    path('auth/register/student/', views.RegisterStudentView.as_view()),
    path('auth/register/officer/', views.RegisterOfficerView.as_view()),
    path('auth/login/', views.LoginView.as_view()),
    path('auth/logout/', views.LogoutView.as_view()),
    path('auth/profile/', views.ProfileView.as_view()),
    path('auth/resume/', views.ResumeView.as_view()),
    path('students/<int:pk>/resume/', views.ResumeDownloadView.as_view()),
    path('dashboard/', views.DashboardView.as_view()),
    path('admin/users/', views.UserListView.as_view()),
    path('admin/users/<int:pk>/', views.UserActionView.as_view()),
    path('admin/users/<int:pk>/<str:action>/', views.UserActionView.as_view()),
    path('admin/activity/', views.ActivityLogView.as_view()),
]
