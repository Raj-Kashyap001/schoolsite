from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from base.views import get_user_role
from .forms import StudentProfileForm
from .models import Student
from .data_utils import (
    prepare_student_profile_data,
    handle_certificate_request,
    get_student_documents,
    get_student_certificates,
    get_student_payments,
    validate_payment_receipt_download,
    generate_profile_pdf_response,
    generate_receipt_pdf_response,
)


@login_required
def profile(request: HttpRequest):
    user = request.user
    role = get_user_role(user)

    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        # Handle AJAX photo upload
        if role not in ["Student", "Teacher"]:
            return JsonResponse({"success": False, "error": "Access denied"})

        if role == "Student":
            try:
                student = Student.objects.get(user=user)
            except Student.DoesNotExist:  # type: ignore
                return JsonResponse(
                    {"success": False, "error": "Student profile not found"}
                )

            if "profile_photo" in request.FILES:
                # Delete old image if it exists
                if student.profile_photo:
                    import os
                    from django.conf import settings

                    old_image_path = os.path.join(
                        settings.MEDIA_ROOT, str(student.profile_photo)
                    )
                    if os.path.exists(old_image_path):
                        try:
                            os.remove(old_image_path)
                        except OSError:
                            pass  # Ignore if file doesn't exist or can't be deleted

                form = StudentProfileForm(request.POST, request.FILES, instance=student)
                if form.is_valid():
                    form.save()
                    return JsonResponse(
                        {
                            "success": True,
                            "photo_url": (
                                student.profile_photo.url
                                if student.profile_photo
                                else None
                            ),
                        }
                    )
                else:
                    return JsonResponse({"success": False, "error": "Invalid file"})

        return JsonResponse({"success": False, "error": "Invalid request"})

    context = {"user": user}

    if role == "Student":
        try:
            student = Student.objects.get(user=user)
            context["student"] = student
        except Student.DoesNotExist:
            context["student"] = None

    return render(request, "students/profile.html", context)


@login_required
def documents(request: HttpRequest):
    role = get_user_role(request.user)
    context = {}

    if role == "Student":
        try:
            student = Student.objects.get(user=request.user)
            context["documents"] = get_student_documents(student)
            context["student"] = student
        except Student.DoesNotExist:
            context["error"] = "Student profile not found"

    return render(request, "students/documents.html", context)


@login_required
def certificates(request: HttpRequest):
    role = get_user_role(request.user)
    context = {}

    if role == "Student":
        try:
            student = Student.objects.get(user=request.user)
            if request.method == "POST":
                handle_certificate_request(student, request)

            cert_data = get_student_certificates(student)
            context.update(cert_data)
            context["student"] = student
        except Student.DoesNotExist:
            context["error"] = "Student profile not found"

    return render(request, "students/certificates.html", context)


@login_required
def payments(request: HttpRequest):
    role = get_user_role(request.user)
    context = {}

    if role == "Student":
        try:
            student = Student.objects.get(user=request.user)
            context["payments"] = get_student_payments(student)
            context["student"] = student
        except Student.DoesNotExist:
            context["error"] = "Student profile not found"

    return render(request, "students/payments.html", context)


@login_required
def download_receipt(request: HttpRequest, payment_id: int):
    role = get_user_role(request.user)

    if role != "Student":
        return HttpResponse("Access denied", status=403)

    try:
        student = Student.objects.get(user=request.user)
        payment = validate_payment_receipt_download(student, payment_id)
        if not payment:
            return HttpResponse("Payment not found or not paid", status=404)
    except Student.DoesNotExist:
        return HttpResponse("Student profile not found", status=404)

    return generate_receipt_pdf_response(payment)


@login_required
def download_profile_pdf(request: HttpRequest):
    role = get_user_role(request.user)

    if role != "Student":
        return HttpResponse("Access denied", status=403)

    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return HttpResponse("Student profile not found", status=404)

    student_data, user_data = prepare_student_profile_data(student, request.user)
    return generate_profile_pdf_response(student_data, user_data, request.user.username)
