from django.http import HttpRequest, HttpResponseBadRequest
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.contrib.auth import login, authenticate


# Create your views here.
def homepage(request: HttpRequest):
    return render(request, "base/home.html")


def login_page(request: HttpRequest, role: str):
    valid_roles = [r.name for r in Group.objects.all()]
    if role not in valid_roles:
        return HttpResponseBadRequest("Invalid Role!")
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(username=username, password=password)
        if user is not None and user.groups.filter(name=role).exists():
            login(request, user)
            return render(request, "dashboard/index.html", {"role": role})
        else:
            messages.error(request, "Invalid Credentials!")

    context = {"role": role}
    return render(request, "base/login.html", context)
