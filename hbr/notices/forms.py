from django import forms
from .models import Notice
from students.models import Student


class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ["title", "content", "notice_type", "attachment", "target_students"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 4}),
            "target_students": forms.SelectMultiple(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["target_students"].queryset = Student.objects.all()
        self.fields["target_students"].required = False
