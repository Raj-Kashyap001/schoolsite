from django.urls import path
from . import views

app_name = "students"

urlpatterns = [
    path("profile/", views.profile, name="profile"),
    path("documents/", views.documents, name="documents"),
    path("certificates/", views.certificates, name="certificates"),
    path("payments/", views.payments, name="payments"),
    path(
        "download-receipt/<int:payment_id>/",
        views.download_receipt,
        name="download_receipt",
    ),
    path(
        "download-profile-pdf/", views.download_profile_pdf, name="download_profile_pdf"
    ),
]
