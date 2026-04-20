"""
Procurement signals for cache invalidation and data synchronization.

Invalidates AI insights cache when procurement data changes.
"""

import logging

from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver

from .models import Transaction, DataUpload

logger = logging.getLogger(__name__)


def _invalidate_ai_cache(organization_id: int, reason: str) -> None:
    """
    Invalidate AI insights cache for an organization.

    Imports AIInsightsCache lazily to avoid circular imports.
    """
    try:
        from apps.analytics.ai_cache import AIInsightsCache
        invalidated = AIInsightsCache.invalidate_org_cache(organization_id)
        logger.info(
            f"AI cache invalidated for org {organization_id}: "
            f"{invalidated} entries cleared ({reason})"
        )
    except ImportError:
        logger.warning("AIInsightsCache not available")
    except Exception as e:
        logger.error(f"Failed to invalidate AI cache: {e}")


@receiver(post_save, sender=DataUpload)
def invalidate_ai_cache_on_upload(sender, instance, created, **kwargs):
    """
    Invalidate AI insights cache when a data upload completes.

    Only triggers on completed uploads to avoid premature invalidation.
    """
    if instance.status == 'completed':
        _invalidate_ai_cache(
            instance.organization_id,
            f"DataUpload completed (id={instance.id})"
        )


@receiver(post_delete, sender=Transaction)
def invalidate_ai_cache_on_transaction_delete(sender, instance, **kwargs):
    """Invalidate AI insights cache when transactions are deleted."""
    _invalidate_ai_cache(
        instance.organization_id,
        f"Transaction deleted (id={instance.id})"
    )


@receiver(post_save, sender=Transaction)
def invalidate_ai_cache_on_transaction_save(sender, instance, created, **kwargs):
    """
    Invalidate AI insights cache when transactions are created or modified.

    Note: Bulk creates via upload are handled by DataUpload signal.
    This handles individual transaction edits.
    """
    if not created:
        _invalidate_ai_cache(
            instance.organization_id,
            f"Transaction updated (id={instance.id})"
        )
