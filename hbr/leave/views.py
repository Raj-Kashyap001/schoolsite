from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import csv
import io
import json
import pandas as pd
from datetime import date
from base.views import get_user_role
from .models import Leave
from students.models import Student
from teachers.models import Teacher


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
                    Leave.objects.create(
                        teacher=teacher,
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
            context["leaves"] = leaves
            context["student"] = student
        except Student.DoesNotExist:
            context["error"] = "Student profile not found"

    elif role == "Teacher":
        try:
            teacher = Teacher.objects.get(user=request.user)
            leaves = Leave.objects.filter(teacher=teacher).order_by("-apply_date")
            context["leaves"] = leaves
            context["teacher"] = teacher
        except Teacher.DoesNotExist:
            context["error"] = "Teacher profile not found"

    elif role == "Admin":
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
        context["all_teacher_leaves"] = all_teacher_leaves
        context["all_student_leaves"] = all_student_leaves

    return render(request, "leave/leave.html", context)
