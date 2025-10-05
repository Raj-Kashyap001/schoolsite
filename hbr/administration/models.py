from django.db import models
from django.contrib.auth.models import User


def admin_profile_photo_path(instance, filename):
    return f"admins/{instance.user.username}/profile/{filename}"


class Administrator(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile_no = models.BigIntegerField(blank=True, null=True)
    profile_photo = models.ImageField(
        upload_to=admin_profile_photo_path, null=True, blank=True
    )
    department = models.CharField(max_length=100, blank=True)
    designation = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username
