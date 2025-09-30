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
