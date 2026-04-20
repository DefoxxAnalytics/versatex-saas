# How to Assign a User to an Organization

This guide explains how to assign users to organizations in Versatex Analytics using the Django Admin panel.

## Overview

In Versatex Analytics, user-organization relationships are managed through the **UserProfile** model. Each UserProfile links a Django User to exactly one Organization with a specific role.

## Prerequisites

- Access to Django Admin (`http://localhost:8001/admin`)
- Superuser account OR admin role within your organization
- The target user must already exist as a Django User

## Step-by-Step Guide

### Method 1: Via Django Admin UI

1. **Access Django Admin**
   - Navigate to `http://localhost:8001/admin`
   - Log in with your admin credentials

2. **Navigate to User Profiles**
   - Under the **AUTHENTICATION** section, click **User Profiles**

3. **Add a New User Profile**
   - Click the **Add User Profile** button in the top right

4. **Fill in the Form**
   | Field | Description |
   |-------|-------------|
   | **User** | Select an existing Django User from the dropdown |
   | **Organization** | Select the target organization |
   | **Role** | Choose: `admin`, `manager`, or `viewer` |
   | **Phone** | (Optional) User's phone number |
   | **Department** | (Optional) User's department |
   | **Preferences** | (Optional) JSON object for user preferences |
   | **Is active** | Check to enable the profile |

5. **Save**
   - Click **Save** to create the UserProfile

### Method 2: Via Django Shell

For bulk operations or scripting, use the Django shell:

```bash
# Access the Django shell
docker-compose exec backend python manage.py shell
```

```python
from apps.authentication.models import Organization, UserProfile
from django.contrib.auth.models import User

# Get the organization
org = Organization.objects.get(slug='your-org-slug')

# Get the user
user = User.objects.get(username='username')

# Create the UserProfile
UserProfile.objects.create(
    user=user,
    organization=org,
    role='admin',  # Options: 'admin', 'manager', 'viewer'
    is_active=True
)
```

### Method 3: Create User and Profile Together

To create a new user with an organization assignment in one session:

```bash
docker-compose exec backend python manage.py shell
```

```python
from apps.authentication.models import Organization, UserProfile
from django.contrib.auth.models import User

# Get the organization
org = Organization.objects.get(slug='your-org-slug')

# Create the user
user = User.objects.create_user(
    username='newuser',
    email='newuser@example.com',
    password='securepassword123'
)

# Create the profile
UserProfile.objects.create(
    user=user,
    organization=org,
    role='manager',
    is_active=True
)

print(f"Created user '{user.username}' with {org.name} organization")
```

## Access Control by Role

| Your Role | What You Can Manage |
|-----------|---------------------|
| **Superuser** | All UserProfiles across all organizations |
| **Org Admin** | Only UserProfiles within your organization |
| **Manager** | No access to UserProfile management |
| **Viewer** | No access to UserProfile management |

## Role Capabilities

| Capability | Admin | Manager | Viewer |
|------------|-------|---------|--------|
| View dashboards | Yes | Yes | Yes |
| Upload data | Yes | Yes | No |
| Delete data | Yes | No | No |
| Manage users | Yes | No | No |
| Access Django Admin | Yes | No | No |

## Common Issues

### User Cannot Log In After Assignment

**Symptoms:** User created but cannot access the application.

**Checklist:**
1. Verify the UserProfile exists: `UserProfile.objects.filter(user__username='username').exists()`
2. Ensure `is_active=True` on the UserProfile
3. Ensure `is_active=True` on the Django User
4. Verify the Organization `is_active=True`

### "User has no profile" Error

**Cause:** A Django User was created without a corresponding UserProfile.

**Solution:** Create the UserProfile via admin or shell as shown above.

### Cannot See Other Users in Admin

**Cause:** You are not a superuser, so you only see users in your organization.

**Solution:** This is expected behavior for multi-tenancy. Contact a superuser if you need to manage users in other organizations.

## Updating an Existing Assignment

### Change Organization

To move a user to a different organization:

```python
from apps.authentication.models import UserProfile, Organization

profile = UserProfile.objects.get(user__username='username')
new_org = Organization.objects.get(slug='new-org-slug')
profile.organization = new_org
profile.save()
```

> **Warning:** Changing a user's organization will affect their access to all organization-scoped data.

### Change Role

```python
profile = UserProfile.objects.get(user__username='username')
profile.role = 'admin'  # or 'manager', 'viewer'
profile.save()
```

## API Alternative

User profiles can also be managed via the REST API:

```bash
# List profiles (requires admin role)
curl -X GET http://localhost:8001/api/v1/authentication/user-profiles/ \
  -H "Authorization: Bearer <token>"

# Create profile
curl -X POST http://localhost:8001/api/v1/authentication/user-profiles/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user": 1,
    "organization": 1,
    "role": "manager",
    "is_active": true
  }'
```

## Related Documentation

- [CLAUDE.md](../../CLAUDE.md) - Project overview and architecture
- [Django Admin Setup](../setup/) - Initial admin configuration
- [Authentication API](../../backend/apps/authentication/) - API reference
