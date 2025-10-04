from django.urls import path
from . import views

app_name = "academics"

urlpatterns = [
    path("exams/", views.exams, name="exams"),
    path(
        "exam-timetable/<int:exam_id>/",
        views.get_exam_timetable,
        name="get_exam_timetable",
    ),
    path(
        "download-timetable/<int:exam_id>/",
        views.download_exam_timetable,
        name="download_exam_timetable",
    ),
    path(
        "download-admit-card/<int:exam_id>/",
        views.download_admit_card,
        name="download_admit_card",
    ),
    path(
        "exam-results/<int:term_id>/", views.get_exam_results, name="get_exam_results"
    ),
]
