from django.db import models
from django.contrib.auth.models import User


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "PRESENT"
        ABSENT = "ABSENT"
        LATE = "LATE"

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE)
    teacher = models.ForeignKey("teachers.Teacher", on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(choices=Status.choices, default=Status.PRESENT)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ("student", "date")

    def __str__(self):
        return f"{self.student} - {self.date} - {self.status}"


class TeacherAttendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "PRESENT"
        ABSENT = "ABSENT"
        LATE = "LATE"

    teacher = models.ForeignKey("teachers.Teacher", on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(choices=Status.choices, default=Status.PRESENT)
    remarks = models.TextField(blank=True)
    marked_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        unique_together = ("teacher", "date")

    def __str__(self):
        return f"{self.teacher} - {self.date} - {self.status}"
