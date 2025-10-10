from django.urls import path
from . import views

app_name = "notices"

urlpatterns = [
    path("board/", views.notice_board, name="notice_board"),
    path("create/", views.create_notice, name="create_notice"),
    path("search-students/", views.search_students, name="search_students"),
    path("bulk-delete/", views.bulk_delete_notices, name="bulk_delete_notices"),
    path("bulk-disable/", views.bulk_disable_notices, name="bulk_disable_notices"),
    path(
        "attachment/<int:notice_id>/",
        views.download_notice_attachment,
        name="download_notice_attachment",
    ),
]
