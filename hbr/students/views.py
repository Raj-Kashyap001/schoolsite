from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.core.files.storage import FileSystemStorage
import csv
import pandas as pd
from io import StringIO, BytesIO
import openpyxl
import pdfkit
from academics.models import Exam, ExamResult
from academics.views import get_current_session
from base.views import get_user_role
from .forms import (
    StudentProfileForm,
    StudentUserCreationForm,
    StudentProfileForm as StudentDetailsForm,
    StudentEditForm,
    DocumentUploadForm,
    PaymentForm,
    CertificateRequestForm,
    StudentBulkImportForm,
    generate_student_credentials,
    generate_admission_number,
    generate_roll_number,
)
from .models import (
    Student,
    Classroom,
    DailyTimetable,
    ExamTimetable,
    TeacherNotification,
    Document,
    Payment,
    Certificate,
    CertificateType,
)
from notices.models import Notice
from teachers.models import Teacher
from .data_utils import (
    handle_certificate_request,
    get_student_documents,
    get_student_certificates,
    get_student_payments,
)
from .generation_utils import (
    prepare_student_profile_data,
    generate_profile_pdf_response,
    validate_payment_receipt_download,
    generate_receipt_pdf_response,
    process_certificate_actions,
)

from academics.result_utils import (
    calculate_student_results,
    generate_marksheet_html,
    generate_marksheet_pdf,
    get_class_results_summary,
    generate_annual_result_sheet_pdf,
)


@login_required
def profile(request: HttpRequest):
    user = request.user
    role = get_user_role(user)

    # Check if admin is viewing a specific student's profile
    student_id = request.GET.get("student_id")
    if student_id and role == "Admin":
        try:
            student = Student.objects.get(id=student_id)
            view_user = student.user
            view_role = "Student"
            is_admin_viewing = True
        except Student.DoesNotExist:
            return HttpResponse("Student not found", status=404)
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

        if view_role == "Student":
            try:
                student = Student.objects.get(user=view_user)
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

    context = {"user": view_user, "is_admin_viewing": is_admin_viewing}

    if view_role == "Student":
        try:
            student = Student.objects.get(user=view_user)
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
def cancel_certificate(request: HttpRequest, certificate_id: int):
    """Cancel a pending certificate request."""
    role = get_user_role(request.user)
    if role != "Student":
        return JsonResponse({"success": False, "error": "Access denied"}, status=403)

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Method not allowed"}, status=405
        )

    try:
        student = Student.objects.get(user=request.user)
        certificate = Certificate.objects.get(
            id=certificate_id, student=student, status="PENDING"
        )
        certificate.delete()
        return JsonResponse({"success": True})
    except Student.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Student profile not found"}, status=404
        )
    except Certificate.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Certificate not found or not cancellable"},
            status=404,
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


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


@login_required
def class_management(request: HttpRequest):
    """Class management overview for admin"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    def get_grade_number(grade):
        digits = "".join(filter(str.isdigit, grade))
        return int(digits) if digits else 0

    classrooms = sorted(
        Classroom.objects.all(), key=lambda c: get_grade_number(c.grade)
    )
    context = {
        "classrooms": classrooms,
        "role": role,
    }
    return render(request, "students/class_management.html", context)


@login_required
def manage_class_students(request: HttpRequest, classroom_id: int):
    """Manage students in a specific classroom"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    try:
        classroom = Classroom.objects.get(id=classroom_id)
    except Classroom.DoesNotExist:
        return HttpResponse("Classroom not found", status=404)

    if request.method == "POST":
        action = request.POST.get("action")
        student_ids = request.POST.getlist("student_ids")

        if action == "assign":
            # Assign selected students to this classroom
            Student.objects.filter(id__in=student_ids).update(classroom=classroom)
        elif action == "remove":
            # Remove selected students from this classroom (assign to a default or None)
            # For now, we'll just remove them - they can be reassigned later
            Student.objects.filter(id__in=student_ids).update(classroom=None)

    # Get all students and current classroom students
    all_students = Student.objects.select_related("user", "classroom").order_by(
        "roll_no"
    )
    classroom_students = classroom.student.all().order_by("roll_no")

    context = {
        "classroom": classroom,
        "all_students": all_students,
        "classroom_students": classroom_students,
        "role": role,
    }
    return render(request, "students/manage_class_students.html", context)


@login_required
def manage_timetables(request: HttpRequest, classroom_id: int):
    """Manage daily and exam timetables for a classroom"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    try:
        classroom = Classroom.objects.get(id=classroom_id)
    except Classroom.DoesNotExist:
        return HttpResponse("Classroom not found", status=404)

    if request.method == "POST":
        if "daily_timetable" in request.FILES:
            day_of_week = request.POST.get("day_of_week")
            file = request.FILES["daily_timetable"]

            # Create or update daily timetable
            DailyTimetable.objects.update_or_create(
                classroom=classroom,
                day_of_week=day_of_week,
                defaults={
                    "timetable_file": file,
                    "uploaded_by": request.user,
                    "is_active": True,
                },
            )

        elif "exam_timetable" in request.FILES:
            title = request.POST.get("exam_title")
            file = request.FILES["exam_timetable"]

            # Create exam timetable
            ExamTimetable.objects.create(
                classroom=classroom,
                title=title,
                timetable_file=file,
                uploaded_by=request.user,
                is_active=True,
            )

        elif "delete_daily" in request.POST:
            timetable_id = request.POST.get("delete_daily")
            DailyTimetable.objects.filter(id=timetable_id, classroom=classroom).delete()

        elif "delete_exam" in request.POST:
            timetable_id = request.POST.get("delete_exam")
            ExamTimetable.objects.filter(id=timetable_id, classroom=classroom).delete()

    # Get existing timetables
    daily_timetables = DailyTimetable.objects.filter(
        classroom=classroom, is_active=True
    )
    exam_timetables = ExamTimetable.objects.filter(classroom=classroom, is_active=True)

    context = {
        "classroom": classroom,
        "daily_timetables": daily_timetables,
        "exam_timetables": exam_timetables,
        "days_of_week": DailyTimetable.DAYS_OF_WEEK,
        "role": role,
    }
    return render(request, "students/manage_timetables.html", context)


@login_required
def manage_teacher_notifications(request: HttpRequest, classroom_id: int):
    """Manage teacher notifications for a classroom"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    try:
        classroom = Classroom.objects.get(id=classroom_id)
    except Classroom.DoesNotExist:
        return HttpResponse("Classroom not found", status=404)

    if request.method == "POST":
        if "create_notification" in request.POST:
            teacher_id = request.POST.get("teacher_id")
            title = request.POST.get("title")
            message = request.POST.get("message")
            priority = request.POST.get("priority", "MEDIUM")

            try:
                teacher = Teacher.objects.get(id=teacher_id)
                TeacherNotification.objects.create(
                    teacher=teacher,
                    classroom=classroom,
                    title=title,
                    message=message,
                    priority=priority,
                    created_by=request.user,
                )
            except Teacher.DoesNotExist:
                pass  # Handle error appropriately

        elif "delete_notification" in request.POST:
            notification_id = request.POST.get("delete_notification")
            TeacherNotification.objects.filter(
                id=notification_id, classroom=classroom
            ).delete()

    # Get teachers assigned to this classroom
    teachers = classroom.teachers.all()
    notifications = (
        TeacherNotification.objects.filter(classroom=classroom, is_active=True)
        .select_related("teacher")
        .order_by("-created_at")
    )

    context = {
        "classroom": classroom,
        "teachers": teachers,
        "notifications": notifications,
        "priorities": TeacherNotification.PRIORITY_CHOICES,
        "role": role,
    }
    return render(request, "students/manage_teacher_notifications.html", context)


@login_required
def student_management(request: HttpRequest):
    """Admin view for managing students"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    from django.core.paginator import Paginator
    from django.db.models import Q

    # Get filter parameters
    selected_classes = request.GET.getlist("classroom")
    search_query = request.GET.get("search", "").strip()
    order_by = request.GET.get("order", "user__first_name")
    page_number = request.GET.get("page", 1)

    # Base queryset
    students = Student.objects.select_related("user", "classroom")

    # Apply classroom filter
    if selected_classes:
        students = students.filter(classroom__id__in=selected_classes)

    # Apply search filter
    if search_query:
        students = students.filter(
            Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__username__icontains=search_query)
        )

    # Apply ordering
    if order_by.startswith("-"):
        students = students.order_by(order_by, "user__first_name")
    else:
        students = students.order_by(order_by, "user__first_name")

    # Pagination
    paginator = Paginator(students, 15)  # 15 students per page
    page_obj = paginator.get_page(page_number)

    # Get all classrooms for filter dropdown
    def get_grade_number(grade):
        digits = "".join(filter(str.isdigit, grade))
        return int(digits) if digits else 0

    classrooms = sorted(
        Classroom.objects.all(), key=lambda c: get_grade_number(c.grade)
    )

    context = {
        "page_obj": page_obj,
        "classrooms": classrooms,
        "selected_classes": selected_classes,
        "search_query": search_query,
        "current_order": order_by,
        "role": role,
    }
    return render(request, "students/student_management.html", context)


@login_required
def add_student(request: HttpRequest):
    """Admin view for adding a new student"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        print("DEBUG: POST request received")
        print(f"DEBUG: POST data keys: {list(request.POST.keys())}")

        # Create modified POST data with first_name and last_name from full_name
        modified_post = request.POST.copy()

        # Handle full_name field
        full_name = request.POST.get("full_name", "").strip()
        print(f"DEBUG: full_name from POST: '{full_name}'")

        if full_name:
            name_parts = full_name.split()
            first_name = name_parts[0] if name_parts else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        else:
            first_name = ""
            last_name = ""

        print(f"DEBUG: first_name: '{first_name}', last_name: '{last_name}'")
        modified_post["first_name"] = first_name
        modified_post["last_name"] = last_name

        # Generate credentials and add them to the form data
        # We need to generate them early so the form validation passes
        if full_name and request.POST.get("dob"):
            from datetime import datetime

            dob = datetime.strptime(request.POST.get("dob"), "%Y-%m-%d").date()
            username, password = generate_student_credentials(
                first_name, last_name, dob
            )
            modified_post["username"] = username
            modified_post["password1"] = password
            modified_post["password2"] = password
            print(f"DEBUG: Generated and set credentials - username: {username}")

        user_form = StudentUserCreationForm(modified_post)
        profile_form = StudentDetailsForm(modified_post, request.FILES)

        print(f"DEBUG: user_form.is_valid(): {user_form.is_valid()}")
        print(f"DEBUG: profile_form.is_valid(): {profile_form.is_valid()}")

        if not user_form.is_valid():
            print(f"DEBUG: user_form.errors: {user_form.errors}")
            print(f"DEBUG: user_form.non_field_errors: {user_form.non_field_errors}")

        if not profile_form.is_valid():
            print(f"DEBUG: profile_form.errors: {profile_form.errors}")
            print(
                f"DEBUG: profile_form.non_field_errors: {profile_form.non_field_errors}"
            )

        if user_form.is_valid() and profile_form.is_valid():
            try:
                print("DEBUG: Starting student creation process")

                # Generate credentials
                dob = profile_form.cleaned_data["dob"]
                username, password = generate_student_credentials(
                    first_name, last_name, dob
                )
                print(f"DEBUG: Generated - {username}, {password}")

                # Generate IDs
                classroom = profile_form.cleaned_data["classroom"]
                existing_students = Student.objects.filter(classroom=classroom)
                sequence = existing_students.count() + 1
                admission_no = generate_admission_number(classroom.grade)
                roll_no = generate_roll_number(classroom, sequence)
                print(
                    f"DEBUG: Generated IDs - Admission: {admission_no}, Roll: {roll_no}"
                )

                # Create user
                user = User.objects.create_user(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=user_form.cleaned_data.get("email", ""),
                    password=password,
                )

                # Assign user to Student group
                from django.contrib.auth.models import Group

                student_group, created = Group.objects.get_or_create(name="Student")
                user.groups.add(student_group)

                print(f"DEBUG: User created: {user.id} and assigned to Student group")

                # Create student
                student = Student.objects.create(
                    user=user,
                    sr_no=sequence,
                    roll_no=roll_no,
                    admission_no=admission_no,
                    father_name=profile_form.cleaned_data["father_name"],
                    mother_name=profile_form.cleaned_data["mother_name"],
                    dob=dob,
                    mobile_no=profile_form.cleaned_data["mobile_no"],
                    category=profile_form.cleaned_data.get("category"),
                    gender=profile_form.cleaned_data["gender"],
                    profile_photo=profile_form.cleaned_data.get("profile_photo"),
                    current_address=profile_form.cleaned_data.get("current_address"),
                    permanent_address=profile_form.cleaned_data.get(
                        "permanent_address"
                    ),
                    weight=profile_form.cleaned_data.get("weight"),
                    height=profile_form.cleaned_data.get("height"),
                    plain_text_password=password,
                    classroom=classroom,
                )
                print(f"DEBUG: Student created: {student.id}")

                # Set many-to-many relationships
                if profile_form.cleaned_data.get("subjects"):
                    student.subjects.set(profile_form.cleaned_data["subjects"])

                if profile_form.cleaned_data.get("stream"):
                    student.stream = profile_form.cleaned_data["stream"]
                    student.save()

                print("DEBUG: Student creation completed successfully")
                messages.success(
                    request,
                    f"Student {user.get_full_name()} added successfully. "
                    f"Username: {username}, Password: {password}, "
                    f"Admission No: {admission_no}, Roll No: {roll_no}",
                )
                return redirect("students:student_management")

            except Exception as e:
                print(f"DEBUG: Exception: {type(e).__name__}: {e}")
                import traceback

                print(f"DEBUG: Traceback: {traceback.format_exc()}")
                messages.error(request, f"Error creating student: {e}")
        else:
            print("DEBUG: Forms are not valid")
            print(f"DEBUG: user_form errors: {user_form.errors}")
            print(f"DEBUG: profile_form errors: {profile_form.errors}")
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = StudentUserCreationForm()
        profile_form = StudentDetailsForm()

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "role": role,
    }
    return render(request, "students/add_student.html", context)


@login_required
def edit_student(request: HttpRequest, student_id: int):
    """Admin view for editing a student"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        form = StudentEditForm(request.POST, request.FILES, instance=student)

        if form.is_valid():
            with transaction.atomic():
                # Update user fields
                student.user.first_name = form.cleaned_data["first_name"]
                student.user.last_name = form.cleaned_data["last_name"]
                student.user.email = form.cleaned_data.get("email", "")
                student.user.save()

                # Update student fields
                form.save()

                # Update many-to-many relationships
                if form.cleaned_data.get("subjects"):
                    student.subjects.set(form.cleaned_data["subjects"])
                else:
                    student.subjects.clear()

                if form.cleaned_data.get("stream"):
                    student.stream = form.cleaned_data["stream"]
                    student.save()
                else:
                    student.stream = None
                    student.save()

                messages.success(
                    request,
                    f"Student {student.user.get_full_name()} updated successfully.",
                )
                return redirect("students:student_management")


@login_required
def delete_student(request: HttpRequest, student_id: int):
    """Admin view for deleting a student"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        user = student.user
        student.delete()
        user.delete()  # Also delete the user account
        messages.success(
            request, f"Student {user.get_full_name()} deleted successfully."
        )
        return redirect("students:student_management")

    context = {
        "student": student,
        "role": role,
    }
    return render(request, "students/delete_student.html", context)


@login_required
def bulk_delete_students(request: HttpRequest):
    """Admin view for bulk deleting students"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    student_ids = request.POST.getlist("student_ids")

    if not student_ids:
        messages.error(request, "No students selected for deletion.")
        return redirect("students:student_management")

    try:
        # Get students to delete
        students = Student.objects.filter(id__in=student_ids).select_related("user")
        deleted_count = 0

        with transaction.atomic():
            for student in students:
                user = student.user
                student.delete()
                user.delete()  # Also delete the user account
                deleted_count += 1

        if deleted_count > 0:
            messages.success(
                request,
                f"Successfully deleted {deleted_count} student{'s' if deleted_count > 1 else ''}."
            )
        else:
            messages.warning(request, "No students were deleted.")

    except Exception as e:
        messages.error(request, f"Error deleting students: {e}")

    return redirect("students:student_management")


@login_required
def manage_student_documents(request: HttpRequest, student_id: int):
    """Admin view for managing student documents"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.student = student
            document.save()
            # Create system alert for admin
            Notice.objects.create(
                title=f"Document Uploaded: {student.user.get_full_name()}",
                content=f"Student {student.user.get_full_name()} (Roll: {student.roll_no}, Class: {student.classroom}) has uploaded a document: {document.name}.",
                notice_type=Notice.NoticeType.SYSTEM_ALERT,
                created_by=request.user,
            )
            messages.success(request, "Document uploaded successfully.")
            return redirect("students:manage_student_documents", student_id=student.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DocumentUploadForm()

    documents = Document.objects.filter(student=student).order_by("-uploaded_at")

    context = {
        "student": student,
        "form": form,
        "documents": documents,
        "role": role,
    }
    return render(request, "students/manage_student_documents.html", context)


@login_required
def manage_student_payments(request: HttpRequest, student_id: int):
    """Admin view for managing student payments"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.student = student
            payment.save()
            messages.success(request, "Payment record added successfully.")
            return redirect("students:manage_student_payments", student_id=student.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PaymentForm()

    payments = Payment.objects.filter(student=student).order_by("-created_at")

    context = {
        "student": student,
        "form": form,
        "payments": payments,
        "role": role,
    }
    return render(request, "students/manage_student_payments.html", context)


@login_required
def manage_student_certificates(request: HttpRequest, student_id: int):
    """Admin view for managing student certificates"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        return process_certificate_actions(request, student)

    certificates = Certificate.objects.filter(student=student).order_by("-issued_date")
    available_types = (
        CertificateType.objects.filter(is_active=True)
        .exclude(id__in=certificates.values_list("certificate_type_id", flat=True))
        .exclude(name__exact="")
    )

    context = {
        "student": student,
        "certificates": certificates,
        "available_types": available_types,
        "certificate_form": CertificateRequestForm(),
        "role": role,
    }
    return render(request, "students/manage_student_certificates.html", context)


@login_required
def export_students(request: HttpRequest):
    """Admin view for exporting students to CSV/Excel"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    # Get filter parameters (same as student_management)
    selected_classes = request.GET.getlist("classroom")
    search_query = request.GET.get("search", "").strip()

    # Base queryset
    students = Student.objects.select_related("user", "classroom")

    # Apply classroom filter
    if selected_classes:
        students = students.filter(classroom__id__in=selected_classes)

    # Apply search filter
    if search_query:
        from django.db.models import Q

        students = students.filter(
            Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__username__icontains=search_query)
        )

    students = students.order_by("user__first_name")

    # Get export format
    export_format = request.GET.get("format", "csv")

    if export_format == "excel":
        # Export to Excel
        data = []
        for student in students:
            data.append(
                {
                    "Admission No": student.admission_no,
                    "Roll No": student.roll_no,
                    "First Name": student.user.first_name,
                    "Last Name": student.user.last_name,
                    "Username": student.user.username,
                    "Email": student.user.email,
                    "Father Name": student.father_name,
                    "Mother Name": student.mother_name,
                    "Date of Birth": (
                        student.dob.strftime("%Y-%m-%d") if student.dob else ""
                    ),
                    "Mobile No": str(student.mobile_no),
                    "Category": student.category,
                    "Gender": student.gender,
                    "Classroom": str(student.classroom),
                    "Stream": str(student.stream) if student.stream else "",
                    "Subjects": ", ".join([str(s) for s in student.subjects.all()]),
                    "Current Address": student.current_address,
                    "Permanent Address": student.permanent_address,
                    "Weight": str(student.weight) if student.weight else "",
                    "Height": str(student.height) if student.height else "",
                }
            )

        df = pd.DataFrame(data)

        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Students", index=False)

        output.seek(0)
        response = HttpResponse(output.read(), content_type="application/vnd.openpyxl")
        filename = (
            f"students_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

    else:
        # Export to CSV (default)
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "Admission No",
                "Roll No",
                "First Name",
                "Last Name",
                "Username",
                "Email",
                "Father Name",
                "Mother Name",
                "Date of Birth",
                "Mobile No",
                "Category",
                "Gender",
                "Classroom",
                "Stream",
                "Subjects",
                "Current Address",
                "Permanent Address",
                "Weight",
                "Height",
            ]
        )

        # Write student data
        for student in students:
            writer.writerow(
                [
                    student.admission_no,
                    student.roll_no,
                    student.user.first_name,
                    student.user.last_name,
                    student.user.username,
                    student.user.email,
                    student.father_name,
                    student.mother_name,
                    student.dob.strftime("%Y-%m-%d") if student.dob else "",
                    str(student.mobile_no),
                    student.category,
                    student.gender,
                    str(student.classroom),
                    str(student.stream) if student.stream else "",
                    ", ".join([str(s) for s in student.subjects.all()]),
                    student.current_address,
                    student.permanent_address,
                    str(student.weight) if student.weight else "",
                    str(student.height) if student.height else "",
                ]
            )

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        filename = f"students_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response


@login_required
def import_students(request: HttpRequest):
    """Admin view for importing students from CSV/Excel files"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        form = StudentBulkImportForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["file"]
            classroom = form.cleaned_data["classroom"]
            overwrite_existing = form.cleaned_data["overwrite_existing"]

            try:
                # Save uploaded file temporarily
                fs = FileSystemStorage()
                filename = fs.save(file.name, file)
                file_path = fs.path(filename)

                imported_count = 0
                error_messages = []

                try:
                    if file.name.endswith((".xlsx", ".xls")):
                        # Read Excel file
                        df = pd.read_excel(file_path)
                    else:
                        # Read CSV file
                        df = pd.read_csv(file_path)

                    # Process each row with progress feedback
                    total_rows = len(df)
                    for index, row in df.iterrows():
                        try:
                            current_row = index + 1
                            print(
                                f"DEBUG: Processing student {current_row}/{total_rows}"
                            )

                            # Show progress every 5 students
                            if current_row % 5 == 0 or current_row == total_rows:
                                print(
                                    f"DEBUG: Progress: {current_row}/{total_rows} students processed"
                                )
                            # Extract data from row (handle missing columns gracefully)
                            admission_no = str(row.get("Admission No", "")).strip()
                            first_name = str(row.get("First Name", "")).strip()
                            last_name = str(row.get("Last Name", "")).strip()
                            email = str(row.get("Email", "")).strip()

                            if not first_name or not last_name:
                                error_messages.append(
                                    f"Row {index + 1}: First name and last name are required"
                                )
                                continue

                            # Check if student already exists
                            existing_student = None
                            if admission_no:
                                existing_student = Student.objects.filter(
                                    admission_no=admission_no
                                ).first()

                            if existing_student and not overwrite_existing:
                                error_messages.append(
                                    f"Row {index + 1}: Student with admission no {admission_no} already exists"
                                )
                                continue
                            elif existing_student and overwrite_existing:
                                # Update existing student
                                user = existing_student.user
                                user.first_name = first_name
                                user.last_name = last_name
                                user.email = email
                                user.save()

                                existing_student.father_name = str(
                                    row.get("Father Name", "")
                                ).strip()
                                existing_student.mother_name = str(
                                    row.get("Mother Name", "")
                                ).strip()
                                existing_student.mobile_no = (
                                    int(row.get("Mobile No", 0))
                                    if row.get("Mobile No")
                                    else 0
                                )
                                existing_student.category = str(
                                    row.get("Category", "")
                                ).strip()
                                existing_student.gender = str(
                                    row.get("Gender", "")
                                ).strip()
                                existing_student.current_address = str(
                                    row.get("Current Address", "")
                                ).strip()
                                existing_student.permanent_address = str(
                                    row.get("Permanent Address", "")
                                ).strip()
                                existing_student.classroom = classroom

                                # Handle optional fields
                                if row.get("Date of Birth"):
                                    existing_student.dob = pd.to_datetime(
                                        row.get("Date of Birth")
                                    ).date()
                                if row.get("Weight"):
                                    existing_student.weight = float(row.get("Weight"))
                                if row.get("Height"):
                                    existing_student.height = float(row.get("Height"))

                                existing_student.save()
                                imported_count += 1
                            else:
                                # Create new student
                                # Generate username and password
                                dob_str = str(row.get("Date of Birth", ""))
                                if dob_str:
                                    try:
                                        dob = pd.to_datetime(dob_str).date()
                                    except:
                                        dob = None
                                else:
                                    dob = None

                                username, password = generate_student_credentials(
                                    first_name,
                                    last_name,
                                    dob or pd.Timestamp.now().date(),
                                )

                                # Create user
                                user = User.objects.create_user(
                                    username=username,
                                    first_name=first_name,
                                    last_name=last_name,
                                    email=email,
                                    password=password,
                                )

                                # Assign user to Student group
                                from django.contrib.auth.models import Group

                                student_group, created = Group.objects.get_or_create(
                                    name="Student"
                                )
                                user.groups.add(student_group)

                                # Generate sequence and IDs
                                existing_students = Student.objects.filter(
                                    classroom=classroom
                                )
                                sequence = existing_students.count() + 1

                                # Generate admission number if not provided
                                if not admission_no:
                                    admission_no = generate_admission_number(
                                        classroom.grade
                                    )

                                roll_no = generate_roll_number(classroom, sequence)

                                # Create student
                                student = Student.objects.create(
                                    user=user,
                                    sr_no=sequence,
                                    roll_no=roll_no,
                                    admission_no=admission_no,
                                    father_name=str(row.get("Father Name", "")).strip(),
                                    mother_name=str(row.get("Mother Name", "")).strip(),
                                    dob=dob,
                                    mobile_no=(
                                        int(row.get("Mobile No", 0))
                                        if row.get("Mobile No")
                                        else 0
                                    ),
                                    category=str(row.get("Category", "")).strip(),
                                    gender=str(row.get("Gender", "")).strip(),
                                    current_address=str(
                                        row.get("Current Address", "")
                                    ).strip(),
                                    permanent_address=str(
                                        row.get("Permanent Address", "")
                                    ).strip(),
                                    classroom=classroom,
                                )

                                # Handle optional fields
                                if row.get("Weight"):
                                    student.weight = float(row.get("Weight"))
                                if row.get("Height"):
                                    student.height = float(row.get("Height"))
                                student.save()

                                imported_count += 1

                        except Exception as e:
                            error_messages.append(f"Row {index + 1}: {str(e)}")

                finally:
                    # Clean up uploaded file
                    fs.delete(filename)

                # Show results
                if imported_count > 0:
                    messages.success(
                        request, f"Successfully imported {imported_count} students."
                    )

                if error_messages:
                    messages.warning(
                        request, f"Errors encountered: {'; '.join(error_messages[:5])}"
                    )
                    if len(error_messages) > 5:
                        messages.warning(
                            request, f"... and {len(error_messages) - 5} more errors"
                        )

                return redirect("students:student_management")

            except Exception as e:
                messages.error(request, f"Error processing file: {e}")
                return redirect("students:student_management")

    else:
        form = StudentBulkImportForm()

    context = {
        "form": form,
        "role": role,
    }
    return render(request, "students/import_students.html", context)


@login_required
def manage_certificate_types(request: HttpRequest):
    """Admin view for managing certificate types"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        if "create" in request.POST:
            name = request.POST.get("name", "").strip()
            description = request.POST.get("description", "").strip()
            html_template = request.POST.get("html_template", "").strip()
            if name:
                CertificateType.objects.create(
                    name=name,
                    description=description,
                    html_template=html_template,
                )
                messages.success(
                    request, f"Certificate type '{name}' created successfully."
                )
        elif "update" in request.POST:
            type_id = request.POST.get("type_id")
            name = request.POST.get("name", "").strip()
            description = request.POST.get("description", "").strip()
            html_template = request.POST.get("html_template", "").strip()
            is_active = request.POST.get("is_active") == "on"
            try:
                cert_type = CertificateType.objects.get(id=type_id)
                cert_type.name = name
                cert_type.description = description
                cert_type.html_template = html_template
                cert_type.is_active = is_active
                cert_type.save()
                messages.success(
                    request, f"Certificate type '{name}' updated successfully."
                )
            except CertificateType.DoesNotExist:
                messages.error(request, "Certificate type not found.")
        elif "delete" in request.POST:
            type_id = request.POST.get("type_id")
            try:
                cert_type = CertificateType.objects.get(id=type_id)
                cert_type.delete()
                messages.success(
                    request,
                    f"Certificate type '{cert_type.name}' deleted successfully.",
                )
            except CertificateType.DoesNotExist:
                messages.error(request, "Certificate type not found.")

        return redirect("students:manage_certificate_types")

    certificate_types = CertificateType.objects.all().order_by("name")
    context = {
        "certificate_types": certificate_types,
        "role": role,
    }
    return render(request, "students/manage_certificate_types.html", context)


@login_required
def promote_students(request: HttpRequest):
    """Admin view for promoting students to next class"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        from_classroom_id = request.POST.get("from_classroom")
        to_classroom_id = request.POST.get("to_classroom")
        passed_only = request.POST.get("passed_only") == "on"

        try:
            from_classroom = Classroom.objects.get(id=from_classroom_id)
            to_classroom = Classroom.objects.get(id=to_classroom_id)

            # Get students to promote
            students_to_promote = Student.objects.filter(classroom=from_classroom)

            if passed_only:
                # Only promote students who passed final exams
                from academics.models import Exam, ExamResult

                # Get final exams for the session
                current_session = get_current_session(request)
                final_exams = Exam.objects.filter(
                    term__academic_session=current_session, is_yearly_final=True
                )

                if final_exams.exists():
                    # Get students who passed final exams
                    passed_students = set()
                    for exam in final_exams:
                        results = ExamResult.objects.filter(
                            exam=exam,
                            student__classroom=from_classroom,
                            status=ExamResult.Status.PUBLISHED,
                        ).select_related("student")

                        for result in results:
                            # Calculate percentage
                            total_marks = sum(
                                float(r.total_marks)
                                for r in ExamResult.objects.filter(
                                    exam=exam,
                                    student=result.student,
                                    status=ExamResult.Status.PUBLISHED,
                                )
                            )
                            obtained_marks = sum(
                                float(r.marks_obtained or 0)
                                for r in ExamResult.objects.filter(
                                    exam=exam,
                                    student=result.student,
                                    status=ExamResult.Status.PUBLISHED,
                                )
                            )

                            if (
                                total_marks > 0
                                and (obtained_marks / total_marks * 100) >= 33
                            ):
                                passed_students.add(result.student.id)

                    students_to_promote = students_to_promote.filter(
                        id__in=passed_students
                    )

            # Promote students
            promoted_count = students_to_promote.update(classroom=to_classroom)

            messages.success(
                request,
                f"Successfully promoted {promoted_count} students from {from_classroom} to {to_classroom}.",
            )

        except Classroom.DoesNotExist:
            messages.error(request, "Invalid classroom selection.")
        except Exception as e:
            messages.error(request, f"Error promoting students: {e}")

    return redirect("students:student_management")
