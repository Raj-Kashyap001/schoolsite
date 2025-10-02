from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from base.views import get_user_role
from .pdf_utils import generate_student_profile_pdf
from .forms import StudentProfileForm
from .models import Attendance, Document, Leave, Student, CertificateType, Certificate


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
        from .models import Student, Attendance

        try:
            student = Student.objects.get(user=user)
            context["student"] = student
        except Student.DoesNotExist:
            context["student"] = None

    return render(request, "dashboard/profile.html", context)


@login_required
def attendance(request: HttpRequest):
    role = get_user_role(request.user)
    context = {"role": role, "attendance_events": []}

    if role == "Student":
        try:
            student = Student.objects.get(user=request.user)
            attendances = Attendance.objects.filter(student=student).order_by("date")

            # Prepare events for fullcalendar
            events = []
            for att in attendances:
                color = {
                    "PRESENT": "#28a745",  # green
                    "ABSENT": "#dc3545",  # red
                    "LATE": "#ffc107",  # yellow
                }.get(
                    att.status, "#6c757d"
                )  # default gray

                events.append(
                    {
                        "title": att.status,
                        "start": att.date.isoformat(),
                        "color": color,
                        "extendedProps": {
                            "remarks": att.remarks,
                            "teacher": str(att.teacher),
                        },
                    }
                )

            context["attendance_events"] = events  # type: ignore
            context["student"] = student  # type: ignore
        except Student.DoesNotExist:
            context["error"] = "Student profile not found"

    return render(request, "dashboard/attendance.html", context)


@login_required
def leave(request: HttpRequest):
    role = get_user_role(request.user)
    context = {"role": role}

    if role == "Student":
        try:
            student = Student.objects.get(user=request.user)
            if request.method == "GET" and request.GET.get("action") == "get":
                leave_id = request.GET.get("leave_id")
                try:
                    leave = Leave.objects.get(id=leave_id, student=student)
                    return JsonResponse(
                        {
                            "success": True,
                            "leave": {
                                "reason": leave.reason,
                                "from_date": leave.from_date.isoformat(),
                                "to_date": leave.to_date.isoformat(),
                            },
                        }
                    )
                except Leave.DoesNotExist:
                    return JsonResponse({"success": False, "error": "Leave not found"})

            if request.method == "POST":
                action = request.POST.get("action")
                if action == "create":
                    reason = request.POST.get("reason")
                    from_date = request.POST.get("from_date")
                    to_date = request.POST.get("to_date")
                    if reason and from_date and to_date:
                        Leave.objects.create(
                            student=student,
                            reason=reason,
                            from_date=from_date,
                            to_date=to_date,
                        )
                        return JsonResponse({"success": True})
                    else:
                        return JsonResponse(
                            {"success": False, "error": "All fields are required"}
                        )
                elif action == "edit":
                    leave_id = request.POST.get("leave_id")
                    reason = request.POST.get("reason")
                    from_date = request.POST.get("from_date")
                    to_date = request.POST.get("to_date")
                    try:
                        leave = Leave.objects.get(
                            id=leave_id, student=student, status="PENDING"
                        )
                        leave.reason = reason  # type: ignore
                        leave.from_date = from_date  # type: ignore
                        leave.to_date = to_date  # type: ignore
                        leave.save()
                        return JsonResponse({"success": True})
                    except Leave.DoesNotExist:
                        return JsonResponse(
                            {
                                "success": False,
                                "error": "Leave request not found or not editable",
                            }
                        )
                elif action == "delete":
                    leave_id = request.POST.get("leave_id")
                    try:
                        leave = Leave.objects.get(
                            id=leave_id, student=student, status="PENDING"
                        )
                        leave.delete()
                        return JsonResponse({"success": True})
                    except Leave.DoesNotExist:
                        return JsonResponse(
                            {
                                "success": False,
                                "error": "Leave request not found or not deletable",
                            }
                        )

            leaves = Leave.objects.filter(student=student).order_by("-apply_date")
            context["leaves"] = leaves  # type: ignore
            context["student"] = student  # type: ignore
        except Student.DoesNotExist:
            context["error"] = "Student profile not found"

    return render(request, "dashboard/leave.html", context)


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
def documents(request: HttpRequest):
    role = get_user_role(request.user)
    context = {"role": role}

    if role == "Student":
        try:
            student = Student.objects.get(user=request.user)
            documents = Document.objects.filter(student=student).order_by(
                "-uploaded_at"
            )
            context["documents"] = documents  # type: ignore
            context["student"] = student  # type: ignore
        except Student.DoesNotExist:
            context["error"] = "Student profile not found"

    return render(request, "dashboard/documents.html", context)


@login_required
def certificates(request: HttpRequest):
    role = get_user_role(request.user)
    context = {"role": role}

    if role == "Student":
        try:
            student = Student.objects.get(user=request.user)
            if request.method == "POST":
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
                            Certificate.objects.create(
                                student=student,
                                certificate_type=certificate_type,
                                status="PENDING",
                            )
                            messages.success(
                                request,
                                f"{certificate_type.name} request submitted successfully!",
                            )
                        else:
                            messages.warning(
                                request, f"{certificate_type.name} already requested."
                            )
                    except CertificateType.DoesNotExist:
                        messages.error(request, "Invalid certificate type.")

            all_certificates = Certificate.objects.filter(student=student).order_by(
                "-issued_date"
            )
            issued_certificates = all_certificates.filter(status="PENDING")
            my_certificates = all_certificates.filter(status="APPROVED")
            available_types = CertificateType.objects.filter(is_active=True).exclude(
                id__in=all_certificates.values_list("certificate_type_id", flat=True)
            )
            context["issued_certificates"] = issued_certificates  # type: ignore
            context["my_certificates"] = my_certificates  # type: ignore
            context["available_types"] = available_types  # type: ignore
            context["student"] = student  # type: ignore
        except Student.DoesNotExist:
            context["error"] = "Student profile not found"

    return render(request, "dashboard/certificates.html", context)


@login_required
def settings(request: HttpRequest):
    user = request.user
    role = get_user_role(user)

    context = {"role": role, "user": user}
    return render(request, "dashboard/settings.html", context)
