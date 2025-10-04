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

        elif role == "Teacher":
            try:
                teacher = Teacher.objects.get(user=user)
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

    context = {"role": role, "user": user, "current_session": get_current_session()}

    if role == "Student":
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

    elif role == "Teacher":
        try:
            teacher = Teacher.objects.get(user=user)
            context["teacher"] = teacher
        except Teacher.DoesNotExist:
            context["teacher"] = None

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

    from datetime import date

    today = date.today()

    context = {"role": role, "current_session": get_current_session()}

    try:
        teacher = Teacher.objects.get(user=request.user)
        # Get students in teacher's classrooms who don't have attendance marked for today
        students = (
            Student.objects.filter(classroom__in=teacher.classroom.all())
            .exclude(attendance__date=today)
            .distinct()
            .order_by("sr_no")
        )
        # Get students who already have attendance marked for today
        marked_students = (
            Student.objects.filter(
                classroom__in=teacher.classroom.all(), attendance__date=today
            )
            .distinct()
            .order_by("sr_no")
        )
        context["students"] = students  # type: ignore
        context["marked_students"] = marked_students  # type: ignore
        context["teacher"] = teacher  # type: ignore
        context["today"] = today  # type: ignore
        context["has_marked_attendance"] = marked_students.exists()  # type: ignore

        if request.method == "POST":
            action = request.POST.get("action")
            if action == "undo":
                student_id = request.POST.get("student_id")
                Attendance.objects.filter(student_id=student_id, date=today).delete()
                messages.success(request, "Attendance undone for student")
                return redirect("mark_student_attendance")

            # Commit attendance
            date = today
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
def import_attendance_csv(request: HttpRequest):
    """Import attendance data from CSV file"""
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    if request.method != "POST" or not request.FILES.get("csv_file"):
        return JsonResponse({"success": False, "error": "No file provided"})

    try:
        teacher = Teacher.objects.get(user=request.user)
        csv_file = request.FILES["csv_file"]

        # Read CSV file
        if csv_file.name.endswith(".csv"):
            # Handle CSV file
            file_content = csv_file.read().decode("utf-8")
            csv_reader = csv.DictReader(io.StringIO(file_content))
        else:
            return JsonResponse({"success": False, "error": "Please upload a CSV file"})

        imported_count = 0
        errors = []

        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 for header row
            try:
                # Expected columns: student_name, roll_no, class, status, remarks, date
                student_name = row.get("student_name", "").strip()
                roll_no = row.get("roll_no", "").strip()
                class_name = row.get("class", "").strip()
                status = row.get("status", "").strip().upper()
                remarks = row.get("remarks", "").strip()
                date_str = row.get("date", "").strip()

                # Validate required fields
                if not all([student_name, roll_no, class_name, status, date_str]):
                    errors.append(f"Row {row_num}: Missing required fields")
                    continue

                # Validate status
                if status not in ["PRESENT", "ABSENT", "LATE"]:
                    errors.append(f"Row {row_num}: Invalid status '{status}'")
                    continue

                # Parse date (handle multiple formats)
                attendance_date = None
                try:
                    # Try different date formats
                    date_formats = [
                        "%d-%m-%y",  # DD-MM-YY
                        "%d-%m-%Y",  # DD-MM-YYYY
                        "%d/%m/%y",  # DD/MM/YY
                        "%d/%m/%Y",  # DD/MM/YYYY
                        "%Y-%m-%d",  # YYYY-MM-DD (ISO format)
                    ]

                    for fmt in date_formats:
                        try:
                            from datetime import datetime

                            parsed_date = datetime.strptime(date_str, fmt).date()
                            attendance_date = parsed_date
                            break
                        except ValueError:
                            continue

                    if attendance_date is None:
                        raise ValueError("No valid format found")

                except ValueError:
                    errors.append(
                        f"Row {row_num}: Invalid date format '{date_str}' (expected DD-MM-YY, DD-MM-YYYY, DD/MM/YY, DD/MM/YYYY, or YYYY-MM-DD)"
                    )
                    continue

                # Find student
                try:
                    student = Student.objects.get(
                        roll_no=roll_no,
                        classroom__grade=class_name,
                        user__first_name__icontains=student_name.split()[0],
                    )
                except Student.DoesNotExist:
                    errors.append(
                        f"Row {row_num}: Student not found - {student_name} (Roll: {roll_no}, Class: {class_name})"
                    )
                    continue
                except Student.MultipleObjectsReturned:
                    errors.append(
                        f"Row {row_num}: Multiple students found - {student_name} (Roll: {roll_no}, Class: {class_name})"
                    )
                    continue

                # Check if student is in teacher's classroom
                if not teacher.classroom.filter(id=student.classroom.id).exists():
                    errors.append(
                        f"Row {row_num}: Student {student_name} is not in your assigned classes"
                    )
                    continue

                # Check if attendance already exists for this date
                existing_attendance = Attendance.objects.filter(
                    student=student, date=attendance_date
                ).first()

                if existing_attendance:
                    errors.append(
                        f"Row {row_num}: Attendance already marked for {student_name} on {attendance_date} - skipping"
                    )
                    continue

                # Create new attendance record
                Attendance.objects.create(
                    student=student,
                    teacher=teacher,
                    date=attendance_date,
                    status=status,
                    remarks=remarks,
                )

                imported_count += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        response_data = {
            "success": True,
            "imported_count": imported_count,
            "errors": errors[:10],  # Limit errors to first 10
        }

        if errors:
            response_data["message"] = (
                f"Imported {imported_count} records with {len(errors)} errors"
            )

        return JsonResponse(response_data)

    except Teacher.DoesNotExist:
        return JsonResponse({"success": False, "error": "Teacher profile not found"})
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Error processing file: {str(e)}"}
        )


@login_required
def export_attendance_csv(request: HttpRequest):
    """Export attendance data to CSV file"""
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    try:
        teacher = Teacher.objects.get(user=request.user)

        # Get date parameter - export all marked data from the specified date
        from_date = request.GET.get("from_date")

        # Build query for attendance records
        attendance_query = Attendance.objects.filter(teacher=teacher)

        if from_date:
            attendance_query = attendance_query.filter(date__gte=from_date)

        attendance_records = attendance_query.select_related(
            "student", "student__user", "student__classroom"
        ).order_by("date", "student__roll_no")

        # Create CSV response
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="attendance_export.csv"'

        writer = csv.writer(response)

        # Write title header for teacher exports
        if from_date:
            today_date = date.fromisoformat(from_date)
            writer.writerow(
                [
                    f'Attendance for Class - {today_date.strftime("%Y-%m-%d")} by {teacher.user.get_full_name()}'
                ]
            )
            writer.writerow([])  # Empty row for spacing

        # Write column headers
        writer.writerow(
            ["Date", "Student Name", "Roll No", "Class", "Status", "Remarks"]
        )

        # Write data
        for attendance in attendance_records:
            writer.writerow(
                [
                    attendance.date.strftime("%Y-%m-%d"),
                    attendance.student.user.get_full_name(),
                    attendance.student.roll_no,
                    str(attendance.student.classroom),
                    attendance.status,
                    attendance.remarks or "",
                ]
            )

        return response

    except Teacher.DoesNotExist:
        return HttpResponse("Teacher profile not found", status=404)


@login_required
def import_attendance_excel(request: HttpRequest):
    """Import attendance data from Excel file"""
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    if request.method != "POST" or not request.FILES.get("excel_file"):
        return JsonResponse({"success": False, "error": "No file provided"})

    try:
        teacher = Teacher.objects.get(user=request.user)
        excel_file = request.FILES["excel_file"]

        # Read Excel file
        if excel_file.name.endswith((".xlsx", ".xls")):
            # Handle Excel file
            df = pd.read_excel(excel_file)
        else:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Please upload an Excel file (.xlsx or .xls)",
                }
            )

        imported_count = 0
        errors = []

        for row_num, row in df.iterrows():
            try:
                # Expected columns: student_name, roll_no, class, status, remarks, date
                student_name = str(row.get("student_name", "")).strip()
                roll_no = str(row.get("roll_no", "")).strip()
                class_name = str(row.get("class", "")).strip()
                status = str(row.get("status", "")).strip().upper()
                remarks = str(row.get("remarks", "")).strip()
                date_str = str(row.get("date", "")).strip()

                # Validate required fields
                if not all([student_name, roll_no, class_name, status, date_str]):
                    errors.append(f"Row {row_num + 2}: Missing required fields")
                    continue

                # Validate status
                if status not in ["PRESENT", "ABSENT", "LATE"]:
                    errors.append(f"Row {row_num + 2}: Invalid status '{status}'")
                    continue

                # Parse date (handle multiple formats)
                attendance_date = None
                try:
                    # Handle pandas datetime objects that come as strings like '2025-10-02 00:00:00'
                    if (
                        isinstance(date_str, str)
                        and " " in date_str
                        and ":" in date_str
                    ):
                        # Extract date part from datetime string
                        date_str = date_str.split(" ")[0]

                    # Try different date formats
                    date_formats = [
                        "%d-%m-%y",  # DD-MM-YY
                        "%d-%m-%Y",  # DD-MM-YYYY
                        "%d/%m/%y",  # DD/MM/YY
                        "%d/%m/%Y",  # DD/MM/YYYY
                        "%Y-%m-%d",  # YYYY-MM-DD (ISO format)
                    ]

                    for fmt in date_formats:
                        try:
                            from datetime import datetime

                            parsed_date = datetime.strptime(date_str, fmt).date()
                            attendance_date = parsed_date
                            break
                        except ValueError:
                            continue

                    if attendance_date is None:
                        raise ValueError("No valid format found")

                except ValueError:
                    errors.append(
                        f"Row {row_num + 2}: Invalid date format '{date_str}' (expected DD-MM-YY, DD-MM-YYYY, DD/MM/YY, DD/MM/YYYY, or YYYY-MM-DD)"
                    )
                    continue

                # Find student
                try:
                    student = Student.objects.get(
                        roll_no=roll_no,
                        classroom__grade=class_name,
                        user__first_name__icontains=student_name.split()[0],
                    )
                except Student.DoesNotExist:
                    errors.append(
                        f"Row {row_num + 2}: Student not found - {student_name} (Roll: {roll_no}, Class: {class_name})"
                    )
                    continue
                except Student.MultipleObjectsReturned:
                    errors.append(
                        f"Row {row_num + 2}: Multiple students found - {student_name} (Roll: {roll_no}, Class: {class_name})"
                    )
                    continue

                # Check if student is in teacher's classroom
                if not teacher.classroom.filter(id=student.classroom.id).exists():
                    errors.append(
                        f"Row {row_num + 2}: Student {student_name} is not in your assigned classes"
                    )
                    continue

                # Check if attendance already exists for this date
                existing_attendance = Attendance.objects.filter(
                    student=student, date=attendance_date
                ).first()

                if existing_attendance:
                    errors.append(
                        f"Row {row_num + 2}: Attendance already marked for {student_name} on {attendance_date} - skipping"
                    )
                    continue

                # Create new attendance record
                Attendance.objects.create(
                    student=student,
                    teacher=teacher,
                    date=attendance_date,
                    status=status,
                    remarks=remarks,
                )

                imported_count += 1

            except Exception as e:
                errors.append(f"Row {row_num + 2}: {str(e)}")

        response_data = {
            "success": True,
            "imported_count": imported_count,
            "errors": errors[:10],  # Limit errors to first 10
        }

        if errors:
            response_data["message"] = (
                f"Imported {imported_count} records with {len(errors)} errors"
            )

        return JsonResponse(response_data)

    except Teacher.DoesNotExist:
        return JsonResponse({"success": False, "error": "Teacher profile not found"})
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Error processing file: {str(e)}"}
        )


@login_required
def export_attendance_json(request: HttpRequest):
    """Export attendance data to JSON file"""
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    try:
        teacher = Teacher.objects.get(user=request.user)

        # Get date parameter - export all marked data from the specified date
        from_date = request.GET.get("from_date")

        # Build query for attendance records
        attendance_query = Attendance.objects.filter(teacher=teacher)

        if from_date:
            attendance_query = attendance_query.filter(date__gte=from_date)

        attendance_records = attendance_query.select_related(
            "student", "student__user", "student__classroom"
        ).order_by("date", "student__roll_no")

        # Prepare data for JSON
        data = {
            "export_info": {
                "exported_by": teacher.user.get_full_name(),
                "export_date": date.today().strftime("%Y-%m-%d"),
                "from_date": from_date,
                "total_records": attendance_records.count(),
            },
            "attendance_records": [],
        }

        for attendance in attendance_records:
            record = {
                "date": attendance.date.strftime("%Y-%m-%d"),
                "student_name": attendance.student.user.get_full_name(),
                "roll_no": attendance.student.roll_no,
                "class": str(attendance.student.classroom),
                "status": attendance.status,
                "remarks": attendance.remarks or "",
                "teacher": teacher.user.get_full_name(),
            }
            data["attendance_records"].append(record)

        # Create JSON response
        response = HttpResponse(
            json.dumps(data, indent=2, ensure_ascii=False),
            content_type="application/json",
        )
        response["Content-Disposition"] = (
            'attachment; filename="attendance_export.json"'
        )

        return response

    except Teacher.DoesNotExist:
        return HttpResponse("Teacher profile not found", status=404)


@login_required
def export_attendance_excel(request: HttpRequest):
    """Export attendance data to Excel file"""
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    try:
        teacher = Teacher.objects.get(user=request.user)

        # Get date parameter - export all marked data from the specified date
        from_date = request.GET.get("from_date")

        # Build query for attendance records
        attendance_query = Attendance.objects.filter(teacher=teacher)

        if from_date:
            attendance_query = attendance_query.filter(date__gte=from_date)

        attendance_records = attendance_query.select_related(
            "student", "student__user", "student__classroom"
        ).order_by("date", "student__roll_no")

        # Prepare data for DataFrame
        data = []
        for attendance in attendance_records:
            data.append(
                {
                    "Date": attendance.date.strftime("%Y-%m-%d"),
                    "Student Name": attendance.student.user.get_full_name(),
                    "Roll No": attendance.student.roll_no,
                    "Class": str(attendance.student.classroom),
                    "Status": attendance.status,
                    "Remarks": attendance.remarks or "",
                }
            )

        # Create DataFrame
        df = pd.DataFrame(data)

        # Create Excel response
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            'attachment; filename="attendance_export.xlsx"'
        )

        # Write to Excel
        with pd.ExcelWriter(response, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Attendance", index=False)

            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets["Attendance"]

            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = max_length + 2
                worksheet.column_dimensions[column_letter].width = adjusted_width

        return response

    except Teacher.DoesNotExist:
        return HttpResponse("Teacher profile not found", status=404)


@login_required
def download_attendance_template(request: HttpRequest):
    """Download CSV template for attendance import"""
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    # Create CSV response
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="attendance_template.csv"'

    writer = csv.writer(response)

    # Write header with instructions
    writer.writerow(["# Attendance Import Template"])
    writer.writerow(["# Required columns: student_name, roll_no, class, status, date"])
    writer.writerow(["# Optional columns: remarks"])
    writer.writerow(["# Status values: PRESENT, ABSENT, LATE"])
    writer.writerow(
        [
            "# Date format: DD-MM-YY, DD-MM-YYYY, DD/MM/YY, DD/MM/YYYY, or YYYY-MM-DD (e.g., 15-01-24, 15-01-2024, 15/01/24, 15/01/2024, or 2024-01-15)"
        ]
    )
    writer.writerow(["# First row should be headers"])
    writer.writerow([])  # Empty row

    # Write column headers
    writer.writerow(["student_name", "roll_no", "class", "status", "date", "remarks"])

    # Write sample data rows
    writer.writerow(["John Doe", "1", "10th A", "PRESENT", "15-01-24", "On time"])
    writer.writerow(["Jane Smith", "2", "10th A", "ABSENT", "15-01-24", "Sick leave"])
    writer.writerow(["Bob Johnson", "3", "10th A", "LATE", "15-01-24", "Traffic delay"])

    return response


@login_required
def download_attendance_excel_template(request: HttpRequest):
    """Download Excel template for attendance import"""
    role = get_user_role(request.user)
    if role not in ["Teacher", "Admin"]:
        return HttpResponse("Access denied", status=403)

    # Create Excel response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        'attachment; filename="attendance_excel_template.xlsx"'
    )

    # Create sample data
    data = {
        "student_name": ["John Doe", "Jane Smith", "Bob Johnson"],
        "roll_no": ["1", "2", "3"],
        "class": ["10th A", "10th A", "10th A"],
        "status": ["PRESENT", "ABSENT", "LATE"],
        "date": ["15-01-24", "15-01-24", "15-01-24"],
        "remarks": ["On time", "Sick leave", "Traffic delay"],
    }

    df = pd.DataFrame(data)

    # Write to Excel
    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Template", index=False)

        # Get the workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets["Template"]

        # Add instructions sheet
        instructions_sheet = workbook.create_sheet("Instructions")
        instructions_sheet["A1"] = "Attendance Import Template Instructions"
        instructions_sheet["A2"] = ""
        instructions_sheet["A3"] = (
            "Required columns: student_name, roll_no, class, status, date"
        )
        instructions_sheet["A4"] = "Optional column: remarks"
        instructions_sheet["A5"] = "Status values: PRESENT, ABSENT, LATE"
        instructions_sheet["A6"] = (
            "Date format: DD-MM-YY, DD-MM-YYYY, DD/MM/YY, DD/MM/YYYY, or YYYY-MM-DD (e.g., 15-01-24, 15-01-2024, 15/01/24, 15/01/2024, or 2024-01-15)"
        )
        instructions_sheet["A7"] = "First row should be headers"
        instructions_sheet["A8"] = ""
        instructions_sheet["A9"] = (
            "Note: Delete this instructions sheet before importing"
        )

        # Auto-adjust column widths for template sheet
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = max_length + 2
            worksheet.column_dimensions[column_letter].width = adjusted_width

    return response


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
        context["all_teacher_leaves"] = all_teacher_leaves

    return render(request, "dashboard/leave.html", context)


@login_required
def download_profile_pdf(request: HttpRequest):
    user = request.user
    role = get_user_role(user)

    if role != "Student":
        return HttpResponse("Access denied", status=403)

    try:
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
