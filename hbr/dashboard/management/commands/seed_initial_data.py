from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, time, date, timedelta
from decimal import Decimal
import random

# Import all models from their respective apps
from academics.models import AcademicSession, Term, Exam, ExamSchedule
from attendance.models import Attendance, TeacherAttendance
from students.models import (
    Student,
    Classroom,
    Subject,
    Stream,
    Certificate,
    CertificateType,
    Payment,
    Document,
)
from teachers.models import Teacher
from leave.models import Leave
from notices.models import Notice


class Command(BaseCommand):
    help = "Seed comprehensive dummy data for all models using current dates"

    def handle(self, *args, **options):
        self.stdout.write("Starting comprehensive data seeding...")

        # Get current date for dynamic data
        today = date.today()
        current_year = today.year
        current_month = today.month

        # 1. Seed Users first
        self.stdout.write("Seeding users...")
        self.seed_users()

        # 2. Seed Classrooms
        self.stdout.write("Seeding classrooms...")
        self.seed_classrooms()

        # 3. Seed Streams
        self.stdout.write("Seeding streams...")
        self.seed_streams()

        # 4. Seed Subjects
        self.stdout.write("Seeding subjects...")
        self.seed_subjects()

        # 5. Seed Academic Sessions and Terms
        self.stdout.write("Seeding academic data...")
        self.seed_academic_data(current_year)

        # 6. Seed Students
        self.stdout.write("Seeding students...")
        self.seed_students()

        # 7. Seed Teachers
        self.stdout.write("Seeding teachers...")
        self.seed_teachers()

        # 8. Seed Attendance
        self.stdout.write("Seeding attendance records...")
        self.seed_attendance(today)

        # 9. Seed Leave records
        self.stdout.write("Seeding leave records...")
        self.seed_leave_records(today)

        # 10. Seed Notices
        self.stdout.write("Seeding notices...")
        self.seed_notices(today)

        # 11. Seed Certificate Types and Certificates
        self.stdout.write("Seeding certificates...")
        self.seed_certificates()

        # 12. Seed Payments
        self.stdout.write("Seeding payments...")
        self.seed_payments()

        # 13. Seed Documents
        self.stdout.write("Seeding documents...")
        self.seed_documents()

        self.stdout.write(
            self.style.SUCCESS("All dummy data seeding completed successfully!")
        )

    def seed_users(self):
        """Seed basic user accounts"""
        users_data = [
            ("admin", "admin@hbr.edu", "Admin", "User", True, True),
            ("teacher1", "teacher1@hbr.edu", "Rajesh", "Sharma", False, False),
            ("teacher2", "teacher2@hbr.edu", "Priya", "Verma", False, False),
            ("student1", "student1@hbr.edu", "Amit", "Kumar", False, False),
            ("student2", "student2@hbr.edu", "Sneha", "Patel", False, False),
            ("student3", "student3@hbr.edu", "Rahul", "Singh", False, False),
        ]

        for (
            username,
            email,
            first_name,
            last_name,
            is_staff,
            is_superuser,
        ) in users_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_staff": is_staff,
                    "is_superuser": is_superuser,
                },
            )
            if created:
                user.set_password("password123")
                user.save()
                self.stdout.write(f"Created user: {username}")

    def seed_classrooms(self):
        """Seed classroom data"""
        classes = [
            "Nursery",
            "LKG",
            "UKG",
            "1st",
            "2nd",
            "3rd",
            "4th",
            "5th",
            "6th",
            "7th",
            "8th",
            "9th",
            "10th",
            "11th",
            "12th",
        ]

        for grade in classes:
            classroom, created = Classroom.objects.get_or_create(
                grade=grade, defaults={"section": None}
            )
            if created:
                self.stdout.write(f"Created classroom: {grade}")

    def seed_streams(self):
        """Seed stream data"""
        streams_data = [
            ("SCIENCE", "Science Stream"),
            ("COMMERCE", "Commerce Stream"),
            ("ARTS", "Arts/Humanities Stream"),
            ("MATHS", "Mathematics Stream"),
        ]

        for stream_code, description in streams_data:
            stream, created = Stream.objects.get_or_create(
                name=stream_code,
                defaults={"description": description, "is_active": True},
            )
            if created:
                self.stdout.write(f"Created stream: {stream_code}")

    def seed_subjects(self):
        """Seed subject data"""
        subjects_data = [
            ("HINDI", "HIN"),
            ("ENGLISH", "ENG"),
            ("MATHS", "MAT"),
            ("SCIENCE", "SCI"),
            ("EVS", "EVS"),
            ("SOCIAL SCIENCE", "SOC"),
            ("SANSKRIT", "SAN"),
            ("SBC", "SBC"),
            ("COMPUTER", "COM"),
            ("PHYSICS", "PHY"),
            ("CHEMISTRY", "CHE"),
            ("BIOLOGY", "BIO"),
        ]

        for name, code in subjects_data:
            subject, created = Subject.objects.get_or_create(
                name=name, defaults={"code": code, "is_active": True}
            )
            if created:
                self.stdout.write(f"Created subject: {name}")

    def seed_academic_data(self, current_year):
        """Seed academic sessions, terms, exams and schedules"""
        today = date.today()

        # Create current academic session
        session_year = f"{current_year}-{current_year + 1}"
        session, created = AcademicSession.objects.get_or_create(
            year=session_year,
            defaults={
                "start_date": date(current_year, 4, 1),
                "end_date": date(current_year + 1, 3, 31),
            },
        )
        if created:
            self.stdout.write(f"Created academic session: {session_year}")

        # Create terms
        terms_data = [
            ("First Term", date(current_year, 4, 1), date(current_year, 9, 30)),
            ("Second Term", date(current_year, 10, 1), date(current_year + 1, 3, 31)),
        ]

        for name, start, end in terms_data:
            term, created = Term.objects.get_or_create(
                academic_session=session,
                name=name,
                defaults={"start_date": start, "end_date": end},
            )
            if created:
                self.stdout.write(f"Created term: {name}")

        # Seed Exams
        exams_data = [
            "Assessment 1",
            "Internal 1",
            "Quarterly Exam",
            "Assessment 2",
            "Internal 2",
            "Half-Yearly Exam",
            "Annual Practical",
            "Annual Theory",
        ]

        # Determine which term to seed based on current date
        current_term = None
        for term in Term.objects.filter(academic_session=session):
            if term.start_date <= today <= term.end_date:
                current_term = term
                break

        # If no current term, use the first term
        if not current_term:
            current_term = Term.objects.filter(academic_session=session).first()

        if current_term:
            for exam_name in exams_data:
                exam, created = Exam.objects.get_or_create(
                    term=current_term,
                    name=exam_name,
                    defaults={"description": f"{exam_name} examination"},
                )
                if created:
                    self.stdout.write(f"Created exam: {exam_name}")

            # Create Exam Schedules
            self.seed_exam_schedules(current_term, current_year)

    def seed_exam_schedules(self, term, current_year):
        """Seed exam schedules with current year dates"""
        subjects = ["HINDI", "ENGLISH", "MATHS", "SCIENCE", "SOCIAL SCIENCE"]
        exams = Exam.objects.filter(term=term)

        schedule_data = []
        for exam in exams:
            for i, subject in enumerate(subjects):
                # Create dates within the term
                exam_date = term.start_date + timedelta(days=30 + (exam.id * 7) + i)
                if exam_date <= term.end_date:
                    schedule_data.append(
                        (exam.name, subject, exam_date, time(9, 0), f"Room {101 + i}")
                    )

        for exam_name, subject_name, exam_date, exam_time, room in schedule_data:
            try:
                exam = Exam.objects.get(term=term, name=exam_name)
                schedule, created = ExamSchedule.objects.get_or_create(
                    exam=exam,
                    subject=subject_name,
                    date=exam_date,
                    time=exam_time,
                    defaults={"room": room},
                )
                if created:
                    self.stdout.write(
                        f"Created exam schedule: {exam_name} - {subject_name} - {exam_date}"
                    )
            except Exam.DoesNotExist:
                self.stdout.write(f"Warning: Exam '{exam_name}' not found")

    def seed_students(self):
        """Seed student profiles"""
        classrooms = Classroom.objects.all()
        users = User.objects.filter(username__startswith="student")

        student_data = [
            ("student1", "1001", "10th", "Male", "2008-05-15", "9876543210"),
            ("student2", "1002", "9th", "Female", "2009-03-20", "9876543211"),
            ("student3", "1003", "8th", "Male", "2010-07-10", "9876543212"),
        ]

        for username, sr_no, grade, gender, dob, mobile in student_data:
            try:
                user = User.objects.get(username=username)
                classroom = Classroom.objects.get(grade=grade)

                student, created = Student.objects.get_or_create(
                    user=user,
                    defaults={
                        "sr_no": int(sr_no),
                        "roll_no": int(sr_no),
                        "admission_no": f"ADM{sr_no}",
                        "father_name": f"{user.last_name} Father",
                        "mother_name": f"{user.last_name} Mother",
                        "dob": dob,
                        "gender": gender,
                        "mobile_no": mobile,
                        "classroom": classroom,
                        "category": "General",
                        "current_address": "123 School Street, Education City",
                        "permanent_address": "123 School Street, Education City",
                    },
                )
                if created:
                    self.stdout.write(f"Created student: {user.get_full_name()}")
            except (User.DoesNotExist, Classroom.DoesNotExist):
                self.stdout.write(f"Warning: Could not create student for {username}")

    def seed_teachers(self):
        """Seed teacher profiles"""
        users = User.objects.filter(username__startswith="teacher")
        classrooms = Classroom.objects.all()[:3]  # Assign first 3 classrooms

        teacher_data = [
            ("teacher1", "Mathematics", "9876543213"),
            ("teacher2", "English", "9876543214"),
        ]

        for username, subject_name, mobile in teacher_data:
            try:
                user = User.objects.get(username=username)

                teacher, created = Teacher.objects.get_or_create(
                    user=user,
                    defaults={
                        "subject": subject_name,
                        "mobile_no": mobile,
                        "qualification": "M.Sc. B.Ed.",
                    },
                )
                if created:
                    teacher.classroom.set(classrooms)
                    teacher.save()
                    self.stdout.write(f"Created teacher: {user.get_full_name()}")
            except User.DoesNotExist:
                self.stdout.write(f"Warning: Could not create teacher for {username}")

    def seed_attendance(self, today):
        """Seed attendance records for current month"""
        students = Student.objects.all()
        teachers = Teacher.objects.all()
        start_of_month = today.replace(day=1)

        for student in students:
            # Create attendance for first 20 days of current month
            for day in range(1, min(21, today.day + 1)):
                attendance_date = start_of_month.replace(day=day)

                # Skip weekends
                if attendance_date.weekday() >= 5:
                    continue

                status = random.choice(
                    ["PRESENT", "PRESENT", "PRESENT", "ABSENT"]
                )  # 75% present

                # Get a random teacher for this attendance record
                teacher = teachers.first() if teachers.exists() else None
                if teacher:
                    attendance, created = Attendance.objects.get_or_create(
                        student=student,
                        date=attendance_date,
                        defaults={
                            "teacher": teacher,
                            "status": status,
                        },
                    )
                    if created:
                        self.stdout.write(
                            f"Created attendance: {student.user.get_full_name()} - {attendance_date} - {status}"
                        )

        # Seed teacher attendance
        admin_user = User.objects.filter(is_superuser=True).first()
        for teacher in teachers:
            for day in range(1, min(21, today.day + 1)):
                attendance_date = start_of_month.replace(day=day)
                if attendance_date.weekday() >= 5:
                    continue

                status = random.choice(["PRESENT", "PRESENT", "PRESENT", "ABSENT"])

                teacher_attendance, created = TeacherAttendance.objects.get_or_create(
                    teacher=teacher,
                    date=attendance_date,
                    defaults={
                        "status": status,
                        "marked_by": admin_user,
                    },
                )
                if created:
                    self.stdout.write(
                        f"Created teacher attendance: {teacher.user.get_full_name()} - {attendance_date}"
                    )

    def seed_leave_records(self, today):
        """Seed leave records"""
        students = Student.objects.all()
        teachers = Teacher.objects.all()

        reasons = ["Fever", "Family function", "Medical checkup", "Personal work"]

        # Student leaves
        for student in students:
            for _ in range(2):  # 2 leaves per student
                from_date = today - timedelta(days=random.randint(1, 30))
                to_date = from_date + timedelta(days=random.randint(1, 3))

                leave, created = Leave.objects.get_or_create(
                    student=student,
                    from_date=from_date,
                    defaults={
                        "to_date": to_date,
                        "reason": random.choice(reasons),
                        "status": random.choice(["APPROVED", "PENDING", "REJECTED"]),
                        "approved_by": User.objects.filter(is_superuser=True).first(),
                    },
                )
                if created:
                    self.stdout.write(
                        f"Created student leave: {student.user.get_full_name()} - {from_date} to {to_date}"
                    )

        # Teacher leaves
        for teacher in teachers:
            for _ in range(1):  # 1 leave per teacher
                from_date = today - timedelta(days=random.randint(1, 30))
                to_date = from_date + timedelta(days=random.randint(1, 5))

                leave, created = Leave.objects.get_or_create(
                    teacher=teacher,
                    from_date=from_date,
                    defaults={
                        "to_date": to_date,
                        "reason": random.choice(reasons),
                        "status": random.choice(["APPROVED", "PENDING", "REJECTED"]),
                    },
                )
                if created:
                    self.stdout.write(
                        f"Created teacher leave: {teacher.user.get_full_name()} - {from_date} to {to_date}"
                    )

    def seed_notices(self, today):
        """Seed notice board data"""
        notices_data = [
            (
                "School Reopening Notice",
                "All students are requested to report to school by 8:30 AM",
                "ANNOUNCEMENT",
            ),
            (
                "Exam Schedule Released",
                "Final examination schedule has been released",
                "ANNOUNCEMENT",
            ),
            (
                "Fee Payment Reminder",
                "Please clear all pending fees before the deadline",
                "ANNOUNCEMENT",
            ),
            (
                "Teacher Meeting",
                "All teachers to attend staff meeting tomorrow",
                "ANNOUNCEMENT",
            ),
            (
                "Holiday Notice",
                "School will remain closed on account of festival",
                "ANNOUNCEMENT",
            ),
        ]

        for title, content, notice_type in notices_data:
            notice, created = Notice.objects.get_or_create(
                title=title,
                defaults={
                    "content": content,
                    "notice_type": notice_type,
                    "created_by": User.objects.filter(is_superuser=True).first(),
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(f"Created notice: {title}")

    def seed_certificates(self):
        """Seed certificate types and certificates"""
        # Certificate Types
        cert_types_data = [
            ("COMPLETION", "Course Completion Certificate"),
            ("ACHIEVEMENT", "Achievement Certificate"),
            ("PARTICIPATION", "Participation Certificate"),
            ("CONDUCT", "Conduct Certificate"),
        ]

        for name, description in cert_types_data:
            cert_type, created = CertificateType.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            if created:
                self.stdout.write(f"Created certificate type: {name}")

        # Sample Certificates
        students = Student.objects.all()
        cert_types = CertificateType.objects.all()

        for student in students:
            for cert_type in cert_types[:2]:  # 2 certificates per student
                certificate, created = Certificate.objects.get_or_create(
                    student=student,
                    certificate_type=cert_type,
                    defaults={
                        "status": random.choice(["PENDING", "APPROVED", "REJECTED"]),
                        "issued_date": timezone.now().date()
                        - timedelta(days=random.randint(1, 30)),
                    },
                )
                if created:
                    self.stdout.write(
                        f"Created certificate: {student.user.get_full_name()} - {cert_type.name}"
                    )

    def seed_payments(self):
        """Seed payment records"""
        students = Student.objects.all()
        payment_descriptions = [
            "Tuition Fee",
            "Examination Fee",
            "Library Fee",
            "Computer Lab Fee",
            "Sports Fee",
            "Transportation Fee",
            "Stationery Fee",
        ]

        for student in students:
            for _ in range(3):  # 3 payments per student
                amount = Decimal(str(random.randint(500, 5000)))
                payment_date = timezone.now().date() - timedelta(
                    days=random.randint(1, 60)
                )

                payment, created = Payment.objects.get_or_create(
                    student=student,
                    amount=amount,
                    payment_date=payment_date,
                    defaults={
                        "description": random.choice(payment_descriptions),
                        "status": random.choice(["PAID", "PENDING", "OVERDUE"]),
                        "transaction_id": f"TXN{random.randint(100000, 999999)}",
                    },
                )
                if created:
                    self.stdout.write(
                        f"Created payment: {student.user.get_full_name()} - INR {amount} - {payment.description}"
                    )

    def seed_documents(self):
        """Seed document records"""
        students = Student.objects.all()
        document_names = [
            "Birth Certificate",
            "Aadhaar Card",
            "Marksheet",
            "Medical Certificate",
            "Address Proof",
        ]

        for student in students:
            for doc_name in document_names[:3]:  # 3 documents per student
                document, created = Document.objects.get_or_create(
                    student=student,
                    name=doc_name,
                    defaults={
                        "file": None,  # No actual file, just metadata
                        "uploaded_at": timezone.now()
                        - timedelta(days=random.randint(1, 90)),
                    },
                )
                if created:
                    self.stdout.write(
                        f"Created document: {student.user.get_full_name()} - {doc_name}"
                    )
