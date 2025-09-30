from django.http import HttpRequest
from django.shortcuts import render


# Create your views here.
def dashboard_home(request: HttpRequest):
    return render(request, "dashboard/index.html")
