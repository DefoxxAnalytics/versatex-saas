"""
Serializers for authentication
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Organization, UserProfile, AuditLog, UserOrganizationMembership


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model"""

    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'description', 'is_active', 'is_demo', 'created_at']
        read_only_fields = ['id', 'is_demo', 'created_at']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model with optional organizations list."""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    organization_is_demo = serializers.BooleanField(source='organization.is_demo', read_only=True)
    is_super_admin = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'id', 'organization', 'organization_name', 'organization_is_demo', 'role',
            'phone', 'department', 'preferences', 'is_active',
            'created_at', 'is_super_admin', 'organizations'
        ]
        read_only_fields = ['id', 'organization_is_demo', 'created_at', 'is_super_admin', 'organizations']

    def to_representation(self, instance):
        """Mask secret preference keys (e.g. aiApiKey) before serialization."""
        data = super().to_representation(instance)
        data['preferences'] = UserProfile.mask_preferences(data.get('preferences') or {})
        return data

    def get_is_super_admin(self, obj):
        """Return whether the user is a super admin (Django superuser)."""
        return obj.is_super_admin()

    def get_organizations(self, obj):
        """Return all active organization memberships for this user."""
        memberships = UserOrganizationMembership.objects.filter(
            user=obj.user,
            is_active=True
        ).select_related('organization')
        # Return simplified list for API response
        return [
            {
                'id': m.id,
                'organization': m.organization.id,
                'organization_name': m.organization.name,
                'organization_slug': m.organization.slug,
                'organization_is_demo': m.organization.is_demo,
                'role': m.role,
                'is_primary': m.is_primary,
            }
            for m in memberships
        ]


class UserPreferencesSerializer(serializers.Serializer):
    """Serializer for user preferences update."""
    theme = serializers.ChoiceField(choices=['light', 'dark', 'system'], required=False)
    colorScheme = serializers.ChoiceField(choices=['navy', 'classic', 'versatex'], required=False)
    notifications = serializers.BooleanField(required=False)
    exportFormat = serializers.ChoiceField(choices=['csv', 'xlsx', 'json'], required=False)
    currency = serializers.CharField(max_length=10, required=False)
    dateFormat = serializers.ChoiceField(
        choices=['MM/DD/YYYY', 'DD/MM/YYYY', 'YYYY-MM-DD'],
        required=False
    )
    dashboardLayout = serializers.CharField(max_length=50, required=False)
    sidebarCollapsed = serializers.BooleanField(required=False)

    # AI / Predictive settings — must match UserProfile.ALLOWED_PREFERENCE_KEYS.
    useExternalAI = serializers.BooleanField(required=False)
    aiProvider = serializers.ChoiceField(choices=['anthropic', 'openai'], required=False)
    aiApiKey = serializers.CharField(required=False, allow_blank=True, max_length=300, trim_whitespace=True)
    forecastingModel = serializers.ChoiceField(
        choices=['simple_average', 'linear', 'advanced'],
        required=False,
    )
    forecastHorizonMonths = serializers.IntegerField(required=False, min_value=1, max_value=36)
    anomalySensitivity = serializers.FloatField(required=False, min_value=0.5, max_value=5.0)

    def validate(self, attrs):
        """Filter out keys not in ALLOWED_PREFERENCE_KEYS."""
        allowed_keys = UserProfile.ALLOWED_PREFERENCE_KEYS
        return {k: v for k, v in attrs.items() if k in allowed_keys}


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with profile"""
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']
        read_only_fields = ['id']


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(is_active=True)
    )
    role = serializers.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        default='viewer'
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'organization', 'role'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def create(self, validated_data):
        # Remove password_confirm and organization/role from user data
        validated_data.pop('password_confirm')
        organization = validated_data.pop('organization')
        role = validated_data.pop('role', 'viewer')
        
        # Create user
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        
        # Create user profile
        UserProfile.objects.create(
            user=user,
            organization=organization,
            role=role
        )
        
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_name', 'organization', 'organization_name',
            'action', 'resource', 'resource_id', 'details',
            'ip_address', 'user_agent', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class UserOrganizationMembershipSerializer(serializers.ModelSerializer):
    """Serializer for organization memberships."""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    organization_slug = serializers.CharField(source='organization.slug', read_only=True)
    organization_is_demo = serializers.BooleanField(source='organization.is_demo', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = UserOrganizationMembership
        fields = [
            'id', 'user', 'user_username', 'user_email',
            'organization', 'organization_name', 'organization_slug', 'organization_is_demo',
            'role', 'is_primary', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'organization_is_demo', 'created_at']


class UserProfileWithOrgsSerializer(serializers.ModelSerializer):
    """Extended UserProfile serializer that includes all organization memberships."""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    organization_is_demo = serializers.BooleanField(source='organization.is_demo', read_only=True)
    is_super_admin = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'id', 'organization', 'organization_name', 'organization_is_demo', 'role',
            'phone', 'department', 'preferences', 'is_active',
            'created_at', 'is_super_admin', 'organizations'
        ]
        read_only_fields = ['id', 'organization_is_demo', 'created_at', 'is_super_admin', 'organizations']

    def get_is_super_admin(self, obj):
        """Return whether the user is a super admin (Django superuser)."""
        return obj.is_super_admin()

    def get_organizations(self, obj):
        """Return all active organization memberships for this user."""
        memberships = UserOrganizationMembership.objects.filter(
            user=obj.user,
            is_active=True
        ).select_related('organization')
        return UserOrganizationMembershipSerializer(memberships, many=True).data


class AddUserToOrgSerializer(serializers.Serializer):
    """Serializer for adding a user to an organization."""
    user_id = serializers.IntegerField()
    organization_id = serializers.IntegerField()
    role = serializers.ChoiceField(
        choices=['admin', 'manager', 'viewer'],
        default='viewer'
    )
    is_primary = serializers.BooleanField(default=False)

    def validate_user_id(self, value):
        from django.contrib.auth.models import User
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User not found")
        return value

    def validate_organization_id(self, value):
        if not Organization.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Organization not found or inactive")
        return value

    def validate(self, attrs):
        # Check if membership already exists
        if UserOrganizationMembership.objects.filter(
            user_id=attrs['user_id'],
            organization_id=attrs['organization_id']
        ).exists():
            raise serializers.ValidationError(
                "User already has a membership in this organization"
            )
        return attrs


class UpdateMembershipSerializer(serializers.Serializer):
    """Serializer for updating a membership."""
    role = serializers.ChoiceField(
        choices=['admin', 'manager', 'viewer'],
        required=False
    )
    is_primary = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


class SavingsConfigSerializer(serializers.Serializer):
    """
    Serializer for organization savings configuration.

    Validates savings rate configuration based on industry benchmarks
    (FY2025 Procurement Savings Initiative).
    """
    benchmark_profile = serializers.ChoiceField(
        choices=['conservative', 'moderate', 'aggressive', 'custom'],
        required=False
    )
    consolidation_rate = serializers.FloatField(
        min_value=0.005,
        max_value=0.15,
        required=False,
        help_text='Vendor consolidation rate (0.5-15%)'
    )
    anomaly_recovery_rate = serializers.FloatField(
        min_value=0.001,
        max_value=0.05,
        required=False,
        help_text='Anomaly/invoice error recovery rate (0.1-5%)'
    )
    price_variance_capture = serializers.FloatField(
        min_value=0.10,
        max_value=0.90,
        required=False,
        help_text='Price variance negotiation capture rate (10-90%)'
    )
    specification_rate = serializers.FloatField(
        min_value=0.005,
        max_value=0.10,
        required=False,
        help_text='Specification standardization rate (0.5-10%)'
    )
    payment_terms_rate = serializers.FloatField(
        min_value=0.001,
        max_value=0.03,
        required=False,
        help_text='Payment terms optimization rate (0.1-3%)'
    )
    process_savings_per_txn = serializers.FloatField(
        min_value=10,
        max_value=100,
        required=False,
        help_text='Process automation savings per transaction ($10-100)'
    )
    enabled_insights = serializers.ListField(
        child=serializers.ChoiceField(
            choices=['consolidation', 'anomaly', 'cost_optimization', 'risk']
        ),
        required=False,
        help_text='List of enabled insight types'
    )

    def validate(self, attrs):
        """Filter to only allowed keys."""
        allowed_keys = Organization.ALLOWED_SAVINGS_CONFIG_KEYS
        return {k: v for k, v in attrs.items() if k in allowed_keys}
