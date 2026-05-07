"""Critical S-#4 permanent fix: JSONField read-merge-write must be atomic.

Bug background: UserPreferencesView.patch and OrganizationSavingsConfigView.patch
read profile.preferences / org.savings_config, merged user input in Python, and
saved the entire JSON blob via update_fields. Two concurrent writers (two browser
tabs editing different keys, two admins editing config) silently lost one update
- the second writer's blob overwrote the first.

Permanent fix: wrap each read-merge-write in transaction.atomic() with
select_for_update() on the row, so the second writer blocks on the row lock
until the first writer commits, then re-reads the merged state.

These drift-guard tests assert that the view exercises both primitives
(transaction.atomic + select_for_update). A future contributor reverting the
atomic wrapper will see these fail. The pattern mirrors v2.12's
test_switch_org_atomicity.py.

See docs/codebase-review-2026-05-06-second-pass.md Critical #4.
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import Organization, UserProfile

User = get_user_model()


@pytest.fixture
def auth_client(admin_user):
    """APIClient authenticated via cookie path (DEBUG-only header fallback)."""
    client = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    client.cookies['access_token'] = str(refresh.access_token)
    return client


@pytest.mark.django_db
class TestUserPreferencesAtomicity:
    """UserPreferencesView.patch must use transaction.atomic + select_for_update."""

    def test_patch_uses_select_for_update_in_atomic_block(
        self, admin_user, auth_client
    ):
        """Drift-guard: the view must wrap read-merge-write in atomic+sfu.

        Without these primitives, two concurrent PATCH requests editing
        different preference keys silently lose one update - the second
        writer's full blob overwrites the first. This test makes a future
        revert of the atomic wrapper a hard test failure.
        """
        original_sfu = UserProfile.objects.select_for_update
        sfu_calls = {"n": 0}

        def counting_sfu(*args, **kwargs):
            sfu_calls["n"] += 1
            return original_sfu(*args, **kwargs)

        original_atomic = transaction.atomic
        atomic_calls = {"n": 0}

        def counting_atomic(*args, **kwargs):
            atomic_calls["n"] += 1
            return original_atomic(*args, **kwargs)

        with patch.object(
            UserProfile.objects, 'select_for_update', side_effect=counting_sfu
        ), patch(
            'apps.authentication.views.transaction.atomic',
            side_effect=counting_atomic,
        ):
            response = auth_client.patch(
                '/api/v1/auth/preferences/',
                {'theme': 'dark', 'colorScheme': 'navy'},
                format='json',
            )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert atomic_calls["n"] >= 1, (
            "UserPreferencesView.patch must wrap the read-merge-write in "
            "transaction.atomic() to prevent lost updates under concurrent writes."
        )
        assert sfu_calls["n"] >= 1, (
            "UserPreferencesView.patch must use select_for_update() to lock "
            "the profile row during the read-merge-write."
        )

    def test_patch_merge_still_correct(self, admin_user, auth_client):
        """Regression guard: atomic wrap must not break the merge semantics.

        Pre-existing keys must survive a partial-update PATCH.
        """
        # Seed.
        response = auth_client.patch(
            '/api/v1/auth/preferences/', {'theme': 'dark'}, format='json',
        )
        assert response.status_code == status.HTTP_200_OK, response.data

        # Partial update: add a new key.
        response = auth_client.patch(
            '/api/v1/auth/preferences/', {'colorScheme': 'navy'}, format='json',
        )
        assert response.status_code == status.HTTP_200_OK, response.data

        admin_user.profile.refresh_from_db()
        prefs = admin_user.profile.preferences or {}
        assert prefs.get('theme') == 'dark', (
            f"Pre-existing key dropped on merge: {prefs!r}"
        )
        assert prefs.get('colorScheme') == 'navy', (
            f"New key not persisted on merge: {prefs!r}"
        )


@pytest.mark.django_db
class TestSavingsConfigAtomicity:
    """OrganizationSavingsConfigView.patch must use atomic + select_for_update."""

    def test_patch_uses_select_for_update_in_atomic_block(
        self, organization, admin_user, admin_client
    ):
        """Drift-guard: the view must wrap read-merge-write in atomic+sfu.

        Two admins editing the same org's savings_config simultaneously will
        lose one update without row-level locking.
        """
        original_sfu = Organization.objects.select_for_update
        sfu_calls = {"n": 0}

        def counting_sfu(*args, **kwargs):
            sfu_calls["n"] += 1
            return original_sfu(*args, **kwargs)

        original_atomic = transaction.atomic
        atomic_calls = {"n": 0}

        def counting_atomic(*args, **kwargs):
            atomic_calls["n"] += 1
            return original_atomic(*args, **kwargs)

        url = f'/api/v1/auth/organizations/{organization.id}/savings-config/'
        with patch.object(
            Organization.objects, 'select_for_update', side_effect=counting_sfu
        ), patch(
            'apps.authentication.views.transaction.atomic',
            side_effect=counting_atomic,
        ):
            response = admin_client.patch(
                url, {'consolidation_rate': 0.04}, format='json',
            )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert atomic_calls["n"] >= 1, (
            "OrganizationSavingsConfigView.patch must wrap the read-merge-write "
            "in transaction.atomic() to prevent lost updates under concurrent writes."
        )
        assert sfu_calls["n"] >= 1, (
            "OrganizationSavingsConfigView.patch must use select_for_update() "
            "to lock the org row during the read-merge-write."
        )

    def test_patch_merge_still_correct(
        self, organization, admin_user, admin_client
    ):
        """Regression guard: atomic wrap must not break the merge semantics."""
        url = f'/api/v1/auth/organizations/{organization.id}/savings-config/'
        # Seed.
        response = admin_client.patch(
            url, {'consolidation_rate': 0.04}, format='json',
        )
        assert response.status_code == status.HTTP_200_OK, response.data

        # Partial update: add a second key.
        response = admin_client.patch(
            url, {'anomaly_recovery_rate': 0.01}, format='json',
        )
        assert response.status_code == status.HTTP_200_OK, response.data

        organization.refresh_from_db()
        config = organization.savings_config or {}
        assert config.get('consolidation_rate') == 0.04, (
            f"Merge dropped pre-existing key: {config!r}"
        )
        assert config.get('anomaly_recovery_rate') == 0.01, (
            f"Merge failed to add new key: {config!r}"
        )
