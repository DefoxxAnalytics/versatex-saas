"""
URL patterns for authentication
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, LoginView, LogoutView, CookieTokenRefreshView,
    CurrentUserView, ChangePasswordView, UserPreferencesView,
    OrganizationViewSet, UserProfileViewSet, AuditLogViewSet,
    UserOrganizationMembershipViewSet, user_organizations, switch_organization,
    OrganizationSavingsConfigView, export_savings_config_pdf
)

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'profiles', UserProfileViewSet, basename='profile')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
router.register(r'memberships', UserOrganizationMembershipViewSet, basename='membership')

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),

    # User management
    path('user/', CurrentUserView.as_view(), name='current-user'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('preferences/', UserPreferencesView.as_view(), name='user-preferences'),

    # Multi-organization support
    path('user/organizations/', user_organizations, name='user-organizations'),
    path('user/organizations/<int:org_id>/switch/', switch_organization, name='switch-organization'),

    # Organization settings
    path('organizations/<int:org_id>/savings-config/', OrganizationSavingsConfigView.as_view(), name='savings-config'),
    path('organizations/<int:org_id>/savings-config/export/', export_savings_config_pdf, name='savings-config-export'),

    # Router URLs
    path('', include(router.urls)),
]
