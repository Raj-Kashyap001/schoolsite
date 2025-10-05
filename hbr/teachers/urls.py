from django.urls import path
from . import views

app_name = "teachers"

urlpatterns = [
    path("profile/", views.profile, name="profile"),
    path("salary/", views.salary, name="salary"),
    path("management/", views.teacher_management, name="teacher_management"),
    path("add/", views.add_teacher, name="add_teacher"),
    path("edit/<int:teacher_id>/", views.edit_teacher, name="edit_teacher"),
    path("delete/<int:teacher_id>/", views.delete_teacher, name="delete_teacher"),
    path("salary/<int:teacher_id>/", views.manage_salary, name="manage_salary"),
]
