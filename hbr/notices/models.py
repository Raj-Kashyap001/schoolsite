from django.db import models
from django.contrib.auth.models import User


def notice_attachment_path(instance, filename):
    return f"notices/{filename}"


class Notice(models.Model):
    class NoticeType(models.TextChoices):
        ANNOUNCEMENT = "ANNOUNCEMENT", "Announcement"  # Global notice for all students
        INDIVIDUAL = "INDIVIDUAL", "Individual"  # Specific to individual students

    title = models.CharField(max_length=255)
    content = models.TextField()
    notice_type = models.CharField(
        max_length=20, choices=NoticeType.choices, default=NoticeType.ANNOUNCEMENT
    )
    attachment = models.FileField(
        upload_to=notice_attachment_path, blank=True, null=True
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # For individual notices, specify which student(s) it applies to
    target_students = models.ManyToManyField(
        "students.Student",
        related_name="individual_notices",
        blank=True,
        help_text="For individual notices, select which students this applies to",
    )

    def __str__(self):
        return f"{self.title} ({self.notice_type})"

    class Meta:
        ordering = ["-created_at"]
