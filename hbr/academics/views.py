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

                # For modal: all terms for the current session
                all_terms = Term.objects.filter(
                    academic_session=current_term.academic_session
                )

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
        # Update all results for this exam to PUBLISHED
        ExamResult.objects.filter(exam=exam).update(status=ExamResult.Status.PUBLISHED)
        return JsonResponse({"success": True})
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
