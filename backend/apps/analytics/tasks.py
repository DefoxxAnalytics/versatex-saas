"""
Celery tasks for analytics module.

Contains background tasks for:
- Refreshing materialized views after data uploads
- Pre-computing analytics for large datasets
- Async AI enhancement processing
- Deep insight analysis
- Batch AI insight generation (overnight)
- Semantic cache maintenance
"""
import logging
import json
from datetime import timedelta
from celery import shared_task
from django.db import connection
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name='refresh_materialized_views',
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    track_started=True,
)
def refresh_materialized_views(self):
    """
    Refresh all analytics materialized views concurrently.

    This task should be triggered after data uploads complete.
    Uses CONCURRENTLY option to avoid locking the views during refresh.

    Returns:
        dict: Status and count of views refreshed
    """
    views = [
        'mv_monthly_category_spend',
        'mv_monthly_supplier_spend',
        'mv_daily_transaction_summary',
    ]

    refreshed = 0
    errors = []

    with connection.cursor() as cursor:
        for view in views:
            try:
                # Use CONCURRENTLY to avoid locking (requires unique index)
                cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}")
                refreshed += 1
                logger.info(f"Refreshed materialized view: {view}")
            except Exception as e:
                error_msg = f"Failed to refresh {view}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

                # Try non-concurrent refresh as fallback
                try:
                    cursor.execute(f"REFRESH MATERIALIZED VIEW {view}")
                    refreshed += 1
                    logger.info(f"Refreshed materialized view (non-concurrent): {view}")
                    errors.pop()  # Remove error if fallback succeeded
                except Exception as e2:
                    logger.error(f"Fallback refresh also failed for {view}: {str(e2)}")

    return {
        'status': 'success' if not errors else 'partial',
        'views_refreshed': refreshed,
        'total_views': len(views),
        'errors': errors,
    }


@shared_task(
    name='refresh_single_materialized_view',
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def refresh_single_view(self, view_name: str):
    """
    Refresh a single materialized view.

    Args:
        view_name: Name of the materialized view to refresh

    Returns:
        dict: Status of the refresh operation
    """
    valid_views = {
        'mv_monthly_category_spend',
        'mv_monthly_supplier_spend',
        'mv_daily_transaction_summary',
    }

    if view_name not in valid_views:
        return {
            'status': 'error',
            'message': f"Invalid view name: {view_name}. Valid views: {valid_views}"
        }

    with connection.cursor() as cursor:
        try:
            cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
            logger.info(f"Refreshed materialized view: {view_name}")
            return {
                'status': 'success',
                'view': view_name,
            }
        except Exception as e:
            logger.error(f"Failed to refresh {view_name}: {str(e)}")
            # Try non-concurrent as fallback
            try:
                cursor.execute(f"REFRESH MATERIALIZED VIEW {view_name}")
                return {
                    'status': 'success',
                    'view': view_name,
                    'note': 'Used non-concurrent refresh',
                }
            except Exception as e2:
                return {
                    'status': 'error',
                    'view': view_name,
                    'message': str(e2),
                }


# ============================================================================
# Async AI Enhancement Tasks
# ============================================================================

ENHANCEMENT_STATUS_PREFIX = "ai_enhancement_status"
ENHANCEMENT_RESULT_PREFIX = "ai_enhancement_result"
ENHANCEMENT_CACHE_TTL = 300  # 5 minutes


@shared_task(
    name='enhance_insights_async',
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    track_started=True,
)
def enhance_insights_async(self, org_id: int, user_id: int, insights_data: list):
    """
    Async task to enhance insights with external AI.

    Results are stored in cache for polling by frontend.

    Args:
        org_id: Organization ID
        user_id: User ID who requested the enhancement
        insights_data: List of insight dictionaries to enhance

    Returns:
        dict: Status and result of the enhancement
    """
    from apps.authentication.models import Organization, UserProfile
    from .ai_services import AIInsightsService

    status_key = f"{ENHANCEMENT_STATUS_PREFIX}:{org_id}:{user_id}"
    result_key = f"{ENHANCEMENT_RESULT_PREFIX}:{org_id}:{user_id}"

    try:
        cache.set(status_key, {"status": "processing", "progress": 10}, ENHANCEMENT_CACHE_TTL)

        org = Organization.objects.get(id=org_id)
        profile = UserProfile.objects.filter(user_id=user_id).first()

        if not profile:
            cache.set(status_key, {"status": "failed", "error": "User profile not found"}, ENHANCEMENT_CACHE_TTL)
            return {"status": "failed", "error": "User profile not found"}

        ai_settings = getattr(profile, 'ai_settings', None) or profile.preferences.get('ai_settings', {})

        cache.set(status_key, {"status": "processing", "progress": 30}, ENHANCEMENT_CACHE_TTL)

        service = AIInsightsService(
            organization=org,
            use_external_ai=True,
            ai_provider=ai_settings.get('ai_provider', 'anthropic'),
            api_key=ai_settings.get('ai_api_key')
        )

        cache.set(status_key, {"status": "processing", "progress": 50}, ENHANCEMENT_CACHE_TTL)

        enhancement = service._enhance_with_external_ai_structured(insights_data)

        if enhancement:
            cache.set(status_key, {"status": "processing", "progress": 90}, ENHANCEMENT_CACHE_TTL)
            cache.set(result_key, enhancement, ENHANCEMENT_CACHE_TTL)
            cache.set(status_key, {"status": "completed", "progress": 100}, ENHANCEMENT_CACHE_TTL)

            logger.info(f"AI enhancement completed for org {org_id}")
            return {"status": "completed", "org_id": org_id}
        else:
            cache.set(status_key, {
                "status": "failed",
                "error": "AI enhancement returned no results",
                "progress": 0
            }, ENHANCEMENT_CACHE_TTL)
            return {"status": "failed", "error": "No enhancement results"}

    except Organization.DoesNotExist:
        error_msg = f"Organization {org_id} not found"
        logger.error(error_msg)
        cache.set(status_key, {"status": "failed", "error": error_msg, "progress": 0}, ENHANCEMENT_CACHE_TTL)
        return {"status": "failed", "error": error_msg}

    except Exception as e:
        error_msg = f"AI enhancement failed: {str(e)}"
        logger.error(f"AI enhancement failed for org {org_id}: {e}")
        cache.set(status_key, {"status": "failed", "error": error_msg, "progress": 0}, ENHANCEMENT_CACHE_TTL)
        raise


@shared_task(
    name='perform_deep_analysis_async',
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    track_started=True,
)
def perform_deep_analysis_async(self, org_id: int, user_id: int, insight_data: dict):
    """
    Async task to perform deep analysis on a specific insight.

    Args:
        org_id: Organization ID
        user_id: User ID who requested the analysis
        insight_data: The insight to analyze deeply

    Returns:
        dict: Deep analysis results
    """
    from apps.authentication.models import Organization, UserProfile
    from .ai_services import AIInsightsService

    insight_id = insight_data.get('id', 'unknown')
    status_key = f"deep_analysis_status:{org_id}:{insight_id}"
    result_key = f"deep_analysis_result:{org_id}:{insight_id}"

    try:
        cache.set(status_key, {"status": "processing", "progress": 10}, ENHANCEMENT_CACHE_TTL)

        org = Organization.objects.get(id=org_id)
        profile = UserProfile.objects.filter(user_id=user_id).first()

        if not profile:
            cache.set(status_key, {"status": "failed", "error": "User profile not found"}, ENHANCEMENT_CACHE_TTL)
            return {"status": "failed", "error": "User profile not found"}

        ai_settings = getattr(profile, 'ai_settings', None) or profile.preferences.get('ai_settings', {})

        cache.set(status_key, {"status": "processing", "progress": 30}, ENHANCEMENT_CACHE_TTL)

        service = AIInsightsService(
            organization=org,
            use_external_ai=True,
            ai_provider=ai_settings.get('ai_provider', 'anthropic'),
            api_key=ai_settings.get('ai_api_key')
        )

        cache.set(status_key, {"status": "processing", "progress": 50}, ENHANCEMENT_CACHE_TTL)

        analysis = service.perform_deep_analysis(insight_data)

        if analysis:
            cache.set(status_key, {"status": "processing", "progress": 90}, ENHANCEMENT_CACHE_TTL)
            cache.set(result_key, analysis, ENHANCEMENT_CACHE_TTL)
            cache.set(status_key, {"status": "completed", "progress": 100}, ENHANCEMENT_CACHE_TTL)

            logger.info(f"Deep analysis completed for insight {insight_id} in org {org_id}")
            return {"status": "completed", "insight_id": insight_id}
        else:
            cache.set(status_key, {
                "status": "failed",
                "error": "Deep analysis returned no results",
                "progress": 0
            }, ENHANCEMENT_CACHE_TTL)
            return {"status": "failed", "error": "No analysis results"}

    except Organization.DoesNotExist:
        error_msg = f"Organization {org_id} not found"
        logger.error(error_msg)
        cache.set(status_key, {"status": "failed", "error": error_msg, "progress": 0}, ENHANCEMENT_CACHE_TTL)
        return {"status": "failed", "error": error_msg}

    except Exception as e:
        error_msg = f"Deep analysis failed: {str(e)}"
        logger.error(f"Deep analysis failed for insight {insight_id} in org {org_id}: {e}")
        cache.set(status_key, {"status": "failed", "error": error_msg, "progress": 0}, ENHANCEMENT_CACHE_TTL)
        raise


# ============================================================================
# Batch Processing Tasks (Overnight Jobs)
# ============================================================================

@shared_task(
    name='batch_generate_insights',
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    track_started=True,
    soft_time_limit=3600,
    time_limit=3900,
)
def batch_generate_insights(self):
    """
    Nightly batch generation of AI insights for all active organizations.

    This task:
    1. Fetches all active organizations
    2. Generates base insights for each organization
    3. Enhances insights using AI (if configured)
    4. Caches results for immediate availability next day

    Benefits:
    - Pre-computed insights ready when users log in
    - Can use Anthropic Batch API for 50% cost savings (future enhancement)
    - Reduces daytime API load

    Returns:
        dict: Summary of batch processing results
    """
    from apps.authentication.models import Organization
    from .ai_services import AIInsightsService
    from .ai_cache import AIInsightsCache

    start_time = timezone.now()
    results = {
        'organizations_processed': 0,
        'organizations_failed': 0,
        'insights_generated': 0,
        'errors': [],
        'started_at': start_time.isoformat(),
    }

    organizations = Organization.objects.filter(is_active=True)
    total_orgs = organizations.count()

    logger.info(f"Starting batch insight generation for {total_orgs} organizations")

    for idx, org in enumerate(organizations):
        try:
            logger.info(f"Processing organization {idx + 1}/{total_orgs}: {org.name}")

            service = AIInsightsService(
                organization=org,
                use_external_ai=False,
            )

            insights = service.get_all_insights()

            if insights:
                cache_service = AIInsightsCache(org.id)
                cache_key = cache_service._generate_cache_key(
                    insight_type='all',
                    filters={}
                )
                cache.set(
                    cache_key,
                    {
                        'insights': insights,
                        'generated_at': timezone.now().isoformat(),
                        'batch_generated': True,
                    },
                    timeout=86400
                )

                results['insights_generated'] += len(insights)
                results['organizations_processed'] += 1

                logger.info(f"Generated {len(insights)} insights for {org.name}")
            else:
                results['organizations_processed'] += 1
                logger.info(f"No insights generated for {org.name} (no data)")

        except Exception as e:
            error_msg = f"Failed to process {org.name}: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            results['organizations_failed'] += 1

    end_time = timezone.now()
    duration = (end_time - start_time).total_seconds()

    results['completed_at'] = end_time.isoformat()
    results['duration_seconds'] = duration
    results['status'] = 'success' if not results['errors'] else 'partial'

    logger.info(
        f"Batch insight generation completed: "
        f"{results['organizations_processed']} orgs, "
        f"{results['insights_generated']} insights, "
        f"{results['organizations_failed']} failures, "
        f"{duration:.1f}s duration"
    )

    return results


@shared_task(
    name='batch_enhance_insights',
    bind=True,
    max_retries=1,
    soft_time_limit=7200,
    time_limit=7500,
)
def batch_enhance_insights(self):
    """
    Enhance pre-generated insights with external AI for all organizations
    with AI enabled.

    This should run AFTER batch_generate_insights completes.
    Uses external AI to add recommendations and priority actions.

    Returns:
        dict: Summary of enhancement results
    """
    from apps.authentication.models import Organization, UserProfile
    from .ai_services import AIInsightsService

    start_time = timezone.now()
    results = {
        'organizations_enhanced': 0,
        'organizations_skipped': 0,
        'organizations_failed': 0,
        'errors': [],
        'started_at': start_time.isoformat(),
    }

    organizations = Organization.objects.filter(is_active=True)

    for org in organizations:
        try:
            admin_profile = UserProfile.objects.filter(
                organization=org,
                role='admin',
                is_active=True
            ).first()

            if not admin_profile:
                results['organizations_skipped'] += 1
                continue

            ai_settings = admin_profile.preferences.get('ai_settings', {})

            if not ai_settings.get('use_external_ai') or not ai_settings.get('ai_api_key'):
                results['organizations_skipped'] += 1
                continue

            service = AIInsightsService(
                organization=org,
                use_external_ai=True,
                ai_provider=ai_settings.get('ai_provider', 'anthropic'),
                api_key=ai_settings.get('ai_api_key')
            )

            insights = service.get_all_insights()
            if insights:
                enhanced = service._enhance_with_external_ai_structured(insights)
                if enhanced:
                    results['organizations_enhanced'] += 1
                    logger.info(f"Enhanced insights for {org.name}")
                else:
                    results['organizations_failed'] += 1
            else:
                results['organizations_skipped'] += 1

        except Exception as e:
            error_msg = f"Enhancement failed for {org.name}: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            results['organizations_failed'] += 1

    end_time = timezone.now()
    results['completed_at'] = end_time.isoformat()
    results['duration_seconds'] = (end_time - start_time).total_seconds()
    results['status'] = 'success' if not results['errors'] else 'partial'

    logger.info(
        f"Batch enhancement completed: "
        f"{results['organizations_enhanced']} enhanced, "
        f"{results['organizations_skipped']} skipped, "
        f"{results['organizations_failed']} failed"
    )

    return results


# ============================================================================
# Cache Maintenance Tasks
# ============================================================================

@shared_task(
    name='cleanup_semantic_cache',
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def cleanup_semantic_cache(self):
    """
    Clean up expired entries from the semantic cache.

    This task removes:
    - Expired cache entries (past expires_at)
    - Orphaned entries (organization deleted)
    - Low-value entries (hit_count=0 and older than 24 hours)

    Returns:
        dict: Summary of cleanup results
    """
    from .models import SemanticCache

    start_time = timezone.now()
    results = {
        'expired_deleted': 0,
        'orphaned_deleted': 0,
        'low_value_deleted': 0,
        'total_remaining': 0,
        'started_at': start_time.isoformat(),
    }

    try:
        expired = SemanticCache.objects.filter(
            expires_at__lt=timezone.now()
        )
        results['expired_deleted'] = expired.count()
        expired.delete()
        logger.info(f"Deleted {results['expired_deleted']} expired cache entries")

        orphaned = SemanticCache.objects.filter(
            organization__isnull=True
        )
        results['orphaned_deleted'] = orphaned.count()
        orphaned.delete()

        cutoff = timezone.now() - timedelta(hours=24)
        low_value = SemanticCache.objects.filter(
            hit_count=0,
            created_at__lt=cutoff
        )
        results['low_value_deleted'] = low_value.count()
        low_value.delete()
        logger.info(f"Deleted {results['low_value_deleted']} low-value cache entries")

        results['total_remaining'] = SemanticCache.objects.count()

    except Exception as e:
        logger.error(f"Semantic cache cleanup failed: {str(e)}")
        raise

    end_time = timezone.now()
    results['completed_at'] = end_time.isoformat()
    results['duration_seconds'] = (end_time - start_time).total_seconds()
    results['status'] = 'success'

    logger.info(
        f"Semantic cache cleanup completed: "
        f"{results['expired_deleted'] + results['orphaned_deleted'] + results['low_value_deleted']} deleted, "
        f"{results['total_remaining']} remaining"
    )

    return results


@shared_task(
    name='cleanup_llm_request_logs',
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def cleanup_llm_request_logs(self, days_to_keep: int = 30):
    """
    Archive or delete old LLM request logs.

    Keeps recent logs for debugging and cost analysis,
    deletes logs older than specified retention period.

    Args:
        days_to_keep: Number of days of logs to retain (default: 30)

    Returns:
        dict: Summary of cleanup results
    """
    from .models import LLMRequestLog

    start_time = timezone.now()
    cutoff_date = timezone.now() - timedelta(days=days_to_keep)

    results = {
        'logs_deleted': 0,
        'logs_remaining': 0,
        'cutoff_date': cutoff_date.isoformat(),
        'started_at': start_time.isoformat(),
    }

    try:
        old_logs = LLMRequestLog.objects.filter(created_at__lt=cutoff_date)
        results['logs_deleted'] = old_logs.count()
        old_logs.delete()

        results['logs_remaining'] = LLMRequestLog.objects.count()

        logger.info(f"Deleted {results['logs_deleted']} old LLM request logs")

    except Exception as e:
        logger.error(f"LLM log cleanup failed: {str(e)}")
        raise

    end_time = timezone.now()
    results['completed_at'] = end_time.isoformat()
    results['duration_seconds'] = (end_time - start_time).total_seconds()
    results['status'] = 'success'

    return results


@shared_task(
    name='refresh_rag_documents',
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=1800,
    time_limit=2100,
)
def refresh_rag_documents(self):
    """
    Refresh RAG document embeddings for all organizations.

    This task:
    1. Re-ingests supplier profiles with updated data
    2. Re-ingests historical insights
    3. Updates embeddings for modified documents

    Returns:
        dict: Summary of refresh results
    """
    from apps.authentication.models import Organization
    from .document_ingestion import DocumentIngestionService

    start_time = timezone.now()
    results = {
        'organizations_processed': 0,
        'documents_updated': 0,
        'errors': [],
        'started_at': start_time.isoformat(),
    }

    organizations = Organization.objects.filter(is_active=True)

    for org in organizations:
        try:
            ingestion_service = DocumentIngestionService(org.id)

            supplier_count = ingestion_service.ingest_supplier_profiles()
            insight_count = ingestion_service.ingest_historical_insights()

            results['documents_updated'] += supplier_count + insight_count
            results['organizations_processed'] += 1

            logger.info(
                f"Refreshed RAG documents for {org.name}: "
                f"{supplier_count} suppliers, {insight_count} insights"
            )

        except Exception as e:
            error_msg = f"RAG refresh failed for {org.name}: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)

    end_time = timezone.now()
    results['completed_at'] = end_time.isoformat()
    results['duration_seconds'] = (end_time - start_time).total_seconds()
    results['status'] = 'success' if not results['errors'] else 'partial'

    logger.info(
        f"RAG document refresh completed: "
        f"{results['organizations_processed']} orgs, "
        f"{results['documents_updated']} documents"
    )

    return results
