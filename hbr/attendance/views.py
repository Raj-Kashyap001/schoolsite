from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
import csv
import io
import json
import pandas as pd
from datetime import date, datetime
from typing import Dict, List, Tuple, Optional, Any
from base.views import get_user_role
from .models import Attendance, TeacherAttendance
from students.models import Student
from teachers.models import Teacher


# ==================== HELPER FUNCTIONS ====================


def get_attendance_color(status: str) -> str:
    """Get color code for attendance status"""
    return {
        "PRESENT": "#28a745",
        "ABSENT": "#dc3545",
        "LATE": "#ffc107",
    }.get(status, "#6c757d")


def create_calendar_event(attendance, extra_props: Dict[str, Any]) -> Dict[str, Any]:
    """Create a calendar event from attendance record"""
    return {
        "title": attendance.status,
        "start": attendance.date.isoformat(),
        "color": get_attendance_color(attendance.status),
        "extendedProps": {"remarks": attendance.remarks, **extra_props},
    }


def parse_date_flexible(date_str: str) -> Optional[date]:
    """Parse date string with multiple format support"""
    date_formats = [
        "%d-%m-%y",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def validate_attendance_status(status: str) -> bool:
    """Validate attendance status"""
    return status in ["PRESENT", "ABSENT", "LATE"]


def get_teacher_or_error(request) -> Tuple[Optional[Teacher], Optional[JsonResponse]]:
    """Get teacher from request user or return error response"""
    try:
        return Teacher.objects.get(user=request.user), None
    except Teacher.DoesNotExist:
        return None, JsonResponse(
            {"success": False, "error": "Teacher profile not found"}
        )


def find_student(
    student_name: str, roll_no: str, class_name: str
) -> Tuple[Optional[Student], Optional[str]]:
    """Find student by name, roll number and class"""
    try:
        first_name = student_name.split()[0] if student_name else ""
        student = Student.objects.get(
            roll_no=roll_no,
            classroom__grade=class_name,
            user__first_name__icontains=first_name,
        )
        return student, None
    except Student.DoesNotExist:
        return (
            None,
            f"Student not found - {student_name} (Roll: {roll_no}, Class: {class_name})",
        )
    except Student.MultipleObjectsReturned:
        return (
            None,
            f"Multiple students found - {student_name} (Roll: {roll_no}, Class: {class_name})",
        )


def process_attendance_row(
    row: Dict[str, str], teacher: Teacher, row_num: int
) -> Tuple[bool, Optional[str]]:
    """Process a single attendance row from CSV/Excel"""
    # Extract and clean data
    student_name = row.get("student_name", "").strip()
    roll_no = row.get("roll_no", "").strip()
    class_name = row.get("class", "").strip()
    status = row.get("status", "").strip().upper()
    remarks = row.get("remarks", "").strip()
    date_str = row.get("date", "").strip()

    # Skip empty rows
    if not any([student_name, roll_no, class_name, status, date_str]):
        return False, None

    # Validate required fields
    if not all([student_name, roll_no, class_name, status, date_str]):
        return False, f"Row {row_num}: Missing required fields"

    # Validate status
    if not validate_attendance_status(status):
        return False, f"Row {row_num}: Invalid status '{status}'"

    # Parse date
    attendance_date = parse_date_flexible(date_str)
    if not attendance_date:
        return False, f"Row {row_num}: Invalid date format '{date_str}'"

    # Find student
    student, error = find_student(student_name, roll_no, class_name)
    if error:
        return False, f"Row {row_num}: {error}"

    # Check if student is in teacher's classroom
    if not teacher.classroom.filter(id=student.classroom.id).exists():
        return (
            False,
            f"Row {row_num}: Student {student_name} is not in your assigned classes",
        )

    # Check if attendance already exists
    if Attendance.objects.filter(student=student, date=attendance_date).exists():
        return (
            False,
            f"Row {row_num}: Attendance already marked for {student_name} on {attendance_date}",
        )

    # Create attendance record
    Attendance.objects.create(
        student=student,
        teacher=teacher,
        date=attendance_date,
        status=status,
        remarks=remarks,
    )
    return True, None


def get_attendance_data_for_export(
    teacher: Teacher, from_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get attendance data for export in standard format"""
    attendance_query = Attendance.objects.filter(teacher=teacher)
    if from_date:
        attendance_query = attendance_query.filter(date__gte=from_date)

    attendance_records = attendance_query.select_related(
        "student", "student__user", "student__classroom"
    ).order_by("date", "student__roll_no")

    return [
        {
            "date": att.date.strftime("%Y-%m-%d"),
            "student_name": att.student.user.get_full_name(),
            "roll_no": att.student.roll_no,
            "class": str(att.student.classroom),
            "status": att.status,
            "remarks": att.remarks or "",
        }
        for att in attendance_records
    ]


# ==================== VIEW FUNCTIONS ====================


@login_required
def attendance(request: HttpRequest):
    """View attendance calendar for students and teachers"""
    role = get_user_role(request.user)
    context = {"attendance_events": []}

    if role == "Student":
        try:
            student = Student.objects.get(user=request.user)
            attendances = Attendance.objects.filter(student=student).order_by("date")

            context["attendance_events"] = [
                create_calendar_event(att, {"teacher": str(att.teacher)})
                for att in attendances
            ]
            context["student"] = student
        except Student.DoesNotExist:
            context["error"] = "Student profile not found"

    elif role == "Teacher":
        try:
            teacher = Teacher.objects.get(user=request.user)
            attendances = TeacherAttendance.objects.filter(teacher=teacher).order_by(
                "date"
            )

            context["attendance_events"] = [
                create_calendar_event(
                    att,
                    {"marked_by": str(att.marked_by) if att.marked_by else "System"},
                )
                for att in attendances
            ]
            context["teacher"] = teacher
        except Teacher.DoesNotExist:
            context["error"] = "Teacher profile not found"

    return render(request, "attendance/attendance.html", context)


@login_required
def mark_student_attendance(request: HttpRequest):
    """Mark attendance for students"""
    role = get_user_role(request.user)
    if role != "Teacher":
        return HttpResponse("Access denied", status=403)

    today = date.today()
    context = {"today": today}

    try:
        teacher = Teacher.objects.get(user=request.user)
        teacher_classrooms = teacher.classroom.all()

        # Get students with and without attendance marked for today
        students = (
            Student.objects.filter(classroom__in=teacher_classrooms)
            .exclude(attendance__date=today)
            .distinct()
            .order_by("sr_no")
        )

        marked_students = (
            Student.objects.filter(
                classroom__in=teacher_classrooms, attendance__date=today
            )
            .distinct()
            .order_by("sr_no")
        )

        context.update(
            {
                "students": students,
                "marked_students": marked_students,
                "teacher": teacher,
                "has_marked_attendance": marked_students.exists(),
            }
        )

        if request.method == "POST":
            action = request.POST.get("action")

            # Handle undo action
            if action == "undo":
                student_id = request.POST.get("student_id")
                Attendance.objects.filter(student_id=student_id, date=today).delete()
                messages.success(request, "Attendance undone for student")
                return redirect("attendance:mark_student_attendance")

            # Mark attendance for students
            attendance_count = 0
            for student in students:
                status = request.POST.get(f"status_{student.id}")
                remarks = request.POST.get(f"remarks_{student.id}", "")

                if status:
                    Attendance.objects.update_or_create(
                        student=student,
                        date=today,
                        defaults={
                            "teacher": teacher,
                            "status": status,
                            "remarks": remarks,
                        },
                    )
                    attendance_count += 1

            messages.success(
                request, f"Attendance marked for {attendance_count} students"
            )
            return redirect("attendance:mark_student_attendance")

    except Teacher.DoesNotExist:
        context["error"] = "Teacher profile not found"

    return render(request, "attendance/mark_student_attendance.html", context)


def read_file_to_dataframe(
    file, file_type: str
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Read CSV or Excel file and return DataFrame"""
    try:
        if file_type == "csv":
            if not file.name.endswith(".csv"):
                return None, "Please upload a CSV file"
            file_content = file.read().decode("utf-8")
            df = pd.read_csv(io.StringIO(file_content))
        elif file_type == "excel":
            if not file.name.endswith((".xlsx", ".xls")):
                return None, "Please upload an Excel file"
            df = pd.read_excel(file)
        else:
            return None, "Unsupported file type"

        return df, None
    except Exception as e:
        return None, f"Error reading file: {str(e)}"


def import_attendance_from_dataframe(
    df: pd.DataFrame, teacher: Teacher
) -> Dict[str, Any]:
    """Import attendance records from DataFrame"""
    imported_count = 0
    errors = []

    for row_num, row in df.iterrows():
        try:
            # Convert row to dict with string values
            row_dict = {k: str(v).strip() for k, v in row.to_dict().items()}
            success, error = process_attendance_row(row_dict, teacher, row_num + 2)

            if success:
                imported_count += 1
            elif error:
                errors.append(error)
        except Exception as e:
            errors.append(f"Row {row_num + 2}: {str(e)}")

    response_data = {
        "success": True,
        "imported_count": imported_count,
        "errors": errors[:10],
    }

    if errors:
        response_data["message"] = (
            f"Imported {imported_count} records with {len(errors)} errors"
        )

    return response_data


@login_required
def import_attendance(request: HttpRequest):
    """Import attendance data from CSV or Excel file"""
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return JsonResponse({"success": False, "error": "Access denied"})

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"})

    # Determine file type from request
    file_type = None
    file = None

    if request.FILES.get("csv_file"):
        file = request.FILES["csv_file"]
        file_type = "csv"
    elif request.FILES.get("excel_file"):
        file = request.FILES["excel_file"]
        file_type = "excel"
    else:
        return JsonResponse({"success": False, "error": "No file provided"})

    teacher, error_response = get_teacher_or_error(request)
    if error_response:
        return error_response

    try:
        # Read file to DataFrame
        df, error = read_file_to_dataframe(file, file_type)
        if error:
            return JsonResponse({"success": False, "error": error})

        # Import attendance from DataFrame
        result = import_attendance_from_dataframe(df, teacher)
        return JsonResponse(result)

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Error processing file: {str(e)}"}
        )


# Keep separate endpoints for backward compatibility
@login_required
def import_attendance_csv(request: HttpRequest):
    """Import attendance data from CSV file (wrapper)"""
    return import_attendance(request)


@login_required
def import_attendance_excel(request: HttpRequest):
    """Import attendance data from Excel file (wrapper)"""
    return import_attendance(request)


def get_template_data() -> Dict[str, List]:
    """Get sample data for templates"""
    return {
        "student_name": ["John Doe", "Jane Smith", "Bob Johnson"],
        "roll_no": ["1001", "1002", "1003"],
        "class": ["10th", "10th", "10th"],
        "status": ["PRESENT", "ABSENT", "LATE"],
        "remarks": ["Good attendance", "Sick leave", "Traffic delay"],
        "date": ["15-01-2025", "15-01-2025", "15-01-2025"],
    }


@login_required
def download_template(request: HttpRequest, file_format: str = "csv"):
    """Download CSV or Excel template for attendance import"""
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    data = get_template_data()

    if file_format == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="attendance_template.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(data.keys())
        writer.writerows(zip(*data.values()))

    elif file_format == "excel":
        df = pd.DataFrame(data)
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            'attachment; filename="attendance_template.xlsx"'
        )

        with pd.ExcelWriter(response, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Attendance Template", index=False)
    else:
        return HttpResponse("Invalid format", status=400)

    return response


@login_required
def download_csv_template(request: HttpRequest):
    """Download CSV template (wrapper)"""
    return download_template(request, "csv")


@login_required
def download_excel_template(request: HttpRequest):
    """Download Excel template (wrapper)"""
    return download_template(request, "excel")


def create_export_response(file_format: str, filename: str) -> HttpResponse:
    """Create HTTP response for file export"""
    content_types = {
        "csv": "text/csv",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
    }

    response = HttpResponse(content_type=content_types.get(file_format, "text/plain"))
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def export_attendance(request: HttpRequest, file_format: str = "csv"):
    """Export attendance data in CSV, Excel, or JSON format"""
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    teacher, _ = get_teacher_or_error(request)
    if not teacher:
        return HttpResponse("Teacher profile not found", status=404)

    from_date = request.GET.get("from_date")
    data = get_attendance_data_for_export(teacher, from_date)

    if file_format == "json":
        response = create_export_response("json", "attendance_export.json")
        response.write(json.dumps(data, indent=2))

    elif file_format == "excel":
        df = pd.DataFrame(data)
        df.columns = ["Date", "Student Name", "Roll No", "Class", "Status", "Remarks"]

        response = create_export_response("excel", "attendance_export.xlsx")
        with pd.ExcelWriter(response, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Attendance", index=False)

    elif file_format == "csv":
        response = create_export_response("csv", "attendance_export.csv")
        writer = csv.writer(response)

        # Write title header if from_date is provided
        if from_date:
            writer.writerow(
                [
                    f"Attendance for Class - {from_date} by {teacher.user.get_full_name()}"
                ]
            )
            writer.writerow([])

        # Write headers and data
        writer.writerow(
            ["Date", "Student Name", "Roll No", "Class", "Status", "Remarks"]
        )
        writer.writerows(
            [
                [
                    row["date"],
                    row["student_name"],
                    row["roll_no"],
                    row["class"],
                    row["status"],
                    row["remarks"],
                ]
                for row in data
            ]
        )
    else:
        return HttpResponse("Invalid format", status=400)

    return response


@login_required
def export_attendance_csv(request: HttpRequest):
    """Export attendance data to CSV (wrapper)"""
    return export_attendance(request, "csv")


@login_required
def export_attendance_excel(request: HttpRequest):
    """Export attendance data to Excel (wrapper)"""
    return export_attendance(request, "excel")


@login_required
def export_attendance_json(request: HttpRequest):
    """Export attendance data to JSON (wrapper)"""
    return export_attendance(request, "json")


@login_required
def mark_teacher_attendance(request: HttpRequest):
    """Mark attendance for teachers (Admin only)"""
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponse("Access denied", status=403)

    teachers = Teacher.objects.all().order_by("user__first_name", "user__last_name")
    context = {"teachers": teachers}

    if request.method == "POST":
        attendance_date = request.POST.get("date")
        if not attendance_date:
            messages.error(request, "Date is required")
            return render(request, "attendance/mark_teacher_attendance.html", context)

        attendance_count = 0
        for teacher in teachers:
            status = request.POST.get(f"status_{teacher.id}")
            remarks = request.POST.get(f"remarks_{teacher.id}", "")

            if status:
                TeacherAttendance.objects.update_or_create(
                    teacher=teacher,
                    date=attendance_date,
                    defaults={
                        "status": status,
                        "remarks": remarks,
                        "marked_by": request.user,
                    },
                )
                attendance_count += 1

        messages.success(request, f"Attendance marked for {attendance_count} teachers")
        return redirect("attendance:mark_teacher_attendance")

    return render(request, "attendance/mark_teacher_attendance.html", context)
