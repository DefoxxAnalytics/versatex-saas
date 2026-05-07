"""
Procurement signals for cache invalidation and data synchronization.

Invalidates AI insights cache when procurement data changes.

All cache-invalidation side effects are deferred via ``transaction.on_commit``
so they only fire after the surrounding transaction successfully commits. This
prevents cold-cache + read-your-write inconsistency when the transaction rolls
back (FK violation, partial batch failure, etc.). When no transaction is active
(autocommit), Django's ``on_commit`` runs the callback immediately.
"""

import logging

from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .models import DataUpload, Transaction

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


def _schedule_invalidation(organization_id: int, reason: str) -> None:
    """
    Defer cache invalidation until the surrounding transaction commits.

    Outside a transaction, ``on_commit`` invokes the callback immediately, so
    autocommit code paths are unaffected. Inside a transaction that rolls back,
    the callback is discarded — the cache is never touched, preserving the
    pre-rollback state.
    """
    transaction.on_commit(lambda: _invalidate_ai_cache(organization_id, reason))


@receiver(post_save, sender=DataUpload)
def invalidate_ai_cache_on_upload(sender, instance, created, **kwargs):
    """
    Invalidate AI insights cache when a data upload completes.

    Only triggers on completed uploads to avoid premature invalidation.
    """
    if instance.status == "completed":
        _schedule_invalidation(
            instance.organization_id, f"DataUpload completed (id={instance.id})"
        )


@receiver(post_delete, sender=Transaction)
def invalidate_ai_cache_on_transaction_delete(sender, instance, **kwargs):
    """Invalidate AI insights cache when transactions are deleted."""
    _schedule_invalidation(
        instance.organization_id, f"Transaction deleted (id={instance.id})"
    )


@receiver(post_save, sender=Transaction)
def invalidate_ai_cache_on_transaction_save(sender, instance, created, **kwargs):
    """
    Invalidate AI insights cache when transactions are created or modified.

    Note: Bulk creates via upload are handled by DataUpload signal.
    This handles individual transaction edits.
    """
    if not created:
        _schedule_invalidation(
            instance.organization_id, f"Transaction updated (id={instance.id})"
        )
