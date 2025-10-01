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


# class Attendance(models.Model):
#     date = models.DateTimeField()
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     status = ]


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
    # stream = ["commerce", "maths", "bio", "arts"]
    # subjust = []
    # current_address = models.TextField()
    # weight = models.CharField(null=True)
    # height = models.CharField(null=True)
    # permanent_address = models.TextField()

    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name="student"
    )

    def __str__(self):
        return self.user.get_full_name()
