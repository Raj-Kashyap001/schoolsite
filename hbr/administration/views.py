from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Administrator
from .forms import AdministratorProfileForm


@login_required
def profile(request):
    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        # Handle AJAX photo upload
        try:
            admin = Administrator.objects.get(user=request.user)
        except Administrator.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Administrator profile not found"}
            )

        if "profile_photo" in request.FILES:
            # Delete old image if it exists
            if admin.profile_photo:
                import os
                from django.conf import settings

                old_image_path = os.path.join(
                    settings.MEDIA_ROOT, str(admin.profile_photo)
                )
                if os.path.exists(old_image_path):
                    try:
                        os.remove(old_image_path)
                    except OSError:
                        pass  # Ignore if file doesn't exist or can't be deleted

            form = AdministratorProfileForm(request.POST, request.FILES, instance=admin)
            if form.is_valid():
                form.save()
                return JsonResponse(
                    {
                        "success": True,
                        "photo_url": (
                            admin.profile_photo.url if admin.profile_photo else None
                        ),
                    }
                )
            else:
                return JsonResponse({"success": False, "error": "Invalid file"})

        return JsonResponse({"success": False, "error": "Invalid request"})

    admin, created = Administrator.objects.get_or_create(user=request.user)

    context = {
        "admin": admin,
    }
    return render(request, "administration/profile.html", context)
