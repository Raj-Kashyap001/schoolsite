from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User


class Categories(models.TextChoices):
    GENERAL = "GENERAL"
    OBC = "OBC"
    SC = "SC"
    ST = "ST"


class Genders(models.TextChoices):
    MALE = "MALE"
    FEMALE = "FEMALE"


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Stream(models.Model):
    STREAM_CHOICES = [
        ("SCIENCE", "Science"),
        ("COMMERCE", "Commerce"),
        ("ARTS", "Arts"),
        ("MATHS", "Maths"),
    ]

    name = models.CharField(max_length=50, choices=STREAM_CHOICES, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Classroom(models.Model):
    grade = models.CharField()
    section = models.CharField(blank=True, null=True)

    def __str__(self):
        if self.section:
            return f"{self.grade} {self.section}"
        return self.grade


def student_profile_photo_path(instance, filename):
    return f"students/{instance.roll_no}/profile/{filename}"


class Student(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sr_no = models.IntegerField()
    roll_no = models.IntegerField()
    admission_no = models.CharField()
    father_name = models.CharField()
    mother_name = models.CharField()
    dob = models.DateField()
    mobile_no = models.BigIntegerField()
    category = models.CharField(choices=Categories.choices, blank=True)
    gender = models.CharField(choices=Genders.choices)
    profile_photo = models.ImageField(
        upload_to=student_profile_photo_path, null=True, blank=True
    )
    current_address = models.TextField(blank=True)
    permanent_address = models.TextField(blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name="student"
    )
    subjects = models.ManyToManyField(Subject, related_name="students", blank=True)
    stream = models.ForeignKey(
        Stream,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )

    def __str__(self):
        return self.user.get_full_name()


def student_document_path(instance, filename):
    return f"students/{instance.student.roll_no}/documents/{filename}"


def student_certificate_path(instance, filename):
    return f"students/{instance.student.roll_no}/certificates/{filename}"


class Document(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=student_document_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} - {self.name}"


class CertificateType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Certificate(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    certificate_type = models.ForeignKey(CertificateType, on_delete=models.CASCADE)
    issued_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(choices=Status.choices, default=Status.PENDING)
    file = models.FileField(upload_to=student_certificate_path, blank=True, null=True)

    def __str__(self):
        return (
            f"{self.student} - {self.certificate_type.name} - {self.issued_date.date()}"
        )

    class Meta:
        unique_together = ("student", "certificate_type")


class Payment(models.Model):
    class Status(models.TextChoices):
        PAID = "PAID"
        UNPAID = "UNPAID"
        FAILED = "FAILED"

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    status = models.CharField(choices=Status.choices, default=Status.UNPAID)
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_link = models.URLField(blank=True)
    transaction_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student} - {self.description} - {self.amount} - {self.status}"


def timetable_file_path(instance, filename):
    return f"timetables/{instance.classroom.grade}/daily/{filename}"


class DailyTimetable(models.Model):
    DAYS_OF_WEEK = [
        ("MONDAY", "Monday"),
        ("TUESDAY", "Tuesday"),
        ("WEDNESDAY", "Wednesday"),
        ("THURSDAY", "Thursday"),
        ("FRIDAY", "Friday"),
        ("SATURDAY", "Saturday"),
        ("SUNDAY", "Sunday"),
    ]

    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name="daily_timetables"
    )
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    timetable_file = models.FileField(
        upload_to=timetable_file_path, blank=True, null=True
    )
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.classroom} - {self.day_of_week} - {self.uploaded_at.date()}"

    class Meta:
        unique_together = ("classroom", "day_of_week")


def exam_timetable_file_path(instance, filename):
    return f"timetables/{instance.classroom.grade}/exam/{filename}"


class ExamTimetable(models.Model):
    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name="exam_timetables"
    )
    title = models.CharField(max_length=255, help_text="e.g., Mid-term Exam Timetable")
    timetable_file = models.FileField(upload_to=exam_timetable_file_path)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.classroom} - {self.title}"


class TeacherNotification(models.Model):
    PRIORITY_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("URGENT", "Urgent"),
    ]

    teacher = models.ForeignKey(
        "teachers.Teacher", on_delete=models.CASCADE, related_name="notifications"
    )
    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name="teacher_notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="MEDIUM"
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.teacher} - {self.classroom} - {self.title}"

    class Meta:
        ordering = ["-created_at"]
