from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from base.views import get_user_role
from .pdf_utils import generate_student_profile_pdf
from .forms import StudentProfileForm
from .models import Student


@login_required
def dashboard_home(request: HttpRequest):
    user = request.user
    role = get_user_role(user)

    context = {"role": role}
    return render(request, "dashboard/index.html", context)


@login_required
def profile(request: HttpRequest):
    user = request.user
    role = get_user_role(user)

    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        # Handle AJAX photo upload
        if role != "Student":
            return JsonResponse({"success": False, "error": "Access denied"})

        try:
            from .models import Student

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
                            student.profile_photo.url if student.profile_photo else None
                        ),
                    }
                )
            else:
                return JsonResponse({"success": False, "error": "Invalid file"})

        return JsonResponse({"success": False, "error": "No file uploaded"})

    context = {"role": role, "user": user}

    if role == "Student":
        from .models import Student

        try:
            student = Student.objects.get(user=user)
            context["student"] = student
        except Student.DoesNotExist:
            context["student"] = None

    return render(request, "dashboard/profile.html", context)


@login_required
def download_profile_pdf(request: HttpRequest):
    user = request.user
    role = get_user_role(user)

    if role != "Student":
        return HttpResponse("Access denied", status=403)

    try:
        from .models import Student

        student = Student.objects.get(user=user)
    except Student.DoesNotExist:  # type: ignore
        return HttpResponse("Student profile not found", status=404)

    # Prepare data dictionaries
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
    }

    user_data = {
        "first_name": user.first_name,  # pyright: ignore[reportAttributeAccessIssue]
        "last_name": user.last_name,  # pyright: ignore[reportAttributeAccessIssue]
        "username": user.username,
        "email": user.email,  # pyright: ignore[reportAttributeAccessIssue]
        "date_joined": user.date_joined,  # pyright: ignore[reportAttributeAccessIssue]
    }

    # Generate PDF using utility function
    buffer = generate_student_profile_pdf(student_data, user_data)

    # Return PDF response
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{user.username}_profile.pdf"'
    )
    return response


@login_required
def settings(request: HttpRequest):
    user = request.user
    role = get_user_role(user)

    context = {"role": role, "user": user}
    return render(request, "dashboard/settings.html", context)
