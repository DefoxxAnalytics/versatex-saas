# Versatex Analytics Security Audit Report

**Audit Date:** January 8, 2026
**Auditor:** Security Review Team
**Version:** 1.0
**Classification:** Internal - Confidential

---

## Executive Summary

A comprehensive security audit was conducted across all layers of the Versatex Analytics platform, including backend authentication, API endpoints, database models, frontend application, and deployment configuration.

### Overall Risk Assessment

| Risk Level | Assessment |
|------------|------------|
| **Overall** | MEDIUM-HIGH |
| **Immediate Action Required** | YES |

### Findings Summary

| Severity | Count | Immediate Action Required |
|----------|-------|---------------------------|
| **CRITICAL** | 8 | YES - This Week |
| **HIGH** | 15 | YES - Next Sprint |
| **MEDIUM** | 20 | Recommended |
| **LOW** | 15 | Optional Enhancement |
| **Total** | **58** | |

### Risk by Area

| Area | Risk Level | Critical Issues |
|------|------------|-----------------|
| Configuration & Secrets | CRITICAL | Exposed secrets in .env, weak defaults |
| Backend Authentication | HIGH | Token refresh rate limiting, race conditions |
| Backend API | HIGH | IDOR in drilldown endpoints, bulk operations |
| Database Models | HIGH | Multi-tenancy gaps in Report.can_access() |
| Frontend | MEDIUM | localStorage data exposure |
| Django Admin | MEDIUM | FK filtering, bulk action validation |

---

## Audit Scope

### Systems Reviewed

1. **Backend Authentication** (`backend/apps/authentication/`)
   - JWT token handling and refresh
   - Login/logout/password change views
   - Rate limiting implementation
   - Session management
   - Password policies

2. **Backend API Endpoints** (`backend/apps/`)
   - Procurement views
   - Analytics views and P2P views
   - Reports views
   - Permission classes and decorators
   - Input validation

3. **Database Models** (`backend/apps/*/models.py`)
   - Multi-tenancy implementation
   - Sensitive data storage
   - Model validators
   - Cascade behaviors

4. **Frontend Application** (`frontend/src/`)
   - Authentication state management
   - Token handling
   - XSS vulnerabilities
   - localStorage usage
   - Input validation

5. **Configuration & Deployment**
   - Django settings
   - Docker configuration
   - Environment variables
   - Secret management

---

## Critical Findings

### CRITICAL-001: Exposed Secrets in Version Control

**File:** `.env`
**Severity:** CRITICAL
**CVSS Score:** 9.8

**Description:**
The `.env` file contains exposed secrets including:
- Django SECRET_KEY in plaintext
- Database credentials (username/password)
- Redis connection strings

**Evidence:**
```
SECRET_KEY=sz-o%4aie#o!*(bvjxt&^#&fq89d!39j^_bcuw1lxbi%ain1(z)
DB_USER=analytics_user
DB_PASSWORD=analytics_pass
```

**Impact:**
- Complete application compromise
- Database access by unauthorized parties
- Session hijacking via SECRET_KEY

**Remediation:**
1. Rotate ALL secrets immediately
2. Remove .env from git history:
   ```bash
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch .env' \
     --prune-empty --tag-name-filter cat -- --all
   git push origin --force --all
   ```
3. Generate new secrets:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
4. Verify `.gitignore` includes `.env`

---

### CRITICAL-002: API Documentation Exposed in Production

**File:** `backend/config/urls.py`
**Lines:** 34-37
**Severity:** CRITICAL
**CVSS Score:** 7.5

**Description:**
Swagger and ReDoc API documentation endpoints are unconditionally exposed, regardless of DEBUG setting.

**Vulnerable Code:**
```python
# API Documentation (only in development) - COMMENT LIES!
path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
```

**Impact:**
- Full API endpoint enumeration
- Parameter and data structure discovery
- Attack surface mapping

**Remediation:**
```python
from django.conf import settings

# Only include API docs in DEBUG mode
if settings.DEBUG:
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]
```

---

### CRITICAL-003: Race Condition in Primary Membership

**File:** `backend/apps/authentication/models.py`
**Lines:** 239-247
**Severity:** CRITICAL
**CVSS Score:** 8.1

**Description:**
The `UserOrganizationMembership.save()` method performs a non-atomic update when setting primary membership, allowing race conditions.

**Vulnerable Code:**
```python
def save(self, *args, **kwargs):
    if self.is_primary:
        # Non-atomic - race condition vulnerability
        UserOrganizationMembership.objects.filter(
            user=self.user,
            is_primary=True
        ).exclude(pk=self.pk).update(is_primary=False)
    super().save(*args, **kwargs)
```

**Impact:**
- Users could have multiple primary memberships simultaneously
- Authorization bypass
- Data integrity issues

**Remediation:**
```python
from django.db import transaction

def save(self, *args, **kwargs):
    if self.is_primary:
        with transaction.atomic():
            UserOrganizationMembership.objects.filter(
                user=self.user,
                is_primary=True
            ).exclude(pk=self.pk).select_for_update().update(is_primary=False)
            super().save(*args, **kwargs)
    else:
        super().save(*args, **kwargs)
```

---

### CRITICAL-004: No Rate Limiting on Token Refresh

**File:** `backend/apps/authentication/views.py`
**Lines:** 447-479
**Severity:** CRITICAL
**CVSS Score:** 7.5

**Description:**
The `CookieTokenRefreshView` lacks rate limiting, unlike the login endpoint which has a 5/minute limit.

**Impact:**
- Token brute-force attacks
- Denial of service via token refresh flooding
- Potential token discovery

**Remediation:**
```python
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

@method_decorator(ratelimit(key='ip', rate='30/m', method='POST', block=True), name='dispatch')
class CookieTokenRefreshView(generics.GenericAPIView):
    # ... existing code
```

---

### CRITICAL-005: IDOR in Drilldown Endpoints

**File:** `backend/apps/analytics/views.py`
**Lines:** 196-611
**Severity:** CRITICAL
**CVSS Score:** 8.6

**Description:**
Multiple drilldown endpoints accept resource IDs without validating they belong to the user's organization.

**Affected Endpoints:**
- `supplier_drilldown(request, supplier_id)` - Line 216
- `seasonality_category_drilldown(request, category_id)` - Line 465
- `yoy_category_drilldown(request, category_id)` - Line 565
- `yoy_supplier_drilldown(request, supplier_id)` - Line 606
- `tail_spend_category_drilldown(request, category_id)` - Line 692
- `tail_spend_vendor_drilldown(request, supplier_id)` - Line 719

**Vulnerable Code:**
```python
def supplier_drilldown(request, supplier_id):
    organization = get_target_organization(request)
    # NO VALIDATION that supplier_id belongs to organization!
    data = service.get_supplier_drilldown(supplier_id)
```

**Impact:**
- Cross-organization data access
- Information disclosure
- Privacy violations

**Remediation:**
```python
from apps.procurement.models import Supplier

def supplier_drilldown(request, supplier_id):
    organization = get_target_organization(request)

    # Validate supplier belongs to organization
    try:
        supplier = Supplier.objects.get(id=supplier_id, organization=organization)
    except Supplier.DoesNotExist:
        return Response(
            {'error': 'Supplier not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    service = AnalyticsService(organization)
    data = service.get_supplier_drilldown(supplier_id)
    return Response(data)
```

---

### CRITICAL-006: Bulk Operation IDOR in P2P

**File:** `backend/apps/analytics/p2p_views.py`
**Lines:** 753-817
**Severity:** CRITICAL
**CVSS Score:** 8.6

**Description:**
The `bulk_resolve_exceptions` endpoint validates that `invoice_ids` are integers but does NOT verify that all invoices belong to the user's organization.

**Vulnerable Code:**
```python
def bulk_resolve_exceptions(request):
    invoice_ids = request.data.get('invoice_ids', [])

    # Only validates they are integers
    try:
        invoice_ids = [int(id) for id in invoice_ids]
    except (ValueError, TypeError):
        return Response({'error': 'All invoice_ids must be integers'}, status=400)

    # NO validation that invoices belong to organization!
    service.bulk_resolve_exceptions(
        invoice_ids=invoice_ids,
        user=request.user,
        resolution_notes=resolution_notes.strip()
    )
```

**Impact:**
- Modify invoices in other organizations
- Data integrity compromise
- Audit trail manipulation

**Remediation:**
```python
from apps.procurement.models import Invoice

def bulk_resolve_exceptions(request):
    organization = get_target_organization(request)
    invoice_ids = request.data.get('invoice_ids', [])

    # Validate invoices exist and belong to organization
    invoices = Invoice.objects.filter(
        id__in=invoice_ids,
        organization=organization
    )

    if invoices.count() != len(invoice_ids):
        return Response(
            {'error': 'Some invoices not found or access denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Proceed with validated IDs only
    validated_ids = list(invoices.values_list('id', flat=True))
    service.bulk_resolve_exceptions(
        invoice_ids=validated_ids,
        user=request.user,
        resolution_notes=resolution_notes.strip()
    )
```

---

### CRITICAL-007: Incomplete Multi-Tenancy in Report.can_access()

**File:** `backend/apps/reports/models.py`
**Line:** 201
**Severity:** CRITICAL
**CVSS Score:** 8.1

**Description:**
The `Report.can_access()` method uses the legacy single-org model (`user.profile.organization`) instead of the new multi-org membership model.

**Vulnerable Code:**
```python
def can_access(self, user):
    if user.is_superuser:
        return True
    # Uses legacy model - doesn't check UserOrganizationMembership
    if hasattr(user, 'profile') and user.profile.organization == self.organization:
        return True
    return False
```

**Impact:**
- Multi-org users may be denied legitimate access
- Users switching organizations might access unauthorized reports

**Remediation:**
```python
from apps.authentication.organization_utils import user_can_access_org

def can_access(self, user):
    if user.is_superuser:
        return True

    # Use new membership model
    if user_can_access_org(user, self.organization):
        return True

    # Check if shared with user
    if user in self.shared_with.all():
        return True

    return False
```

---

### CRITICAL-008: Organization CASCADE Delete

**File:** `backend/apps/authentication/models.py`
**Lines:** 88-91, 200-202
**Severity:** CRITICAL
**CVSS Score:** 7.5

**Description:**
The `organization` ForeignKey uses `on_delete=models.CASCADE`, causing all user profiles and memberships to be instantly deleted when an organization is deleted.

**Vulnerable Code:**
```python
class UserProfile(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,  # DANGEROUS!
        related_name='user_profiles'
    )

class UserOrganizationMembership(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,  # DANGEROUS!
        related_name='memberships'
    )
```

**Impact:**
- Accidental mass user deletion
- Loss of audit trail
- GDPR/compliance violations
- No recovery without backups

**Remediation:**
```python
class UserProfile(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,  # Prevent accidental deletion
        related_name='user_profiles'
    )

class UserOrganizationMembership(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,  # Prevent accidental deletion
        related_name='memberships'
    )
```

Or implement soft delete:
```python
class Organization(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
```

---

## High Severity Findings

### HIGH-001: Attempt Count Disclosure in Login Error

**File:** `backend/apps/authentication/views.py`
**Lines:** 172-184
**Severity:** HIGH

**Description:**
Login error messages reveal the number of remaining attempts before lockout.

**Vulnerable Code:**
```python
is_locked, remaining = record_failed_login(request, username)
error_msg = 'Invalid credentials'
if remaining > 0:
    error_msg += f' ({remaining} attempts remaining)'  # Information leak!
```

**Impact:** Account enumeration, lockout mechanism discovery

**Remediation:** Return generic error messages only.

---

### HIGH-002: Weak Password Requirements

**File:** `backend/config/settings.py`
**Lines:** 116-121
**Severity:** HIGH

**Description:**
Password validators only enforce minimum length (10 chars) without requiring special characters, uppercase, or digits.

**Remediation:** Add custom validator requiring complexity.

---

### HIGH-003: Silent Token Validation Errors

**File:** `backend/apps/authentication/views.py`
**Lines:** 255-261
**Severity:** HIGH

**Description:**
Token errors during logout are silently caught without logging.

**Remediation:** Log suspicious token errors for security monitoring.

---

### HIGH-004: X-Forwarded-For Spoofing

**File:** `backend/apps/authentication/utils.py`
**Lines:** 16-37
**Severity:** HIGH

**Description:**
`get_client_ip()` trusts X-Forwarded-For header without validation.

**Remediation:** Configure trusted proxy validation.

---

### HIGH-005: Password Change Doesn't Invalidate Tokens

**File:** `backend/apps/authentication/views.py`
**Lines:** 326-351
**Severity:** HIGH

**Description:**
When password is changed, existing refresh tokens remain valid for 24 hours.

**Remediation:** Blacklist all existing tokens on password change.

---

### HIGH-006 to HIGH-010: Backend API Issues

| # | Finding | File | Lines |
|---|---------|------|-------|
| 6 | Contract access control missing | analytics/views.py | 1074-1248 |
| 7 | CSV DoS via memory (50MB file) | procurement/services.py | 56-58 |
| 8 | Error info exposure in responses | reports/views.py | 280-285 |
| 9 | Weak year parameter validation | analytics/views.py | 510-524 |
| 10 | Enum parameters silently ignored | analytics/views.py | 1317-1351 |

---

### HIGH-011 to HIGH-015: Configuration Issues

| # | Finding | File | Lines |
|---|---------|------|-------|
| 11 | Weak Docker defaults (redis password) | docker-compose.yml | 24 |
| 12 | Hardcoded admin URL (predictable) | .env | 5 |
| 13 | Missing HTTPS configuration | docker-compose.yml | 110-121 |
| 14 | Frontend Docker runs as root | frontend/Dockerfile | 32-74 |
| 15 | Insecure media file serving | config/urls.py | 40-42 |

---

## Medium Severity Findings

### Django Admin (6 issues)

| # | Finding | Impact |
|---|---------|--------|
| 1 | Missing FK filtering in P2P admin forms | Cross-org resource selection |
| 2 | Missing M2M filtering in Report admin | Share with any user |
| 3 | Bulk actions missing org validation | Modify other org data |
| 4 | list_editable bypasses permission flow | Unauthorized inline edits |
| 5 | CSV upload org selection not validated | Import to wrong org |
| 6 | Upload detail view timing leak | Timing attacks |

### Database Models (5 issues)

| # | Finding | Impact |
|---|---------|--------|
| 1 | PII stored without encryption | GDPR violation |
| 2 | Logo path exposure in get_branding() | Server path leak |
| 3 | JSONField preferences no validation | JSON injection |
| 4 | AuditLog user_agent unbounded | Database bloat |
| 5 | Invoice notes unbounded | Performance DoS |

### Frontend (5 issues)

| # | Finding | Impact |
|---|---------|--------|
| 1 | Sensitive user data in localStorage | XSS data access |
| 2 | Admin URL hardcoded with window.location | Open redirect |
| 3 | Organization ID from untrusted localStorage | Privilege escalation |
| 4 | Password field not cleared on login failure | Credential exposure |
| 5 | Missing integer validation on parseInt() | Logic errors |

### API (4 issues)

| # | Finding | Impact |
|---|---------|--------|
| 1 | Missing throttle configuration verification | Rate limit bypass |
| 2 | Organization name collision risk | Data conflicts |
| 3 | Bulk operation limits too high (100) | DoS potential |
| 4 | Circular imports in p2p_views | Maintenance issues |

---

## Positive Security Findings

The following security controls are well-implemented:

| Control | Implementation | Status |
|---------|---------------|--------|
| Password Hashing | Argon2 with fallbacks | Excellent |
| JWT Tokens | HTTP-only cookies, SameSite=Lax | Excellent |
| CORS | Explicit origin whitelist | Good |
| CSRF | Enabled with secure cookies | Good |
| Rate Limiting | Comprehensive throttle scopes | Good |
| Non-Root Docker | Backend runs as appuser | Good |
| Multi-Tenancy | Organization-scoped querysets | Good |
| Audit Logging | Comprehensive action tracking | Excellent |
| UUID References | External IDs use UUIDs | Good |
| Session Management | 30-min timeout with warnings | Good |

---

## Remediation Priority

### Immediate (This Week)

| Priority | Action | Owner |
|----------|--------|-------|
| 1 | Rotate all exposed secrets | DevOps |
| 2 | Remove .env from git history | DevOps |
| 3 | Add rate limiting to token refresh | Backend |
| 4 | Fix IDOR in drilldown endpoints | Backend |
| 5 | Wrap API docs in DEBUG check | Backend |
| 6 | Fix Report.can_access() multi-tenancy | Backend |

### High Priority (Next Sprint)

| Priority | Action | Owner |
|----------|--------|-------|
| 7 | Change CASCADE to PROTECT on org FK | Backend |
| 8 | Add transactions to primary membership save | Backend |
| 9 | Fix contract/resource access control | Backend |
| 10 | Implement streaming CSV reader | Backend |
| 11 | Sanitize all error responses | Backend |
| 12 | Add HTTPS configuration | DevOps |
| 13 | Fix frontend Docker to non-root | DevOps |

### Medium Priority (Following Sprint)

| Priority | Action | Owner |
|----------|--------|-------|
| 14 | Add FK/M2M filtering to all admins | Backend |
| 15 | Validate bulk action permissions | Backend |
| 16 | Encrypt PII fields | Backend |
| 17 | Move user data from localStorage | Frontend |
| 18 | Add CSP headers | DevOps |
| 19 | Improve logging (no sensitive data) | Backend |
| 20 | Add security test coverage | QA |

---

## Verification Checklist

After implementing fixes, verify:

- [ ] All secrets rotated and .env removed from git
- [ ] Token refresh returns 429 after 30 requests/minute
- [ ] Drilldown endpoints return 403 for wrong-org resources
- [ ] Bulk operations validate all IDs belong to org
- [ ] API docs return 404 when DEBUG=False
- [ ] Report.can_access() works for multi-org users
- [ ] Organization delete blocked by PROTECT
- [ ] Primary membership update is atomic
- [ ] Error responses contain no stack traces
- [ ] Frontend admin links use config, not window.location
- [ ] Django system check passes
- [ ] Security test suite passes

---

## Files Requiring Changes

| File | Priority | Changes |
|------|----------|---------|
| `.env` | CRITICAL | Rotate all secrets |
| `backend/config/urls.py` | CRITICAL | Wrap API docs in DEBUG |
| `backend/apps/authentication/models.py` | CRITICAL | Add transaction to save(), change CASCADE |
| `backend/apps/authentication/views.py` | CRITICAL | Add rate limiting to token refresh |
| `backend/apps/analytics/views.py` | CRITICAL | Add org validation to drilldowns |
| `backend/apps/analytics/p2p_views.py` | CRITICAL | Validate bulk operation IDs |
| `backend/apps/reports/models.py` | CRITICAL | Fix can_access() multi-tenancy |
| `backend/apps/procurement/admin.py` | HIGH | Add FK filtering to P2P admins |
| `backend/apps/reports/admin.py` | MEDIUM | Add M2M filtering |
| `frontend/src/lib/auth.ts` | MEDIUM | Remove user data from localStorage |
| `frontend/Dockerfile` | HIGH | Add non-root user |
| `docker-compose.yml` | HIGH | Fix weak defaults |

---

## Appendix A: Testing Procedures

### IDOR Testing

```bash
# Test supplier drilldown with wrong-org ID
curl -X GET "http://localhost:8001/api/v1/analytics/pareto/supplier/999/" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 403 or 404, NOT data from another org
```

### Rate Limit Testing

```bash
# Test token refresh rate limiting
for i in {1..35}; do
  curl -X POST "http://localhost:8001/api/v1/auth/token/refresh/" \
    -H "Cookie: refresh_token=$REFRESH"
done
# Expected: 429 after 30 requests
```

### Multi-Tenancy Testing

```python
# Test Report.can_access() with multi-org user
user = User.objects.get(username='multiorg_user')
report = Report.objects.get(organization_id=2)  # Different from primary
assert report.can_access(user) == True  # Should pass if user has membership
```

---

## Appendix B: Security Headers Checklist

Recommended security headers for production:

```nginx
# Nginx configuration
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-08 | Security Team | Initial audit |

---

**Audit Completed:** January 8, 2026
**Next Review:** Recommended after remediation (2 weeks)
**Distribution:** Internal Only - Do Not Share Externally
