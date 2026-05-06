"""
Drift-guard parity tests — Phase 5 Task 5.1 / Finding #3.

Both UserProfileSerializer and UserProfileWithOrgsSerializer expose the
``preferences`` JSONField. Per CLAUDE.md §5 (no-silent-fallback for sensitive
keys) and `UserProfile.MASKED_PREFERENCE_KEYS`, every outbound serialization
path MUST mask `aiApiKey` (and any other masked key).

UserProfileSerializer enforces this via `to_representation`. The parallel
`UserProfileWithOrgsSerializer` had no override (Finding #3) — making the
first endpoint to wire it up leak plaintext. This test pins masking parity
between the two so future refactors can't regress to plaintext silently.
"""
import pytest

from apps.authentication.models import UserProfile
from apps.authentication.serializers import (
    UserProfileSerializer,
    UserProfileWithOrgsSerializer,
)


FAKE_KEY = 'sk-ant-FAKE-0123456789abcdef'
EXPECTED_MASK = '****' + FAKE_KEY[-4:]


@pytest.mark.django_db
class TestSerializerMaskingParity:
    """UserProfile{,WithOrgs}Serializer must both mask aiApiKey on read."""

    def _profile_with_key(self, admin_user):
        admin_user.profile.preferences = {
            'aiApiKey': FAKE_KEY,
            'useExternalAI': True,
            'aiProvider': 'anthropic',
            'theme': 'dark',
        }
        admin_user.profile.save()
        admin_user.profile.refresh_from_db()
        return admin_user.profile

    def test_user_profile_serializer_masks_api_key(self, admin_user):
        profile = self._profile_with_key(admin_user)
        data = UserProfileSerializer(profile).data
        assert data['preferences']['aiApiKey'] == EXPECTED_MASK
        assert FAKE_KEY not in str(data)

    def test_user_profile_with_orgs_serializer_masks_api_key(self, admin_user):
        profile = self._profile_with_key(admin_user)
        data = UserProfileWithOrgsSerializer(profile).data
        assert data['preferences']['aiApiKey'] == EXPECTED_MASK, (
            "UserProfileWithOrgsSerializer leaks plaintext aiApiKey — "
            "must apply UserProfile.mask_preferences in to_representation "
            "(parity with UserProfileSerializer)."
        )
        assert FAKE_KEY not in str(data)

    def test_both_serializers_produce_same_masked_preferences(self, admin_user):
        """Drift-guard: any divergence between the two paths is a regression."""
        profile = self._profile_with_key(admin_user)
        base_prefs = UserProfileSerializer(profile).data['preferences']
        ext_prefs = UserProfileWithOrgsSerializer(profile).data['preferences']
        assert base_prefs == ext_prefs, (
            "Masked preferences must match across both serializer paths."
        )
        assert base_prefs['aiApiKey'] == EXPECTED_MASK
        assert ext_prefs['aiApiKey'] == EXPECTED_MASK

    def test_empty_key_renders_as_none_in_both(self, admin_user):
        admin_user.profile.preferences = {'aiApiKey': '', 'theme': 'dark'}
        admin_user.profile.save()
        admin_user.profile.refresh_from_db()

        base = UserProfileSerializer(admin_user.profile).data['preferences']
        ext = UserProfileWithOrgsSerializer(admin_user.profile).data['preferences']
        assert base.get('aiApiKey') is None
        assert ext.get('aiApiKey') is None

    def test_non_secret_keys_pass_through_unchanged_in_both(self, admin_user):
        admin_user.profile.preferences = {
            'theme': 'dark',
            'colorScheme': 'versatex',
            'aiApiKey': FAKE_KEY,
        }
        admin_user.profile.save()
        admin_user.profile.refresh_from_db()

        for serializer_cls in (UserProfileSerializer, UserProfileWithOrgsSerializer):
            prefs = serializer_cls(admin_user.profile).data['preferences']
            assert prefs['theme'] == 'dark'
            assert prefs['colorScheme'] == 'versatex'
            assert prefs['aiApiKey'] == EXPECTED_MASK
