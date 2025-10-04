from django.urls import path
from . import views

app_name = "notices"

urlpatterns = [
    path("board/", views.notice_board, name="notice_board"),
    path(
        "attachment/<int:notice_id>/",
        views.download_notice_attachment,
        name="download_notice_attachment",
    ),
]
