from django.http import HttpRequest, HttpResponse, FileResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from base.views import get_user_role
from .models import Notice
from .forms import NoticeForm
from students.models import Student
from teachers.models import Teacher


@login_required
def notice_board(request: HttpRequest):
    role = get_user_role(request.user)
    context = {}

    if role == "Student":
        try:
            student = Student.objects.get(user=request.user)
            # Get all active notices that are targeted to this student
            notices = (
                Notice.objects.filter(is_active=True)
                .filter(
                    Q(notice_type=Notice.NoticeType.PUBLIC)
                    | Q(notice_type=Notice.NoticeType.ALL_STUDENTS)
                    | Q(
                        notice_type=Notice.NoticeType.CLASS_STUDENTS,
                        target_class=student.classroom,
                    )
                    | Q(
                        notice_type=Notice.NoticeType.INDIVIDUAL_STUDENT,
                        target_students=student,
                    )
                )
                .exclude(dismissed_by=request.user)
                .order_by("-created_at")
                .distinct()
            )
            context["notices"] = notices  # type: ignore
            context["student"] = student  # type: ignore
        except Student.DoesNotExist:
            context["error"] = "Student profile not found"

    elif role == "Teacher":
        try:
            teacher = Teacher.objects.get(user=request.user)
            # Teachers see notices targeted to them
            notices = (
                Notice.objects.filter(is_active=True)
                .filter(
                    Q(notice_type=Notice.NoticeType.PUBLIC)
                    | Q(notice_type=Notice.NoticeType.ALL_TEACHERS)
                    | Q(
                        notice_type=Notice.NoticeType.INDIVIDUAL_TEACHER,
                        target_teachers=teacher,
                    )
                )
                .exclude(dismissed_by=request.user)
                .order_by("-created_at")
            )
            context["notices"] = notices  # type: ignore
            context["teacher"] = teacher  # type: ignore
        except Teacher.DoesNotExist:
            context["error"] = "Teacher profile not found"

    elif role == "Admin":
        # Admins see all notices except system alerts
        notices = Notice.objects.exclude(
            notice_type=Notice.NoticeType.SYSTEM_ALERT
        ).order_by("-created_at")
        context["notices"] = notices  # type: ignore
        context["role"] = role  # type: ignore
        context["form"] = NoticeForm()  # type: ignore

    context["role"] = role  # type: ignore
    return render(request, "notices/notice_board.html", context)


@login_required
def download_notice_attachment(request: HttpRequest, notice_id: int):
    role = get_user_role(request.user)
    if role not in ["Student", "Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    try:
        notice = Notice.objects.get(id=notice_id, is_active=True)
        if not notice.attachment:
            return HttpResponse("No attachment found", status=404)

        # Return the file using FileResponse for proper file serving
        response = FileResponse(
            notice.attachment.open("rb"), content_type="application/octet-stream"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{notice.attachment.name.split("/")[-1]}"'
        )
        return response
    except Notice.DoesNotExist:
        return HttpResponse("Notice not found", status=404)


@login_required
def create_notice(request: HttpRequest):
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        notice_id = request.POST.get("notice_id")
        if notice_id:
            # Update existing notice
            try:
                notice = Notice.objects.get(id=notice_id)
                form = NoticeForm(request.POST, request.FILES, instance=notice)
                if form.is_valid():
                    updated_notice = form.save(commit=False)
                    # Handle attachment clearing
                    if request.POST.get("clear_attachment") == "true":
                        updated_notice.attachment = None
                    updated_notice.save()
                    form.save_m2m()
                    messages.success(request, "Notice updated successfully.")
                    return redirect("notices:notice_board")
            except Notice.DoesNotExist:
                messages.error(request, "Notice not found.")
                return redirect("notices:notice_board")
        else:
            # Create new notice
            form = NoticeForm(request.POST, request.FILES)
            if form.is_valid():
                notice = form.save(commit=False)
                notice.created_by = request.user
                notice.save()
                form.save_m2m()
                messages.success(request, "Notice created successfully.")
                return redirect("notices:notice_board")
    else:
        form = NoticeForm(user=request.user)

    context = {"form": form, "role": role}
    return render(request, "notices/notice_board.html", context)


@login_required
def bulk_delete_notices(request: HttpRequest):
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        notice_ids = request.POST.getlist("notice_ids")
        if notice_ids:
            Notice.objects.filter(id__in=notice_ids).delete()
            messages.success(request, f"Deleted {len(notice_ids)} notice(s).")
        return redirect("notices:notice_board")

    return HttpResponse("Invalid request", status=400)


@login_required
def search_students(request: HttpRequest):
    """API endpoint for searching students"""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"students": []})

    # Search students by name, roll number, or class
    students = Student.objects.select_related("classroom", "user").filter(
        Q(user__first_name__icontains=query)
        | Q(user__last_name__icontains=query)
        | Q(roll_no__icontains=query)
        | Q(classroom__grade__icontains=query)
        | Q(classroom__section__icontains=query)
    )[
        :20
    ]  # Limit results

    students_data = []
    for student in students:
        students_data.append(
            {
                "id": student.id,
                "name": student.user.get_full_name(),
                "roll_no": student.roll_no,
                "classroom": str(student.classroom),
                "display": f"{student.user.get_full_name()} (Roll: {student.roll_no}, Class: {student.classroom})",
            }
        )

    return JsonResponse({"students": students_data})


@login_required
def bulk_disable_notices(request: HttpRequest):
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        notice_ids = request.POST.getlist("notice_ids")
        if notice_ids:
            Notice.objects.filter(id__in=notice_ids).update(is_active=False)
            messages.success(request, f"Disabled {len(notice_ids)} notice(s).")
        return redirect("notices:notice_board")

    return HttpResponse("Invalid request", status=400)


@login_required
def bulk_enable_notices(request: HttpRequest):
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        notice_ids = request.POST.getlist("notice_ids")
        if notice_ids:
            Notice.objects.filter(id__in=notice_ids).update(is_active=True)
            messages.success(request, f"Enabled {len(notice_ids)} notice(s).")
        return redirect("notices:notice_board")

    return HttpResponse("Invalid request", status=400)


@login_required
def dismiss_notice(request: HttpRequest, notice_id: int):
    """AJAX endpoint to dismiss a notice for the current user"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        notice = Notice.objects.get(id=notice_id, is_active=True)
        # Check if user can see this notice
        role = get_user_role(request.user)
        can_dismiss = False
        if role == "Student":
            student = Student.objects.get(user=request.user)
            can_dismiss = notice.target_students.filter(id=student.id).exists()
        elif role == "Teacher":
            teacher = Teacher.objects.get(user=request.user)
            can_dismiss = notice.target_teachers.filter(id=teacher.id).exists()
        elif role == "Admin":
            can_dismiss = True

        if can_dismiss:
            notice.dismissed_by.add(request.user)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"error": "Cannot dismiss this notice"}, status=403)
    except Notice.DoesNotExist:
        return JsonResponse({"error": "Notice not found"}, status=404)
    except Student.DoesNotExist:
        return JsonResponse({"error": "Student profile not found"}, status=404)
    except Teacher.DoesNotExist:
        return JsonResponse({"error": "Teacher profile not found"}, status=404)
