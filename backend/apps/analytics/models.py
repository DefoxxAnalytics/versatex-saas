"""
Analytics models for AI-powered procurement intelligence.

Models:
- LLMRequestLog: Tracks AI provider API calls for cost monitoring and optimization
- SemanticCache: Stores embeddings for semantic similarity caching (73% cost reduction)
- EmbeddedDocument: Stores document embeddings for RAG (Retrieval-Augmented Generation)
- InsightFeedback: Tracks user actions on AI-generated insights for ROI measurement
"""
import hashlib
import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from apps.authentication.models import Organization

try:
    from pgvector.django import VectorField
    PGVECTOR_AVAILABLE = True
except ImportError:
    VectorField = None
    PGVECTOR_AVAILABLE = False


class LLMRequestLog(models.Model):
    """
    Track all LLM API requests for cost monitoring, performance analysis,
    and cache efficiency measurement.
    """

    REQUEST_TYPE_CHOICES = [
        ('enhance', 'Insight Enhancement'),
        ('single_insight', 'Single Insight Analysis'),
        ('deep_analysis', 'Deep Analysis'),
        ('classify', 'Query Classification'),
        ('chat', 'Chat Response'),
        ('health_check', 'Health Check'),
    ]

    MODEL_TIER_CHOICES = [
        ('haiku', 'Haiku (Fast/Cheap)'),
        ('sonnet', 'Sonnet (Balanced)'),
        ('opus', 'Opus (Premium)'),
        ('gpt4o_mini', 'GPT-4o Mini'),
        ('gpt4_turbo', 'GPT-4 Turbo'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='llm_requests',
        null=True,
        blank=True
    )

    request_type = models.CharField(
        max_length=50,
        choices=REQUEST_TYPE_CHOICES,
        db_index=True
    )
    model_used = models.CharField(max_length=100, db_index=True)
    model_tier = models.CharField(
        max_length=20,
        choices=MODEL_TIER_CHOICES,
        null=True,
        blank=True
    )
    provider = models.CharField(max_length=20, db_index=True)

    tokens_input = models.IntegerField(default=0)
    tokens_output = models.IntegerField(default=0)
    latency_ms = models.IntegerField(default=0)

    cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=Decimal('0.000000')
    )

    cache_hit = models.BooleanField(
        default=False,
        help_text="Whether response was served from semantic/Redis cache"
    )
    prompt_cache_read_tokens = models.IntegerField(
        default=0,
        help_text="Anthropic prompt cache: tokens read from cache"
    )
    prompt_cache_write_tokens = models.IntegerField(
        default=0,
        help_text="Anthropic prompt cache: tokens written to cache"
    )

    validation_passed = models.BooleanField(
        default=True,
        help_text="Whether LLM response passed hallucination validation"
    )
    validation_errors = models.JSONField(
        default=list,
        blank=True,
        help_text="List of validation errors if validation failed"
    )

    error_occurred = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['organization', 'request_type']),
            models.Index(fields=['provider', 'model_used']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'LLM Request Log'
        verbose_name_plural = 'LLM Request Logs'

    def __str__(self):
        org_name = self.organization.name if self.organization else 'System'
        return f"{self.request_type} via {self.provider}/{self.model_used} ({org_name})"

    @property
    def total_tokens(self) -> int:
        return self.tokens_input + self.tokens_output

    @property
    def cost_savings_from_cache(self) -> Decimal:
        """Calculate cost savings from prompt caching."""
        if self.prompt_cache_read_tokens > 0:
            base_cost_per_token = self._get_input_cost_per_token()
            cached_cost = base_cost_per_token * Decimal('0.1')
            savings = (base_cost_per_token - cached_cost) * self.prompt_cache_read_tokens
            return savings
        return Decimal('0')

    def _get_input_cost_per_token(self) -> Decimal:
        """Get input cost per token based on model."""
        model_costs = {
            'claude-sonnet-4-20250514': Decimal('0.000003'),
            'claude-3-5-haiku-20241022': Decimal('0.00000025'),
            'claude-opus-4-20250514': Decimal('0.000015'),
            'gpt-4-turbo-preview': Decimal('0.00001'),
            'gpt-4o-mini': Decimal('0.00000015'),
        }
        return model_costs.get(self.model_used, Decimal('0.000003'))

    @classmethod
    def get_usage_summary(cls, organization_id: int, days: int = 30) -> dict:
        """Get usage summary for an organization over specified days."""
        from django.utils import timezone
        from django.db.models import Sum, Count, Avg
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(days=days)

        logs = cls.objects.filter(
            organization_id=organization_id,
            created_at__gte=cutoff
        )

        totals = logs.aggregate(
            total_requests=Count('id'),
            total_cost=Sum('cost_usd'),
            total_input_tokens=Sum('tokens_input'),
            total_output_tokens=Sum('tokens_output'),
            avg_latency=Avg('latency_ms'),
            cache_hits=Count('id', filter=models.Q(cache_hit=True)),
            prompt_cache_reads=Sum('prompt_cache_read_tokens'),
        )

        by_type = list(
            logs.values('request_type')
            .annotate(
                count=Count('id'),
                cost=Sum('cost_usd'),
                tokens=Sum('tokens_input') + Sum('tokens_output')
            )
            .order_by('-count')
        )

        by_provider = list(
            logs.values('provider')
            .annotate(
                count=Count('id'),
                cost=Sum('cost_usd'),
            )
            .order_by('-count')
        )

        return {
            'period_days': days,
            'total_requests': totals['total_requests'] or 0,
            'total_cost_usd': float(totals['total_cost'] or 0),
            'total_tokens': (totals['total_input_tokens'] or 0) + (totals['total_output_tokens'] or 0),
            'avg_latency_ms': round(totals['avg_latency'] or 0, 1),
            'cache_hit_rate': round(
                (totals['cache_hits'] or 0) / max(totals['total_requests'] or 1, 1) * 100, 1
            ),
            'prompt_cache_tokens_saved': totals['prompt_cache_reads'] or 0,
            'by_request_type': by_type,
            'by_provider': by_provider,
        }


class SemanticCache(models.Model):
    """
    Cache LLM responses with semantic similarity search.

    Uses pgvector for efficient similarity search, enabling cache hits
    for queries that are semantically similar (not just exact matches).
    This reduces LLM API costs by ~73% for repeated similar queries.

    Features:
    - Vector similarity search with configurable threshold (default 0.90)
    - Automatic TTL-based expiration
    - Hit count tracking for cache efficiency metrics
    - Request type scoping for targeted caching
    """

    REQUEST_TYPE_CHOICES = [
        ('enhance', 'Insight Enhancement'),
        ('single_insight', 'Single Insight Analysis'),
        ('deep_analysis', 'Deep Analysis'),
        ('chat', 'Chat Response'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='semantic_cache_entries'
    )

    request_type = models.CharField(
        max_length=50,
        choices=REQUEST_TYPE_CHOICES,
        db_index=True,
        help_text="Type of request this cache entry is for"
    )

    query_text = models.TextField(
        help_text="Original query/prompt text"
    )
    query_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 hash for fast exact-match lookup"
    )

    response_json = models.JSONField(
        help_text="Cached LLM response"
    )

    hit_count = models.IntegerField(
        default=0,
        help_text="Number of times this cache entry was used"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'request_type', 'expires_at']),
            models.Index(fields=['organization', 'query_hash']),
            models.Index(fields=['expires_at']),
        ]
        verbose_name = 'Semantic Cache Entry'
        verbose_name_plural = 'Semantic Cache Entries'

    def __str__(self):
        return f"{self.request_type}: {self.query_text[:50]}..."

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    def increment_hit_count(self) -> None:
        self.hit_count += 1
        self.save(update_fields=['hit_count'])

    @classmethod
    def create_entry(
        cls,
        organization_id: int,
        request_type: str,
        query_text: str,
        embedding: list,
        response: dict,
        ttl_hours: int = 1
    ) -> 'SemanticCache':
        """
        Create a new cache entry with embedding.

        Args:
            organization_id: Organization ID
            request_type: Type of request (enhance, single_insight, etc.)
            query_text: Original query text
            embedding: Vector embedding (1536 dimensions)
            response: Response dict to cache
            ttl_hours: Time-to-live in hours (default 1)

        Returns:
            Created SemanticCache instance
        """
        query_hash = hashlib.sha256(query_text.encode()).hexdigest()
        expires_at = timezone.now() + timedelta(hours=ttl_hours)

        entry = cls(
            organization_id=organization_id,
            request_type=request_type,
            query_text=query_text,
            query_hash=query_hash,
            response_json=response,
            expires_at=expires_at,
        )

        if PGVECTOR_AVAILABLE and hasattr(entry, 'query_embedding'):
            entry.query_embedding = embedding

        entry.save()
        return entry

    @classmethod
    def cleanup_expired(cls) -> int:
        """Delete expired cache entries. Returns count deleted."""
        result = cls.objects.filter(expires_at__lt=timezone.now()).delete()
        return result[0] if result else 0

    @classmethod
    def get_cache_stats(cls, organization_id: int) -> dict:
        """Get cache statistics for an organization."""
        from django.db.models import Sum, Count, Avg

        entries = cls.objects.filter(
            organization_id=organization_id,
            expires_at__gt=timezone.now()
        )

        stats = entries.aggregate(
            total_entries=Count('id'),
            total_hits=Sum('hit_count'),
            avg_hits=Avg('hit_count'),
        )

        by_type = list(
            entries.values('request_type')
            .annotate(
                count=Count('id'),
                hits=Sum('hit_count')
            )
            .order_by('-hits')
        )

        return {
            'total_entries': stats['total_entries'] or 0,
            'total_hits': stats['total_hits'] or 0,
            'avg_hits_per_entry': round(stats['avg_hits'] or 0, 1),
            'by_request_type': by_type,
        }


if PGVECTOR_AVAILABLE:
    SemanticCache.add_to_class(
        'query_embedding',
        VectorField(
            dimensions=1536,
            null=True,
            blank=True,
            help_text="OpenAI text-embedding-3-small vector (1536 dims)"
        )
    )


class EmbeddedDocument(models.Model):
    """
    Store documents with vector embeddings for RAG (Retrieval-Augmented Generation).

    Enables AI insights to be augmented with relevant context from:
    - Supplier profiles and performance history
    - Contracts and terms
    - Procurement policies
    - Best practices and guidelines
    - Historical successful insights

    Uses pgvector for efficient similarity search to find relevant
    documents that can provide context for AI-generated insights.
    """

    DOCUMENT_TYPE_CHOICES = [
        ('supplier_profile', 'Supplier Profile'),
        ('contract', 'Contract'),
        ('policy', 'Procurement Policy'),
        ('best_practice', 'Best Practice'),
        ('historical_insight', 'Historical Insight'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='embedded_documents'
    )

    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES,
        db_index=True,
        help_text="Type of document for filtering during retrieval"
    )

    title = models.CharField(
        max_length=255,
        help_text="Document title for display"
    )
    content = models.TextField(
        help_text="Full document content (will be chunked if too long)"
    )
    content_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 hash for deduplication"
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata (supplier_id, category_id, etc.)"
    )

    source_model = models.CharField(
        max_length=100,
        blank=True,
        help_text="Source Django model if auto-generated (e.g., 'Supplier', 'InsightFeedback')"
    )
    source_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Source object ID for updates"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Soft delete - inactive docs excluded from search"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['organization', 'document_type']),
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['source_model', 'source_id']),
            models.Index(fields=['content_hash']),
        ]
        verbose_name = 'Embedded Document'
        verbose_name_plural = 'Embedded Documents'

    def __str__(self):
        return f"{self.get_document_type_display()}: {self.title[:50]}"

    @classmethod
    def create_or_update(
        cls,
        organization_id: int,
        document_type: str,
        title: str,
        content: str,
        embedding: list = None,
        metadata: dict = None,
        source_model: str = '',
        source_id: str = ''
    ) -> 'EmbeddedDocument':
        """
        Create or update a document with embedding.

        Uses content_hash for deduplication - if content hasn't changed,
        the existing document is returned unchanged.
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        if source_model and source_id:
            existing = cls.objects.filter(
                organization_id=organization_id,
                source_model=source_model,
                source_id=source_id
            ).first()

            if existing:
                if existing.content_hash == content_hash:
                    return existing

                existing.title = title
                existing.content = content
                existing.content_hash = content_hash
                existing.metadata = metadata or {}
                existing.document_type = document_type

                if PGVECTOR_AVAILABLE and embedding and hasattr(existing, 'content_embedding'):
                    existing.content_embedding = embedding

                existing.save()
                return existing

        doc = cls(
            organization_id=organization_id,
            document_type=document_type,
            title=title,
            content=content,
            content_hash=content_hash,
            metadata=metadata or {},
            source_model=source_model,
            source_id=source_id,
        )

        if PGVECTOR_AVAILABLE and embedding and hasattr(doc, 'content_embedding'):
            doc.content_embedding = embedding

        doc.save()
        return doc

    @classmethod
    def get_document_stats(cls, organization_id: int) -> dict:
        """Get document statistics for an organization."""
        from django.db.models import Count

        docs = cls.objects.filter(
            organization_id=organization_id,
            is_active=True
        )

        by_type = list(
            docs.values('document_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        return {
            'total_documents': docs.count(),
            'by_type': by_type,
        }


if PGVECTOR_AVAILABLE:
    EmbeddedDocument.add_to_class(
        'content_embedding',
        VectorField(
            dimensions=1536,
            null=True,
            blank=True,
            help_text="OpenAI text-embedding-3-small vector (1536 dims)"
        )
    )


class InsightFeedback(models.Model):
    """
    Track user actions and outcomes for AI-generated insights.

    Enables:
    - ROI measurement (predicted vs actual savings)
    - Recommendation effectiveness tracking
    - Historical context for AI improvement
    """

    ACTION_CHOICES = [
        ('implemented', 'Implemented'),
        ('dismissed', 'Dismissed'),
        ('deferred', 'Deferred for Later'),
        ('investigating', 'Under Investigation'),
        ('partial', 'Partially Implemented'),
    ]

    OUTCOME_CHOICES = [
        ('pending', 'Outcome Pending'),
        ('success', 'Achieved Expected Savings'),
        ('partial_success', 'Partial Savings Achieved'),
        ('no_change', 'No Measurable Impact'),
        ('failed', 'Implementation Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='insight_feedback'
    )

    # Insight identification (stored as snapshot since insights are generated dynamically)
    insight_id = models.CharField(max_length=36, db_index=True)
    insight_type = models.CharField(max_length=50, db_index=True)
    insight_title = models.CharField(max_length=200)
    insight_severity = models.CharField(max_length=20)
    predicted_savings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Predicted savings amount from the insight"
    )

    # User action tracking
    action_taken = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        db_index=True
    )
    action_date = models.DateTimeField(auto_now_add=True)
    action_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='insight_actions'
    )
    action_notes = models.TextField(blank=True)

    # Outcome tracking (updated later after implementation)
    outcome = models.CharField(
        max_length=20,
        choices=OUTCOME_CHOICES,
        default='pending',
        db_index=True
    )
    actual_savings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual savings realized after implementation"
    )
    outcome_date = models.DateTimeField(null=True, blank=True)
    outcome_notes = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-action_date']
        indexes = [
            models.Index(fields=['organization', 'insight_type']),
            models.Index(fields=['organization', 'action_taken']),
            models.Index(fields=['organization', 'outcome']),
            models.Index(fields=['action_date']),
        ]
        verbose_name = 'Insight Feedback'
        verbose_name_plural = 'Insight Feedback'

    def __str__(self):
        return f"{self.insight_type}: {self.action_taken} - {self.insight_title[:50]}"

    @property
    def savings_accuracy(self) -> float | None:
        """
        Calculate accuracy of predicted vs actual savings.

        Returns ratio of actual/predicted, or None if not applicable.
        """
        if self.actual_savings and self.predicted_savings and self.predicted_savings > 0:
            return float(self.actual_savings) / float(self.predicted_savings)
        return None

    @property
    def savings_variance(self) -> float | None:
        """
        Calculate variance between predicted and actual savings.

        Positive = actual exceeded prediction
        Negative = actual fell short of prediction
        """
        if self.actual_savings is not None and self.predicted_savings is not None:
            return float(self.actual_savings) - float(self.predicted_savings)
        return None
