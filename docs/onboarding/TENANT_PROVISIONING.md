# Tenant Provisioning Guide

## Overview
Versatex Analytics uses a **restricted onboarding model**. New organizations/tenants must be provisioned by a Superuser. This ensures strict control over who has access to the platform.

## Prerequisites
- You must have access to the backend container or server environment.
- You must be able to run `python manage.py` commands.

## Quick Provisioning (Recommended)
We provide a management command to handle the entire flow (Organization + User + Profile) in one step.

### Command
```bash
# If running via Docker Compose (Standard)
docker-compose exec backend python manage.py create_tenant --org "Client Name" --username "client_admin" --email "admin@client.com"

# If running locally (venv)
python manage.py create_tenant --org "Client Name" --username "client_admin" --email "admin@client.com"
```

### Options
| Argument | Description | Required |
|----------|-------------|----------|
| `--org` | The display name of the Organization (e.g. "Acme Corp") | Yes |
| `--username` | Username for the initial administrator | Yes |
| `--email` | Email address for the initial administrator | Yes |
| `--password` | Initial password. If omitted, a secure random one is generated. | No |

### Example Output
```text
Created Organization: Acme Corp (slug: acme-corp)
Created User: acme_admin
Linked acme_admin to Acme Corp as Admin

--- Tenant Provisioned Successfully ---
Organization: Acme Corp
URL:          (Login Page)
Username:     acme_admin
Password:     XyZ789!@#SafePass
---------------------------------------
```

## Manual Provisioning (Fallback)
If you prefer identifying everything manually via the Django Admin interface:

1.  Log in to Django Admin (`/admin/`) as a Superuser.
2.  Go to **Organizations** -> **Add Organization**.
    *   Name: "Acme Corp"
    *   Slug: "acme-corp"
    *   Save.
3.  Go to **Users** -> **Add User**.
    *   Create the user with username/password.
    *   Save.
4.  Go to **User Profiles** -> **Add User Profile**.
    *   User: Select the new user.
    *   Organization: Select "Acme Corp".
    *   Role: Select "Administrator".
    *   Save.
