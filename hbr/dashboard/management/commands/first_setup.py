from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import User, Group
from decouple import config


class Command(BaseCommand):
    help = "Initial setup: migrate, create groups, create superuser"

    def handle(self, *args, **options):
        # Apply migrations
        self.stdout.write("Applying migrations...")
        call_command("migrate")

        # Create groups
        groups = ["Admin", "Teacher", "Student"]
        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f"Created group: {group_name}")
            else:
                self.stdout.write(f"Group {group_name} already exists")

        # Create superuser from env vars
        username = config("DJANGO_SUPERUSER_USERNAME")
        email = config("DJANGO_SUPERUSER_EMAIL")
        password = config("DJANGO_SUPERUSER_PASSWORD")

        if not User.objects.filter(username=username).exists():
            user = User.objects.create_superuser(
                username=username, email=email, password=password
            )
            admin_group = Group.objects.get(name="Admin")
            user.groups.add(admin_group)
            self.stdout.write(
                f"Created superuser: {username} and assigned to Admin group"
            )
        else:
            self.stdout.write(f"Superuser {username} already exists")
