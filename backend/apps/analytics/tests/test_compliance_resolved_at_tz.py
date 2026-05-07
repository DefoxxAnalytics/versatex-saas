"""Finding #5: compliance_services must use timezone.now(), not datetime.now().

PolicyViolation.resolved_at is a TZ-aware DateTimeField (USE_TZ=True). Storing
datetime.now() (naive) emits a RuntimeWarning and stores a value treated as if
in TIME_ZONE but with the server's local clock — causing off-by-N-hours errors
when the host clock differs from the project TZ.
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.analytics.compliance_services import ComplianceService
from apps.procurement.models import PolicyViolation, SpendingPolicy, Transaction


@pytest.mark.django_db
class TestComplianceResolvedAtIsTzAware:
    """resolve_violation must store a timezone-aware resolved_at."""

    def test_resolving_violation_stores_tz_aware_resolved_at(
        self, organization, supplier, category, admin_user
    ):
        tx = Transaction.objects.create(
            organization=organization,
            supplier=supplier,
            category=category,
            amount=Decimal("1500.00"),
            date=date.today(),
            description="Tx for tz-aware resolved_at test",
            uploaded_by=admin_user,
            upload_batch="tz-aware-test-batch",
        )
        policy = SpendingPolicy.objects.create(
            organization=organization,
            name="TZ Test Policy",
            description="Policy for tz-aware resolved_at test",
            rules={},
            is_active=True,
        )
        violation = PolicyViolation.objects.create(
            organization=organization,
            transaction=tx,
            policy=policy,
            violation_type="amount_exceeded",
            severity="medium",
            details={},
            is_resolved=False,
        )

        service = ComplianceService(organization)
        result = service.resolve_violation(
            violation.id,
            admin_user,
            "Resolved for tz-aware assertion",
        )

        assert result is not None

        violation.refresh_from_db()
        assert violation.resolved_at is not None
        assert (
            violation.resolved_at.tzinfo is not None
        ), f"resolved_at must be timezone-aware. Got naive: {violation.resolved_at!r}"
