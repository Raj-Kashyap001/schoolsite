from django import forms
from .models import CarouselImage, GalleryImage, PopupImage


class CarouselImageForm(forms.ModelForm):
    class Meta:
        model = CarouselImage
        fields = ["title", "image", "caption", "link_url", "display_order", "is_active"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter carousel title"}
            ),
            "caption": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Optional caption text"}
            ),
            "link_url": forms.URLInput(
                attrs={"class": "form-control", "placeholder": "https://example.com"}
            ),
            "display_order": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class GalleryImageForm(forms.ModelForm):
    class Meta:
        model = GalleryImage
        fields = [
            "title",
            "image",
            "category",
            "description",
            "display_order",
            "is_active",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter image title"}
            ),
            "category": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Optional description",
                }
            ),
            "display_order": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class PopupImageForm(forms.ModelForm):
    class Meta:
        model = PopupImage
        fields = ["title", "image", "link_url", "is_active", "start_date", "end_date"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter popup title"}
            ),
            "link_url": forms.URLInput(
                attrs={"class": "form-control", "placeholder": "https://example.com"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "start_date": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "end_date": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
        }
