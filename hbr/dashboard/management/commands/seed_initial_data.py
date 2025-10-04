from django.core.management.base import BaseCommand
from dashboard.models import (
    Classroom,
    Subject,
    Stream,
    Exam,
    Term,
    AcademicSession,
    ExamSchedule,
)
from datetime import datetime, time


class Command(BaseCommand):
    help = "Seed initial data for classes, subjects, and exams"

    def handle(self, *args, **options):
        self.stdout.write("Seeding initial data...")

        # Seed Classes
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

        # Seed Streams
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

        # Seed Subjects (till 10th)
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
        ]

        for name, code in subjects_data:
            subject, created = Subject.objects.get_or_create(
                name=name, defaults={"code": code, "is_active": True}
            )
            if created:
                self.stdout.write(f"Created subject: {name}")

        # Create a default academic session if none exists
        session, created = AcademicSession.objects.get_or_create(
            year="2024-2025",
            defaults={"start_date": "2024-04-01", "end_date": "2025-03-31"},
        )
        if created:
            self.stdout.write("Created academic session: 2024-2025")

        # Create terms
        terms_data = [
            ("First Term", "2024-04-01", "2024-09-30"),
            ("Second Term", "2024-10-01", "2025-03-31"),
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
            "Asst. 1st",
            "Int. 1st",
            "Qtrly Exam",
            "Asst. 2nd",
            "Int. 2nd",
            "Half Yearly Exam",
            "Annual Pract.",
            "Annual Theory",
        ]

        # Get the first term to associate exams with
        first_term = Term.objects.filter(academic_session=session).first()
        if first_term:
            for exam_name in exams_data:
                exam, created = Exam.objects.get_or_create(
                    term=first_term,
                    name=exam_name,
                    defaults={"description": f"{exam_name} examination"},
                )
                if created:
                    self.stdout.write(f"Created exam: {exam_name}")

            # Create Exam Schedules for the exams
            exam_schedules_data = [
                # Asst. 1st exam schedules
                ("Asst. 1st", "HINDI", "2024-04-15", "09:00", "Room 101"),
                ("Asst. 1st", "ENGLISH", "2024-04-16", "09:00", "Room 102"),
                ("Asst. 1st", "MATHS", "2024-04-17", "09:00", "Room 103"),
                ("Asst. 1st", "SCIENCE", "2024-04-18", "09:00", "Room 104"),
                ("Asst. 1st", "SOCIAL SCIENCE", "2024-04-19", "09:00", "Room 105"),
                # Int. 1st exam schedules
                ("Int. 1st", "HINDI", "2024-05-15", "09:00", "Room 101"),
                ("Int. 1st", "ENGLISH", "2024-05-16", "09:00", "Room 102"),
                ("Int. 1st", "MATHS", "2024-05-17", "09:00", "Room 103"),
                ("Int. 1st", "SCIENCE", "2024-05-18", "09:00", "Room 104"),
                ("Int. 1st", "SOCIAL SCIENCE", "2024-05-19", "09:00", "Room 105"),
                # Qtrly Exam schedules
                ("Qtrly Exam", "HINDI", "2024-07-15", "09:00", "Room 101"),
                ("Qtrly Exam", "ENGLISH", "2024-07-16", "09:00", "Room 102"),
                ("Qtrly Exam", "MATHS", "2024-07-17", "09:00", "Room 103"),
                ("Qtrly Exam", "SCIENCE", "2024-07-18", "09:00", "Room 104"),
                ("Qtrly Exam", "SOCIAL SCIENCE", "2024-07-19", "09:00", "Room 105"),
            ]

            for (
                exam_name,
                subject_name,
                date_str,
                time_str,
                room,
            ) in exam_schedules_data:
                try:
                    exam = Exam.objects.get(term=first_term, name=exam_name)
                    schedule, created = ExamSchedule.objects.get_or_create(
                        exam=exam,
                        date=date_str,
                        time=time_str,
                        subject=subject_name,
                        defaults={"room": room},
                    )
                    if created:
                        self.stdout.write(
                            f"Created exam schedule: {exam_name} - {subject_name} - {date_str}"
                        )
                except Exam.DoesNotExist:
                    self.stdout.write(
                        f"Warning: Exam '{exam_name}' not found, skipping schedule creation"
                    )

        self.stdout.write(self.style.SUCCESS("Initial data seeding completed!"))
