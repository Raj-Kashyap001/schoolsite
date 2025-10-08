from django.urls import path
from . import views

app_name = "front_cms"

urlpatterns = [
    # Homepage Content Management
    path("", views.homepage_content_management, name="homepage_content_management"),
    path("manage-carousel/", views.manage_carousel, name="manage_carousel"),
    path("manage-gallery/", views.manage_gallery, name="manage_gallery"),
    path("manage-popup/", views.manage_popup, name="manage_popup"),
    # CRUD Operations
    path("carousel/create/", views.create_carousel_image, name="create_carousel_image"),
    path(
        "carousel/<int:image_id>/update/",
        views.update_carousel_image,
        name="update_carousel_image",
    ),
    path(
        "carousel/<int:image_id>/delete/",
        views.delete_carousel_image,
        name="delete_carousel_image",
    ),
    path(
        "carousel/<int:image_id>/toggle/",
        views.toggle_carousel_status,
        name="toggle_carousel_status",
    ),
    path("gallery/create/", views.create_gallery_image, name="create_gallery_image"),
    path(
        "gallery/<int:image_id>/update/",
        views.update_gallery_image,
        name="update_gallery_image",
    ),
    path(
        "gallery/<int:image_id>/delete/",
        views.delete_gallery_image,
        name="delete_gallery_image",
    ),
    path(
        "gallery/<int:image_id>/toggle/",
        views.toggle_gallery_status,
        name="toggle_gallery_status",
    ),
    path("popup/create/", views.create_popup_image, name="create_popup_image"),
    path(
        "popup/<int:image_id>/update/",
        views.update_popup_image,
        name="update_popup_image",
    ),
    path(
        "popup/<int:image_id>/delete/",
        views.delete_popup_image,
        name="delete_popup_image",
    ),
    path(
        "popup/<int:image_id>/toggle/",
        views.toggle_popup_status,
        name="toggle_popup_status",
    ),
    path(
        "carousel/bulk-import/", views.bulk_import_carousel, name="bulk_import_carousel"
    ),
    path("gallery/bulk-import/", views.bulk_import_gallery, name="bulk_import_gallery"),
]
