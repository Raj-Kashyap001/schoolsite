from django.http import HttpRequest, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from front_cms.models import CarouselImage, GalleryImage, PopupImage
from notices.models import Notice
from academics.models import Exam, ExamResult
from students.models import Student


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

    # Get public notices
    public_notices = Notice.objects.filter(
        notice_type=Notice.NoticeType.PUBLIC, is_active=True
    ).order_by("-created_at")[
        :3
    ]  # Limit to 3 for homepage

    context = {
        "carousel_images": carousel_images,
        "gallery_images": gallery_images,
        "popup": popup,
        "public_notices": public_notices,
    }
    return render(request, "base/home.html", context)


def about(request: HttpRequest):
    return render(request, "base/about.html")


def academics(request: HttpRequest):
    return render(request, "base/academics.html")


def apply_enroll(request: HttpRequest):
    return render(request, "base/apply_enroll.html")


def news(request: HttpRequest):
    # Get all active public notices
    public_notices = Notice.objects.filter(
        notice_type=Notice.NoticeType.PUBLIC, is_active=True
    ).order_by("-created_at")

    context = {
        "notices": public_notices,
    }
    return render(request, "base/news.html", context)


def result(request: HttpRequest):
    context = {}
    if request.method == "POST":
        roll_no = request.POST.get("roll_no")
        exam_id = request.POST.get("exam")

        if roll_no and exam_id:
            try:
                student = Student.objects.get(roll_no=roll_no)
                exam = Exam.objects.get(id=exam_id)
                results = ExamResult.objects.filter(
                    student=student, exam=exam, status=ExamResult.Status.PUBLISHED
                ).order_by("subject")

                if results.exists():
                    # Calculate totals
                    total_marks = sum(float(r.total_marks) for r in results)
                    obtained_marks = sum(float(r.marks_obtained or 0) for r in results)
                    percentage = (
                        (obtained_marks / total_marks * 100) if total_marks > 0 else 0
                    )
                    result_status = "Pass" if percentage >= 33 else "Fail"

                    context.update(
                        {
                            "student": student,
                            "exam": exam,
                            "results": results,
                            "total_marks": total_marks,
                            "obtained_marks": obtained_marks,
                            "percentage": round(percentage, 2),
                            "result_status": result_status,
                            "found": True,
                        }
                    )
                else:
                    context["error"] = "No results found for this roll number and exam."
            except Student.DoesNotExist:
                context["error"] = "Student with this roll number not found."
            except Exam.DoesNotExist:
                context["error"] = "Invalid exam selected."
        else:
            context["error"] = "Please provide both roll number and exam type."

    # Get all published exams for the dropdown
    exams = (
        Exam.objects.filter(examresult__status=ExamResult.Status.PUBLISHED)
        .distinct()
        .order_by("-term__start_date", "name")
    )

    context["exams"] = exams
    return render(request, "base/result.html", context)


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
