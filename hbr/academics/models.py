from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User


class AcademicSession(models.Model):
    year = models.CharField(max_length=20, unique=True)  # e.g., "2024-2025"
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.year


class Term(models.Model):
    academic_session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # e.g., "First Term", "Second Term"
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.name} - {self.academic_session.year}"

    class Meta:
        unique_together = ("academic_session", "name")


def exam_admit_card_path(instance, filename):
    return f"exams/{instance.term.academic_session.year}/{instance.term.name}/{instance.name}/admit_cards/{filename}"


class Exam(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # e.g., "Asst. 1st", "Int. 1st"
    description = models.TextField(blank=True)
    is_yearly_final = models.BooleanField(default=False)  # For yearly final exams
    admit_card_available = models.BooleanField(
        default=False
    )  # Whether admit card is available for download

    def __str__(self):
        return f"{self.name} - {self.term}"

    class Meta:
        unique_together = ("term", "name")


class ExamSchedule(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()
    subject = models.CharField(max_length=100)
    room = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.exam.name} - {self.subject} - {self.date}"

    class Meta:
        unique_together = ("exam", "date", "time", "subject")


class ExamAssignment(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    teacher = models.ForeignKey("teachers.Teacher", on_delete=models.CASCADE)
    classroom = models.ForeignKey("students.Classroom", on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.teacher} - {self.exam.name} - {self.classroom}"

    class Meta:
        unique_together = ("exam", "teacher", "classroom")


class ExamResult(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        LOCKED = "LOCKED", "Locked"

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100)
    marks_obtained = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    total_marks = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("100")
    )
    grade = models.CharField(max_length=10, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"{self.student} - {self.exam.name} - {self.subject}"

    class Meta:
        unique_together = ("student", "exam", "subject")
