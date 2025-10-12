from django.contrib import admin

from .models import (
    AcademicSession,
    Exam,
    ExamResult,
    ExamSchedule,
    Term,
    ExamAssignment,
)


@admin.register(ExamSchedule)
class ExamScheduleAdmin(admin.ModelAdmin):
    list_display = ("exam", "subject", "date", "time", "room")
    list_filter = ("exam__term", "subject", "date")
    search_fields = ("exam__name", "subject", "room")
    ordering = ("date", "time")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("exam", "exam__term")


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "exam",
        "subject",
        "marks_obtained",
        "grade",
        "status",
        "marking_disabled",
    )
    list_filter = ("exam__term", "subject", "status", "marking_disabled")
    search_fields = ("student__user__username", "exam__name", "subject")
    ordering = ("exam", "student", "subject")


admin.site.register([AcademicSession, Exam, Term, ExamAssignment])
