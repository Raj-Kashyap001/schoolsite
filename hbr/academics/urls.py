from django.urls import path
from . import views

app_name = "academics"

urlpatterns = [
    path("exams/", views.exams, name="exams"),
    path(
        "exam-timetable/<int:exam_id>/",
        views.get_exam_timetable,
        name="get_exam_timetable",
    ),
    path(
        "download-timetable/<int:exam_id>/",
        views.download_exam_timetable,
        name="download_exam_timetable",
    ),
    path(
        "download-admit-card/<int:exam_id>/",
        views.download_admit_card,
        name="download_admit_card",
    ),
    path(
        "exam-results/<int:term_id>/", views.get_exam_results, name="get_exam_results"
    ),
    # Teacher exam marking
    path("teacher/marking/", views.teacher_exam_marking, name="teacher_exam_marking"),
    path(
        "teacher/select-exam/<int:classroom_id>/",
        views.teacher_select_exam,
        name="teacher_select_exam",
    ),
    path(
        "teacher/mark-exam/<int:exam_id>/<int:classroom_id>/",
        views.teacher_mark_exam,
        name="teacher_mark_exam",
    ),
    path(
        "teacher/save-results/<int:exam_id>/<int:classroom_id>/",
        views.save_exam_results,
        name="save_exam_results",
    ),
    path(
        "teacher/bulk-import/<int:exam_id>/<int:classroom_id>/",
        views.bulk_import_results,
        name="bulk_import_results",
    ),
    path(
        "teacher/export-results/<int:exam_id>/<int:classroom_id>/",
        views.export_results,
        name="export_results",
    ),
    path(
        "teacher/download-template/<int:exam_id>/<int:classroom_id>/",
        views.download_import_template,
        name="download_import_template",
    ),
]
