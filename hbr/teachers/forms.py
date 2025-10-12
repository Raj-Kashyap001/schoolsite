from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Teacher, TeacherSalary
from students.models import Classroom


class TeacherUserCreationForm(UserCreationForm):
    """Form for creating a new user for teacher"""

    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )


class TeacherProfileForm(forms.ModelForm):
    """Form for teacher profile details"""

    classroom = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.SelectMultiple(attrs={"class": "form-control"}),
        required=False,
        help_text="Classes this teacher teaches subjects in",
    )
    is_class_teacher = forms.BooleanField(
        required=False,
        label="",
        help_text="Check this to assign this teacher as class teacher for a specific class",
    )
    class_teacher_class = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        empty_label="Select class for class teacher role",
        help_text="Only classes without a class teacher are shown",
    )

    class Meta:
        model = Teacher
        fields = ["subject", "qualification", "mobile_no", "profile_photo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # All classrooms for teaching subjects
        self.fields["classroom"].queryset = Classroom.objects.all().order_by(
            "grade", "section"
        )
        # Only classrooms without class teachers for class teacher assignment
        self.fields["class_teacher_class"].queryset = Classroom.objects.filter(
            class_teacher__isnull=True
        ).order_by("grade", "section")

        # If editing existing teacher, set initial values
        if self.instance and self.instance.pk:
            self.fields["classroom"].initial = self.instance.classroom.all()
            # Check if this teacher is a class teacher
            try:
                class_teacher_class = Classroom.objects.get(class_teacher=self.instance)
                self.fields["is_class_teacher"].initial = True
                self.fields["class_teacher_class"].initial = class_teacher_class
            except Classroom.DoesNotExist:
                self.fields["is_class_teacher"].initial = False


class TeacherEditForm(forms.ModelForm):
    """Form for editing teacher details"""

    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    classroom = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.SelectMultiple(attrs={"class": "form-control"}),
        required=False,
        help_text="Classes this teacher teaches subjects in",
    )
    is_class_teacher = forms.BooleanField(
        required=False,
        label="",
        help_text="Check this to assign this teacher as class teacher for a specific class",
    )
    class_teacher_class = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        empty_label="Select class for class teacher role",
        help_text="Only classes without a class teacher are shown",
    )

    class Meta:
        model = Teacher
        fields = ["subject", "qualification", "mobile_no", "profile_photo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email

        # All classrooms for teaching subjects
        self.fields["classroom"].queryset = Classroom.objects.all().order_by(
            "grade", "section"
        )
        # Only classrooms without class teachers for class teacher assignment
        # Include current class teacher assignment if editing
        current_class_teacher_class = None
        if self.instance and self.instance.pk:
            try:
                current_class_teacher_class = Classroom.objects.get(
                    class_teacher=self.instance
                )
            except Classroom.DoesNotExist:
                pass

        available_classes = Classroom.objects.filter(class_teacher__isnull=True)
        if current_class_teacher_class:
            available_classes = available_classes | Classroom.objects.filter(
                pk=current_class_teacher_class.pk
            )

        self.fields["class_teacher_class"].queryset = available_classes.order_by(
            "grade", "section"
        )

        # If editing existing teacher, set initial values
        if self.instance and self.instance.pk:
            self.fields["classroom"].initial = self.instance.classroom.all()
            # Check if this teacher is a class teacher
            if current_class_teacher_class:
                self.fields["is_class_teacher"].initial = True
                self.fields["class_teacher_class"].initial = current_class_teacher_class
            else:
                self.fields["is_class_teacher"].initial = False


class TeacherSalaryForm(forms.ModelForm):
    """Form for adding teacher salary records"""

    class Meta:
        model = TeacherSalary
        fields = ["amount", "description", "payment_date", "attachment"]
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
        }
