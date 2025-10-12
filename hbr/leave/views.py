from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.core.paginator import Paginator
import csv
import io
import json
import pandas as pd
from datetime import date
from base.views import get_user_role
from .models import Leave
from students.models import Student
from teachers.models import Teacher
from notices.models import Notice


@login_required
def leave(request: HttpRequest):
    role = get_user_role(request.user)
    context = {}

    if request.method == "POST":
        action = request.POST.get("action")
        if role == "Student":
            try:
                student = Student.objects.get(user=request.user)
            except Student.DoesNotExist:
                return JsonResponse(
                    {"success": False, "error": "Student profile not found"}
                )

            if action == "create" or not action:
                reason = request.POST.get("reason")
                from_date = request.POST.get("from_date")
                to_date = request.POST.get("to_date")
                if not all([reason, from_date, to_date]):
                    return JsonResponse(
                        {"success": False, "error": "All fields are required"}
                    )
                try:
                    Leave.objects.create(
                        student=student,
                        reason=reason,
                        from_date=from_date,
                        to_date=to_date,
                    )
                    return JsonResponse({"success": True})
                except Exception as e:
                    return JsonResponse(
                        {"success": False, "error": f"Error creating leave: {str(e)}"}
                    )
            elif action == "edit":
                leave_id = request.POST.get("leave_id")
                reason = request.POST.get("reason")
                from_date = request.POST.get("from_date")
                to_date = request.POST.get("to_date")
                if not all([leave_id, reason, from_date, to_date]):
                    return JsonResponse(
                        {"success": False, "error": "All fields are required"}
                    )
                try:
                    leave = Leave.objects.get(
                        id=leave_id, student=student, status="PENDING"
                    )
                    leave.reason = reason
                    leave.from_date = from_date
                    leave.to_date = to_date
                    leave.save()
                    return JsonResponse({"success": True})
                except Leave.DoesNotExist:
                    return JsonResponse(
                        {"success": False, "error": "Leave not found or not editable"}
                    )
                except Exception as e:
                    return JsonResponse(
                        {"success": False, "error": f"Error updating leave: {str(e)}"}
                    )
            elif action == "delete":
                leave_id = request.POST.get("leave_id")
                if not leave_id:
                    return JsonResponse(
                        {"success": False, "error": "Leave ID required"}
                    )
                try:
                    leave = Leave.objects.get(
                        id=leave_id, student=student, status="PENDING"
                    )
                    leave.delete()
                    return JsonResponse({"success": True})
                except Leave.DoesNotExist:
                    return JsonResponse(
                        {"success": False, "error": "Leave not found or not deletable"}
                    )
                except Exception as e:
                    return JsonResponse(
                        {"success": False, "error": f"Error deleting leave: {str(e)}"}
                    )
            else:
                return JsonResponse({"success": False, "error": "Invalid action"})

        elif role == "Teacher":
            try:
                teacher = Teacher.objects.get(user=request.user)
            except Teacher.DoesNotExist:
                return JsonResponse(
                    {"success": False, "error": "Teacher profile not found"}
                )

            if action == "create" or not action:
                reason = request.POST.get("reason")
                from_date = request.POST.get("from_date")
                to_date = request.POST.get("to_date")
                if not all([reason, from_date, to_date]):
                    return JsonResponse(
                        {"success": False, "error": "All fields are required"}
                    )
                try:
                    leave = Leave.objects.create(
                        teacher=teacher,
                        reason=reason,
                        from_date=from_date,
                        to_date=to_date,
                    )
                    # Create system alert for admin
                    Notice.objects.create(
                        title=f"Leave Application: {teacher.user.get_full_name()}",
                        content=f"Teacher {teacher.user.get_full_name()} has applied for leave from {from_date} to {to_date}. Reason: {reason}",
                        notice_type=Notice.NoticeType.SYSTEM_ALERT,
                        created_by=request.user,
                    )
                    return JsonResponse({"success": True})
                except Exception as e:
                    return JsonResponse(
                        {"success": False, "error": f"Error creating leave: {str(e)}"}
                    )
            elif action == "edit":
                leave_id = request.POST.get("leave_id")
                reason = request.POST.get("reason")
                from_date = request.POST.get("from_date")
                to_date = request.POST.get("to_date")
                if not all([leave_id, reason, from_date, to_date]):
                    return JsonResponse(
                        {"success": False, "error": "All fields are required"}
                    )
                try:
                    leave = Leave.objects.get(
                        id=leave_id, teacher=teacher, status="PENDING"
                    )
                    leave.reason = reason
                    leave.from_date = from_date
                    leave.to_date = to_date
                    leave.save()
                    return JsonResponse({"success": True})
                except Leave.DoesNotExist:
                    return JsonResponse(
                        {"success": False, "error": "Leave not found or not editable"}
                    )
                except Exception as e:
                    return JsonResponse(
                        {"success": False, "error": f"Error updating leave: {str(e)}"}
                    )
            elif action == "delete":
                leave_id = request.POST.get("leave_id")
                if not leave_id:
                    return JsonResponse(
                        {"success": False, "error": "Leave ID required"}
                    )
                try:
                    leave = Leave.objects.get(
                        id=leave_id, teacher=teacher, status="PENDING"
                    )
                    leave.delete()
                    return JsonResponse({"success": True})
                except Leave.DoesNotExist:
                    return JsonResponse(
                        {"success": False, "error": "Leave not found or not deletable"}
                    )
                except Exception as e:
                    return JsonResponse(
                        {"success": False, "error": f"Error deleting leave: {str(e)}"}
                    )
            else:
                return JsonResponse({"success": False, "error": "Invalid action"})

        elif role == "Admin":
            if action == "approve":
                leave_id = request.POST.get("leave_id")
                if not leave_id:
                    return JsonResponse(
                        {"success": False, "error": "Leave ID required"}
                    )
                try:
                    leave = Leave.objects.get(id=leave_id, status="PENDING")
                    leave.status = "APPROVED"
                    leave.approved_on = timezone.now()
                    leave.approved_by = request.user
                    leave.save()
                    return JsonResponse({"success": True})
                except Leave.DoesNotExist:
                    return JsonResponse({"success": False, "error": "Leave not found"})
                except Exception as e:
                    return JsonResponse(
                        {"success": False, "error": f"Error approving leave: {str(e)}"}
                    )
            elif action == "reject":
                leave_id = request.POST.get("leave_id")
                if not leave_id:
                    return JsonResponse(
                        {"success": False, "error": "Leave ID required"}
                    )
                try:
                    leave = Leave.objects.get(id=leave_id, status="PENDING")
                    leave.status = "REJECTED"
                    leave.approved_on = timezone.now()
                    leave.approved_by = request.user
                    leave.save()
                    return JsonResponse({"success": True})
                except Leave.DoesNotExist:
                    return JsonResponse({"success": False, "error": "Leave not found"})
                except Exception as e:
                    return JsonResponse(
                        {"success": False, "error": f"Error rejecting leave: {str(e)}"}
                    )
            else:
                return JsonResponse({"success": False, "error": "Invalid action"})
        else:
            return JsonResponse({"success": False, "error": "Invalid role"})

    elif request.method == "GET" and request.GET.get("action") == "get":
        leave_id = request.GET.get("leave_id")
        if not leave_id:
            return JsonResponse({"success": False, "error": "Leave ID required"})

        if role == "Student":
            try:
                student = Student.objects.get(user=request.user)
                leave = Leave.objects.get(id=leave_id, student=student)
            except (Student.DoesNotExist, Leave.DoesNotExist):
                return JsonResponse({"success": False, "error": "Leave not found"})
        elif role == "Teacher":
            try:
                teacher = Teacher.objects.get(user=request.user)
                leave = Leave.objects.get(id=leave_id, teacher=teacher)
            except (Teacher.DoesNotExist, Leave.DoesNotExist):
                return JsonResponse({"success": False, "error": "Leave not found"})
        else:
            return JsonResponse({"success": False, "error": "Access denied"})

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

    # Render template for GET requests
    if role == "Student":
        try:
            student = Student.objects.get(user=request.user)
            leaves = Leave.objects.filter(student=student).order_by("-apply_date")

            # Apply user filters
            user_search = request.GET.get("user_search", "").strip()
            user_status = request.GET.get("user_status", "")

            if user_search:
                leaves = leaves.filter(reason__icontains=user_search)
            if user_status:
                leaves = leaves.filter(status=user_status)

            context["leaves"] = leaves
            context["student"] = student
        except Student.DoesNotExist:
            context["error"] = "Student profile not found"

    elif role == "Teacher":
        try:
            teacher = Teacher.objects.get(user=request.user)
            leaves = Leave.objects.filter(teacher=teacher).order_by("-apply_date")

            # Apply user filters
            user_search = request.GET.get("user_search", "").strip()
            user_status = request.GET.get("user_status", "")

            if user_search:
                leaves = leaves.filter(reason__icontains=user_search)
            if user_status:
                leaves = leaves.filter(status=user_status)

            context["leaves"] = leaves
            context["teacher"] = teacher
        except Teacher.DoesNotExist:
            context["error"] = "Teacher profile not found"

    elif role == "Admin":
        # Get page numbers and filters from request
        teacher_page = request.GET.get("teacher_page", 1)
        student_page = request.GET.get("student_page", 1)
        teacher_search = request.GET.get("teacher_search", "").strip()
        student_search = request.GET.get("student_search", "").strip()
        teacher_status = request.GET.get("teacher_status", "")
        student_status = request.GET.get("student_status", "")

        # Base querysets
        all_teacher_leaves = (
            Leave.objects.filter(teacher__isnull=False)
            .select_related("teacher", "approved_by")
            .order_by("-apply_date")
        )
        all_student_leaves = (
            Leave.objects.filter(student__isnull=False)
            .select_related("student", "approved_by")
            .order_by("-apply_date")
        )

        # Apply teacher filters
        if teacher_search:
            all_teacher_leaves = all_teacher_leaves.filter(
                teacher__user__first_name__icontains=teacher_search
            ) | all_teacher_leaves.filter(
                teacher__user__last_name__icontains=teacher_search
            )
        if teacher_status:
            all_teacher_leaves = all_teacher_leaves.filter(status=teacher_status)

        # Apply student filters
        if student_search:
            all_student_leaves = all_student_leaves.filter(
                student__user__first_name__icontains=student_search
            ) | all_student_leaves.filter(
                student__user__last_name__icontains=student_search
            )
        if student_status:
            all_student_leaves = all_student_leaves.filter(status=student_status)

        # Paginate teacher leaves
        teacher_paginator = Paginator(all_teacher_leaves, 10)  # 10 items per page
        try:
            teacher_leaves_page = teacher_paginator.page(teacher_page)
        except:
            teacher_leaves_page = teacher_paginator.page(1)

        # Paginate student leaves
        student_paginator = Paginator(all_student_leaves, 10)  # 10 items per page
        try:
            student_leaves_page = student_paginator.page(student_page)
        except:
            student_leaves_page = student_paginator.page(1)

        context["all_teacher_leaves"] = teacher_leaves_page
        context["all_student_leaves"] = student_leaves_page
        context["teacher_paginator"] = teacher_paginator
        context["student_paginator"] = student_paginator

    # Render appropriate template based on role
    if role == "Admin":
        template = "dashboard/leave.html"
    else:
        template = "leave/leave.html"

    return render(request, template, context)
