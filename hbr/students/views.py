from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from base.views import get_user_role
from .forms import StudentProfileForm
from .models import (
    Student,
    Classroom,
    DailyTimetable,
    ExamTimetable,
    TeacherNotification,
)
from teachers.models import Teacher
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


@login_required
def class_management(request: HttpRequest):
    """Class management overview for admin"""
    role = get_user_role(request.user)

    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    classrooms = Classroom.objects.all().order_by("grade")
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
