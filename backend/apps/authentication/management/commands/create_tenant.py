import secrets
import string

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.authentication.models import Organization, UserProfile


class Command(BaseCommand):
    help = "Provision a new tenant (Organization + Admin User)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--org", type=str, required=True, help="Name of the Organization"
        )
        parser.add_argument(
            "--username", type=str, required=True, help="Username for the initial admin"
        )
        parser.add_argument(
            "--email", type=str, required=True, help="Email for the initial admin"
        )
        parser.add_argument(
            "--password",
            type=str,
            required=False,
            help="Password (generated if omitted)",
        )

    def handle(self, *args, **options):
        """Provision a tenant atomically.

        v3.1 Phase 4 (A-H3): the prior implementation wrapped the three-step
        Org/User/UserProfile creation in a bare `try/except Exception` that
        swallowed errors and printed them, leaving partial state behind. A
        UserProfile failure (signal error, integrity violation) would commit
        the Org and User but no profile — the exact state that produces the
        "Login 403/500" error documented in CLAUDE.md, AND re-running the
        command then fails because the user already exists.

        Now wraps in `transaction.atomic()` so any failure rolls back the
        whole tenant. The exception is logged via CommandError (Django's
        standard management-command failure path — surfaces a non-zero exit
        for CI/automation) instead of being swallowed.
        """
        org_name = options["org"]
        username = options["username"]
        email = options["email"]
        password = options["password"]

        # Generate password if not provided
        if not password:
            alphabet = string.ascii_letters + string.digits + string.punctuation
            password = "".join(secrets.choice(alphabet) for i in range(16))

        # Pre-check: refusing to start the atomic block at all if username
        # already exists is cleaner than rolling back mid-transaction.
        if User.objects.filter(username=username).exists():
            raise CommandError(f"User {username} already exists")

        try:
            with transaction.atomic():
                # 1. Create Organization
                slug = slugify(org_name)
                org, created = Organization.objects.get_or_create(
                    name=org_name, defaults={"slug": slug}
                )

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created Organization: {org_name} (slug: {org.slug})"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"Organization already exists: {org_name}")
                    )

                # 2. Create User
                user = User.objects.create_user(
                    username=username, email=email, password=password
                )
                self.stdout.write(self.style.SUCCESS(f"Created User: {username}"))

                # 3. Create UserProfile (Link User to Org as Admin)
                # Check if profile was auto-created by signal (if applicable)
                if not hasattr(user, "profile"):
                    UserProfile.objects.create(
                        user=user, organization=org, role="admin", is_active=True
                    )
                else:
                    # Update existing profile if signal created it
                    profile = user.profile
                    profile.organization = org
                    profile.role = "admin"
                    profile.save()

                self.stdout.write(
                    self.style.SUCCESS(f"Linked {username} to {org_name} as Admin")
                )
        except Exception as e:
            # Atomic block already rolled back; surface as CommandError so
            # the management command exits non-zero with the original
            # traceback intact (BaseCommand prints it).
            raise CommandError(f"Tenant provisioning failed: {e}") from e

        # 4. Success Output (outside the atomic block — only reached on
        # successful commit)
        self.stdout.write(
            self.style.SUCCESS("\n--- Tenant Provisioned Successfully ---")
        )
        self.stdout.write(f"Organization: {org_name}")
        self.stdout.write(f"URL:          (Login Page)")
        self.stdout.write(f"Username:     {username}")
        self.stdout.write(f"Password:     {password}")
        self.stdout.write("---------------------------------------")
