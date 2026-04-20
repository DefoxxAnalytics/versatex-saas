# Generated migration for UserOrganizationMembership model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('authentication', '0004_add_organization_branding_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserOrganizationMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('admin', 'Administrator'), ('manager', 'Manager'), ('viewer', 'Viewer')], default='viewer', max_length=20)),
                ('is_primary', models.BooleanField(default=False, help_text="Designates this as the user's default/primary organization")),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('invited_by', models.ForeignKey(blank=True, help_text='User who invited this member to the organization', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_invitations', to=settings.AUTH_USER_MODEL)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_memberships', to='authentication.organization')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='organization_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Organization Membership',
                'verbose_name_plural': 'User Organization Memberships',
                'ordering': ['-is_primary', 'organization__name'],
            },
        ),
        migrations.AddConstraint(
            model_name='userorganizationmembership',
            constraint=models.UniqueConstraint(fields=('user', 'organization'), name='unique_user_organization'),
        ),
        migrations.AddIndex(
            model_name='userorganizationmembership',
            index=models.Index(fields=['user', 'is_primary'], name='authenticat_user_id_7c5f3e_idx'),
        ),
        migrations.AddIndex(
            model_name='userorganizationmembership',
            index=models.Index(fields=['organization', 'role'], name='authenticat_organiz_3a8b2c_idx'),
        ),
    ]
