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
from dashboard.pdf_utils import (
    generate_exam_timetable_pdf,
    generate_admit_card_pdf as dashboard_generate_admit_card_pdf,
)

from django import template

register = template.Library()


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

        return JsonResponse({"success": True})
    except (Teacher.DoesNotExist, Exam.DoesNotExist, Classroom.DoesNotExist):
        return JsonResponse({"error": "Not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def download_import_template(request: HttpRequest, exam_id: int, classroom_id: int):
    role = get_user_role(request.user)
    if role != "Teacher":
        return HttpResponse("Access denied", status=403)

    try:
        teacher = Teacher.objects.get(user=request.user)
        exam = Exam.objects.get(id=exam_id)
        classroom = Classroom.objects.get(id=classroom_id)

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
        if ExamResult.objects.filter(
            exam=exam, student__classroom=classroom, status=ExamResult.Status.LOCKED
        ).exists():
            return JsonResponse({"error": "Exam results are locked"}, status=403)

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
    if role != "Teacher":
        return HttpResponse("Access denied", status=403)

    try:
        teacher = Teacher.objects.get(user=request.user)
        exam = Exam.objects.get(id=exam_id)
        classroom = Classroom.objects.get(id=classroom_id)

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
    if role != "Teacher":
        return HttpResponse("Access denied", status=403)

    try:
        teacher = Teacher.objects.get(user=request.user)
        exam = Exam.objects.get(id=exam_id)
        classroom = Classroom.objects.get(id=classroom_id)

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

        context = {
            "exam": exam,
            "classroom": classroom,
            "students": students,
            "exam_schedules": exam_schedules,
            "results_dict": results_dict,
            "is_locked": is_locked,
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

        return JsonResponse({"success": True})
    except (Teacher.DoesNotExist, Exam.DoesNotExist, Classroom.DoesNotExist):
        return JsonResponse({"error": "Not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
