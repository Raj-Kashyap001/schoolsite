from django.http import HttpRequest
from django.shortcuts import render


# Create your views here.
def homepage(request: HttpRequest):
    return render(request, "base/home.html")
