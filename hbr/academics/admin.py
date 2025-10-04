from django.contrib import admin

from .models import AcademicSession, Exam, ExamResult, ExamSchedule, Term


@admin.register(ExamSchedule)
class ExamScheduleAdmin(admin.ModelAdmin):
    list_display = ("exam", "subject", "date", "time", "room")
    list_filter = ("exam__term", "subject", "date")
    search_fields = ("exam__name", "subject", "room")
    ordering = ("date", "time")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("exam", "exam__term")


admin.site.register(
    [
        AcademicSession,
        Exam,
        ExamResult,
        Term,
    ]
)
