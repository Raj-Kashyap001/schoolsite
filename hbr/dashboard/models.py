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


class Classroom(models.Model):
    grade = models.CharField()
    section = models.CharField()

    def __str__(self):
        return f"{self.grade} {self.section}"


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100)
    qualification = models.CharField(max_length=200, blank=True)
    mobile_no = models.BigIntegerField(blank=True, null=True)
    classroom = models.ManyToManyField(Classroom, related_name="teachers", blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


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
    # stream = ["commerce", "maths", "bio", "arts"]
    # subjects = []
    # current_address = models.TextField()
    # weight = models.CharField(null=True)
    # height = models.CharField(null=True)
    # permanent_address = models.TextField()

    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name="student"
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


class Leave(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    apply_date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()
    from_date = models.DateField()
    to_date = models.DateField()
    status = models.CharField(choices=Status.choices, default=Status.PENDING)
    approved_on = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.from_date} to {self.to_date} - {self.status}"


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
