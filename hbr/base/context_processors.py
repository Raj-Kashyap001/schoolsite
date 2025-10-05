from academics.models import AcademicSession
from datetime import date


def get_user_role(user):
    if user.groups.filter(name="Admin").exists():
        return "Admin"
    elif user.groups.filter(name="Teacher").exists():
        return "Teacher"
    else:
        return "Student"


def current_session(request):
    """Context processor to add current academic session to all templates"""
    # Check if user has selected a specific session
    selected_session_id = request.session.get("selected_academic_session_id")

    if selected_session_id:
        try:
            current_session_obj = AcademicSession.objects.get(id=selected_session_id)
        except AcademicSession.DoesNotExist:
            current_session_obj = None
    else:
        current_session_obj = None

    # If no selected session or invalid, use current session based on date
    if not current_session_obj:
        today = date.today()
        current_session_obj = AcademicSession.objects.filter(
            start_date__lte=today, end_date__gte=today
        ).first()

        # If no current session, get the latest one
        if not current_session_obj:
            current_session_obj = AcademicSession.objects.order_by("-end_date").first()

    return {"current_session": current_session_obj}


def user_role(request):
    """Context processor to add user role to all templates"""
    if request.user.is_authenticated:
        return {"role": get_user_role(request.user)}
    return {}
