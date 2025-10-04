from django.db import models
from django.contrib.auth.models import User


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
    classroom = models.ManyToManyField(
        "students.Classroom", related_name="teachers", blank=True
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username
