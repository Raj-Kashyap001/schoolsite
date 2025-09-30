from django.urls import path
from . import views

urlpatterns = [
    path("", views.homepage, name="home"),
    path("login/<str:role>", views.login_page, name="login"),
]
