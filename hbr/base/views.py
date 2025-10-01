from django.http import HttpRequest, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required


def get_user_role(user):
    if user.groups.filter(name="Admin").exists():
        return "Admin"
    elif user.groups.filter(name="Teacher").exists():
        return "Teacher"
    else:
        return "Student"


@login_required
def logout_view(request: HttpRequest):
    logout(request)
    return redirect("home")


# Create your views here.
def homepage(request: HttpRequest):
    return render(request, "base/home.html")


def about(request: HttpRequest):
    return render(request, "base/about.html")


def academics(request: HttpRequest):
    return render(request, "base/academics.html")


def apply_enroll(request: HttpRequest):
    return render(request, "base/apply_enroll.html")


def login_page(request: HttpRequest, role: str):
    valid_roles = [r.name for r in Group.objects.all()]
    if role not in valid_roles:
        return HttpResponseBadRequest("Invalid Role!")

    if request.user.is_authenticated:
        user_role = get_user_role(request.user)
        if user_role == role:
            return redirect("dashboard")
        else:
            # Show confirmation page
            if request.method == "POST":
                if "logout" in request.POST:
                    logout(request)
                    return redirect(f"/login/{role}")
                elif "cancel" in request.POST:
                    return redirect("dashboard")
            context = {"current_role": user_role, "target_role": role}
            return render(request, "base/confirm_logout.html", context)

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(username=username, password=password)
        if user is not None and user.groups.filter(name=role).exists():
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid Credentials!")

    context = {"role": role}
    return render(request, "base/login.html", context)
