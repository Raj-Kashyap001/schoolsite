from django.db import models
from django.contrib.auth.models import User


def teacher_profile_photo_path(instance, filename):
    return f"teachers/{instance.user.username}/profile/{filename}"


def teacher_salary_attachment_path(instance, filename):
    return f"teachers/{instance.teacher.user.username}/salary/{filename}"


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100)
    qualification = models.CharField(max_length=200, blank=True)
    mobile_no = models.BigIntegerField(blank=True, null=True)
    profile_photo = models.ImageField(
        upload_to=teacher_profile_photo_path, null=True, blank=True
    )
    classroom = models.ManyToManyField(
        "students.Classroom", related_name="teachers", blank=True
    )
    plain_text_password = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Plain text password for admin reference",
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class TeacherSalary(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    payment_date = models.DateField()
    attachment = models.FileField(
        upload_to=teacher_salary_attachment_path, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.teacher} - {self.description} - {self.amount} - {self.payment_date}"
        )
