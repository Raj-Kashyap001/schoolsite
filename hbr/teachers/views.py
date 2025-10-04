from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

import pandas as pd
from datetime import date
from base.views import get_user_role
from .models import Teacher


@login_required
def profile(request: HttpRequest):
    user = request.user
    role = get_user_role(user)

    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        # Handle AJAX photo upload
        if role not in ["Student", "Teacher"]:
            return JsonResponse({"success": False, "error": "Access denied"})

        if role == "Teacher":
            try:
                teacher = Teacher.objects.get(user=user)
            except Teacher.DoesNotExist:  # type: ignore
                return JsonResponse(
                    {"success": False, "error": "Teacher profile not found"}
                )

            if "profile_photo" in request.FILES:
                # Delete old image if it exists
                if teacher.profile_photo:
                    import os
                    from django.conf import settings

                    old_image_path = os.path.join(
                        settings.MEDIA_ROOT, str(teacher.profile_photo)
                    )
                    if os.path.exists(old_image_path):
                        try:
                            os.remove(old_image_path)
                        except OSError:
                            pass  # Ignore if file doesn't exist or can't be deleted

                # Simple file handling for teacher profile photo
                teacher.profile_photo = request.FILES["profile_photo"]
                teacher.save()
                return JsonResponse(
                    {
                        "success": True,
                        "photo_url": (
                            teacher.profile_photo.url if teacher.profile_photo else None
                        ),
                    }
                )
            else:
                return JsonResponse({"success": False, "error": "No file uploaded"})

        return JsonResponse({"success": False, "error": "Invalid request"})

    context = {"role": role, "user": user}

    if role == "Teacher":
        try:
            teacher = Teacher.objects.get(user=user)
            context["teacher"] = teacher
        except Teacher.DoesNotExist:
            context["teacher"] = None

    return render(request, "teachers/profile.html", context)
