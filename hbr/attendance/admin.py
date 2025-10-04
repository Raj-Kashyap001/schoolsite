from django.contrib import admin

from .models import Attendance, TeacherAttendance


admin.site.register(
    [
        Attendance,
        TeacherAttendance,
    ]
)
