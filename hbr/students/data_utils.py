"""
Data utilities for student-related operations.
Contains helper functions for data processing, PDF generation, and business logic.
"""

from django.http import HttpResponse
from django.contrib import messages
from .pdf_utils import (
    generate_student_profile_pdf,
    generate_payment_receipt_pdf,
)
from .models import (
    Document,
    CertificateType,
    Certificate,
    Payment,
    Student,
)
from notices.models import Notice


def prepare_student_profile_data(student, user):
    """Prepare data dictionaries for student profile PDF generation."""
    student_data = {
        "sr_no": student.sr_no,
        "roll_no": student.roll_no,
        "admission_no": student.admission_no,
        "father_name": student.father_name,
        "mother_name": student.mother_name,
        "dob": student.dob,
        "mobile_no": student.mobile_no,
        "category": student.category,
        "gender": student.gender,
        "classroom": student.classroom,
        "profile_photo": student.profile_photo,
        "stream": student.stream.name if student.stream else None,
        "subjects": (
            ", ".join([subject.name for subject in student.subjects.all()])
            if student.subjects.exists()
            else None
        ),
        "current_address": student.current_address,
        "permanent_address": student.permanent_address,
        "weight": float(student.weight) if student.weight else None,
        "height": float(student.height) if student.height else None,
    }

    user_data = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "email": user.email,
        "date_joined": user.date_joined,
    }

    return student_data, user_data


def handle_certificate_request(student, request):
    """Handle certificate request submission."""
    certificate_type_id = request.POST.get("certificate_type")
    if certificate_type_id:
        try:
            certificate_type = CertificateType.objects.get(
                id=certificate_type_id, is_active=True
            )
            # Check if certificate already exists (any status)
            if not Certificate.objects.filter(
                student=student, certificate_type=certificate_type
            ).exists():
                certificate = Certificate.objects.create(
                    student=student,
                    certificate_type=certificate_type,
                    status="PENDING",
                )
                # Create system alert for admin
                Notice.objects.create(
                    title=f"Certificate Request: {student.user.get_full_name()} (ID: {student.id})",
                    content=f"Student {student.user.get_full_name()} (Roll: {student.roll_no}, Class: {student.classroom}) has requested a certificate: {certificate_type.name}. <a href='/students/certificates/{certificate.id}/' class='notice-link'>Manage Certificate</a>",
                    notice_type=Notice.NoticeType.SYSTEM_ALERT,
                    created_by=request.user,
                )
                messages.success(
                    request,
                    f"{certificate_type.name} request submitted successfully!",
                )
            else:
                messages.warning(request, f"{certificate_type.name} already requested.")
        except CertificateType.DoesNotExist:
            messages.error(request, "Invalid certificate type.")


def get_student_documents(student):
    """Get documents for a student."""
    return Document.objects.filter(student=student).order_by("-uploaded_at")


def get_student_certificates(student):
    """Get certificate data for a student."""
    all_certificates = Certificate.objects.filter(student=student).order_by(
        "-issued_date"
    )
    issued_certificates = all_certificates.filter(status="PENDING")
    my_certificates = all_certificates.filter(status="APPROVED")
    available_types = (
        CertificateType.objects.filter(is_active=True)
        .exclude(id__in=all_certificates.values_list("certificate_type_id", flat=True))
        .exclude(name__exact="")
    )

    return {
        "issued_certificates": issued_certificates,
        "my_certificates": my_certificates,
        "available_types": available_types,
    }


def get_student_payments(student):
    """Get payments for a student."""
    return Payment.objects.filter(student=student).order_by("-created_at")


def validate_payment_receipt_download(student, payment_id):
    """Validate if student can download payment receipt."""
    try:
        payment = Payment.objects.get(id=payment_id, student=student, status="PAID")
        return payment
    except Payment.DoesNotExist:
        return None


def generate_profile_pdf_response(student_data, user_data, username):
    """Generate and return PDF response for student profile."""
    buffer = generate_student_profile_pdf(student_data, user_data)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{username}_profile.pdf"'
    return response


def generate_receipt_pdf_response(payment):
    """Generate and return PDF response for payment receipt."""
    buffer = generate_payment_receipt_pdf(payment)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="receipt_{payment.id}.pdf"'
    return response
