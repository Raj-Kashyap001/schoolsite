from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.contrib.auth.models import User

import pandas as pd
from datetime import date
from base.views import get_user_role
from students.models import Classroom
from .models import Teacher, TeacherSalary
from .forms import (
    TeacherUserCreationForm,
    TeacherProfileForm,
    TeacherEditForm,
    TeacherSalaryForm,
)


@login_required
def profile(request: HttpRequest):
    user = request.user
    role = get_user_role(user)

    # Check if admin is viewing a specific teacher's profile
    teacher_id = request.GET.get("teacher_id")
    if teacher_id and role == "Admin":
        try:
            teacher = Teacher.objects.get(id=teacher_id)
            view_user = teacher.user
            view_role = "Teacher"
            is_admin_viewing = True
        except Teacher.DoesNotExist:
            return HttpResponse("Teacher not found", status=404)
    else:
        view_user = user
        view_role = role
        is_admin_viewing = False

    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        # Handle AJAX photo upload
        if view_role not in ["Student", "Teacher"]:
            return JsonResponse({"success": False, "error": "Access denied"})

        if view_role == "Teacher":
            try:
                teacher = Teacher.objects.get(user=view_user)
            except Teacher.DoesNotExist:  # type: ignore
                return JsonResponse(
                    {"success": False, "error": "Teacher profile not found"}
                )

            if "profile_photo" in request.FILES:
                # Delete old image if it exists
                if teacher.profile_photo:
                    import os
                    from django.conf import settings

                    old_image_path = os.path.join(
                        settings.MEDIA_ROOT, str(teacher.profile_photo)
                    )
                    if os.path.exists(old_image_path):
                        try:
                            os.remove(old_image_path)
                        except OSError:
                            pass  # Ignore if file doesn't exist or can't be deleted

                # Simple file handling for teacher profile photo
                teacher.profile_photo = request.FILES["profile_photo"]
                teacher.save()
                return JsonResponse(
                    {
                        "success": True,
                        "photo_url": (
                            teacher.profile_photo.url if teacher.profile_photo else None
                        ),
                    }
                )
            else:
                return JsonResponse({"success": False, "error": "No file uploaded"})

        return JsonResponse({"success": False, "error": "Invalid request"})

    context = {
        "role": role,
        "view_role": view_role,
        "user": view_user,
        "is_admin_viewing": is_admin_viewing,
    }

    if view_role == "Teacher":
        try:
            teacher = Teacher.objects.get(user=view_user)
            context["teacher"] = teacher
        except Teacher.DoesNotExist:
            context["teacher"] = None

    return render(request, "teachers/profile.html", context)


@login_required
def salary(request: HttpRequest):
    """View for teacher to see their salary records"""
    user = request.user
    role = get_user_role(user)

    if role != "Teacher":
        return HttpResponse("Unauthorized", status=403)

    teacher = get_object_or_404(Teacher, user=user)
    salaries = TeacherSalary.objects.filter(teacher=teacher).order_by("-payment_date")

    context = {
        "salaries": salaries,
    }
    return render(request, "teachers/salary.html", context)


@login_required
def teacher_management(request: HttpRequest):
    """Admin view for managing teachers"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    teachers = Teacher.objects.select_related("user").all().order_by("user__first_name")
    context = {
        "teachers": teachers,
        "role": role,
    }
    return render(request, "teachers/teacher_management.html", context)


@login_required
def add_teacher(request: HttpRequest):
    """Admin view for adding a new teacher"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        user_form = TeacherUserCreationForm(request.POST)
        profile_form = TeacherProfileForm(request.POST, request.FILES)

        if user_form.is_valid() and profile_form.is_valid():
            # Create the user
            user = user_form.save()

            # Assign user to Teacher group
            from django.contrib.auth.models import Group

            teacher_group, created = Group.objects.get_or_create(name="Teacher")
            user.groups.add(teacher_group)

            # Create the teacher profile
            teacher = profile_form.save(commit=False)
            teacher.user = user

            # Store plain text password for admin reference
            teacher.plain_text_password = user_form.cleaned_data.get("password1", "")

            teacher.save()

            # Handle class teacher assignment
            if profile_form.cleaned_data.get(
                "is_class_teacher"
            ) and profile_form.cleaned_data.get("class_teacher_class"):
                classroom = profile_form.cleaned_data["class_teacher_class"]
                classroom.class_teacher = teacher
                classroom.save()

            # Handle classroom assignments for teaching
            if profile_form.cleaned_data.get("classroom"):
                teacher.classroom.set(profile_form.cleaned_data["classroom"])

            messages.success(
                request, f"Teacher {user.get_full_name()} added successfully."
            )
            return redirect("teachers:teacher_management")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = TeacherUserCreationForm()
        profile_form = TeacherProfileForm()

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "role": role,
    }
    return render(request, "teachers/add_teacher.html", context)


@login_required
def edit_teacher(request: HttpRequest, teacher_id: int):
    """Admin view for editing a teacher"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    teacher = get_object_or_404(Teacher, id=teacher_id)

    if request.method == "POST":
        form = TeacherEditForm(request.POST, request.FILES, instance=teacher)

        if form.is_valid():
            # Update user fields
            teacher.user.first_name = form.cleaned_data["first_name"]
            teacher.user.last_name = form.cleaned_data["last_name"]
            teacher.user.email = form.cleaned_data["email"]
            teacher.user.save()

            # Update teacher fields
            form.save()

            # Handle class teacher assignment changes
            is_class_teacher = form.cleaned_data.get("is_class_teacher", False)
            class_teacher_class = form.cleaned_data.get("class_teacher_class")

            # Remove current class teacher assignment if exists
            try:
                current_class = Classroom.objects.get(class_teacher=teacher)
                current_class.class_teacher = None
                current_class.save()
            except Classroom.DoesNotExist:
                pass

            # Assign new class teacher if selected
            if is_class_teacher and class_teacher_class:
                # Make sure the class doesn't already have a class teacher
                if (
                    class_teacher_class.class_teacher is None
                    or class_teacher_class.class_teacher == teacher
                ):
                    class_teacher_class.class_teacher = teacher
                    class_teacher_class.save()
                else:
                    messages.warning(
                        request,
                        f"Class {class_teacher_class} already has a class teacher.",
                    )

            # Handle classroom assignments for teaching
            if form.cleaned_data.get("classroom"):
                teacher.classroom.set(form.cleaned_data["classroom"])
            else:
                teacher.classroom.clear()

            messages.success(
                request, f"Teacher {teacher.user.get_full_name()} updated successfully."
            )
            return redirect("teachers:teacher_management")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TeacherEditForm(instance=teacher)

    context = {
        "form": form,
        "teacher": teacher,
        "role": role,
    }
    return render(request, "teachers/edit_teacher.html", context)


@login_required
def delete_teacher(request: HttpRequest, teacher_id: int):
    """Admin view for deleting a teacher"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    teacher = get_object_or_404(Teacher, id=teacher_id)

    if request.method == "POST":
        user = teacher.user
        # Remove class teacher assignment if exists
        try:
            classroom = Classroom.objects.get(class_teacher=teacher)
            classroom.class_teacher = None
            classroom.save()
        except Classroom.DoesNotExist:
            pass

        teacher.delete()
        user.delete()  # Also delete the user account
        messages.success(
            request, f"Teacher {user.get_full_name()} deleted successfully."
        )
        return redirect("teachers:teacher_management")

    context = {
        "teacher": teacher,
        "role": role,
    }
    return render(request, "teachers/delete_teacher.html", context)


@login_required
def manage_salary(request: HttpRequest, teacher_id: int):
    """Admin view for managing teacher salary records"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    teacher = get_object_or_404(Teacher, id=teacher_id)

    if request.method == "POST":
        form = TeacherSalaryForm(request.POST, request.FILES)
        if form.is_valid():
            salary = form.save(commit=False)
            salary.teacher = teacher
            salary.save()
            messages.success(request, "Salary record added successfully.")
            return redirect("teachers:manage_salary", teacher_id=teacher.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TeacherSalaryForm()

    salaries = TeacherSalary.objects.filter(teacher=teacher).order_by("-payment_date")

    context = {
        "teacher": teacher,
        "form": form,
        "salaries": salaries,
        "role": role,
    }
    return render(request, "teachers/manage_salary.html", context)


@login_required
def edit_salary(request: HttpRequest, teacher_id: int, salary_id: int):
    """Admin view for editing a teacher salary record"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    teacher = get_object_or_404(Teacher, id=teacher_id)
    salary = get_object_or_404(TeacherSalary, id=salary_id, teacher=teacher)

    if request.method == "POST":
        form = TeacherSalaryForm(request.POST, request.FILES, instance=salary)
        if form.is_valid():
            form.save()
            messages.success(request, "Salary record updated successfully.")
            return redirect("teachers:manage_salary", teacher_id=teacher.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TeacherSalaryForm(instance=salary)

    context = {
        "teacher": teacher,
        "salary": salary,
        "form": form,
        "role": role,
    }
    return render(request, "teachers/edit_salary.html", context)


@login_required
def delete_salary(request: HttpRequest, teacher_id: int, salary_id: int):
    """Admin view for deleting a teacher salary record"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    teacher = get_object_or_404(Teacher, id=teacher_id)
    salary = get_object_or_404(TeacherSalary, id=salary_id, teacher=teacher)

    if request.method == "POST":
        salary.delete()
        messages.success(request, "Salary record deleted successfully.")
        return redirect("teachers:manage_salary", teacher_id=teacher.id)

    context = {
        "teacher": teacher,
        "salary": salary,
        "role": role,
    }
    return render(request, "teachers/delete_salary.html", context)
