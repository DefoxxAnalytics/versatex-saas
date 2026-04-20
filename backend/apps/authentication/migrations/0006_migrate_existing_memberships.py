# Data migration to copy existing UserProfile relationships to UserOrganizationMembership

from django.db import migrations


def forwards_func(apps, schema_editor):
    """
    Copy existing UserProfile organization/role data to UserOrganizationMembership.
    Each existing profile becomes a primary membership in the new model.
    """
    UserProfile = apps.get_model('authentication', 'UserProfile')
    UserOrganizationMembership = apps.get_model('authentication', 'UserOrganizationMembership')

    for profile in UserProfile.objects.select_related('user', 'organization').all():
        # Create membership from existing profile
        UserOrganizationMembership.objects.get_or_create(
            user=profile.user,
            organization=profile.organization,
            defaults={
                'role': profile.role,
                'is_primary': True,  # Existing org becomes primary
                'is_active': profile.is_active,
            }
        )


def backwards_func(apps, schema_editor):
    """
    Remove all memberships created by this migration.
    Note: This will delete all memberships, including any added after migration.
    """
    UserOrganizationMembership = apps.get_model('authentication', 'UserOrganizationMembership')
    UserOrganizationMembership.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0005_add_user_organization_membership'),
    ]

    operations = [
        migrations.RunPython(forwards_func, backwards_func),
    ]
