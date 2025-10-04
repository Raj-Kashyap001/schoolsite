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
]
