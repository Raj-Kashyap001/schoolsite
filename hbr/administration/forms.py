from django import forms
from .models import Administrator


class AdministratorProfileForm(forms.ModelForm):
    class Meta:
        model = Administrator
        fields = ["profile_photo"]
