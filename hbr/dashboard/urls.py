from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_home, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("attendance/", views.attendance, name="attendance"),
    path("leave/", views.leave, name="leave"),
    path("documents/", views.documents, name="documents"),
    path("certificates/", views.certificates, name="certificates"),
    path("profile/download/", views.download_profile_pdf, name="download_profile_pdf"),
    path("settings/", views.settings, name="settings"),
]
