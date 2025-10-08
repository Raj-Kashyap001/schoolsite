from django.http import HttpRequest, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from front_cms.models import CarouselImage, GalleryImage, PopupImage


def get_user_role(user):
    if user.groups.filter(name="Admin").exists():
        return "Admin"
    elif user.groups.filter(name="Teacher").exists():
        return "Teacher"
    else:
        return "Student"


@login_required
def logout_view(request: HttpRequest):
    logout(request)
    return redirect(f"/login/{get_user_role(request.user)}")


# Create your views here.
def homepage(request: HttpRequest):
    # Get active carousel images ordered by display_order
    carousel_images = CarouselImage.objects.filter(is_active=True).order_by(
        "display_order", "-created_at"
    )

    # Get active gallery images
    gallery_images = GalleryImage.objects.filter(is_active=True).order_by(
        "display_order", "-created_at"
    )

    # Get active popup (only one should be active at a time)
    popup = PopupImage.objects.filter(is_active=True).first()

    context = {
        "carousel_images": carousel_images,
        "gallery_images": gallery_images,
        "popup": popup,
    }
    return render(request, "base/home.html", context)


def about(request: HttpRequest):
    return render(request, "base/about.html")


def academics(request: HttpRequest):
    return render(request, "base/academics.html")


def apply_enroll(request: HttpRequest):
    return render(request, "base/apply_enroll.html")


def login_page(request: HttpRequest, role: str):
    valid_roles = [r.name for r in Group.objects.all()]
    if role not in valid_roles:
        return HttpResponseBadRequest("Invalid Role!")

    if request.user.is_authenticated:
        user_role = get_user_role(request.user)
        if user_role == role:
            return redirect("dashboard:dashboard")
        else:
            # Show confirmation page
            if request.method == "POST":
                if "logout" in request.POST:
                    logout(request)
                    return redirect(f"/login/{role}")
                elif "cancel" in request.POST:
                    return redirect("dashboard:dashboard")
            context = {"current_role": user_role, "target_role": role}
            return render(request, "base/confirm_logout.html", context)

    error_message = None
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(username=username, password=password)
        if user is not None and user.groups.filter(name=role).exists():
            login(request, user)
            return redirect("dashboard:dashboard")
        else:
            error_message = "Invalid Credentials!"

    context = {
        "role": role,
        "valid_roles": valid_roles,
        "error_message": error_message,
        "school_name": "HBR School",
    }
    return render(request, "base/login.html", context)
