from django.db import models
from django.core.exceptions import ValidationError
import os


def carousel_image_path(instance, filename):
    return f"homepage/carousel/{filename}"


def gallery_image_path(instance, filename):
    return f"homepage/gallery/{filename}"


def popup_image_path(instance, filename):
    return f"homepage/popup/{filename}"


class CarouselImage(models.Model):
    title = models.CharField(
        max_length=200, help_text="Display title for the carousel image"
    )
    image = models.ImageField(
        upload_to=carousel_image_path,
        help_text="Carousel image (recommended: 1920x800px)",
    )
    caption = models.CharField(
        max_length=300, blank=True, help_text="Optional caption text"
    )
    link_url = models.URLField(
        blank=True, help_text="Optional link URL when image is clicked"
    )
    display_order = models.PositiveIntegerField(
        default=0, help_text="Order of display (lower numbers appear first)"
    )
    is_active = models.BooleanField(
        default=True, help_text="Show this image in carousel"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-created_at"]
        verbose_name = "Carousel Image"
        verbose_name_plural = "Carousel Images"

    def __str__(self):
        return self.title

    def clean(self):
        if self.image:
            # Validate image size (max 5MB)
            if self.image.size > 5 * 1024 * 1024:
                raise ValidationError("Image file size must be less than 5MB")


class GalleryImage(models.Model):
    CATEGORY_CHOICES = [
        ("school", "School Activities"),
        ("events", "Events"),
        ("achievements", "Achievements"),
        ("facilities", "Facilities"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=200, help_text="Image title")
    image = models.ImageField(upload_to=gallery_image_path, help_text="Gallery image")
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="other"
    )
    description = models.TextField(blank=True, help_text="Optional description")
    display_order = models.PositiveIntegerField(default=0, help_text="Order of display")
    is_active = models.BooleanField(
        default=True, help_text="Show this image in gallery"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-created_at"]
        verbose_name = "Gallery Image"
        verbose_name_plural = "Gallery Images"

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"

    def clean(self):
        if self.image:
            # Validate image size (max 5MB)
            if self.image.size > 5 * 1024 * 1024:
                raise ValidationError("Image file size must be less than 5MB")


class PopupImage(models.Model):
    title = models.CharField(max_length=200, help_text="Popup title")
    image = models.ImageField(
        upload_to=popup_image_path, help_text="Popup image (recommended: 800x600px)"
    )
    link_url = models.URLField(
        blank=True, help_text="Optional link URL when image is clicked"
    )
    is_active = models.BooleanField(
        default=False, help_text="Show this popup (only one can be active at a time)"
    )
    start_date = models.DateTimeField(
        blank=True, null=True, help_text="When to start showing the popup"
    )
    end_date = models.DateTimeField(
        blank=True, null=True, help_text="When to stop showing the popup"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Popup Image"
        verbose_name_plural = "Popup Images"

    def __str__(self):
        return self.title

    def clean(self):
        if self.image:
            # Validate image size (max 3MB for popup)
            if self.image.size > 3 * 1024 * 1024:
                raise ValidationError("Image file size must be less than 3MB")

        # Ensure only one active popup at a time
        if self.is_active:
            active_popups = PopupImage.objects.filter(is_active=True)
            if self.pk:
                active_popups = active_popups.exclude(pk=self.pk)
            if active_popups.exists():
                raise ValidationError(
                    "Only one popup can be active at a time. Please deactivate other popups first."
                )

    def save(self, *args, **kwargs):
        # Deactivate other popups if this one is being activated
        if self.is_active:
            PopupImage.objects.filter(is_active=True).exclude(pk=self.pk).update(
                is_active=False
            )
        super().save(*args, **kwargs)
