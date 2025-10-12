from django import forms
from django.utils.html import format_html
from .models import Notice
from students.models import Student, Classroom
from teachers.models import Teacher


class SearchableStudentSelect(forms.SelectMultiple):
    """Custom widget for searchable student selection with roll number and class"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.classes = "form-control searchable-student-select"

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = []

        # Ensure value is a list for consistent handling
        if not isinstance(value, (list, tuple)):
            value = [value]

        # Get all students with their details for the search
        students = Student.objects.select_related("classroom", "user").all()

        # Create options with student details
        options = []
        for student in students:
            student_display = f"{student.user.get_full_name()} (Roll: {student.roll_no}, Class: {student.classroom})"
            selected = student.id in value
            options.append(
                f'<option value="{student.id}" {"selected" if selected else ""}>{student_display}</option>'
            )

        # Create the select element with search functionality
        select_html = f"""
        <div class="searchable-select-container">
            <input type="text" class="search-input" placeholder="Search students by name, roll number, or class..." />
            <select name="{name}" id="id_{name}" multiple class="form-control searchable-student-select" style="display: none;">
                {''.join(options)}
            </select>
            <div class="selected-students" id="selected-students-{name}">
              <div class="no-students-selected" style="color: #999; font-style: italic;">No students selected yet. Search and click "Add" to select students.</div>
            </div>
            <div class="search-results" id="search-results-{name}" style="display: none;"></div>
        </div>
        """

        return format_html(select_html)

    def value_from_datadict(self, data, files, name):
        """Extract the selected values from form data"""
        if name in data:
            value = data.getlist(name)
            return value
        return []


class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = [
            "title",
            "content",
            "notice_type",
            "attachment",
            "target_class",
            "target_students",
            "target_teachers",
        ]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 4}),
            "target_students": SearchableStudentSelect(),
            "target_teachers": forms.SelectMultiple(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit notice types based on user role (admin can create system alerts, others cannot)
        user = kwargs.get("user")
        if user and not user.groups.filter(name="Admin").exists():
            # Non-admins cannot create system alerts
            self.fields["notice_type"].choices = [
                choice
                for choice in self.fields["notice_type"].choices
                if choice[0] != Notice.NoticeType.SYSTEM_ALERT
            ]
        self.fields["target_students"].queryset = Student.objects.all()
        self.fields["target_students"].required = False
        self.fields["target_teachers"].queryset = Teacher.objects.all()
        self.fields["target_teachers"].required = False
        self.fields["target_class"].queryset = Classroom.objects.all()
        self.fields["target_class"].required = False
