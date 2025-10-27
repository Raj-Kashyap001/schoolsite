from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.conf import settings
import os
import shutil

# Import models across apps with safe fallbacks
try:
    from students.models import Student, Classroom
except Exception:  # pragma: no cover
    Student = None
    Classroom = None

try:
    from teachers.models import Teacher
except Exception:  # pragma: no cover
    Teacher = None

try:
    from notices.models import Notice
except Exception:  # pragma: no cover
    Notice = None


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
    """Clear all media files to ensure demo data isolation."""
    media_root = getattr(settings, "MEDIA_ROOT", None)
    if media_root and os.path.exists(media_root):
        try:
            # Remove all contents of media directory but keep the directory itself
            for filename in os.listdir(media_root):
                file_path = os.path.join(media_root, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    # Log but don't fail on individual file deletion errors
                    pass
        except Exception:
            # Silently fail if media directory cleanup has issues
            pass


class Command(BaseCommand):
    help = "Seed demo data for demo mode. Safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset demo-related objects first, then seed",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not getattr(settings, "DEMO_MODE", False):
            self.stdout.write(self.style.WARNING("DEMO_MODE is not enabled in settings."))
        reset = options.get("reset")

        # Create required groups
        groups = ensure_groups()

        # Optionally clear demo objects while preserving auth superuser if exists
        if reset:
            # Clear media files first to ensure data isolation
            clear_media_directory()
            
            # Delete dependent app data in safe order
            if Notice:
                Notice.objects.all().delete()
            if Student:
                Student.objects.all().delete()
            if Teacher:
                Teacher.objects.all().delete()
            if Classroom:
                Classroom.objects.all().delete()

        # Users
        admin = get_or_create_user("demo_admin", "demo1234", "Demo", "Admin", "admin@example.com")
        teacher_user = get_or_create_user("demo_teacher", "demo1234", "Demo", "Teacher", "teacher@example.com")
        student_user = get_or_create_user("demo_student", "demo1234", "Demo", "Student", "student@example.com")

        # Group assignments
        admin.groups.add(groups["Admin"])  # type: ignore[attr-defined]
        teacher_user.groups.add(groups["Teacher"])  # type: ignore[attr-defined]
        student_user.groups.add(groups["Student"])  # type: ignore[attr-defined]

        # Classroom: adapt to model fields (grade, section)
        classroom = None
        if Classroom:
            # Create or get a Grade 1, Section A class without using a 'name' field
            classroom, _ = Classroom.objects.get_or_create(
                grade="1",
                section="A",
            )

        # Teacher profile
        if Teacher:
            teacher, _ = Teacher.objects.get_or_create(
                user=teacher_user,
                defaults={
                    "subject": "Mathematics",
                    "mobile_no": 9999999999,
                    "plain_text_password": "demo1234",
                },
            )
            # Associate teacher to classroom if the model supports it
            if classroom and hasattr(teacher, "classroom"):
                try:
                    # ManyToMany relation
                    teacher.classroom.add(classroom)
                except Exception:
                    try:
                        # ForeignKey/OneToOne
                        setattr(teacher, "classroom", classroom)
                        teacher.save()
                    except Exception:
                        pass

        # Student profile
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
            # Ensure classroom set even if instance existed without it
            if classroom and getattr(student, "classroom_id", None) is None:
                student.classroom = classroom
                student.save()

        # Notices to make the dashboard look alive
        if Notice:
            Notice.objects.get_or_create(
                title="Welcome to Demo",
                content="This is a demo notice visible to all roles.",
                notice_type=getattr(Notice.NoticeType, "GENERAL", 1),
                created_by=admin,
            )

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
