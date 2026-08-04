"""Create a demo superuser when none exists."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Ensure a local demo superuser exists for Django Admin access."""

    help = (
        "Create a demo superuser if the auth user table has no superusers. "
        "Defaults: username=admin, email=admin@example.com, password=admin."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--username", default="admin")
        parser.add_argument("--email", default="admin@example.com")
        parser.add_argument("--password", default="admin")

    def handle(self, *args, **options) -> None:
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.SUCCESS("A superuser already exists."))
            return

        User.objects.create_superuser(
            username=options["username"],
            email=options["email"],
            password=options["password"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created superuser '{options['username']}' "
                f"(password: {options['password']})."
            )
        )
