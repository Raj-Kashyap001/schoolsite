from decimal import Decimal
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
from .models import (
    AcademicSession,
    Term,
    Exam,
    ExamSchedule,
    ExamResult,
    ExamAssignment,
)
from students.models import Student, Classroom
from teachers.models import Teacher
from notices.models import Notice
from dashboard.pdf_utils import (
    generate_exam_timetable_pdf,
    generate_admit_card_pdf as dashboard_generate_admit_card_pdf,
)
from .result_utils import (
    generate_annual_result_sheet_html,
    generate_marksheet_html,
    generate_marksheet_pdf,

)

import pdfkit
from decouple import config


def get_current_session(request=None):
    """Helper function to get the current academic session"""
    from datetime import date

    # Check if user has selected a specific session
    if request and hasattr(request, "session"):
        selected_session_id = request.session.get("selected_academic_session_id")
        if selected_session_id:
            try:
                current_session = AcademicSession.objects.get(id=selected_session_id)
                return current_session
            except AcademicSession.DoesNotExist:
                pass

    # Default logic: get current session based on date
    today = date.today()
    current_session = AcademicSession.objects.filter(
        start_date__lte=today, end_date__gte=today
    ).first()

    # If no current session, get the latest one
    if not current_session:
        current_session = AcademicSession.objects.order_by("-end_date").first()

    return current_session


@login_required
def exams(request: HttpRequest):
    role = get_user_role(request.user)
    context = {}

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
                        Q(term=current_term)
                        | Q(term__end_date__lt=today, examschedule__date__gte=today)
                    )
                    .prefetch_related("examschedule_set")
                    .distinct()
                )

                # Exam results for current term (only published results)
                current_results = ExamResult.objects.filter(
                    student=student,
                    exam__term=current_term,
                    status=ExamResult.Status.PUBLISHED,
                ).select_related("exam")

                # Group results by exam and calculate summaries
                exam_results = {}
                for result in current_results:
                    exam_id = result.exam.id
                    if exam_id not in exam_results:
                        exam_results[exam_id] = {
                            "exam": result.exam,
                            "subjects": [],
                            "total_marks": 0,
                            "obtained_marks": 0,
                        }
                    exam_results[exam_id]["subjects"].append(result)
                    exam_results[exam_id]["total_marks"] += float(result.total_marks)
                    if result.marks_obtained:
                        exam_results[exam_id]["obtained_marks"] += float(
                            result.marks_obtained
                        )

                # Calculate percentages and sort exams by date
                for exam_data in exam_results.values():
                    if exam_data["total_marks"] > 0:
                        exam_data["percentage"] = (
                            exam_data["obtained_marks"] / exam_data["total_marks"]
                        ) * 100
                    else:
                        exam_data["percentage"] = 0

                # Sort exams by name for consistent display
                sorted_exam_results = sorted(
                    exam_results.values(), key=lambda x: x["exam"].name
                )

                # For modal: all terms for the current session
                all_terms = Term.objects.filter(
                    academic_session=current_term.academic_session
                )

                context.update(
                    {
                        "upcoming_exams": upcoming_exams,
                        "exam_results": sorted_exam_results,
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

    return render(request, "academics/exams.html", context)


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
        buffer = dashboard_generate_admit_card_pdf(exam, student)

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
def teacher_exam_marking(request: HttpRequest):
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    try:
        if role == "Teacher":
            teacher = Teacher.objects.get(user=request.user)
            # Get assigned classrooms
            assigned_classrooms = teacher.classroom.all()
        else:  # Admin
            from students.models import Classroom

            assigned_classrooms = Classroom.objects.all()
        context = {
            "assigned_classrooms": assigned_classrooms,
        }
        return render(request, "academics/teacher_exam_marking.html", context)
    except Teacher.DoesNotExist:
        return HttpResponse("Teacher profile not found", status=404)


@login_required
def teacher_select_exam(request: HttpRequest, classroom_id: int):
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    try:
        classroom = Classroom.objects.get(id=classroom_id)

        if role == "Teacher":
            teacher = Teacher.objects.get(user=request.user)
            # Check if classroom is assigned to teacher
            if not teacher.classroom.filter(id=classroom_id).exists():
                return HttpResponse("Access denied", status=403)
            # Get assigned exams for this classroom
            assigned_exams = ExamAssignment.objects.filter(
                teacher=teacher, classroom=classroom
            ).select_related("exam")
        else:  # Admin
            # Get all exams for this classroom
            assigned_exams = ExamAssignment.objects.filter(
                classroom=classroom
            ).select_related("exam")

        context = {
            "classroom": classroom,
            "assigned_exams": assigned_exams,
        }
        return render(request, "academics/teacher_select_exam.html", context)
    except (Teacher.DoesNotExist, Classroom.DoesNotExist):
        return HttpResponse("Not found", status=404)


@login_required
def save_exam_results(request: HttpRequest, exam_id: int, classroom_id: int):
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return JsonResponse({"error": "Access denied"}, status=403)

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        exam = Exam.objects.get(id=exam_id)
        classroom = Classroom.objects.get(id=classroom_id)

        if role == "Teacher":
            teacher = Teacher.objects.get(user=request.user)
            # Check assignment
            if not ExamAssignment.objects.filter(
                teacher=teacher, exam=exam, classroom=classroom
            ).exists():
                return JsonResponse({"error": "Access denied"}, status=403)

        # Check if exam is locked
        locked_results = ExamResult.objects.filter(
            exam=exam, student__classroom=classroom, status=ExamResult.Status.LOCKED
        )
        if locked_results.exists():
            return JsonResponse({"error": "Exam results are locked"}, status=403)

        data = json.loads(request.body)
        action = data.get("action")  # "save_draft", "commit", "lock"

        students_data = data.get("students", [])

        for student_data in students_data:
            student_id = student_data["student_id"]
            subjects = student_data["subjects"]

            for subject_data in subjects:
                subject = subject_data["subject"]
                marks = subject_data.get("marks")
                grade = subject_data.get("grade", "")
                disabled = subject_data.get("disabled", False)

                # Get or create result
                result, created = ExamResult.objects.get_or_create(
                    student_id=student_id,
                    exam=exam,
                    subject=subject,
                    defaults={
                        "total_marks": Decimal("100"),
                        "submitted_by": request.user,
                    },
                )

                # Update marks, grade, and disabled status
                result.marks_obtained = Decimal(marks) if marks else None
                result.grade = grade
                result.marking_disabled = disabled

                # Set status based on action
                if action == "save_draft":
                    result.status = ExamResult.Status.DRAFT
                    result.submitted_at = None
                elif action == "commit":
                    result.status = ExamResult.Status.SUBMITTED
                    result.submitted_at = timezone.now()
                elif action == "lock":
                    result.status = ExamResult.Status.LOCKED
                    result.submitted_at = timezone.now()

                result.save()

        return JsonResponse({"success": True})
    except (Teacher.DoesNotExist, Exam.DoesNotExist, Classroom.DoesNotExist):
        return JsonResponse({"error": "Not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def download_import_template(request: HttpRequest, exam_id: int, classroom_id: int):
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    try:
        exam = Exam.objects.get(id=exam_id)
        classroom = Classroom.objects.get(id=classroom_id)

        if role == "Teacher":
            teacher = Teacher.objects.get(user=request.user)
            # Check assignment
            if not ExamAssignment.objects.filter(
                teacher=teacher, exam=exam, classroom=classroom
            ).exists():
                return HttpResponse("Access denied", status=403)

        # Get students and exam schedules
        students = Student.objects.filter(classroom=classroom).order_by("roll_no")
        exam_schedules = ExamSchedule.objects.filter(exam=exam).order_by("subject")

        # Create CSV response
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{exam.name}_{classroom.grade}{classroom.section or ""}_import_template.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(["roll_no", "subject", "marks", "grade"])

        # Add sample data for each student and subject combination
        for student in students[:3]:  # Show first 3 students as examples
            for schedule in exam_schedules:
                writer.writerow(
                    [
                        student.roll_no,
                        schedule.subject,
                        "85",  # Sample marks
                        "A",  # Sample grade
                    ]
                )

        return response
    except (Teacher.DoesNotExist, Exam.DoesNotExist, Classroom.DoesNotExist):
        return HttpResponse("Not found", status=404)


@login_required
def bulk_import_results(request: HttpRequest, exam_id: int, classroom_id: int):
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return JsonResponse({"error": "Access denied"}, status=403)

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        exam = Exam.objects.get(id=exam_id)
        classroom = Classroom.objects.get(id=classroom_id)

        if role == "Teacher":
            teacher = Teacher.objects.get(user=request.user)
            # Check assignment
            if not ExamAssignment.objects.filter(
                teacher=teacher, exam=exam, classroom=classroom
            ).exists():
                return JsonResponse({"error": "Access denied"}, status=403)

        # Check if exam is locked
        if ExamResult.objects.filter(
            exam=exam, student__classroom=classroom, status=ExamResult.Status.LOCKED
        ).exists():
            return JsonResponse({"error": "Exam results are locked"}, status=403)

        # Check if marks entry is open
        if not exam.marks_entry_open:
            return JsonResponse(
                {"error": "Marks entry is currently closed for this exam"}, status=403
            )

        file = request.FILES.get("file")
        if not file:
            return JsonResponse({"error": "No file provided"}, status=400)

        # Process CSV or Excel file
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        elif file.name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file)
        else:
            return JsonResponse({"error": "Unsupported file format"}, status=400)

        # Expected columns: roll_no, subject, marks, grade
        required_columns = ["roll_no", "subject", "marks"]
        if not all(col in df.columns for col in required_columns):
            return JsonResponse(
                {"error": "Missing required columns: roll_no, subject, marks"},
                status=400,
            )

        students = {
            str(student.roll_no).strip(): student
            for student in Student.objects.filter(classroom=classroom)
        }

        for _, row in df.iterrows():
            roll_no = str(row["roll_no"]).strip()
            subject = str(row["subject"]).strip()
            marks = row.get("marks")
            grade = str(row.get("grade", "")).strip() if "grade" in df.columns else ""

            if roll_no not in students:
                continue  # Skip invalid roll numbers

            student = students[roll_no]

            # Get or create result
            result, created = ExamResult.objects.get_or_create(
                student=student,
                exam=exam,
                subject=subject,
                defaults={
                    "total_marks": Decimal("100"),
                    "submitted_by": request.user,
                },
            )

            # Update marks and grade
            try:
                if marks is not None and str(marks).strip():
                    result.marks_obtained = Decimal(str(marks).strip())
                else:
                    result.marks_obtained = None
            except (ValueError, TypeError):
                result.marks_obtained = None

            result.grade = grade.strip() if grade else ""
            result.status = ExamResult.Status.DRAFT
            result.save()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def export_results(request: HttpRequest, exam_id: int, classroom_id: int):
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    try:
        exam = Exam.objects.get(id=exam_id)
        classroom = Classroom.objects.get(id=classroom_id)

        if role == "Teacher":
            teacher = Teacher.objects.get(user=request.user)
            # Check assignment
            if not ExamAssignment.objects.filter(
                teacher=teacher, exam=exam, classroom=classroom
            ).exists():
                return HttpResponse("Access denied", status=403)

        # Get all results for this exam and classroom
        results = (
            ExamResult.objects.filter(exam=exam, student__classroom=classroom)
            .select_related("student")
            .order_by("student__roll_no", "subject")
        )

        # Create CSV response
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{exam.name}_{classroom.grade}{classroom.section or ""}_results.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                "Roll No",
                "Student Name",
                "Subject",
                "Marks Obtained",
                "Total Marks",
                "Grade",
                "Status",
            ]
        )

        for result in results:
            writer.writerow(
                [
                    result.student.roll_no,
                    result.student.user.get_full_name(),
                    result.subject,
                    result.marks_obtained or "",
                    result.total_marks,
                    result.grade or "",
                    result.status,
                ]
            )

        return response
    except (Teacher.DoesNotExist, Exam.DoesNotExist, Classroom.DoesNotExist):
        return HttpResponse("Not found", status=404)


@login_required
def get_exam_results(request: HttpRequest, term_id: int):
    role = get_user_role(request.user)
    if role != "Student":
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        student = Student.objects.get(user=request.user)
        term = Term.objects.get(id=term_id)
        results = ExamResult.objects.filter(
            student=student, exam__term=term, status=ExamResult.Status.PUBLISHED
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
def teacher_exam_marking(request: HttpRequest):
    role = get_user_role(request.user)
    if role != "Teacher":
        return HttpResponse("Access denied", status=403)

    try:
        teacher = Teacher.objects.get(user=request.user)
        # Get assigned classrooms
        assigned_classrooms = teacher.classroom.all()
        context = {
            "assigned_classrooms": assigned_classrooms,
        }
        return render(request, "academics/teacher_exam_marking.html", context)
    except Teacher.DoesNotExist:
        return HttpResponse("Teacher profile not found", status=404)


@login_required
def teacher_select_exam(request: HttpRequest, classroom_id: int):
    role = get_user_role(request.user)
    if role != "Teacher":
        return HttpResponse("Access denied", status=403)

    try:
        teacher = Teacher.objects.get(user=request.user)
        classroom = Classroom.objects.get(id=classroom_id)

        # Check if classroom is assigned to teacher
        if not teacher.classroom.filter(id=classroom_id).exists():
            return HttpResponse("Access denied", status=403)

        # Get assigned exams for this classroom
        assigned_exams = ExamAssignment.objects.filter(
            teacher=teacher, classroom=classroom
        ).select_related("exam")

        context = {
            "classroom": classroom,
            "assigned_exams": assigned_exams,
        }
        return render(request, "academics/teacher_select_exam.html", context)
    except (Teacher.DoesNotExist, Classroom.DoesNotExist):
        return HttpResponse("Not found", status=404)


@login_required
def teacher_mark_exam(request: HttpRequest, exam_id: int, classroom_id: int):
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    try:
        exam = Exam.objects.get(id=exam_id)
        classroom = Classroom.objects.get(id=classroom_id)

        if role == "Teacher":
            teacher = Teacher.objects.get(user=request.user)
            # Check assignment
            if not ExamAssignment.objects.filter(
                teacher=teacher, exam=exam, classroom=classroom
            ).exists():
                return HttpResponse("Access denied", status=403)

        # Get students in classroom
        students = Student.objects.filter(classroom=classroom).order_by("roll_no")

        # Get exam schedule for subjects
        exam_schedules = ExamSchedule.objects.filter(exam=exam).order_by("subject")

        # Get existing results
        existing_results = ExamResult.objects.filter(
            exam=exam, student__classroom=classroom
        ).select_related("student")

        # Create results dict for easy lookup
        results_dict = {}
        for result in existing_results:
            key = f"{result.student.id}_{result.subject}"
            results_dict[key] = result

        # Check if exam is locked
        is_locked = any(
            result.status == ExamResult.Status.LOCKED for result in existing_results
        )

        # Check if marks entry is open
        marks_entry_open = exam.marks_entry_open

        context = {
            "exam": exam,
            "classroom": classroom,
            "students": students,
            "exam_schedules": exam_schedules,
            "results_dict": results_dict,
            "is_locked": is_locked,
            "marks_entry_open": marks_entry_open,
            "user_role": role,
        }
        return render(request, "academics/teacher_mark_exam.html", context)
    except (Teacher.DoesNotExist, Exam.DoesNotExist, Classroom.DoesNotExist):
        return HttpResponse("Not found", status=404)


@login_required
def save_exam_results(request: HttpRequest, exam_id: int, classroom_id: int):
    role = get_user_role(request.user)
    if role != "Teacher":
        return JsonResponse({"error": "Access denied"}, status=403)

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        teacher = Teacher.objects.get(user=request.user)
        exam = Exam.objects.get(id=exam_id)
        classroom = Classroom.objects.get(id=classroom_id)

        # Check assignment
        if not ExamAssignment.objects.filter(
            teacher=teacher, exam=exam, classroom=classroom
        ).exists():
            return JsonResponse({"error": "Access denied"}, status=403)

        # Check if exam is locked
        locked_results = ExamResult.objects.filter(
            exam=exam, student__classroom=classroom, status=ExamResult.Status.LOCKED
        )
        if locked_results.exists():
            return JsonResponse({"error": "Exam results are locked"}, status=403)

        # Check if marks entry is open
        if not exam.marks_entry_open:
            return JsonResponse(
                {"error": "Marks entry is currently closed for this exam"}, status=403
            )

        data = json.loads(request.body)
        action = data.get("action")  # "save_draft", "commit", "lock"

        students_data = data.get("students", [])

        for student_data in students_data:
            student_id = student_data["student_id"]
            subjects = student_data["subjects"]

            for subject_data in subjects:
                subject = subject_data["subject"]
                marks = subject_data.get("marks")
                grade = subject_data.get("grade", "")

                # Get or create result
                result, created = ExamResult.objects.get_or_create(
                    student_id=student_id,
                    exam=exam,
                    subject=subject,
                    defaults={
                        "total_marks": Decimal("100"),
                        "submitted_by": request.user,
                    },
                )

                # Update marks and grade
                result.marks_obtained = Decimal(marks) if marks else None
                result.grade = grade

                # Set status based on action
                if action == "save_draft":
                    result.status = ExamResult.Status.DRAFT
                    result.submitted_at = None
                elif action == "commit":
                    result.status = ExamResult.Status.SUBMITTED
                    result.submitted_at = timezone.now()
                elif action == "lock":
                    result.status = ExamResult.Status.LOCKED
                    result.submitted_at = timezone.now()

                result.save()

        # If action was "lock", create system alert for admin
        if action == "lock":
            Notice.objects.create(
                title=f"Exam Results Locked: {exam.name} - {classroom}",
                content=f"Teacher {request.user.get_full_name()} has locked the exam results for {exam.name} in class {classroom}.",
                notice_type=Notice.NoticeType.SYSTEM_ALERT,
                created_by=request.user,
            )

        return JsonResponse({"success": True})
    except (Teacher.DoesNotExist, Exam.DoesNotExist, Classroom.DoesNotExist):
        return JsonResponse({"error": "Not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def admin_exam_management(request: HttpRequest):
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    current_session = get_current_session(request)
    terms = Term.objects.filter(academic_session=current_session).order_by("start_date")
    exams = (
        Exam.objects.filter(term__academic_session=current_session)
        .select_related("term")
        .order_by("term__start_date", "name")
    )

    context = {
        "terms": terms,
        "exams": exams,
        "current_session": current_session,
    }
    return render(request, "academics/admin_exam_management.html", context)


@login_required
def admin_create_exam(request: HttpRequest):
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    if request.method == "POST":
        term_id = request.POST.get("term")
        name = request.POST.get("name")
        description = request.POST.get("description", "")
        is_yearly_final = request.POST.get("is_yearly_final") == "on"

        try:
            term = Term.objects.get(id=term_id)
            exam = Exam.objects.create(
                term=term,
                name=name,
                description=description,
                is_yearly_final=is_yearly_final,
            )
            messages.success(request, f"Exam '{exam.name}' created successfully.")
            return redirect("academics:admin_exam_management")
        except Term.DoesNotExist:
            messages.error(request, "Invalid term selected.")
        except Exception as e:
            messages.error(request, f"Error creating exam: {str(e)}")

    current_session = get_current_session(request)
    terms = Term.objects.filter(academic_session=current_session).order_by("start_date")

    context = {
        "terms": terms,
        "current_session": current_session,
    }
    return render(request, "academics/admin_create_exam.html", context)


@login_required
def admin_edit_exam(request: HttpRequest, exam_id: int):
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    try:
        exam = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        messages.error(request, "Exam not found.")
        return redirect("academics:admin_exam_management")

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description", "")
        is_yearly_final = request.POST.get("is_yearly_final") == "on"
        marks_entry_open = request.POST.get("marks_entry_open") == "on"

        exam.name = name
        exam.description = description
        exam.is_yearly_final = is_yearly_final
        exam.marks_entry_open = marks_entry_open
        exam.save()

        messages.success(request, f"Exam '{exam.name}' updated successfully.")
        return redirect("academics:admin_exam_management")

    context = {
        "exam": exam,
    }
    return render(request, "academics/admin_edit_exam.html", context)


@login_required
def admin_assign_subjects(request: HttpRequest):
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    current_session = get_current_session(request)
    exams = (
        Exam.objects.filter(term__academic_session=current_session)
        .select_related("term")
        .order_by("term__start_date", "name")
    )
    teachers = Teacher.objects.all().order_by("user__first_name", "user__last_name")
    classrooms = Classroom.objects.all().order_by("grade", "section")

    assignments = ExamAssignment.objects.filter(
        exam__term__academic_session=current_session
    ).select_related("exam", "teacher", "classroom")

    context = {
        "exams": exams,
        "teachers": teachers,
        "classrooms": classrooms,
        "assignments": assignments,
        "current_session": current_session,
    }
    return render(request, "academics/admin_assign_subjects.html", context)


@login_required
def admin_create_assignment(request: HttpRequest):
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    exam_id = request.POST.get("exam")
    teacher_id = request.POST.get("teacher")
    classroom_id = request.POST.get("classroom")

    try:
        exam = Exam.objects.get(id=exam_id)
        teacher = Teacher.objects.get(id=teacher_id)
        classroom = Classroom.objects.get(id=classroom_id)

        assignment, created = ExamAssignment.objects.get_or_create(
            exam=exam,
            teacher=teacher,
            classroom=classroom,
        )

        if created:
            return JsonResponse(
                {"success": True, "message": "Assignment created successfully."}
            )
        else:
            return JsonResponse(
                {"success": False, "message": "Assignment already exists."}
            )

    except (Exam.DoesNotExist, Teacher.DoesNotExist, Classroom.DoesNotExist):
        return JsonResponse({"error": "Invalid data provided"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def admin_delete_assignment(request: HttpRequest, assignment_id: int):
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        assignment = ExamAssignment.objects.get(id=assignment_id)
        assignment.delete()
        return JsonResponse({"success": True})
    except ExamAssignment.DoesNotExist:
        return JsonResponse({"error": "Assignment not found"}, status=404)


@login_required
def admin_marks_entry_control(request: HttpRequest):
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    current_session = get_current_session(request)
    exams = (
        Exam.objects.filter(term__academic_session=current_session)
        .select_related("term")
        .order_by("term__start_date", "name")
    )

    context = {
        "exams": exams,
        "current_session": current_session,
    }
    return render(request, "academics/admin_marks_entry_control.html", context)


@login_required
def admin_toggle_marks_entry(request: HttpRequest, exam_id: int):
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        exam = Exam.objects.get(id=exam_id)
        exam.marks_entry_open = not exam.marks_entry_open
        exam.save()
        return JsonResponse(
            {"success": True, "marks_entry_open": exam.marks_entry_open}
        )
    except Exam.DoesNotExist:
        return JsonResponse({"error": "Exam not found"}, status=404)


@login_required
def admin_review_results(request: HttpRequest):
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    current_session = get_current_session(request)
    exams = (
        Exam.objects.filter(term__academic_session=current_session)
        .select_related("term")
        .order_by("term__start_date", "name")
    )

    context = {
        "exams": exams,
        "current_session": current_session,
    }
    return render(request, "academics/admin_review_results.html", context)


@login_required
def admin_get_exam_results(request: HttpRequest, exam_id: int):
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        exam = Exam.objects.get(id=exam_id)
        results = (
            ExamResult.objects.filter(exam=exam)
            .select_related("student", "student__classroom")
            .order_by(
                "student__classroom__grade",
                "student__classroom__section",
                "student__roll_no",
                "subject",
            )
        )

        results_data = []
        for result in results:
            results_data.append(
                {
                    "id": result.id,
                    "student_name": result.student.user.get_full_name(),
                    "roll_no": result.student.roll_no,
                    "classroom": f"{result.student.classroom.grade} {result.student.classroom.section or ''}",
                    "subject": result.subject,
                    "marks_obtained": (
                        str(result.marks_obtained) if result.marks_obtained else None
                    ),
                    "total_marks": str(result.total_marks),
                    "grade": result.grade,
                    "status": result.status,
                    "submitted_by": (
                        result.submitted_by.get_full_name()
                        if result.submitted_by
                        else None
                    ),
                    "submitted_at": (
                        result.submitted_at.strftime("%Y-%m-%d %H:%M")
                        if result.submitted_at
                        else None
                    ),
                }
            )

        return JsonResponse({"results": results_data})
    except Exam.DoesNotExist:
        return JsonResponse({"error": "Exam not found"}, status=404)


@login_required
def admin_publish_results(request: HttpRequest, exam_id: int):
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        exam = Exam.objects.get(id=exam_id)

        # Get all results that will be published
        results_to_publish = ExamResult.objects.filter(
            exam=exam,
            status__in=[ExamResult.Status.SUBMITTED, ExamResult.Status.LOCKED],
        ).select_related("student")

        # Update all results for this exam to PUBLISHED
        updated_count = ExamResult.objects.filter(exam=exam).update(
            status=ExamResult.Status.PUBLISHED
        )

        # Create result documents for students
        from students.models import Document
        from django.core.files.base import ContentFile

        for result in results_to_publish:
            try:
                # Generate individual result PDF for the student
                html_content = generate_individual_result_html(result.student, exam)
                pdf_buffer = pdfkit.from_string(
                    html_content,
                    False,
                    options={
                        "page-size": "A4",
                        "margin-top": "1in",
                        "margin-right": "1in",
                        "margin-bottom": "1in",
                        "margin-left": "1in",
                    },
                )

                # Create document record
                filename = f"exam_result_{exam.name}_{result.student.roll_no}.pdf"
                document = Document.objects.create(
                    student=result.student,
                    name=f"Exam Result - {exam.name}",
                    file=ContentFile(pdf_buffer, name=filename),
                )

                # For final exams, create marksheet certificates for passed students
                if exam.is_yearly_final:
                    student_results = ExamResult.objects.filter(
                        student=result.student,
                        exam=exam,
                        status=ExamResult.Status.PUBLISHED,
                    )

                    # Calculate overall result
                    total_marks = sum(float(r.total_marks) for r in student_results)
                    obtained_marks = sum(
                        float(r.marks_obtained or 0) for r in student_results
                    )
                    percentage = (
                        (obtained_marks / total_marks * 100) if total_marks > 0 else 0
                    )

                    if percentage >= 33:  # Passed
                        from students.models import Certificate, CertificateType

                        # Get or create marksheet certificate type
                        marksheet_type, created = CertificateType.objects.get_or_create(
                            name="Marksheet",
                            defaults={
                                "description": "Final exam marksheet certificate",
                                "is_active": True,
                            },
                        )

                        # Generate marksheet PDF
                        marksheet_html = generate_marksheet_html(
                            result.student, exam, student_results
                        )
                        marksheet_pdf = pdfkit.from_string(
                            marksheet_html,
                            False,
                            options={
                                "page-size": "A4",
                                "margin-top": "0.5in",
                                "margin-right": "0.5in",
                                "margin-bottom": "0.5in",
                                "margin-left": "0.5in",
                            },
                        )

                        # Create certificate
                        certificate = Certificate.objects.create(
                            student=result.student,
                            certificate_type=marksheet_type,
                            status=Certificate.Status.APPROVED,
                        )

                        # Save the PDF file
                        cert_filename = f"marksheet_{exam.term.academic_session.year}_{result.student.roll_no}.pdf"
                        certificate.file.save(cert_filename, ContentFile(marksheet_pdf))

            except Exception as e:
                # Log error but continue with other students
                print(
                    f"Error creating document for student {result.student.roll_no}: {e}"
                )
                continue

        return JsonResponse({"success": True, "published_count": updated_count})
    except Exam.DoesNotExist:
        return JsonResponse({"error": "Exam not found"}, status=404)


@login_required
def admin_delete_exam(request: HttpRequest, exam_id: int):
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        exam = Exam.objects.get(id=exam_id)
        exam_name = exam.name
        exam.delete()
        return JsonResponse(
            {"success": True, "message": f"Exam '{exam_name}' deleted successfully."}
        )
    except Exam.DoesNotExist:
        return JsonResponse({"error": "Exam not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ===== RESULT MANAGEMENT VIEWS =====


@login_required
def result_management(request: HttpRequest):
    """Main result management page for admins"""
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    current_session = get_current_session(request)
    exams = (
        Exam.objects.filter(term__academic_session=current_session)
        .select_related("term")
        .order_by("term__start_date", "name")
    )

    context = {
        "exams": exams,
        "current_session": current_session,
    }
    return render(request, "academics/result_management.html", context)


@login_required
def search_class_results(request: HttpRequest):
    """Search and view results for a particular class"""
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    current_session = get_current_session(request)
    exams = (
        Exam.objects.filter(term__academic_session=current_session)
        .select_related("term")
        .order_by("term__start_date", "name")
    )
    classrooms = Classroom.objects.all().order_by("grade", "section")

    context = {
        "exams": exams,
        "classrooms": classrooms,
        "current_session": current_session,
    }
    return render(request, "academics/search_class_results.html", context)


@login_required
def get_class_results(request: HttpRequest, exam_id: int, classroom_id: int):
    """Get results data for a specific exam and classroom"""
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        exam = Exam.objects.get(id=exam_id)
        classroom = Classroom.objects.get(id=classroom_id)

        if role == "Teacher":
            teacher = Teacher.objects.get(user=request.user)
            # Check if teacher is assigned to this classroom
            if not ExamAssignment.objects.filter(
                teacher=teacher, exam=exam, classroom=classroom
            ).exists():
                return JsonResponse({"error": "Access denied"}, status=403)

        # Get results for this exam and classroom (SUBMITTED and above for review)
        results = (
            ExamResult.objects.filter(
                exam=exam,
                student__classroom=classroom,
                status__in=[
                    ExamResult.Status.SUBMITTED,
                    ExamResult.Status.LOCKED,
                    ExamResult.Status.PUBLISHED,
                ],
            )
            .select_related("student")
            .order_by("student__roll_no", "subject")
        )

        # Group results by student
        students_data = {}
        subjects = set()

        for result in results:
            student_id = result.student.id
            if student_id not in students_data:
                students_data[student_id] = {
                    "student": result.student,
                    "results": {},
                    "total_marks": 0,
                    "obtained_marks": 0,
                }

            students_data[student_id]["results"][result.subject] = result
            students_data[student_id]["total_marks"] += float(result.total_marks)
            if result.marks_obtained:
                students_data[student_id]["obtained_marks"] += float(
                    result.marks_obtained
                )
            subjects.add(result.subject)

        # Calculate percentages and ranks
        students_list = list(students_data.values())
        for student_data in students_list:
            if student_data["total_marks"] > 0:
                student_data["percentage"] = (
                    student_data["obtained_marks"] / student_data["total_marks"]
                ) * 100
            else:
                student_data["percentage"] = 0

        # Sort by percentage for ranking
        students_list.sort(key=lambda x: x["percentage"], reverse=True)
        for rank, student_data in enumerate(students_list, 1):
            student_data["rank"] = rank

        # Prepare response data
        response_data = {
            "exam": {
                "name": exam.name,
                "term": exam.term.name,
                "session": exam.term.academic_session.year,
            },
            "classroom": {
                "grade": classroom.grade,
                "section": classroom.section,
            },
            "subjects": sorted(list(subjects)),
            "students": [
                {
                    "id": student_data["student"].id,
                    "roll_no": student_data["student"].roll_no,
                    "name": student_data["student"].user.get_full_name(),
                    "total_marks": student_data["total_marks"],
                    "obtained_marks": student_data["obtained_marks"],
                    "percentage": round(student_data["percentage"], 2),
                    "rank": student_data["rank"],
                    "results": {
                        subject: (
                            {
                                "marks_obtained": result.marks_obtained,
                                "grade": result.grade,
                            }
                            if result
                            else None
                        )
                        for subject, result in student_data["results"].items()
                    },
                }
                for student_data in students_list
            ],
        }

        return JsonResponse(response_data)
    except (Exam.DoesNotExist, Classroom.DoesNotExist):
        return JsonResponse({"error": "Not found"}, status=404)


@login_required
def declare_class_results(request: HttpRequest, exam_id: int, classroom_id: int):
    """Declare results for a class and generate PDF"""
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    try:
        exam = Exam.objects.get(id=exam_id)
        classroom = Classroom.objects.get(id=classroom_id)

        if role == "Teacher":
            teacher = Teacher.objects.get(user=request.user)
            if not ExamAssignment.objects.filter(
                teacher=teacher, exam=exam, classroom=classroom
            ).exists():
                return HttpResponse("Access denied", status=403)

        # Get results for review/declaration
        results = (
            ExamResult.objects.filter(
                exam=exam,
                student__classroom=classroom,
                status__in=[
                    ExamResult.Status.SUBMITTED,
                    ExamResult.Status.LOCKED,
                    ExamResult.Status.PUBLISHED,
                ],
            )
            .select_related("student")
            .order_by("student__roll_no", "subject")
        )

        if not results:
            messages.error(
                request, "No published results found for this exam and class."
            )
            return redirect("academics:search_class_results")

        # Generate HTML content for PDF
        html_content = generate_result_declaration_html(exam, classroom, results)

        # Generate PDF using pdfkit
        pdf_options = {
            "page-size": "A4",
            "margin-top": "1in",
            "margin-right": "1in",
            "margin-bottom": "1in",
            "margin-left": "1in",
        }

        pdf_buffer = pdfkit.from_string(html_content, False, options=pdf_options)

        # Return PDF response
        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="result_declaration_{exam.name}_{classroom.grade}{classroom.section or ""}.pdf"'
        )
        return response

    except (Exam.DoesNotExist, Classroom.DoesNotExist):
        messages.error(request, "Exam or classroom not found.")
        return redirect("academics:search_class_results")


@login_required
def annual_result_sheet(request: HttpRequest):
    """Generate annual result sheet for a class"""
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    current_session = get_current_session(request)
    classrooms = Classroom.objects.all().order_by("grade", "section")

    context = {
        "classrooms": classrooms,
        "current_session": current_session,
    }
    return render(request, "academics/annual_result_sheet.html", context)


@login_required
def generate_annual_result_sheet(request: HttpRequest, classroom_id: int):
    """Generate annual result sheet PDF for a classroom"""
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    try:
        classroom = Classroom.objects.get(id=classroom_id)
        current_session = get_current_session(request)

        # Get all published exams for the current session
        exams = Exam.objects.filter(
            term__academic_session=current_session, is_yearly_final=True
        ).order_by("term__start_date")

        if not exams:
            messages.error(request, "No final exams found for the current session.")
            return redirect("academics:annual_result_sheet")

        # Get all students in the classroom
        students = Student.objects.filter(classroom=classroom).order_by("roll_no")

        # Generate HTML content
        html_content = generate_annual_result_sheet_html(
            classroom, current_session, exams, students
        )

        # Generate PDF
        pdf_options = {
            "page-size": "A4",
            "orientation": "landscape",
            "margin-top": "0.5in",
            "margin-right": "0.5in",
            "margin-bottom": "0.5in",
            "margin-left": "0.5in",
        }

        pdf_buffer = pdfkit.from_string(html_content, False, options=pdf_options)

        # Return PDF response
        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="annual_result_sheet_{classroom.grade}{classroom.section or ""}_{current_session.year}.pdf"'
        )
        return response

    except Classroom.DoesNotExist:
        messages.error(request, "Classroom not found.")
        return redirect("academics:annual_result_sheet")


def generate_result_declaration_html(exam, classroom, results):
    """Generate HTML content for result declaration PDF"""
    # Group results by student
    students_data = {}
    subjects = set()

    for result in results:
        student_id = result.student.id
        if student_id not in students_data:
            students_data[student_id] = {
                "student": result.student,
                "results": {},
                "total_marks": 0,
                "obtained_marks": 0,
            }

        students_data[student_id]["results"][result.subject] = result
        students_data[student_id]["total_marks"] += float(result.total_marks)
        if result.marks_obtained:
            students_data[student_id]["obtained_marks"] += float(result.marks_obtained)
        subjects.add(result.subject)

    # Calculate percentages and determine results
    students_list = list(students_data.values())
    for student_data in students_list:
        if student_data["total_marks"] > 0:
            student_data["percentage"] = (
                student_data["obtained_marks"] / student_data["total_marks"]
            ) * 100
            student_data["result"] = (
                "Pass" if student_data["percentage"] >= 33 else "Fail"
            )
        else:
            student_data["percentage"] = 0
            student_data["result"] = "N/A"

    # Sort by roll number
    students_list.sort(key=lambda x: x["student"].roll_no)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Result Declaration - {exam.name}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                line-height: 1.6;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #333;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .school-name {{
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .exam-info {{
                font-size: 18px;
                margin-bottom: 10px;
            }}
            .class-info {{
                font-size: 16px;
                margin-bottom: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            th, td {{
                border: 1px solid #333;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #f0f0f0;
                font-weight: bold;
            }}
            .text-center {{
                text-align: center;
            }}
            .pass {{
                color: green;
            }}
            .fail {{
                color: red;
            }}
            .footer {{
                margin-top: 50px;
                display: flex;
                justify-content: space-between;
            }}
            .signature {{
                width: 200px;
                text-align: center;
                border-top: 1px solid #333;
                padding-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="school-name">{config('SCHOOL_NAME', default='SCHOOL')}</div>
            <div class="exam-info">Result Declaration - {exam.name}</div>
            <div class="class-info">Class: {classroom.grade} {classroom.section or ""} | Session: {exam.term.academic_session.year}</div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>S.No.</th>
                    <th>Admission/Roll No.</th>
                    <th>Student Name</th>
                    <th>Total Marks</th>
                    <th>Obtained Marks</th>
                    <th>Percentage</th>
                    <th>Result</th>
                </tr>
            </thead>
            <tbody>
    """

    for i, student_data in enumerate(students_list, 1):
        student = student_data["student"]
        result_class = "pass" if student_data["result"] == "Pass" else "fail"

        html += f"""
                <tr>
                    <td class="text-center">{i}</td>
                    <td class="text-center">{student.roll_no}</td>
                    <td>{student.user.get_full_name()}</td>
                    <td class="text-center">{student_data["total_marks"]:.0f}</td>
                    <td class="text-center">{student_data["obtained_marks"]:.0f}</td>
                    <td class="text-center">{student_data["percentage"]:.2f}%</td>
                    <td class="text-center {result_class}">{student_data["result"]}</td>
                </tr>
        """

    html += """
            </tbody>
        </table>

        <div class="footer">
            <div class="signature">
                <div>Checked By</div>
            </div>
            <div class="signature">
                <div>Controller of Exam</div>
            </div>
            <div class="signature">
                <div>Principal</div>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def generate_individual_result_html(student, exam):
    """Generate HTML content for individual student result PDF"""
    # Get student's results for this exam
    results = ExamResult.objects.filter(
        student=student, exam=exam, status=ExamResult.Status.PUBLISHED
    ).order_by("subject")

    # Calculate totals
    total_marks = sum(float(r.total_marks) for r in results)
    obtained_marks = sum(float(r.marks_obtained or 0) for r in results)
    percentage = (obtained_marks / total_marks * 100) if total_marks > 0 else 0
    result_status = "Pass" if percentage >= 33 else "Fail"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Exam Result - {student.user.get_full_name()}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                line-height: 1.6;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #333;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .school-name {{
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .exam-info {{
                font-size: 18px;
                margin-bottom: 10px;
            }}
            .student-info {{
                margin-bottom: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            th, td {{
                border: 1px solid #333;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #f0f0f0;
                font-weight: bold;
            }}
            .text-center {{
                text-align: center;
            }}
            .summary {{
                background: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 30px;
            }}
            .footer {{
                margin-top: 50px;
                display: flex;
                justify-content: space-between;
            }}
            .signature {{
                width: 200px;
                text-align: center;
                border-top: 1px solid #333;
                padding-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="school-name">{config('SCHOOL_NAME', default='SCHOOL')}</div>
            <div class="exam-info">Exam Result - {exam.name}</div>
            <div>Term: {exam.term.name} | Session: {exam.term.academic_session.year}</div>
        </div>

        <div class="student-info">
            <strong>Student Name:</strong> {student.user.get_full_name()}<br>
            <strong>Roll No:</strong> {student.roll_no}<br>
            <strong>Admission No:</strong> {student.admission_no}<br>
            <strong>Class:</strong> {student.classroom}<br>
            <strong>Father's Name:</strong> {student.father_name}<br>
            <strong>Mother's Name:</strong> {student.mother_name}
        </div>

        <table>
            <thead>
                <tr>
                    <th>Subject</th>
                    <th class="text-center">Max Marks</th>
                    <th class="text-center">Marks Obtained</th>
                    <th class="text-center">Grade</th>
                </tr>
            </thead>
            <tbody>
    """

    for result in results:
        html += f"""
                <tr>
                    <td>{result.subject}</td>
                    <td class="text-center">{result.total_marks}</td>
                    <td class="text-center">{result.marks_obtained or 'N/A'}</td>
                    <td class="text-center">{result.grade or 'N/A'}</td>
                </tr>
        """

    html += f"""
            </tbody>
        </table>

        <div class="summary">
            <strong>Total Marks:</strong> {total_marks:.0f}<br>
            <strong>Marks Obtained:</strong> {obtained_marks:.0f}<br>
            <strong>Percentage:</strong> {percentage:.2f}%<br>
            <strong>Result:</strong> {result_status}
        </div>

        <div class="footer">
            <div class="signature">
                <div>Class Teacher</div>
            </div>
            <div class="signature">
                <div>Principal</div>
            </div>
        </div>
    </body>
    </html>
    """


@login_required
def student_marksheets(request: HttpRequest):
    """View for generating individual student marksheets"""
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    current_session = get_current_session(request)
    classrooms = Classroom.objects.all().order_by("grade", "section")

    context = {
        "classrooms": classrooms,
        "current_session": current_session,
    }
    return render(request, "academics/student_marksheets.html", context)


@login_required
def get_students_for_marksheet(request: HttpRequest, classroom_id: int):
    """Get students for a classroom for marksheet generation"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        classroom = Classroom.objects.get(id=classroom_id)
        students = Student.objects.filter(classroom=classroom).order_by("roll_no")

        students_data = []
        for student in students:
            students_data.append(
                {
                    "id": student.id,
                    "roll_no": student.roll_no,
                    "name": student.user.get_full_name(),
                    "admission_no": student.admission_no,
                }
            )

        return JsonResponse({"students": students_data})
    except Classroom.DoesNotExist:
        return JsonResponse({"error": "Classroom not found"}, status=404)


@login_required
def generate_marksheet(request: HttpRequest, student_id: int):
    """
    Generate marksheet PDF for a specific student for the yearly final exam
    of the current academic session.
    """
    role = get_user_role(request.user)

    if role != "Admin":
        # Allow teachers/staff to also generate marksheet if necessary,
        # but the request explicitly limits to Admin.
        return HttpResponse("Access denied", status=403)

    try:
        # Use select_related/prefetch_related if fetching related data to avoid N+1 queries
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return HttpResponse("Student not found", status=404)

    # Get current session
    current_session = get_current_session(request)

    # Get the final exam for the current session (assuming there is only one)
    try:
        final_exam = Exam.objects.get(
            term__academic_session=current_session, is_yearly_final=True
        )
    except Exam.DoesNotExist:
        messages.error(
            request, f"No yearly final exam found for session {current_session.year}."
        )
        return redirect("academics:student_marksheets")
    except Exam.MultipleObjectsReturned:
        messages.error(
            request, "Multiple final exams found. Please check your exam setup."
        )
        return redirect("academics:student_marksheets")

    # Get student's results for the final exam
    results = (
        ExamResult.objects.filter(
            student=student,
            exam=final_exam,
            status=ExamResult.Status.PUBLISHED,
        )
        .select_related("subject", "exam__term__academic_session")
        .order_by("subject")
    )

    if not results.exists():
        messages.error(
            request,
            f"No marksheet available for {student.user.get_full_name()}. No published results found for the final exam.",
        )
        return redirect("academics:student_marksheets")

    # Generate marksheet PDF using the utility function
    try:
        # We pass the single final_exam object, and the results queryset
        pdf_buffer = generate_marksheet_pdf(student, final_exam, results)

        # Return PDF response
        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        filename = f"marksheet_{student.roll_no}_{current_session.year}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        # This catches errors like pdfkit/wkhtmltopdf being misconfigured or failing
        messages.error(request, f"Error generating marksheet PDF: {e}")
        # Optionally log the error here
        return redirect("academics:student_marksheets")
