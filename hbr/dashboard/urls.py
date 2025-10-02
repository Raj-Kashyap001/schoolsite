from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_home, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("attendance/", views.attendance, name="attendance"),
    path("leave/", views.leave, name="leave"),
    path("documents/", views.documents, name="documents"),
    path("certificates/", views.certificates, name="certificates"),
    path("payments/", views.payments, name="payments"),
    path(
        "payments/receipt/<int:payment_id>/",
        views.download_receipt,
        name="download_receipt",
    ),
    path("profile/download/", views.download_profile_pdf, name="download_profile_pdf"),
    path("exams/", views.exams, name="exams"),
    path(
        "exams/timetable/<int:exam_id>/",
        views.get_exam_timetable,
        name="exam_timetable",
    ),
    path(
        "exams/download/<int:exam_id>/",
        views.download_exam_timetable,
        name="download_exam_timetable",
    ),
    path("exams/results/<int:term_id>/", views.get_exam_results, name="exam_results"),
    path("settings/", views.settings, name="settings"),
]
