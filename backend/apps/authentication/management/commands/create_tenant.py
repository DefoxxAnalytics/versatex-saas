import secrets
import string
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.contrib.auth.models import User
from django.utils.text import slugify
from apps.authentication.models import Organization, UserProfile

class Command(BaseCommand):
    help = 'Provision a new tenant (Organization + Admin User)'

    def add_arguments(self, parser):
        parser.add_argument('--org', type=str, required=True, help='Name of the Organization')
        parser.add_argument('--username', type=str, required=True, help='Username for the initial admin')
        parser.add_argument('--email', type=str, required=True, help='Email for the initial admin')
        parser.add_argument('--password', type=str, required=False, help='Password (generated if omitted)')

    def handle(self, *args, **options):
        org_name = options['org']
        username = options['username']
        email = options['email']
        password = options['password']

        # Generate password if not provided
        if not password:
            alphabet = string.ascii_letters + string.digits + string.punctuation
            password = ''.join(secrets.choice(alphabet) for i in range(16))

        try:
            # 1. Create Organization
            slug = slugify(org_name)
            org, created = Organization.objects.get_or_create(
                name=org_name,
                defaults={'slug': slug}
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Organization: {org_name} (slug: {org.slug})'))
            else:
                self.stdout.write(self.style.WARNING(f'Organization already exists: {org_name}'))

            # 2. Create User
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.ERROR(f'User {username} already exists'))
                return

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'Created User: {username}'))

            # 3. Create UserProfile (Link User to Org as Admin)
            # Check if profile was auto-created by signal (if applicable)
            if not hasattr(user, 'profile'):
                UserProfile.objects.create(
                    user=user,
                    organization=org,
                    role='admin',
                    is_active=True
                )
            else:
                # Update existing profile if signal created it
                profile = user.profile
                profile.organization = org
                profile.role = 'admin'
                profile.save()

            self.stdout.write(self.style.SUCCESS(f'Linked {username} to {org_name} as Admin'))
            
            # 4. Success Output
            self.stdout.write(self.style.SUCCESS('\n--- Tenant Provisioned Successfully ---'))
            self.stdout.write(f'Organization: {org_name}')
            self.stdout.write(f'URL:          (Login Page)')
            self.stdout.write(f'Username:     {username}')
            self.stdout.write(f'Password:     {password}')
            self.stdout.write('---------------------------------------')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error provisioning tenant: {str(e)}'))
