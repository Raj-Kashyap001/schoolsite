from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import datetime, date, timedelta
from django.core.serializers.json import DjangoJSONEncoder
from base.views import get_user_role
from academics.models import AcademicSession, ExamResult, ExamAssignment
from students.models import Student
from teachers.models import Teacher
from attendance.models import Attendance
from leave.models import Leave
from notices.models import Notice
from django.db.models import Q


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
    """Main dashboard home view - provides navigation to different modules"""
    user = request.user
    role = get_user_role(user)

    # Get role-specific data and statistics
    dashboard_data = get_dashboard_data(user, role)

    context = {
        "dashboard_sections": get_dashboard_sections(role),
        "role": role,
        "user": user,
        "current_session": get_current_session(),
        "current_time": datetime.now(),
        **dashboard_data,
    }
    return render(request, "dashboard/index.html", context)


def get_dashboard_sections(role):
    """Get available dashboard sections based on user role"""
    sections = {
        "Student": [
            {"name": "Profile", "url": "/students/profile/", "icon": "user"},
            {"name": "Attendance", "url": "/attendance/view/", "icon": "calendar"},
            {"name": "Documents", "url": "/students/documents/", "icon": "file"},
            {"name": "Certificates", "url": "/students/certificates/", "icon": "award"},
            {"name": "Payments", "url": "/students/payments/", "icon": "credit-card"},
            {"name": "Exams", "url": "/academics/exams/", "icon": "book"},
            {"name": "Leave", "url": "/leave/manage/", "icon": "calendar"},
            {"name": "Notice Board", "url": "/notices/board/", "icon": "bell"},
        ],
        "Teacher": [
            {"name": "Profile", "url": "/teachers/profile/", "icon": "user"},
            {
                "name": "Mark Attendance",
                "url": "/attendance/mark-student/",
                "icon": "check-square",
            },
            {"name": "View Attendance", "url": "/attendance/view/", "icon": "calendar"},
            {
                "name": "Mark Exam Results",
                "url": "/academics/teacher/marking/",
                "icon": "edit",
            },
            {"name": "Leave Management", "url": "/leave/manage/", "icon": "calendar"},
            {"name": "Notice Board", "url": "/notices/board/", "icon": "bell"},
        ],
        "Admin": [
            {"name": "Profile", "url": "/administration/profile/", "icon": "user"},
            {
                "name": "Exam Management",
                "url": "/academics/admin/exam-management/",
                "icon": "book",
            },
            {
                "name": "Teacher Management",
                "url": "/teachers/management/",
                "icon": "user",
            },
            {
                "name": "Mark Teacher Attendance",
                "url": "/attendance/mark-teacher/",
                "icon": "check-square",
            },
            {
                "name": "Leave Approvals",
                "url": "/leave/manage/",
                "icon": "check-circle",
            },
            {"name": "Notice Board", "url": "/notices/board/", "icon": "bell"},
            {"name": "Django Admin", "url": "/admin/", "icon": "cog"},
        ],
    }
    return sections.get(role, [])


def get_dashboard_data(user, role):
    """Get role-specific dashboard data and statistics"""
    data = {
        "stats": {},
        "charts": {},
        "recent_activity": [],
        "quick_actions": [],
    }

    if role == "Admin":
        # Admin statistics
        data["stats"] = {
            "total_students": Student.objects.count(),
            "total_teachers": Teacher.objects.count(),
            "total_exams": ExamAssignment.objects.count(),
            "pending_leaves": Leave.objects.filter(status="pending").count(),
            "active_notices": Notice.objects.filter(is_active=True).count(),
        }

        # Charts data for admin
        data["charts"] = {
            "attendance_trend": get_attendance_trend_data(),
            "exam_performance": get_exam_performance_data(),
            "leave_status": get_leave_status_data(),
        }

        # Recent activity for admin
        data["recent_activity"] = get_recent_activity_admin()

        # Quick actions for admin
        data["quick_actions"] = [
            {
                "title": "Add New Student",
                "url": "/students/add/",
                "icon": "user-plus",
                "color": "primary",
            },
            {
                "title": "Create Exam",
                "url": "/academics/admin/create-exam/",
                "icon": "book",
                "color": "success",
            },
            {
                "title": "Approve Leaves",
                "url": "/leave/manage/",
                "icon": "check-circle",
                "color": "warning",
            },
            {
                "title": "Manage Notices",
                "url": "/notices/manage/",
                "icon": "bell",
                "color": "info",
            },
        ]

    elif role == "Teacher":
        # Teacher statistics
        teacher = Teacher.objects.get(user=user)
        data["stats"] = {
            "my_students": Attendance.objects.filter(teacher=teacher)
            .values("student")
            .distinct()
            .count(),
            "pending_results": ExamResult.objects.filter(
                exam__teacher=teacher, marks__isnull=True
            ).count(),
            "total_exams": ExamAssignment.objects.filter(teacher=teacher).count(),
            "my_leaves": Leave.objects.filter(student__user=user).count(),
        }

        # Charts data for teacher
        data["charts"] = {
            "class_performance": get_class_performance_data(teacher),
            "attendance_overview": get_teacher_attendance_data(teacher),
        }

        # Recent activity for teacher
        data["recent_activity"] = get_recent_activity_teacher(teacher)

        # Quick actions for teacher
        data["quick_actions"] = [
            {
                "title": "Mark Attendance",
                "url": "/attendance/mark-student/",
                "icon": "check-square",
                "color": "primary",
            },
            {
                "title": "Enter Results",
                "url": "/academics/teacher/marking/",
                "icon": "edit",
                "color": "success",
            },
            {
                "title": "Apply Leave",
                "url": "/leave/apply/",
                "icon": "calendar",
                "color": "warning",
            },
            {
                "title": "View Schedule",
                "url": "/academics/schedule/",
                "icon": "clock",
                "color": "info",
            },
        ]

    elif role == "Student":
        # Student statistics
        student = Student.objects.get(user=user)
        data["stats"] = {
            "my_attendance": calculate_student_attendance_percentage(student),
            "total_exams": ExamResult.objects.filter(student=student).count(),
            "pending_fees": 0,  # Placeholder for payment system
            "my_leaves": Leave.objects.filter(teacher__user=user).count(),
        }

        # Charts data for student
        data["charts"] = {
            "performance_trend": get_student_performance_data(student),
            "attendance_chart": get_student_attendance_data(student),
        }

        # Recent activity for student
        data["recent_activity"] = get_recent_activity_student(student)

        # Quick actions for student
        data["quick_actions"] = [
            {
                "title": "View Results",
                "url": "/academics/results/",
                "icon": "chart-bar",
                "color": "primary",
            },
            {
                "title": "Check Attendance",
                "url": "/attendance/view/",
                "icon": "calendar",
                "color": "success",
            },
            {
                "title": "Download Certificates",
                "url": "/students/certificates/",
                "icon": "award",
                "color": "warning",
            },
            {
                "title": "Apply Leave",
                "url": "/leave/apply/",
                "icon": "calendar-plus",
                "color": "info",
            },
        ]

    return data


def get_attendance_trend_data():
    """Get attendance trend data for the last 7 days"""
    today = timezone.now().date()
    data = []

    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        present = Attendance.objects.filter(date=date, status="present").count()
        absent = Attendance.objects.filter(date=date, status="absent").count()
        data.append(
            {
                "date": date.strftime("%b %d"),
                "present": present,
                "absent": absent,
            }
        )

    return data


def get_exam_performance_data():
    """Get exam performance distribution"""
    results = ExamResult.objects.all()
    grade_distribution = {
        "A": results.filter(grade="A").count(),
        "B": results.filter(grade="B").count(),
        "C": results.filter(grade="C").count(),
        "D": results.filter(grade="D").count(),
        "F": results.filter(grade="F").count(),
    }
    return grade_distribution


def get_leave_status_data():
    """Get leave status distribution"""
    return {
        "approved": Leave.objects.filter(status="APPROVED").count(),
        "pending": Leave.objects.filter(status="PENDING").count(),
        "rejected": Leave.objects.filter(status="REJECTED").count(),
    }


def get_class_performance_data(teacher):
    """Get class performance data for teacher"""
    exams = ExamAssignment.objects.filter(teacher=teacher)
    data = []

    for exam in exams[:5]:  # Last 5 exams
        avg_marks = (
            ExamResult.objects.filter(exam=exam).aggregate(avg=Avg("marks"))["avg"] or 0
        )
        data.append(
            {
                "exam": exam.title[:20] + "..." if len(exam.title) > 20 else exam.title,
                "average": round(avg_marks, 1),
            }
        )

    return data


def get_teacher_attendance_data(teacher):
    """Get attendance data marked by teacher"""
    today = timezone.now().date()
    data = []

    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        marked = Attendance.objects.filter(date=date, teacher=teacher).count()
        data.append(
            {
                "date": date.strftime("%b %d"),
                "marked": marked,
            }
        )

    return data


def calculate_student_attendance_percentage(student):
    """Calculate student's attendance percentage"""
    total_classes = Attendance.objects.filter(student=student).count()
    if total_classes == 0:
        return 0

    present_classes = Attendance.objects.filter(
        student=student, status="present"
    ).count()
    return round((present_classes / total_classes) * 100, 1)


def get_student_performance_data(student):
    """Get student's performance trend"""
    # Order by exam name since exam_date field doesn't exist
    results = ExamResult.objects.filter(student=student).order_by("exam__name")[:10]
    data = []

    for result in results:
        data.append(
            {
                "exam": (
                    result.exam.name[:15] + "..."
                    if len(result.exam.name) > 15
                    else result.exam.name
                ),
                "marks": result.marks_obtained or 0,
                "grade": result.grade or "N/A",
            }
        )

    return data


def get_student_attendance_data(student):
    """Get student's attendance data for last 7 days"""
    today = timezone.now().date()
    data = []

    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        attendance = Attendance.objects.filter(student=student, date=date).first()
        status = attendance.status if attendance else "not_marked"
        data.append(
            {
                "date": date.strftime("%b %d"),
                "status": status,
            }
        )

    return data


def get_recent_activity_admin():
    """Get recent activity for admin"""
    activities = []

    # Recent leaves
    recent_leaves = Leave.objects.order_by("-apply_date")[:3]
    for leave in recent_leaves:
        if leave.student:
            applicant_name = leave.student.user.get_full_name()
        elif leave.teacher:
            applicant_name = leave.teacher.user.get_full_name()
        else:
            applicant_name = "Unknown"

        activities.append(
            {
                "type": "leave",
                "message": f"{applicant_name} applied for leave",
                "time": leave.apply_date,
                "status": leave.status.lower(),
            }
        )

    # Recent exam results
    recent_results = ExamResult.objects.filter(submitted_at__isnull=False).order_by(
        "-submitted_at"
    )[:3]
    for result in recent_results:
        activities.append(
            {
                "type": "result",
                "message": f"Result entered for {result.exam.name}",
                "time": result.submitted_at,
                "status": "completed",
            }
        )

    # Convert all times to datetime for consistent sorting
    for activity in activities:
        if isinstance(activity["time"], date) and not isinstance(
            activity["time"], datetime
        ):
            # Convert date to datetime
            activity["time"] = timezone.make_aware(
                datetime.combine(activity["time"], datetime.min.time())
            )

    return sorted(activities, key=lambda x: x["time"], reverse=True)[:5]


def get_recent_activity_teacher(teacher):
    """Get recent activity for teacher"""
    activities = []

    # Recent attendance marked
    recent_attendance = Attendance.objects.filter(teacher=teacher).order_by("-date")[:3]
    for att in recent_attendance:
        activities.append(
            {
                "type": "attendance",
                "message": f"Marked attendance for {att.student.user.get_full_name()}",
                "time": att.date,
                "status": "completed",
            }
        )

    # Recent results entered
    recent_results = ExamResult.objects.filter(
        exam__examassignment__teacher=teacher, submitted_at__isnull=False
    ).order_by("-submitted_at")[:3]
    for result in recent_results:
        activities.append(
            {
                "type": "result",
                "message": f"Entered result for {result.exam.name}",
                "time": result.submitted_at,
                "status": "completed",
            }
        )

    # Convert all times to datetime for consistent sorting
    for activity in activities:
        if isinstance(activity["time"], date) and not isinstance(
            activity["time"], datetime
        ):
            # Convert date to datetime
            activity["time"] = timezone.make_aware(
                datetime.combine(activity["time"], datetime.min.time())
            )

    return sorted(activities, key=lambda x: x["time"], reverse=True)[:5]


def get_recent_activity_student(student):
    """Get recent activity for student"""
    activities = []

    # Recent attendance
    recent_attendance = Attendance.objects.filter(student=student).order_by("-date")[:3]
    for att in recent_attendance:
        activities.append(
            {
                "type": "attendance",
                "message": f"Attendance marked: {att.status.title()}",
                "time": att.date,
                "status": att.status,
            }
        )

    # Recent results
    recent_results = ExamResult.objects.filter(
        student=student, submitted_at__isnull=False
    ).order_by("-submitted_at")[:3]
    for result in recent_results:
        activities.append(
            {
                "type": "result",
                "message": f"Result available for {result.exam.name}",
                "time": result.submitted_at,
                "status": "available",
            }
        )

    # Convert all times to datetime for consistent sorting
    for activity in activities:
        if isinstance(activity["time"], date) and not isinstance(
            activity["time"], datetime
        ):
            # Convert date to datetime
            activity["time"] = timezone.make_aware(
                datetime.combine(activity["time"], datetime.min.time())
            )

    return sorted(activities, key=lambda x: x["time"], reverse=True)[:5]


def get_user_notifications(user, role):
    """Get personal notifications for the user based on role"""
    if role == "Student":
        try:
            student = Student.objects.get(user=user)
            notifications = (
                Notice.objects.filter(is_active=True)
                .filter(
                    Q(
                        notice_type=Notice.NoticeType.INDIVIDUAL_STUDENT,
                        target_students=student,
                    )
                )
                .order_by("-created_at")[:5]
            )
        except Student.DoesNotExist:
            notifications = Notice.objects.none()
    elif role == "Teacher":
        try:
            teacher = Teacher.objects.get(user=user)
            notifications = (
                Notice.objects.filter(is_active=True)
                .filter(
                    Q(
                        notice_type=Notice.NoticeType.INDIVIDUAL_TEACHER,
                        target_teachers=teacher,
                    )
                )
                .order_by("-created_at")[:5]
            )
        except Teacher.DoesNotExist:
            notifications = Notice.objects.none()
    elif role == "Admin":
        notifications = (
            Notice.objects.filter(is_active=True)
            .exclude(notice_type=Notice.NoticeType.SYSTEM_ALERT)
            .exclude(dismissed_by=user)
            .order_by("-created_at")[:5]
        )
    else:
        notifications = Notice.objects.none()

    return notifications


@login_required
def settings_view(request: HttpRequest):
    """Settings view for admin to select academic session"""
    user = request.user
    role = get_user_role(user)

    # Only allow admin access
    if role != "Admin":
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("dashboard:dashboard")

    if request.method == "POST":
        session_id = request.POST.get("academic_session")
        if session_id:
            try:
                # Validate the session exists
                AcademicSession.objects.get(id=session_id)
                request.session["selected_academic_session_id"] = int(session_id)
                messages.success(request, "Academic session updated successfully.")
            except (AcademicSession.DoesNotExist, ValueError):
                messages.error(request, "Invalid academic session selected.")
        else:
            # Clear selection to use current session
            if "selected_academic_session_id" in request.session:
                del request.session["selected_academic_session_id"]
            messages.success(request, "Using current academic session.")

        return redirect("dashboard:settings")

    # Get all available sessions
    sessions = AcademicSession.objects.all().order_by("-start_date")
    current_selected_id = request.session.get("selected_academic_session_id")

    context = {
        "role": role,
        "sessions": sessions,
        "current_selected_id": current_selected_id,
    }
    return render(request, "dashboard/settings.html", context)
