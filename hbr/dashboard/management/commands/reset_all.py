from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.conf import settings
from decouple import config
import os
import shutil
from django.core.files import File

# Import models across apps with safe fallbacks
try:
    from students.models import Student, Classroom
except Exception:
    Student = None
    Classroom = None
try:
    from teachers.models import Teacher
except Exception:
    Teacher = None
try:
    from notices.models import Notice
except Exception:
    Notice = None
try:
    from front_cms.models import GalleryImage, CarouselImage
except Exception:
    GalleryImage = None
    CarouselImage = None

def ensure_groups():
    groups = {}
    for name in ("Admin", "Teacher", "Student"):
        group, _ = Group.objects.get_or_create(name=name)
        groups[name] = group
    return groups

def get_or_create_user(username, password, first_name, last_name, email=""):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
        },
    )
    if created:
        user.set_password(password)
        user.is_staff = username == "demo_admin"
        user.is_superuser = username == "demo_admin"
        user.save()
    return user

def clear_media_directory():
    media_root = getattr(settings, "MEDIA_ROOT", None)
    if media_root and os.path.exists(media_root):
        try:
            for filename in os.listdir(media_root):
                file_path = os.path.join(media_root, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception:
                    pass
        except Exception:
            pass

def seed_gallery_and_carousel_images():
    images_dir = os.path.join(os.path.dirname(__file__), "images")
    if not os.path.exists(images_dir):
        return
    image_files = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]
    # Hardcoded formal school-related titles
    school_titles = [
        "Annual Sports Day",
        "Science Exhibition",
        "Cultural Fest",
        "Independence Day Celebration",
        "Art & Craft Workshop",
        "Teachers' Day Ceremony",
        "School Assembly",
        "Library Inauguration",
        "Student Council Election",
        "Field Trip",
        "Prize Distribution",
        "Parent-Teacher Meeting",
        "Classroom Activities",
        "School Band Performance",
        "Environmental Awareness Drive",
        "Mathematics Olympiad",
        "Annual Function",
        "Welcome Ceremony",
        "Farewell Party",
        "Children's Day Event"
    ]
    for idx, filename in enumerate(image_files):
        image_path = os.path.join(images_dir, filename)
        # Use hardcoded title or fallback to a generic one
        if idx < len(school_titles):
            title = school_titles[idx]
        else:
            title = "School Event"
        if GalleryImage:
            try:
                with open(image_path, "rb") as img_file:
                    GalleryImage.objects.get_or_create(
                        title=title,
                        defaults={
                            "image": File(img_file, name=filename),
                            "category": "school",
                            "description": f"{title} - School event or activity.",
                            "display_order": idx,
                            "is_active": True,
                        },
                    )
            except Exception:
                pass
        if CarouselImage:
            try:
                with open(image_path, "rb") as img_file:
                    CarouselImage.objects.get_or_create(
                        title=title,
                        defaults={
                            "image": File(img_file, name=filename),
                            "caption": f"{title} - School highlight.",
                            "display_order": idx,
                            "is_active": True,
                        },
                    )
            except Exception:
                pass

class Command(BaseCommand):
    help = "Reset all demo and initial setup data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset all demo and setup objects first, then seed",
        )

    def handle(self, *args, **options):
        self.stdout.write("Applying migrations...")
        call_command("migrate")

        @transaction.atomic
        def seed_and_reset():
            groups = ensure_groups()
            username = config("DJANGO_SUPERUSER_USERNAME", default="admin")
            email = config("DJANGO_SUPERUSER_EMAIL", default="admin@example.com")
            password = config("DJANGO_SUPERUSER_PASSWORD", default="admin1234")
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_superuser(
                    username=username, email=email, password=password
                )
                admin_group = Group.objects.get(name="Admin")
                user.groups.add(admin_group)
                self.stdout.write(f"Created superuser: {username} and assigned to Admin group")
            else:
                self.stdout.write(f"Superuser {username} already exists")
            reset = options.get("reset")
            if reset:
                clear_media_directory()
                if Notice:
                    Notice.objects.all().delete()
                if Student:
                    Student.objects.all().delete()
                if Teacher:
                    Teacher.objects.all().delete()
                if Classroom:
                    Classroom.objects.all().delete()
                if GalleryImage:
                    GalleryImage.objects.all().delete()
                if CarouselImage:
                    CarouselImage.objects.all().delete()
            admin = get_or_create_user("demo_admin", "demo1234", "Demo", "Admin", "admin@example.com")
            teacher_user = get_or_create_user("demo_teacher", "demo1234", "Demo", "Teacher", "teacher@example.com")
            student_user = get_or_create_user("demo_student", "demo1234", "Demo", "Student", "student@example.com")
            admin.groups.add(groups["Admin"])
            teacher_user.groups.add(groups["Teacher"])
            student_user.groups.add(groups["Student"])
            classroom = None
            if Classroom:
                classroom, _ = Classroom.objects.get_or_create(
                    grade="1",
                    section="A",
                )
            if Teacher:
                teacher, _ = Teacher.objects.get_or_create(
                    user=teacher_user,
                    defaults={
                        "subject": "Mathematics",
                        "mobile_no": 9999999999,
                        "plain_text_password": "demo1234",
                    },
                )
                if classroom and hasattr(teacher, "classroom"):
                    try:
                        teacher.classroom.add(classroom)
                    except Exception:
                        try:
                            setattr(teacher, "classroom", classroom)
                            teacher.save()
                        except Exception:
                            pass
            if Student:
                student_defaults = {
                    "sr_no": 1,
                    "admission_no": "DEM0001",
                    "roll_no": 1,
                    "father_name": "Demo Father",
                    "mother_name": "Demo Mother",
                    "dob": "2008-01-15",
                    "mobile_no": "8888888888",
                    "category": getattr(Student, "Categories", None).GENERAL if hasattr(Student, "Categories") else "GENERAL",
                    "gender": getattr(Student, "Genders", None).MALE if hasattr(Student, "Genders") else "MALE",
                    "current_address": "123 Demo Street",
                    "permanent_address": "123 Demo Street",
                    "plain_text_password": "demo1234",
                    "classroom": classroom,
                }
                student, created_student = Student.objects.get_or_create(
                    user=student_user,
                    defaults=student_defaults,
                )
                if classroom and getattr(student, "classroom_id", None) is None:
                    student.classroom = classroom
                    student.save()
            if Notice:
                Notice.objects.get_or_create(
                    title="Welcome to Demo",
                    content="This is a demo notice visible to all roles.",
                    notice_type=getattr(Notice.NoticeType, "GENERAL", 1),
                    created_by=admin,
                )
            seed_gallery_and_carousel_images()
            self.stdout.write(self.style.SUCCESS("All setup and demo data ready."))

        seed_and_reset()
