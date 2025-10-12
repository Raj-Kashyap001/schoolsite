from django.http import HttpRequest, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import CarouselImage, GalleryImage, PopupImage
from .forms import CarouselImageForm, GalleryImageForm, PopupImageForm


def get_user_role(user):
    if user.groups.filter(name="Admin").exists():
        return "Admin"
    elif user.groups.filter(name="Teacher").exists():
        return "Teacher"
    else:
        return "Student"


# ===== HOMEPAGE CONTENT MANAGEMENT VIEWS =====


@login_required
def homepage_content_management(request: HttpRequest):
    """Main homepage content management page for admins"""
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponseBadRequest("Access denied")

    # Get stats
    carousel_count = CarouselImage.objects.filter(is_active=True).count()
    gallery_count = GalleryImage.objects.filter(is_active=True).count()
    popup_active = PopupImage.objects.filter(is_active=True).exists()

    context = {
        "role": role,
        "carousel_count": carousel_count,
        "gallery_count": gallery_count,
        "popup_active": popup_active,
    }
    return render(request, "front_cms/homepage_content_management.html", context)


@login_required
def manage_carousel(request: HttpRequest):
    """Manage carousel images"""
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponseBadRequest("Access denied")

    # Get all carousel images with pagination
    carousel_images = CarouselImage.objects.all().order_by(
        "display_order", "-created_at"
    )
    paginator = Paginator(carousel_images, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "role": role,
        "page_obj": page_obj,
        "form": CarouselImageForm(),
    }
    return render(request, "front_cms/manage_carousel.html", context)


@login_required
def manage_gallery(request: HttpRequest):
    """Manage gallery images"""
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponseBadRequest("Access denied")

    # Get all gallery images with pagination
    gallery_images = GalleryImage.objects.all().order_by("display_order", "-created_at")
    paginator = Paginator(gallery_images, 12)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Get category counts
    categories = {}
    for choice in GalleryImage.CATEGORY_CHOICES:
        categories[choice[0]] = {
            "name": choice[1],
            "count": GalleryImage.objects.filter(
                category=choice[0], is_active=True
            ).count(),
        }

    context = {
        "role": role,
        "page_obj": page_obj,
        "form": GalleryImageForm(),
        "categories": categories,
    }
    return render(request, "front_cms/manage_gallery.html", context)


@login_required
def manage_popup(request: HttpRequest):
    """Manage popup images"""
    role = get_user_role(request.user)
    if role != "Admin":
        return HttpResponseBadRequest("Access denied")

    # Get all popup images
    popup_images = PopupImage.objects.all().order_by("-created_at")

    context = {
        "role": role,
        "popup_images": popup_images,
        "form": PopupImageForm(),
        "active_popup": PopupImage.objects.filter(is_active=True).first(),
    }
    return render(request, "front_cms/manage_popup.html", context)


# ===== CRUD OPERATIONS =====


@login_required
def create_carousel_image(request: HttpRequest):
    """Create new carousel image"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    if request.method == "POST":
        form = CarouselImageForm(request.POST, request.FILES)
        if form.is_valid():
            carousel_image = form.save()
            messages.success(
                request,
                f"Carousel image '{carousel_image.title}' created successfully.",
            )
            return JsonResponse(
                {"success": True, "redirect": "/front-cms/manage-carousel/"}
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def update_carousel_image(request: HttpRequest, image_id: int):
    """Update carousel image"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    carousel_image = get_object_or_404(CarouselImage, id=image_id)

    if request.method == "POST":
        form = CarouselImageForm(request.POST, request.FILES, instance=carousel_image)
        if form.is_valid():
            updated_image = form.save()
            messages.success(
                request, f"Carousel image '{updated_image.title}' updated successfully."
            )
            return JsonResponse(
                {"success": True, "redirect": "/front-cms/manage-carousel/"}
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def delete_carousel_image(request: HttpRequest, image_id: int):
    """Delete carousel image"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    if request.method == "POST":
        carousel_image = get_object_or_404(CarouselImage, id=image_id)
        title = carousel_image.title
        carousel_image.delete()
        messages.success(request, f"Carousel image '{title}' deleted successfully.")
        return JsonResponse({"success": True})

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def create_gallery_image(request: HttpRequest):
    """Create new gallery image"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    if request.method == "POST":
        form = GalleryImageForm(request.POST, request.FILES)
        if form.is_valid():
            gallery_image = form.save()
            messages.success(
                request, f"Gallery image '{gallery_image.title}' created successfully."
            )
            return JsonResponse(
                {"success": True, "redirect": "/front-cms/manage-gallery/"}
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def update_gallery_image(request: HttpRequest, image_id: int):
    """Update gallery image"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    gallery_image = get_object_or_404(GalleryImage, id=image_id)

    if request.method == "POST":
        form = GalleryImageForm(request.POST, request.FILES, instance=gallery_image)
        if form.is_valid():
            updated_image = form.save()
            messages.success(
                request, f"Gallery image '{updated_image.title}' updated successfully."
            )
            return JsonResponse(
                {"success": True, "redirect": "/front-cms/manage-gallery/"}
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def delete_gallery_image(request: HttpRequest, image_id: int):
    """Delete gallery image"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    if request.method == "POST":
        gallery_image = get_object_or_404(GalleryImage, id=image_id)
        title = gallery_image.title
        gallery_image.delete()
        messages.success(request, f"Gallery image '{title}' deleted successfully.")
        return JsonResponse({"success": True})

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def create_popup_image(request: HttpRequest):
    """Create new popup image"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    if request.method == "POST":
        form = PopupImageForm(request.POST, request.FILES)
        if form.is_valid():
            popup_image = form.save()
            messages.success(
                request, f"Popup image '{popup_image.title}' created successfully."
            )
            return JsonResponse(
                {"success": True, "redirect": "/front-cms/manage-popup/"}
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def update_popup_image(request: HttpRequest, image_id: int):
    """Update popup image"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    popup_image = get_object_or_404(PopupImage, id=image_id)

    if request.method == "POST":
        form = PopupImageForm(request.POST, request.FILES, instance=popup_image)
        if form.is_valid():
            updated_image = form.save()
            messages.success(
                request, f"Popup image '{updated_image.title}' updated successfully."
            )
            return JsonResponse(
                {"success": True, "redirect": "/front-cms/manage-popup/"}
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def delete_popup_image(request: HttpRequest, image_id: int):
    """Delete popup image"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    if request.method == "POST":
        popup_image = get_object_or_404(PopupImage, id=image_id)
        title = popup_image.title
        popup_image.delete()
        messages.success(request, f"Popup image '{title}' deleted successfully.")
        return JsonResponse({"success": True})

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def toggle_carousel_status(request: HttpRequest, image_id: int):
    """Toggle carousel image active status"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    carousel_image = get_object_or_404(CarouselImage, id=image_id)
    carousel_image.is_active = not carousel_image.is_active
    carousel_image.save()

    status = "activated" if carousel_image.is_active else "deactivated"
    messages.success(
        request, f"Carousel image '{carousel_image.title}' {status} successfully."
    )
    return JsonResponse({"success": True, "is_active": carousel_image.is_active})


@login_required
def toggle_gallery_status(request: HttpRequest, image_id: int):
    """Toggle gallery image active status"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    gallery_image = get_object_or_404(GalleryImage, id=image_id)
    gallery_image.is_active = not gallery_image.is_active
    gallery_image.save()

    status = "activated" if gallery_image.is_active else "deactivated"
    messages.success(
        request, f"Gallery image '{gallery_image.title}' {status} successfully."
    )
    return JsonResponse({"success": True, "is_active": gallery_image.is_active})


@login_required
def toggle_popup_status(request: HttpRequest, image_id: int):
    """Toggle popup image active status"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    popup_image = get_object_or_404(PopupImage, id=image_id)
    popup_image.is_active = not popup_image.is_active
    popup_image.save()

    status = "activated" if popup_image.is_active else "deactivated"
    messages.success(
        request, f"Popup image '{popup_image.title}' {status} successfully."
    )
    return JsonResponse({"success": True, "is_active": popup_image.is_active})


@login_required
def bulk_import_carousel(request: HttpRequest):
    """Bulk import carousel images"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    if request.method == "POST":
        images = request.FILES.getlist("images")
        if not images:
            return JsonResponse(
                {"success": False, "error": "No images provided"}, status=400
            )

        imported_count = 0
        errors = []

        for image_file in images:
            # Validate file type
            if not image_file.content_type.startswith("image/"):
                errors.append(f"{image_file.name}: Invalid file type")
                continue

            # Validate file size (5MB max)
            if image_file.size > 5 * 1024 * 1024:
                errors.append(f"{image_file.name}: File too large (max 5MB)")
                continue

            # Create title from filename (remove extension)
            title = (
                image_file.name.rsplit(".", 1)[0]
                if "." in image_file.name
                else image_file.name
            )

            try:
                CarouselImage.objects.create(
                    title=title, image=image_file, is_active=True
                )
                imported_count += 1
            except Exception as e:
                errors.append(f"{image_file.name}: {str(e)}")

        if imported_count > 0:
            messages.success(
                request, f"Successfully imported {imported_count} carousel images."
            )
        if errors:
            messages.warning(request, f"Errors during import: {', '.join(errors)}")

        return JsonResponse(
            {"success": True, "imported": imported_count, "errors": errors}
        )

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def bulk_import_gallery(request: HttpRequest):
    """Bulk import gallery images"""
    role = get_user_role(request.user)
    if role != "Admin":
        return JsonResponse({"error": "Access denied"}, status=403)

    if request.method == "POST":
        images = request.FILES.getlist("images")
        category = request.POST.get("category", "other")

        if not images:
            return JsonResponse(
                {"success": False, "error": "No images provided"}, status=400
            )

        # Validate category
        valid_categories = [choice[0] for choice in GalleryImage.CATEGORY_CHOICES]
        if category not in valid_categories:
            return JsonResponse(
                {"success": False, "error": "Invalid category"}, status=400
            )

        imported_count = 0
        errors = []

        for image_file in images:
            # Validate file type
            if not image_file.content_type.startswith("image/"):
                errors.append(f"{image_file.name}: Invalid file type")
                continue

            # Validate file size (5MB max)
            if image_file.size > 5 * 1024 * 1024:
                errors.append(f"{image_file.name}: File too large (max 5MB)")
                continue

            # Create title from filename (remove extension)
            title = (
                image_file.name.rsplit(".", 1)[0]
                if "." in image_file.name
                else image_file.name
            )

            try:
                GalleryImage.objects.create(
                    title=title, image=image_file, category=category, is_active=True
                )
                imported_count += 1
            except Exception as e:
                errors.append(f"{image_file.name}: {str(e)}")

        if imported_count > 0:
            messages.success(
                request, f"Successfully imported {imported_count} gallery images."
            )
        if errors:
            messages.warning(request, f"Errors during import: {', '.join(errors)}")

        return JsonResponse(
            {"success": True, "imported": imported_count, "errors": errors}
        )

    return JsonResponse({"error": "Method not allowed"}, status=405)
