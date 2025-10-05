from django.core.management.base import BaseCommand
from datetime import date
from academics.models import AcademicSession, Term


class Command(BaseCommand):
    help = "Seed multiple academic sessions for testing session selection"

    def handle(self, *args, **options):
        self.stdout.write("Starting academic sessions seeding...")

        # Create multiple academic sessions
        sessions_data = [
            ("2022-2023", date(2022, 4, 1), date(2023, 3, 31)),
            ("2023-2024", date(2023, 4, 1), date(2024, 3, 31)),
            ("2024-2025", date(2024, 4, 1), date(2025, 3, 31)),
            ("2025-2026", date(2025, 4, 1), date(2026, 3, 31)),
        ]

        for year, start_date, end_date in sessions_data:
            session, created = AcademicSession.objects.get_or_create(
                year=year,
                defaults={
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            if created:
                self.stdout.write(f"Created academic session: {year}")

                # Create terms for each session
                terms_data = [
                    ("First Term", start_date, date(start_date.year, 9, 30)),
                    ("Second Term", date(start_date.year, 10, 1), end_date),
                ]

                for term_name, term_start, term_end in terms_data:
                    term, term_created = Term.objects.get_or_create(
                        academic_session=session,
                        name=term_name,
                        defaults={
                            "start_date": term_start,
                            "end_date": term_end,
                        },
                    )
                    if term_created:
                        self.stdout.write(f"Created term: {term_name} for {year}")

        self.stdout.write(
            self.style.SUCCESS("Academic sessions seeding completed successfully!")
        )
