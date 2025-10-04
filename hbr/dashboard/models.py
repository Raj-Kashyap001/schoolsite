from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


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


def teacher_profile_photo_path(instance, filename):
    return f"teachers/{instance.user.username}/profile/{filename}"


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100)
    qualification = models.CharField(max_length=200, blank=True)
    mobile_no = models.BigIntegerField(blank=True, null=True)
    profile_photo = models.ImageField(
        upload_to=teacher_profile_photo_path, null=True, blank=True
    )
    classroom = models.ManyToManyField(Classroom, related_name="teachers", blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


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


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "PRESENT"
        ABSENT = "ABSENT"
        LATE = "LATE"

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
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

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
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


class Leave(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"

    # Support both students and teachers
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, null=True, blank=True
    )
    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, null=True, blank=True
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


class ExamResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100)
    marks_obtained = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    total_marks = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("100")
    )
    grade = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return f"{self.student} - {self.exam.name} - {self.subject}"

    class Meta:
        unique_together = ("student", "exam", "subject")


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
        "Student",
        related_name="individual_notices",
        blank=True,
        help_text="For individual notices, select which students this applies to",
    )

    def __str__(self):
        return f"{self.title} ({self.notice_type})"

    class Meta:
        ordering = ["-created_at"]
