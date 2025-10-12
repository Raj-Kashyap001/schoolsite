from django.urls import path
from . import views

urlpatterns = [
    path("", views.homepage, name="home"),
    path("about/", views.about, name="about"),
    path("academics/", views.academics, name="academics"),
    path("result/", views.result, name="result"),
    path("apply-enroll/", views.apply_enroll, name="apply_enroll"),
    path("news/", views.news, name="news"),
    path("login/<str:role>", views.login_page, name="login"),
    path("logout/", views.logout_view, name="logout"),
]
