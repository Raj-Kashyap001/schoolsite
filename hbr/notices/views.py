from django.http import HttpRequest, HttpResponse
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
            # Get all active notices that are either announcements or targeted to this student
            notices = (
                Notice.objects.filter(is_active=True)
                .filter(
                    Q(notice_type=Notice.NoticeType.ANNOUNCEMENT)
                    | Q(
                        notice_type=Notice.NoticeType.INDIVIDUAL,
                        target_students=student,
                    )
                )
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
            # Teachers see all active announcements
            notices = Notice.objects.filter(
                is_active=True, notice_type=Notice.NoticeType.ANNOUNCEMENT
            ).order_by("-created_at")
            context["notices"] = notices  # type: ignore
            context["teacher"] = teacher  # type: ignore
        except Teacher.DoesNotExist:
            context["error"] = "Teacher profile not found"

    elif role == "Admin":
        # Admins see all notices
        notices = Notice.objects.all().order_by("-created_at")
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

        # Return the file
        response = HttpResponse(
            notice.attachment, content_type="application/octet-stream"
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
                messages.success(request, "Notice created successfully.")
                return redirect("notices:notice_board")
    else:
        form = NoticeForm()

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
