from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Leave(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"

    # Support both students and teachers
    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, null=True, blank=True
    )
    teacher = models.ForeignKey(
        "teachers.Teacher", on_delete=models.CASCADE, null=True, blank=True
    )

    apply_date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()
    from_date = models.DateField()
    to_date = models.DateField()
    status = models.CharField(choices=Status.choices, default=Status.PENDING)
    approved_on = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leaves",
    )

    def __str__(self):
        if self.student:
            applicant_name = self.student.user.get_full_name()
        elif self.teacher:
            applicant_name = self.teacher.user.get_full_name()
        else:
            applicant_name = "Unknown"
        return f"{applicant_name} - {self.from_date} to {self.to_date} - {self.status}"

    class Meta:
        # Ensure either student or teacher is set, but not both
        constraints = [
            models.CheckConstraint(
                check=models.Q(student__isnull=False) | models.Q(teacher__isnull=False),
                name="either_student_or_teacher",
            )
        ]
