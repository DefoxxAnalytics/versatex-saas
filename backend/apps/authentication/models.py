"""
Authentication models for organization-based multi-tenancy
"""
from django.db import models, transaction
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError


class Organization(models.Model):
    """
    Organization model for multi-tenancy
    Each organization has its own isolated data
    """
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(
        default=False,
        help_text=(
            'True if this organization contains seeded/synthetic demo data '
            '(not real customer data). Set automatically by the '
            'seed_industry_data and seed_demo_data management commands.'
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Branding fields for reports
    logo = models.ImageField(
        upload_to='org_logos/',
        null=True,
        blank=True,
        help_text='Organization logo for reports (recommended: 200x60px PNG)'
    )
    primary_color = models.CharField(
        max_length=7,
        default='#1e3a5f',
        help_text='Primary brand color in hex format (e.g., #1e3a5f)'
    )
    secondary_color = models.CharField(
        max_length=7,
        default='#2563eb',
        help_text='Secondary brand color in hex format (e.g., #2563eb)'
    )
    report_footer = models.TextField(
        blank=True,
        default='',
        help_text='Custom footer text for reports (e.g., confidentiality notice)'
    )
    website = models.URLField(
        blank=True,
        help_text='Organization website URL'
    )

    # AI Insights Savings Configuration
    savings_config = models.JSONField(
        default=dict,
        blank=True,
        help_text='Configurable savings rates for AI Insights (industry benchmarks)'
    )

    ALLOWED_SAVINGS_CONFIG_KEYS = {
        'benchmark_profile',
        'consolidation_rate',
        'anomaly_recovery_rate',
        'price_variance_capture',
        'specification_rate',
        'payment_terms_rate',
        'process_savings_per_txn',
        'enabled_insights',
    }

    BENCHMARK_PROFILES = {
        'conservative': {
            'consolidation_rate': 0.01,
            'anomaly_recovery_rate': 0.005,
            'price_variance_capture': 0.30,
            'specification_rate': 0.02,
            'payment_terms_rate': 0.005,
            'process_savings_per_txn': 25,
            'realization_probability': 0.90,
            'confidence_range': '85-95%',
        },
        'moderate': {
            'consolidation_rate': 0.03,
            'anomaly_recovery_rate': 0.008,
            'price_variance_capture': 0.40,
            'specification_rate': 0.03,
            'payment_terms_rate': 0.008,
            'process_savings_per_txn': 35,
            'realization_probability': 0.75,
            'confidence_range': '70-85%',
        },
        'aggressive': {
            'consolidation_rate': 0.05,
            'anomaly_recovery_rate': 0.015,
            'price_variance_capture': 0.60,
            'specification_rate': 0.04,
            'payment_terms_rate': 0.012,
            'process_savings_per_txn': 50,
            'realization_probability': 0.55,
            'confidence_range': '50-70%',
        },
    }

    class Meta:
        ordering = ['name']
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'

    def __str__(self):
        return self.name

    def get_branding(self):
        """Return branding configuration for reports."""
        return {
            'name': self.name,
            'logo_path': self.logo.path if self.logo else None,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'footer': self.report_footer,
            'website': self.website,
        }

    def get_savings_config(self) -> dict:
        """
        Get effective savings configuration with defaults.

        Returns merged config with benchmark profile defaults as base,
        overridden by any custom values in savings_config.

        Industry benchmark sources (FY2025 Procurement Savings Initiative):
        - Vendor Consolidation: Deloitte 2024 (1-8%)
        - Invoice Accuracy: Aberdeen Group (0.5-1.5%)
        - Specification Standardization: McKinsey 2024 (2-4%)
        - Payment Terms: Hackett Group (0.5-1.2%)
        - Process Automation: APQC ($25-50/txn)
        """
        config = self.savings_config or {}
        profile = config.get('benchmark_profile', 'moderate')

        if profile in self.BENCHMARK_PROFILES:
            base_config = self.BENCHMARK_PROFILES[profile].copy()
        else:
            base_config = self.BENCHMARK_PROFILES['moderate'].copy()

        base_config.update({k: v for k, v in config.items() if k != 'benchmark_profile'})
        base_config['benchmark_profile'] = profile

        return base_config


class UserProfile(models.Model):
    """
    Extended user profile with organization and role
    """
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('viewer', 'Viewer'),
    ]

    # Allowed keys for the preferences JSONField.
    # Any new key added here must ALSO be declared explicitly on
    # UserPreferencesSerializer so DRF accepts it on PATCH/PUT.
    # The aiApiKey value is masked on read (see UserProfileSerializer
    # .to_representation and UserPreferencesView.get).
    ALLOWED_PREFERENCE_KEYS = {
        'theme', 'colorScheme', 'notifications', 'exportFormat',
        'currency', 'dateFormat', 'dashboardLayout', 'sidebarCollapsed',
        # AI / Predictive settings
        'useExternalAI', 'aiProvider', 'aiApiKey',
        'forecastingModel', 'forecastHorizonMonths', 'anomalySensitivity',
    }

    # Preference keys that contain secrets and MUST be masked in all outbound
    # responses. Mask format: None if absent, '****' + value[-4:] otherwise.
    MASKED_PREFERENCE_KEYS = frozenset({'aiApiKey'})

    @staticmethod
    def mask_preferences(prefs):
        """
        Return a copy of ``prefs`` with secret-marked keys replaced by a
        masked preview. Used by every outbound serialization path.
        """
        if not isinstance(prefs, dict):
            return prefs
        masked = dict(prefs)
        for key in UserProfile.MASKED_PREFERENCE_KEYS:
            value = masked.get(key)
            if not value:
                masked[key] = None
            else:
                masked[key] = '****' + str(value)[-4:]
        return masked

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,  # Prevent accidental organization deletion when users exist
        related_name='users'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    preferences = models.JSONField(default=dict, blank=True, help_text='User preferences (theme, notifications, etc.)')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user__username']
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.username} - {self.organization.name} ({self.role})"
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_manager(self):
        return self.role in ['admin', 'manager']
    
    def can_upload_data(self):
        return self.role in ['admin', 'manager']
    
    def can_delete_data(self):
        return self.role == 'admin'

    def is_super_admin(self):
        """Check if user is a super admin (Django superuser).

        Super admins have platform-level privileges that transcend organization
        boundaries, such as uploading data for multiple organizations at once.
        """
        return self.user.is_superuser

    # Multi-organization support helper methods
    def get_memberships(self):
        """Get all active organization memberships for this user."""
        return UserOrganizationMembership.objects.filter(
            user=self.user,
            is_active=True
        ).select_related('organization')

    def get_primary_membership(self):
        """Get the primary organization membership."""
        return self.get_memberships().filter(is_primary=True).first()

    def get_membership_for_org(self, organization):
        """Get membership for a specific organization."""
        if isinstance(organization, int):
            return self.get_memberships().filter(organization_id=organization).first()
        return self.get_memberships().filter(organization=organization).first()

    def has_org_access(self, organization):
        """Check if user has access to the given organization."""
        if self.user.is_superuser:
            return True
        if isinstance(organization, int):
            return self.get_memberships().filter(organization_id=organization).exists()
        return self.get_memberships().filter(organization=organization).exists()

    def get_role_for_org(self, organization):
        """Get the user's role in a specific organization."""
        if self.user.is_superuser:
            return 'admin'  # Superusers have admin access everywhere
        membership = self.get_membership_for_org(organization)
        return membership.role if membership else None

    def is_admin_in_org(self, organization):
        """Check if user is admin in the given organization."""
        role = self.get_role_for_org(organization)
        return role == 'admin'

    def is_manager_in_org(self, organization):
        """Check if user is manager+ in the given organization."""
        role = self.get_role_for_org(organization)
        return role in ['admin', 'manager']

    def can_upload_in_org(self, organization):
        """Check if user can upload data in the given organization."""
        role = self.get_role_for_org(organization)
        return role in ['admin', 'manager']

    def can_delete_in_org(self, organization):
        """Check if user can delete data in the given organization."""
        role = self.get_role_for_org(organization)
        return role == 'admin'


class UserOrganizationMembership(models.Model):
    """
    Many-to-many relationship between Users and Organizations.
    Allows users to belong to multiple organizations with different roles per org.
    """
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('viewer', 'Viewer'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='organization_memberships'
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,  # Prevent accidental organization deletion when memberships exist
        related_name='user_memberships'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    is_primary = models.BooleanField(
        default=False,
        help_text="Designates this as the user's default/primary organization"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_invitations',
        help_text='User who invited this member to the organization'
    )

    class Meta:
        ordering = ['-is_primary', 'organization__name']
        verbose_name = 'User Organization Membership'
        verbose_name_plural = 'User Organization Memberships'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'organization'],
                name='unique_user_organization'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'is_primary']),
            models.Index(fields=['organization', 'role']),
        ]

    def __str__(self):
        primary_tag = ' (Primary)' if self.is_primary else ''
        return f"{self.user.username} - {self.organization.name} ({self.role}){primary_tag}"

    def save(self, *args, **kwargs):
        """
        Ensure only one primary membership per user.

        Uses atomic transaction with select_for_update to prevent race conditions
        where concurrent requests could both set is_primary=True.
        """
        if self.is_primary:
            # Use atomic transaction to prevent race conditions
            with transaction.atomic():
                # Lock existing primary memberships for this user to prevent races
                existing_primaries = UserOrganizationMembership.objects.select_for_update().filter(
                    user=self.user,
                    is_primary=True
                ).exclude(pk=self.pk)
                # Unset other primaries for this user
                existing_primaries.update(is_primary=False)
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def is_admin(self):
        """Check if this membership has admin role."""
        return self.role == 'admin'

    def is_manager(self):
        """Check if this membership has manager+ role."""
        return self.role in ['admin', 'manager']

    def can_upload_data(self):
        """Check if this membership allows data uploads."""
        return self.role in ['admin', 'manager']

    def can_delete_data(self):
        """Check if this membership allows data deletion."""
        return self.role == 'admin'


class AuditLog(models.Model):
    """
    Audit log for tracking user actions.

    Security: The details JSONField is validated to only accept known keys
    to prevent injection of arbitrary data.
    """
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('upload', 'Upload'),
        ('export', 'Export'),
        ('download', 'Download'),  # Report downloads
        ('view', 'View'),
        ('reset', 'Reset'),           # Organization reset
        ('bulk_delete', 'Bulk Delete'),  # Delete all data
        ('generate', 'Generate'),  # Report generation
        ('share', 'Share'),            # Report sharing
        ('execute', 'Execute'),        # Schedule execution
    ]

    # Allowed keys for the details JSONField (security: prevent arbitrary data injection)
    ALLOWED_DETAIL_KEYS = {
        'file_name', 'successful', 'failed', 'duplicate', 'batch_id', 'record_id',
        'changes', 'count', 'username', 'error', 'old_value', 'new_value',
        'reason', 'target_id', 'target_type', 'organizations_affected',
        # Organization switcher (superuser feature)
        'organization_id',
        # AI & Predictive Analytics keys
        'months', 'category_id', 'supplier_id', 'annual_budget', 'days',
        'contract_id', 'violation_id', 'resolved', 'severity', 'sensitivity',
        'insight_count', 'resolution_notes', 'ai_enhanced', 'cache_hit', 'insight_id', 'insight_type',
        # Insight Feedback keys
        'action_taken', 'outcome', 'actual_savings',
        # Tail Spend Analysis keys
        'threshold',
        # Data Upload Center keys
        'organization_name', 'deleted_counts', 'transactions_deleted', 'uploads_deleted',
        'suppliers_deleted', 'categories_deleted', 'templates_deleted', 'contracts_deleted',
        'duplicates', 'skipped', 'template_name', 'mapping_snapshot', 'processing_mode',
        # P2P document deletion keys (reset organization)
        'invoices_deleted', 'purchase_orders_deleted', 'goods_receipts_deleted', 'purchase_requisitions_deleted',
        # Reports module keys
        'report_type', 'report_id', 'schedule_id', 'format', 'async', 'name',
        'is_public', 'shared_count', 'frequency',  # Report sharing and scheduling
        # P2P Analytics keys
        'weeks', 'stage', 'invoice_id', 'pr_id', 'po_id', 'limit',
        'status', 'exception_type', 'resolved_count', 'failed_count',
        # Seeded dataset export (admin action)
        'is_demo', 'row_counts', 'zip_bytes',
    }

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=100, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['organization', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]

    def clean(self):
        """Validate audit log details schema."""
        super().clean()
        if self.details:
            if not isinstance(self.details, dict):
                raise ValidationError({'details': 'Details must be a dictionary'})

            invalid_keys = set(self.details.keys()) - self.ALLOWED_DETAIL_KEYS
            if invalid_keys:
                raise ValidationError({
                    'details': f"Invalid audit log detail keys: {', '.join(sorted(invalid_keys))}"
                })

            # Validate value types (simple types only for security)
            for key, value in self.details.items():
                if value is not None and not isinstance(value, (str, int, float, bool, list)):
                    raise ValidationError({
                        'details': f"Invalid value type for key '{key}'. Only str, int, float, bool, list allowed."
                    })

    def save(self, *args, **kwargs):
        """Validate before saving."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.action} - {self.resource} at {self.timestamp}"


# =============================================================================
# Signals to sync UserProfile and UserOrganizationMembership
# =============================================================================

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create UserProfile when User is created
    Note: Organization must be set manually after creation
    """
    if created and not hasattr(instance, 'profile'):
        # Don't auto-create profile, let registration handle it
        pass


@receiver(post_save, sender=UserProfile)
def sync_membership_from_profile(sender, instance, created, **kwargs):
    """
    When UserProfile.organization or role changes, sync to UserOrganizationMembership.

    - If no membership exists for the profile's org, create one as primary
    - If membership exists, update role to match profile
    - Sets the profile's org membership as primary
    """
    if not instance.organization_id:
        return

    # Prevent infinite recursion
    if getattr(instance, '_syncing_from_membership', False):
        return

    membership, created_new = UserOrganizationMembership.objects.get_or_create(
        user=instance.user,
        organization=instance.organization,
        defaults={
            'role': instance.role,
            'is_primary': True,
            'is_active': instance.is_active,
        }
    )

    if not created_new:
        # Update existing membership to match profile
        updated = False
        if membership.role != instance.role:
            membership.role = instance.role
            updated = True
        if not membership.is_primary:
            membership.is_primary = True
            updated = True
        if membership.is_active != instance.is_active:
            membership.is_active = instance.is_active
            updated = True

        if updated:
            membership._syncing_from_profile = True
            membership.save()


@receiver(post_save, sender=UserOrganizationMembership)
def sync_profile_from_membership(sender, instance, **kwargs):
    """
    When a membership is set as primary, sync to UserProfile.

    - Updates UserProfile.organization and role to match primary membership
    """
    # Only sync if this is the primary membership
    if not instance.is_primary:
        return

    # Prevent infinite recursion
    if getattr(instance, '_syncing_from_profile', False):
        return

    try:
        profile = instance.user.profile
    except UserProfile.DoesNotExist:
        return

    updated = False
    if profile.organization_id != instance.organization_id:
        profile.organization = instance.organization
        updated = True
    if profile.role != instance.role:
        profile.role = instance.role
        updated = True

    if updated:
        profile._syncing_from_membership = True
        profile.save()
