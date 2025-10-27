from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.conf import settings

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
            # Delete dependent app data first in safe order
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

        # Classroom
        classroom = None
        if Classroom:
            classroom, _ = Classroom.objects.get_or_create(
                name="Demo Class A", defaults={"section": "A", "class_teacher": None}
            )

        # Teacher profile
        if Teacher:
            teacher, _ = Teacher.objects.get_or_create(
                user=teacher_user,
                defaults={
                    "subject": "Mathematics",
                    "mobile_no": "9999999999",
                },
            )
            # Associate teacher to classroom if the model supports it
            if classroom and hasattr(teacher, "classroom"):
                try:
                    teacher.classroom.add(classroom)  # ManyToMany in your admin hints
                except Exception:
                    try:
                        teacher.classroom = classroom  # OneToOne/ForeignKey
                        teacher.save()
                    except Exception:
                        pass

        # Student profile
        if Student:
            student, _ = Student.objects.get_or_create(
                user=student_user,
                defaults={
                    "sr_no": 1,
                    "admission_no": "DEM0001",
                    "roll_no": 1,
                    "father_name": "Demo Father",
                    "mother_name": "Demo Mother",
                    "mobile_no": "8888888888",
                },
            )
            if classroom and hasattr(student, "classroom"):
                try:
                    student.classroom = classroom
                    student.save()
                except Exception:
                    pass

        # Notices to make the dashboard look alive
        if Notice:
            Notice.objects.get_or_create(
                title="Welcome to Demo",
                content="This is a demo notice visible to all roles.",
                notice_type=getattr(Notice.NoticeType, "GENERAL", 1),
                created_by=admin,
            )

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
