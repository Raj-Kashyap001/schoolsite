from django.urls import path
from . import views

app_name = "students"

urlpatterns = [
    path("profile/", views.profile, name="profile"),
    path("documents/", views.documents, name="documents"),
    path("certificates/", views.certificates, name="certificates"),
    path("payments/", views.payments, name="payments"),
    path(
        "download-receipt/<int:payment_id>/",
        views.download_receipt,
        name="download_receipt",
    ),
    path(
        "download-profile-pdf/", views.download_profile_pdf, name="download_profile_pdf"
    ),
    # Class Management URLs (Admin only)
    path("class-management/", views.class_management, name="class_management"),
    path(
        "manage-class/<int:classroom_id>/students/",
        views.manage_class_students,
        name="manage_class_students",
    ),
    path(
        "manage-class/<int:classroom_id>/timetables/",
        views.manage_timetables,
        name="manage_timetables",
    ),
    path(
        "manage-class/<int:classroom_id>/notifications/",
        views.manage_teacher_notifications,
        name="manage_teacher_notifications",
    ),
    # Student Management URLs (Admin only)
    path("management/", views.student_management, name="student_management"),
    path("add/", views.add_student, name="add_student"),
    path("edit/<int:student_id>/", views.edit_student, name="edit_student"),
    path("delete/<int:student_id>/", views.delete_student, name="delete_student"),
    # Bulk operations
    path("export/", views.export_students, name="export_students"),
    path("import/", views.import_students, name="import_students"),
    path(
        "documents/<int:student_id>/",
        views.manage_student_documents,
        name="manage_student_documents",
    ),
    path(
        "payments/<int:student_id>/",
        views.manage_student_payments,
        name="manage_student_payments",
    ),
    path(
        "certificates/<int:student_id>/",
        views.manage_student_certificates,
        name="manage_student_certificates",
    ),
]
