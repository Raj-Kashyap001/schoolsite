from django.db import models
from django.contrib.auth.models import User


def notice_attachment_path(instance, filename):
    return f"notices/{filename}"


class Notice(models.Model):
    class NoticeType(models.TextChoices):
        PUBLIC = "PUBLIC", "Public Announcement"
        ALL_STUDENTS = "ALL_STUDENTS", "All Students"
        CLASS_STUDENTS = "CLASS_STUDENTS", "Specific Class"
        INDIVIDUAL_STUDENT = "INDIVIDUAL_STUDENT", "Individual Student"
        ALL_TEACHERS = "ALL_TEACHERS", "All Teachers"
        INDIVIDUAL_TEACHER = "INDIVIDUAL_TEACHER", "Individual Teacher"

    title = models.CharField(max_length=255)
    content = models.TextField()
    notice_type = models.CharField(
        max_length=20, choices=NoticeType.choices, default=NoticeType.ALL_STUDENTS
    )
    attachment = models.FileField(
        upload_to=notice_attachment_path, blank=True, null=True
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # Targets
    target_class = models.ForeignKey(
        "students.Classroom",
        on_delete=models.CASCADE,
        related_name="class_notices",
        blank=True,
        null=True,
        help_text="For class-specific notices",
    )
    target_students = models.ManyToManyField(
        "students.Student",
        related_name="individual_notices",
        blank=True,
        help_text="For individual student notices",
    )
    target_teachers = models.ManyToManyField(
        "teachers.Teacher",
        related_name="individual_notices",
        blank=True,
        help_text="For individual teacher notices",
    )

    def __str__(self):
        return f"{self.title} ({self.notice_type})"

    class Meta:
        ordering = ["-created_at"]
