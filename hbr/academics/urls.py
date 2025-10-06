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
    # Admin exam management
    path(
        "admin/exam-management/",
        views.admin_exam_management,
        name="admin_exam_management",
    ),
    path("admin/create-exam/", views.admin_create_exam, name="admin_create_exam"),
    path(
        "admin/edit-exam/<int:exam_id>/", views.admin_edit_exam, name="admin_edit_exam"
    ),
    path(
        "admin/assign-subjects/",
        views.admin_assign_subjects,
        name="admin_assign_subjects",
    ),
    path(
        "admin/create-assignment/",
        views.admin_create_assignment,
        name="admin_create_assignment",
    ),
    path(
        "admin/delete-assignment/<int:assignment_id>/",
        views.admin_delete_assignment,
        name="admin_delete_assignment",
    ),
    path(
        "admin/marks-entry-control/",
        views.admin_marks_entry_control,
        name="admin_marks_entry_control",
    ),
    path(
        "admin/toggle-marks-entry/<int:exam_id>/",
        views.admin_toggle_marks_entry,
        name="admin_toggle_marks_entry",
    ),
    path(
        "admin/review-results/", views.admin_review_results, name="admin_review_results"
    ),
    path(
        "admin/get-exam-results/<int:exam_id>/",
        views.admin_get_exam_results,
        name="admin_get_exam_results",
    ),
    path(
        "admin/publish-results/<int:exam_id>/",
        views.admin_publish_results,
        name="admin_publish_results",
    ),
    path(
        "admin/delete-exam/<int:exam_id>/",
        views.admin_delete_exam,
        name="admin_delete_exam",
    ),
    # Result Management
    path(
        "result-management/",
        views.result_management,
        name="result_management",
    ),
    path(
        "search-class-results/",
        views.search_class_results,
        name="search_class_results",
    ),
    path(
        "get-class-results/<int:exam_id>/<int:classroom_id>/",
        views.get_class_results,
        name="get_class_results",
    ),
    path(
        "declare-class-results/<int:exam_id>/<int:classroom_id>/",
        views.declare_class_results,
        name="declare_class_results",
    ),
    path(
        "annual-result-sheet/",
        views.annual_result_sheet,
        name="annual_result_sheet",
    ),
    path(
        "generate-annual-result-sheet/<int:classroom_id>/",
        views.generate_annual_result_sheet,
        name="generate_annual_result_sheet",
    ),
]
