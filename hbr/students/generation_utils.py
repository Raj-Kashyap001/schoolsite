"""
Student generation utilities for PDFs and certificates
"""

from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.models import User
from .models import Student, Payment, Certificate, CertificateType
from .forms import CertificateRequestForm
from .pdf_utils import generate_certificate_pdf


def prepare_student_profile_data(student, user):
    """Prepare data for student profile PDF generation"""
    user_data = {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.get_full_name(),
        "date_joined": user.date_joined.strftime("%d/%m/%Y"),
    }

    student_data = {
        "admission_no": student.admission_no,
        "roll_no": student.roll_no,
        "father_name": student.father_name,
        "mother_name": student.mother_name,
        "dob": student.dob.strftime("%d/%m/%Y") if student.dob else "",
        "mobile_no": str(student.mobile_no),
        "category": student.category,
        "gender": student.gender,
        "current_address": student.current_address,
        "permanent_address": student.permanent_address,
        "weight": f"{student.weight} kg" if student.weight else "",
        "height": f"{student.height} cm" if student.height else "",
        "classroom": str(student.classroom),
        "stream": str(student.stream) if student.stream else "",
        "subjects": ", ".join([str(s) for s in student.subjects.all()]),
    }

    return student_data, user_data


def generate_profile_pdf_response(student_data, user_data, username):
    """Generate and return profile PDF response"""
    from .pdf_utils import generate_profile_pdf

    buffer = generate_profile_pdf(student_data, user_data, username)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="profile_{username}.pdf"'
    return response


def validate_payment_receipt_download(student, payment_id):
    """Validate payment receipt download permissions"""
    try:
        payment = Payment.objects.get(id=payment_id, student=student)
        if payment.status != "PAID":
            return None
        return payment
    except Payment.DoesNotExist:
        return None


def generate_receipt_pdf_response(payment):
    """Generate and return receipt PDF response"""
    from .pdf_utils import generate_receipt_pdf

    buffer = generate_receipt_pdf(payment)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="receipt_{payment.id}.pdf"'
    return response


def handle_certificate_request_generation(student, certificate):
    """Handle certificate PDF generation for approved certificates"""
    try:
        from django.core.files.base import ContentFile

        buffer = generate_certificate_pdf(student, certificate.certificate_type)
        filename = f"{certificate.certificate_type.name.replace(' ', '_')}_{student.roll_no}.pdf"
        certificate.file.save(filename, ContentFile(buffer.getvalue()))
        certificate.status = "APPROVED"
        certificate.save()
        return True
    except Exception as e:
        print(f"Error generating certificate: {e}")
        return False


def process_certificate_actions(request, student):
    """Process certificate-related POST actions"""
    if "request_certificate" in request.POST:
        form = CertificateRequestForm(request.POST)
        if form.is_valid():
            certificate_type = form.cleaned_data["certificate_type"]
            # Check if certificate already exists
            if not Certificate.objects.filter(
                student=student, certificate_type=certificate_type
            ).exists():
                Certificate.objects.create(
                    student=student,
                    certificate_type=certificate_type,
                    status="PENDING",
                )
                messages.success(
                    request,
                    f"{certificate_type.name} certificate requested successfully.",
                )
            else:
                messages.warning(
                    request,
                    f"{certificate_type.name} certificate already requested.",
                )
        return redirect("students:manage_student_certificates", student_id=student.id)

    elif "approve_certificate" in request.POST:
        certificate_id = request.POST.get("certificate_id")
        try:
            certificate = Certificate.objects.get(id=certificate_id, student=student)
            if handle_certificate_request_generation(student, certificate):
                messages.success(request, "Certificate approved and generated.")
            else:
                messages.error(request, "Error generating certificate.")
        except Certificate.DoesNotExist:
            messages.error(request, "Certificate not found.")
        return redirect("students:manage_student_certificates", student_id=student.id)

    elif "reject_certificate" in request.POST:
        certificate_id = request.POST.get("certificate_id")
        try:
            certificate = Certificate.objects.get(id=certificate_id, student=student)
            certificate.status = "REJECTED"
            certificate.save()
            messages.success(request, "Certificate rejected.")
        except Certificate.DoesNotExist:
            messages.error(request, "Certificate not found.")
        return redirect("students:manage_student_certificates", student_id=student.id)
