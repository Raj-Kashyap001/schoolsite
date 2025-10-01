from django.http import HttpRequest
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from base.views import get_user_role


@login_required
def dashboard_home(request: HttpRequest):
    user = request.user
    role = get_user_role(user)

    context = {"role": role}
    return render(request, "dashboard/index.html", context)


@login_required
def profile(request: HttpRequest):
    user = request.user
    role = get_user_role(user)

    context = {"role": role, "user": user}

    if role == "Student":
        from .models import Student

        try:
            student = Student.objects.get(user=user)
            context["student"] = student
        except Student.DoesNotExist:
            context["student"] = None

    return render(request, "dashboard/profile.html", context)


@login_required
def settings(request: HttpRequest):
    user = request.user
    role = get_user_role(user)

    context = {"role": role, "user": user}
    return render(request, "dashboard/settings.html", context)
