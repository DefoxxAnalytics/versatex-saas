# Add is_demo flag to Organization and backfill the three seeded demo tenants.

from django.db import migrations, models


DEMO_SLUGS = ('eaton', 'uch', 'tsu')


def backfill_demo_flag(apps, schema_editor):
    Organization = apps.get_model('authentication', 'Organization')
    Organization.objects.filter(slug__in=DEMO_SLUGS).update(is_demo=True)


def revert_demo_flag(apps, schema_editor):
    Organization = apps.get_model('authentication', 'Organization')
    Organization.objects.filter(slug__in=DEMO_SLUGS).update(is_demo=False)


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0009_savings_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='is_demo',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'True if this organization contains seeded/synthetic demo data '
                    '(not real customer data). Set automatically by the '
                    'seed_industry_data and seed_demo_data management commands.'
                ),
            ),
        ),
        migrations.RunPython(backfill_demo_flag, revert_demo_flag),
    ]
