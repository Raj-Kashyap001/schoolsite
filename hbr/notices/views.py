from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db.models import Q
import csv
import io
import json
import pandas as pd
from datetime import date
from base.views import get_user_role
from .models import Notice
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
        # Admins see all active notices
        notices = Notice.objects.filter(is_active=True).order_by("-created_at")
        context["notices"] = notices  # type: ignore

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
