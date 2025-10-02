from django.contrib import admin
from .models import (
    AcademicSession,
    Attendance,
    Notice,
    Certificate,
    CertificateType,
    Classroom,
    Document,
    Exam,
    ExamResult,
    ExamSchedule,
    Leave,
    Payment,
    Stream,
    Student,
    Subject,
    Teacher,
    TeacherAttendance,
    Term,
)


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("student", "certificate_type", "status", "issued_date", "file")
    list_filter = ("status", "certificate_type", "issued_date")
    search_fields = ("student__user__username", "certificate_type__name")
    actions = ["approve_certificates", "reject_certificates"]

    def approve_certificates(self, request, queryset):
        from .pdf_utils import generate_certificate_pdf
        from django.core.files.base import ContentFile

        for certificate in queryset.filter(status="PENDING"):
            buffer = generate_certificate_pdf(
                certificate.student, certificate.certificate_type
            )
            filename = f"{certificate.certificate_type.name.replace(' ', '_')}_{certificate.student.roll_no}.pdf"
            certificate.file.save(filename, ContentFile(buffer.getvalue()))
            certificate.status = "APPROVED"
            certificate.save()
        self.message_user(
            request,
            f"{queryset.filter(status='PENDING').count()} certificates approved and generated.",
        )

    def reject_certificates(self, request, queryset):
        updated = queryset.filter(status="PENDING").update(status="REJECTED")
        self.message_user(request, f"{updated} certificates rejected.")

    approve_certificates.short_description = "Approve selected certificates"  # type: ignore
    reject_certificates.short_description = "Reject selected certificates"  # type: ignore


# Register your models here.

admin.site.register(
    [
        AcademicSession,
        Attendance,
        CertificateType,
        Classroom,
        Document,
        Exam,
        ExamResult,
        ExamSchedule,
        Leave,
        Payment,
        Stream,
        Student,
        Subject,
        Teacher,
        TeacherAttendance,
        Term,
        Notice,
    ]
)
