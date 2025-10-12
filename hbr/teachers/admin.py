from django.contrib import admin

from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("user", "subject", "mobile_no")
    list_filter = ("subject", "classroom")
    search_fields = ("user__username", "user__first_name", "user__last_name", "subject")
    filter_horizontal = ("classroom",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "classroom":
            # You can add help text here
            kwargs["help_text"] = (
                "Select classrooms this teacher is assigned to. Students from these classrooms will be available for marking."
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)
