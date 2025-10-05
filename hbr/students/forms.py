from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import (
    Student,
    Classroom,
    Stream,
    Subject,
    Document,
    Payment,
    Certificate,
    CertificateType,
)
import random
import string
from datetime import datetime


class StudentUserCreationForm(UserCreationForm):
    """Form for creating a new user for student with auto-generated credentials"""

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make username read-only as it will be auto-generated
        self.fields["username"].widget.attrs["readonly"] = True
        self.fields["password1"].widget.attrs["readonly"] = True
        self.fields["password2"].widget.attrs["readonly"] = True


class StudentProfileForm(forms.ModelForm):
    """Form for student profile details"""

    # Additional fields for auto-generation
    full_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter student's full name"}
        ),
    )
    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(),
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-control"}),
    )
    stream = forms.ModelChoiceField(
        queryset=Stream.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Student
        fields = [
            "father_name",
            "mother_name",
            "dob",
            "mobile_no",
            "category",
            "gender",
            "profile_photo",
            "current_address",
            "permanent_address",
            "weight",
            "height",
        ]
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make certain fields required
        self.fields["father_name"].required = True
        self.fields["mother_name"].required = True
        self.fields["dob"].required = True
        self.fields["mobile_no"].required = True
        self.fields["gender"].required = True


class StudentEditForm(forms.ModelForm):
    """Form for editing student details"""

    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=False)

    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(),
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-control"}),
    )
    stream = forms.ModelChoiceField(
        queryset=Stream.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Student
        fields = [
            "father_name",
            "mother_name",
            "dob",
            "mobile_no",
            "category",
            "gender",
            "profile_photo",
            "current_address",
            "permanent_address",
            "weight",
            "height",
        ]
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email
            self.fields["classroom"].initial = self.instance.classroom
            self.fields["subjects"].initial = self.instance.subjects.all()
            self.fields["stream"].initial = self.instance.stream


class DocumentUploadForm(forms.ModelForm):
    """Form for uploading student documents"""

    class Meta:
        model = Document
        fields = ["name", "file"]


class PaymentForm(forms.ModelForm):
    """Form for adding student payments"""

    class Meta:
        model = Payment
        fields = ["amount", "description", "payment_date"]
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
        }


class CertificateRequestForm(forms.Form):
    """Form for requesting certificates"""

    certificate_type = forms.ModelChoiceField(
        queryset=CertificateType.objects.filter(is_active=True),
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class StudentBulkImportForm(forms.Form):
    """Form for bulk importing students from CSV/Excel files"""

    file = forms.FileField(
        required=True,
        widget=forms.FileInput(
            attrs={"class": "form-control", "accept": ".csv,.xlsx,.xls"}
        ),
        help_text="Upload CSV or Excel file with student data",
    )

    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(),
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Select classroom for imported students",
    )

    overwrite_existing = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Check this to overwrite existing students with same admission number",
    )


def generate_student_credentials(first_name, last_name, dob):
    """Generate username and password for student"""

    # Username: firstname + random numbers (total 8 chars, unique)
    base_username = first_name.lower()[:4]  # First 4 letters of first name
    max_attempts = 10  # Prevent infinite loop
    for attempt in range(max_attempts):
        random_nums = "".join(random.choices(string.digits, k=4))
        username = f"{base_username}{random_nums}"
        if not User.objects.filter(username=username).exists():
            break
    else:
        # Fallback username if we can't generate a unique one
        username = f"{base_username}{random.randint(1000, 9999)}"

    # Password: first four letters of fullname + dob year + extra random chars
    # Make it more complex to avoid similarity with username
    full_name = f"{first_name}{last_name}"
    base_password = full_name[:4].lower() + str(dob.year)

    # Add random characters to make it more complex and avoid similarity issues
    max_attempts = 10  # Prevent infinite loop
    for attempt in range(max_attempts):
        random_chars = "".join(
            random.choices(string.ascii_letters + string.digits, k=3)
        )
        password = base_password + random_chars

        # Check if password is too similar to username
        if username not in password and not any(
            username[i : i + 3] in password for i in range(len(username) - 2)
        ):
            break
    else:
        # Fallback password if we can't generate a dissimilar one
        password = base_password + "XYZ"

    return username, password


def generate_admission_number(grade, year=None):
    """Generate admission number: [HBR][YEAR,yy][GRADE,0 based],[random, unique no. 4]"""

    if year is None:
        year = datetime.now().year

    school_code = "HBR"
    year_short = str(year)[-2:]  # Last 2 digits of year

    # Extract numeric part from grade (e.g., "10th" -> "10")
    grade_numeric = "".join(filter(str.isdigit, str(grade)))
    grade_code = f"{int(grade_numeric):02d}"  # Zero-padded grade

    # Generate unique 4-digit random number
    max_attempts = 10  # Prevent infinite loop
    for attempt in range(max_attempts):
        random_num = "".join(random.choices(string.digits, k=4))
        admission_no = f"{school_code}{year_short}{grade_code}{random_num}"
        if not Student.objects.filter(admission_no=admission_no).exists():
            break
    else:
        # Fallback admission number if we can't generate a unique one
        import time

        timestamp = str(int(time.time()))[-4:]  # Last 4 digits of timestamp
        admission_no = f"{school_code}{year_short}{grade_code}{timestamp}"

    return admission_no


def generate_roll_number(classroom, sequence):
    """Generate roll number: [CLASS_CODE][SECTION_CODE, if available, else 00][SEQUENCE]"""

    # Extract numeric part from grade (e.g., "10th" -> "10")
    grade_numeric = "".join(filter(str.isdigit, classroom.grade))
    class_code = f"{int(grade_numeric):02d}"  # Zero-padded numeric grade

    if classroom.section:
        section_code = classroom.section.upper()[:2]  # First 2 letters of section
    else:
        section_code = "00"

    roll_no = f"{class_code}{section_code}{sequence:03d}"  # Zero-padded sequence

    return roll_no
