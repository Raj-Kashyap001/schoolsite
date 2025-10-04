from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, time, date, timedelta
from decimal import Decimal
import random

# Import all models from their respective apps
from academics.models import (
    AcademicSession,
    Term,
    Exam,
    ExamSchedule,
    ExamAssignment,
    ExamResult,
)
from students.models import Student, Classroom, Subject
from teachers.models import Teacher


class Command(BaseCommand):
    help = "Seed exam-related dummy data for testing exam marking functionality"

    def handle(self, *args, **options):
        self.stdout.write("Starting exam data seeding...")

        # Get current date for dynamic data
        today = date.today()
        current_year = today.year

        # 1. Ensure we have the 10th grade classroom
        self.stdout.write("Ensuring 10th grade classroom exists...")
        classroom_10th, created = Classroom.objects.get_or_create(
            grade="10th", defaults={"section": None}
        )
        if created:
            self.stdout.write("Created 10th grade classroom")

        # 2. Create more students for 10th grade
        self.stdout.write("Seeding 10th grade students...")
        self.seed_10th_grade_students(classroom_10th)

        # 3. Ensure teacher exists and is assigned to 10th grade
        self.stdout.write("Ensuring teacher assignment...")
        self.ensure_teacher_assignment(classroom_10th)

        # 4. Create academic session and term if not exists
        self.stdout.write("Ensuring academic session and term...")
        session, term = self.ensure_academic_session_and_term(current_year)

        # 5. Create exams for the term
        self.stdout.write("Creating exams...")
        exams = self.create_exams_for_term(term)

        # 6. Create exam schedules
        self.stdout.write("Creating exam schedules...")
        self.create_exam_schedules(exams, current_year)

        # 7. Assign exams to teacher
        self.stdout.write("Assigning exams to teacher...")
        self.assign_exams_to_teacher(exams, classroom_10th)

        # 8. Create some sample exam results
        self.stdout.write("Creating sample exam results...")
        self.create_sample_exam_results(exams, classroom_10th)

        self.stdout.write(
            self.style.SUCCESS("Exam data seeding completed successfully!")
        )

    def seed_10th_grade_students(self, classroom_10th):
        """Create multiple students for 10th grade"""
        student_names = [
            ("student1", "Amit", "Kumar", "1001", "Male"),
            ("student2", "Sneha", "Patel", "1002", "Female"),
            ("student3", "Rahul", "Singh", "1003", "Male"),
            ("student4", "Priya", "Sharma", "1004", "Female"),
            ("student5", "Vikram", "Gupta", "1005", "Male"),
            ("student6", "Anjali", "Verma", "1006", "Female"),
            ("student7", "Rohit", "Jain", "1007", "Male"),
            ("student8", "Kavita", "Mishra", "1008", "Female"),
            ("student9", "Arjun", "Yadav", "1009", "Male"),
            ("student10", "Meera", "Chauhan", "1010", "Female"),
        ]

        for username, first_name, last_name, roll_no, gender in student_names:
            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@hbr.edu",
                    "first_name": first_name,
                    "last_name": last_name,
                },
            )
            if user_created:
                user.set_password("password123")
                user.save()

            student, student_created = Student.objects.get_or_create(
                user=user,
                defaults={
                    "sr_no": int(roll_no),
                    "roll_no": int(roll_no),
                    "admission_no": f"ADM{roll_no}",
                    "father_name": f"{last_name} Father",
                    "mother_name": f"{last_name} Mother",
                    "dob": date(2008, 5, 15),  # All born in 2008
                    "gender": gender,
                    "mobile_no": f"9876543{roll_no[-1]}{roll_no[-2]}",
                    "classroom": classroom_10th,
                    "category": "General",
                    "current_address": "123 School Street, Education City",
                    "permanent_address": "123 School Street, Education City",
                },
            )
            if student_created:
                self.stdout.write(
                    f"Created student: {first_name} {last_name} (Roll: {roll_no})"
                )

    def ensure_teacher_assignment(self, classroom_10th):
        """Ensure teacher1 exists and is assigned to 10th grade"""
        user, user_created = User.objects.get_or_create(
            username="teacher1",
            defaults={
                "email": "teacher1@hbr.edu",
                "first_name": "Rajesh",
                "last_name": "Sharma",
            },
        )
        if user_created:
            user.set_password("password123")
            user.save()

        teacher, teacher_created = Teacher.objects.get_or_create(
            user=user,
            defaults={
                "subject": "Mathematics",
                "mobile_no": "9876543213",
                "qualification": "M.Sc. B.Ed.",
            },
        )

        # Assign classroom to teacher
        if not teacher.classroom.filter(id=classroom_10th.id).exists():
            teacher.classroom.add(classroom_10th)
            teacher.save()
            self.stdout.write("Assigned 10th grade to teacher1")

        return teacher

    def ensure_academic_session_and_term(self, current_year):
        """Create academic session and term if not exists"""
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

        # Create current term
        term, created = Term.objects.get_or_create(
            academic_session=session,
            name="First Term",
            defaults={
                "start_date": date(current_year, 4, 1),
                "end_date": date(current_year, 9, 30),
            },
        )
        if created:
            self.stdout.write("Created First Term")

        return session, term

    def create_exams_for_term(self, term):
        """Create exams for the term"""
        exam_names = [
            "Assessment 1",
            "Internal 1",
            "Quarterly Exam",
        ]

        exams = []
        for exam_name in exam_names:
            exam, created = Exam.objects.get_or_create(
                term=term,
                name=exam_name,
                defaults={"description": f"{exam_name} examination for 10th grade"},
            )
            if created:
                self.stdout.write(f"Created exam: {exam_name}")
            exams.append(exam)

        return exams

    def create_exam_schedules(self, exams, current_year):
        """Create exam schedules with subjects"""
        subjects = ["HINDI", "ENGLISH", "MATHS", "SCIENCE", "SOCIAL SCIENCE"]

        for exam in exams:
            for i, subject_name in enumerate(subjects):
                # Create dates within the term
                exam_date = exam.term.start_date + timedelta(
                    days=30 + (exam.id * 7) + i
                )
                if exam_date <= exam.term.end_date:
                    schedule, created = ExamSchedule.objects.get_or_create(
                        exam=exam,
                        subject=subject_name,
                        date=exam_date,
                        time=time(9, 0),
                        defaults={"room": f"Room {101 + i}"},
                    )
                    if created:
                        self.stdout.write(
                            f"Created exam schedule: {exam.name} - {subject_name} - {exam_date}"
                        )

    def assign_exams_to_teacher(self, exams, classroom_10th):
        """Assign exams to teacher for 10th grade"""
        try:
            teacher = Teacher.objects.get(user__username="teacher1")

            for exam in exams:
                assignment, created = ExamAssignment.objects.get_or_create(
                    exam=exam,
                    teacher=teacher,
                    classroom=classroom_10th,
                    defaults={"assigned_at": timezone.now()},
                )
                if created:
                    self.stdout.write(
                        f"Assigned exam '{exam.name}' to teacher1 for 10th grade"
                    )
        except Teacher.DoesNotExist:
            self.stdout.write("Warning: teacher1 not found")

    def create_sample_exam_results(self, exams, classroom_10th):
        """Create some sample exam results"""
        students = Student.objects.filter(classroom=classroom_10th)
        subjects = ["HINDI", "ENGLISH", "MATHS", "SCIENCE", "SOCIAL SCIENCE"]

        # Create results for first exam only, with some marks
        if exams:
            exam = exams[0]  # Assessment 1
            teacher = Teacher.objects.get(user__username="teacher1")

            for student in students[:5]:  # First 5 students
                for subject in subjects:
                    # Random marks between 60-95
                    marks = Decimal(str(random.randint(60, 95)))

                    result, created = ExamResult.objects.get_or_create(
                        student=student,
                        exam=exam,
                        subject=subject,
                        defaults={
                            "marks_obtained": marks,
                            "total_marks": Decimal("100"),
                            "grade": self.calculate_grade(marks),
                            "status": "SUBMITTED",
                            "submitted_by": teacher.user,
                            "submitted_at": timezone.now(),
                        },
                    )
                    if created:
                        self.stdout.write(
                            f"Created result: {student.user.get_full_name()} - {subject} - {marks}"
                        )

    def calculate_grade(self, marks):
        """Calculate grade based on marks"""
        if marks >= 90:
            return "A+"
        elif marks >= 80:
            return "A"
        elif marks >= 70:
            return "B+"
        elif marks >= 60:
            return "B"
        elif marks >= 50:
            return "C"
        else:
            return "D"
