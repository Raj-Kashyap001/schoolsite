from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from base.views import get_user_role
from academics.models import AcademicSession


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

    context = {
        "dashboard_sections": get_dashboard_sections(role),
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
        ],
        "Admin": [
            {"name": "Profile", "url": "/administration/profile/", "icon": "user"},
            {
                "name": "Teacher Management",
                "url": "/teachers/management/",
                "icon": "users",
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
            {"name": "All Sections", "url": "/admin/", "icon": "settings"},
        ],
    }
    return sections.get(role, [])


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
