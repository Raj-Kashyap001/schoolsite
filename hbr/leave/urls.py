from django.urls import path
from . import views

app_name = "leave"

urlpatterns = [
    path("manage/", views.leave, name="leave"),
]
