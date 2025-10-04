from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_home, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("attendance/", views.attendance, name="attendance"),
    path(
        "mark-student-attendance/",
        views.mark_student_attendance,
        name="mark_student_attendance",
    ),
    path(
        "attendance/import-csv/",
        views.import_attendance_csv,
        name="import_attendance_csv",
    ),
    path(
        "attendance/export-csv/",
        views.export_attendance_csv,
        name="export_attendance_csv",
    ),
    path(
        "attendance/template/",
        views.download_attendance_template,
        name="download_attendance_template",
    ),
    path(
        "attendance/import-excel/",
        views.import_attendance_excel,
        name="import_attendance_excel",
    ),
    path(
        "attendance/export-excel/",
        views.export_attendance_excel,
        name="export_attendance_excel",
    ),
    path(
        "attendance/excel-template/",
        views.download_attendance_excel_template,
        name="download_attendance_excel_template",
    ),
    path(
        "attendance/export-json/",
        views.export_attendance_json,
        name="export_attendance_json",
    ),
    path(
        "mark-teacher-attendance/",
        views.mark_teacher_attendance,
        name="mark_teacher_attendance",
    ),
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
    path(
        "exams/admit-card/<int:exam_id>/",
        views.download_admit_card,
        name="download_admit_card",
    ),
    path("exams/results/<int:term_id>/", views.get_exam_results, name="exam_results"),
    path("mark-exam-results/", views.mark_exam_results, name="mark_exam_results"),
    path("notice-board/", views.notice_board, name="notice_board"),
    path(
        "notice-board/download/<int:notice_id>/",
        views.download_notice_attachment,
        name="download_notice_attachment",
    ),
]
