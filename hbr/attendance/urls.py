from django.urls import path
from . import views

app_name = "attendance"

urlpatterns = [
    path("view/", views.attendance, name="attendance"),
    path(
        "mark-student/", views.mark_student_attendance, name="mark_student_attendance"
    ),
    path(
        "mark-teacher/", views.mark_teacher_attendance, name="mark_teacher_attendance"
    ),
    path("template/", views.download_csv_template, name="download_csv_template"),
    path(
        "excel-template/", views.download_excel_template, name="download_excel_template"
    ),
    path("import-csv/", views.import_attendance_csv, name="import_attendance_csv"),
    path(
        "import-excel/", views.import_attendance_excel, name="import_attendance_excel"
    ),
    path("export-csv/", views.export_attendance_csv, name="export_attendance_csv"),
    path(
        "export-excel/", views.export_attendance_excel, name="export_attendance_excel"
    ),
    path("export-json/", views.export_attendance_json, name="export_attendance_json"),
    path(
        "import-teacher-csv/",
        views.import_teacher_attendance_csv,
        name="import_teacher_attendance_csv",
    ),
    path(
        "import-teacher-excel/",
        views.import_teacher_attendance_excel,
        name="import_teacher_attendance_excel",
    ),
    path(
        "export-teacher-csv/",
        views.export_teacher_attendance_csv,
        name="export_teacher_attendance_csv",
    ),
    path(
        "export-teacher-excel/",
        views.export_teacher_attendance_excel,
        name="export_teacher_attendance_excel",
    ),
    path(
        "export-teacher-json/",
        views.export_teacher_attendance_json,
        name="export_teacher_attendance_json",
    ),
    path(
        "teacher-template/",
        views.download_teacher_template,
        name="download_teacher_template",
    ),
    path(
        "teacher-excel-template/",
        views.download_teacher_excel_template,
        name="download_teacher_excel_template",
    ),
]
