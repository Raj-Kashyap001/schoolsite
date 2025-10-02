from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from base.views import get_user_role
from .pdf_utils import (
    generate_student_profile_pdf,
    generate_payment_receipt_pdf,
    generate_exam_timetable_pdf,
    generate_admit_card_pdf,
)
from .forms import StudentProfileForm
from .models import (
    AcademicSession,
    Attendance,
    Document,
    Exam,
    ExamResult,
    ExamSchedule,
    Leave,
    Notice,
    Student,
    Teacher,
    TeacherAttendance,
    Term,
    CertificateType,
    Certificate,
    Payment,
)


def get_current_session():
    """Helper function to get the current academic session"""
    from datetime import date

    today = date.today()
    current_session = AcademicSession.objects.filter(
        start_date__lte=today, end_date__gte=today
    ).first()

    # If no current session, get the latest one
    if not current_session:
        current_session = AcademicSession.objects.order_by("-end_date").first()

    return current_session


@login_required
def dashboard_home(request: HttpRequest):
    user = request.user
    role = get_user_role(user)

    context = {"role": role, "current_session": get_current_session()}
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

    context = {"role": role, "user": user, "current_session": get_current_session()}

    if role == "Student":
        from .models import Student, Attendance

        try:
            student = Student.objects.get(user=user)
            context["student"] = student

            # Get student-specific notices (individual notices targeted to this student)
            individual_notices = Notice.objects.filter(
                is_active=True,
                notice_type=Notice.NoticeType.INDIVIDUAL,
                target_students=student,
            ).order_by("-created_at")[
                :5
            ]  # Show latest 5
            context["individual_notices"] = individual_notices  # type: ignore
        except Student.DoesNotExist:
            context["student"] = None

    return render(request, "dashboard/profile.html", context)


@login_required
def attendance(request: HttpRequest):
    role = get_user_role(request.user)
    context = {
        "role": role,
        "attendance_events": [],
        "current_session": get_current_session(),
    }

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

    elif role == "Teacher":
        try:
            teacher = Teacher.objects.get(user=request.user)
            attendances = TeacherAttendance.objects.filter(teacher=teacher).order_by(
                "date"
            )

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
                            "marked_by": (
                                str(att.marked_by) if att.marked_by else "System"
                            ),
                        },
                    }
                )

            context["attendance_events"] = events  # type: ignore
            context["teacher"] = teacher  # type: ignore
        except Teacher.DoesNotExist:
            context["error"] = "Teacher profile not found"

    return render(request, "dashboard/attendance.html", context)


@login_required
def mark_student_attendance(request: HttpRequest):
    role = get_user_role(request.user)
    if role != "Teacher":
        return HttpResponse("Access denied", status=403)

    context = {"role": role, "current_session": get_current_session()}

    try:
        teacher = Teacher.objects.get(user=request.user)
        # Get students in teacher's classrooms
        students = (
            Student.objects.filter(classroom__in=teacher.classroom.all())
            .distinct()
            .order_by("sr_no")
        )
        context["students"] = students  # type: ignore
        context["teacher"] = teacher  # type: ignore

        if request.method == "POST":
            date = request.POST.get("date")
            if not date:
                messages.error(request, "Date is required")
                return render(
                    request, "dashboard/mark_student_attendance.html", context
                )

            attendance_count = 0
            for student in students:
                status = request.POST.get(f"status_{student.id}")  # type: ignore
                remarks = request.POST.get(f"remarks_{student.id}", "")  # type: ignore

                if status:
                    # Check if attendance already exists for this date
                    attendance, created = Attendance.objects.get_or_create(
                        student=student,
                        date=date,
                        defaults={
                            "teacher": teacher,
                            "status": status,
                            "remarks": remarks,
                        },
                    )
                    if not created:
                        # Update existing attendance
                        attendance.status = status
                        attendance.remarks = remarks
                        attendance.teacher = teacher
                        attendance.save()
                    attendance_count += 1

            messages.success(
                request, f"Attendance marked for {attendance_count} students"
            )
            return redirect("mark_student_attendance")

    except Teacher.DoesNotExist:
        context["error"] = "Teacher profile not found"

    return render(request, "dashboard/mark_student_attendance.html", context)


@login_required
def mark_teacher_attendance(request: HttpRequest):
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    context = {"role": role, "current_session": get_current_session()}

    teachers = Teacher.objects.all().order_by("user__first_name", "user__last_name")
    context["teachers"] = teachers  # type: ignore

    if request.method == "POST":
        date = request.POST.get("date")
        if not date:
            messages.error(request, "Date is required")
            return render(request, "dashboard/mark_teacher_attendance.html", context)

        attendance_count = 0
        for teacher in teachers:
            status = request.POST.get(f"status_{teacher.id}")  # type: ignore
            remarks = request.POST.get(f"remarks_{teacher.id}", "")  # type: ignore

            if status:
                # Check if attendance already exists for this date
                attendance, created = TeacherAttendance.objects.get_or_create(
                    teacher=teacher,
                    date=date,
                    defaults={
                        "status": status,
                        "remarks": remarks,
                        "marked_by": request.user,
                    },
                )
                if not created:
                    # Update existing attendance
                    attendance.status = status
                    attendance.remarks = remarks
                    attendance.marked_by = request.user  # type: ignore
                    attendance.save()
                attendance_count += 1

        messages.success(request, f"Attendance marked for {attendance_count} teachers")
        return redirect("mark_teacher_attendance")

    return render(request, "dashboard/mark_teacher_attendance.html", context)


@login_required
def leave(request: HttpRequest):
    role = get_user_role(request.user)
    context = {"role": role, "current_session": get_current_session()}

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
        "stream": student.stream.name if student.stream else None,
        "subjects": (
            ", ".join([subject.name for subject in student.subjects.all()])
            if student.subjects.exists()
            else None
        ),
        "current_address": student.current_address,
        "permanent_address": student.permanent_address,
        "weight": float(student.weight) if student.weight else None,
        "height": float(student.height) if student.height else None,
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
    context = {"role": role, "current_session": get_current_session()}

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
    context = {"role": role, "current_session": get_current_session()}

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
def notice_board(request: HttpRequest):
    role = get_user_role(request.user)
    context = {"role": role, "current_session": get_current_session()}

    if role == "Student":
        try:
            student = Student.objects.get(user=request.user)
            # Get all active notices that are either announcements or targeted to this student
            notices = (
                Notice.objects.filter(is_active=True)
                .filter(
                    models.Q(notice_type=Notice.NoticeType.ANNOUNCEMENT)
                    | models.Q(
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

    return render(request, "dashboard/notice_board.html", context)


@login_required
def payments(request: HttpRequest):
    role = get_user_role(request.user)
    context = {"role": role, "current_session": get_current_session()}

    if role == "Student":
        try:
            student = Student.objects.get(user=request.user)
            payments = Payment.objects.filter(student=student).order_by("-created_at")
            context["payments"] = payments  # type: ignore
            context["student"] = student  # type: ignore
        except Student.DoesNotExist:
            context["error"] = "Student profile not found"

    return render(request, "dashboard/payments.html", context)


@login_required
def download_receipt(request: HttpRequest, payment_id: int):
    user = request.user
    role = get_user_role(user)

    if role != "Student":
        return HttpResponse("Access denied", status=403)

    try:
        student = Student.objects.get(user=user)
        payment = Payment.objects.get(id=payment_id, student=student, status="PAID")
    except (Student.DoesNotExist, Payment.DoesNotExist):
        return HttpResponse("Payment not found or not paid", status=404)

    # Generate PDF
    buffer = generate_payment_receipt_pdf(payment)

    # Return PDF response
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="receipt_{payment.id}.pdf"'  # type: ignore
    return response


@login_required
def exams(request: HttpRequest):
    role = get_user_role(request.user)
    context = {"role": role, "current_session": get_current_session()}

    if role == "Student":
        try:
            student = Student.objects.get(user=request.user)

            # Get current term based on current date
            from datetime import date

            today = date.today()
            current_term = Term.objects.filter(
                start_date__lte=today, end_date__gte=today
            ).first()

            # If no current term, get the next upcoming term
            if not current_term:
                current_term = (
                    Term.objects.filter(start_date__gt=today)
                    .order_by("start_date")
                    .first()
                )

            # If still no term, fall back to latest term
            if not current_term:
                current_term = Term.objects.order_by("-end_date").first()

            if current_term:
                # Get all upcoming exams in a single query
                from datetime import date

                today = date.today()

                upcoming_exams = (
                    Exam.objects.filter(
                        # Exams from current term OR exams from past terms with future schedules
                        models.Q(term=current_term)
                        | models.Q(
                            term__end_date__lt=today, examschedule__date__gte=today
                        )
                    )
                    .prefetch_related("examschedule_set")
                    .distinct()
                )

                # Exam results for current term
                current_results = ExamResult.objects.filter(
                    student=student, exam__term=current_term
                ).select_related("exam")

                # For modal: all terms for querying previous results
                all_terms = Term.objects.order_by("-end_date")

                context.update(
                    {
                        "upcoming_exams": upcoming_exams,
                        "current_results": current_results,
                        "all_terms": all_terms,
                        "current_term": current_term,
                        "student": student,
                    }  # type: ignore
                )  # type: ignore
            else:
                context["error"] = "No academic terms found"
                context["student"] = student  # type: ignore

        except Student.DoesNotExist:
            context["error"] = "Student profile not found"

    return render(request, "dashboard/exams.html", context)


@login_required
def get_exam_timetable(request: HttpRequest, exam_id: int):
    role = get_user_role(request.user)
    if role != "Student":
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        exam = Exam.objects.get(id=exam_id)
        schedule = ExamSchedule.objects.filter(exam=exam).order_by("date", "time")
        schedule_data = [
            {
                "date": item.date.strftime("%Y-%m-%d"),
                "time": item.time.strftime("%H:%M"),
                "subject": item.subject,
                "room": item.room,
            }
            for item in schedule
        ]
        return JsonResponse({"exam_name": exam.name, "schedule": schedule_data})
    except Exam.DoesNotExist:
        return JsonResponse({"error": "Exam not found"}, status=404)


@login_required
def download_exam_timetable(request: HttpRequest, exam_id: int):
    role = get_user_role(request.user)
    if role != "Student":
        return HttpResponse("Access denied", status=403)

    try:
        exam = Exam.objects.get(id=exam_id)
        schedule = ExamSchedule.objects.filter(exam=exam).order_by("date", "time")

        # Prepare schedule data for PDF
        schedule_data = [
            {
                "date": item.date.strftime("%d/%m/%Y"),
                "time": item.time.strftime("%H:%M"),
                "subject": item.subject,
                "room": item.room,
            }
            for item in schedule
        ]

        # Get student info
        student = Student.objects.get(user=request.user)

        # Generate PDF
        buffer = generate_exam_timetable_pdf(exam, schedule_data, student)

        # Return PDF response
        response = HttpResponse(buffer, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{exam.name}_timetable.pdf"'
        )
        return response
    except Exam.DoesNotExist:
        return HttpResponse("Exam not found", status=404)


@login_required
def download_admit_card(request: HttpRequest, exam_id: int):
    role = get_user_role(request.user)
    if role != "Student":
        return HttpResponse("Access denied", status=403)

    try:
        exam = Exam.objects.get(
            id=exam_id, is_yearly_final=True, admit_card_available=True
        )
        student = Student.objects.get(user=request.user)

        # Generate admit card PDF (for now, we'll use a simple admit card format)
        buffer = generate_admit_card_pdf(exam, student)

        # Return PDF response
        response = HttpResponse(buffer, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="admit_card_{exam.name}_{student.roll_no}.pdf"'
        )
        return response
    except Exam.DoesNotExist:
        return HttpResponse("Admit card not available for this exam", status=404)
    except Student.DoesNotExist:
        return HttpResponse("Student profile not found", status=404)
    except Student.DoesNotExist:
        return HttpResponse("Student profile not found", status=404)


@login_required
def get_exam_results(request: HttpRequest, term_id: int):
    role = get_user_role(request.user)
    if role != "Student":
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        student = Student.objects.get(user=request.user)
        term = Term.objects.get(id=term_id)
        results = ExamResult.objects.filter(
            student=student, exam__term=term
        ).select_related("exam")

        results_data = [
            {
                "exam_name": result.exam.name,
                "subject": result.subject,
                "marks_obtained": (
                    str(result.marks_obtained) if result.marks_obtained else None
                ),
                "grade": result.grade,
            }
            for result in results
        ]
        return JsonResponse({"results": results_data})
    except (Student.DoesNotExist, Term.DoesNotExist):
        return JsonResponse({"error": "Not found"}, status=404)


@login_required
def download_notice_attachment(request: HttpRequest, notice_id: int):
    role = get_user_role(request.user)
    if role != "Student":
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
