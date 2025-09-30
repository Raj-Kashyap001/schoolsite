from django.http import HttpRequest
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


# Create your views here.
@login_required
def dashboard_home(request: HttpRequest):
    user = request.user
    role = None
    if user.groups.filter(name="Admin").exists():
        role = "Admin"
    elif user.groups.filter(name="Teacher").exists():
        role = "Teacher"
    else:
        role = "Student"

    context = {"role": role}
    return render(request, "dashboard/index.html", context)
