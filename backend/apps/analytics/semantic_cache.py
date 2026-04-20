"""
Semantic Cache Service for AI Insights.

Provides vector similarity search for LLM response caching, enabling
~73% cost reduction by serving cached responses for semantically
similar queries (not just exact matches).

Uses OpenAI text-embedding-3-small (1536 dimensions) for embeddings
and pgvector for efficient similarity search.
"""
import hashlib
import logging
from typing import Optional, TYPE_CHECKING

from django.conf import settings
from django.db import connection
from django.utils import timezone

if TYPE_CHECKING:
    from .models import SemanticCache

logger = logging.getLogger(__name__)


class SemanticCacheService:
    """
    Semantic similarity cache for LLM responses.

    Features:
    - Vector similarity search with configurable threshold
    - Fallback to exact hash matching when pgvector unavailable
    - Automatic embedding generation via OpenAI
    - TTL-based expiration with configurable duration
    """

    SIMILARITY_THRESHOLD = 0.90
    DEFAULT_TTL_HOURS = 1
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536

    def __init__(self, organization_id: int, openai_api_key: str = None):
        """
        Initialize the semantic cache service.

        Args:
            organization_id: Organization to scope cache entries
            openai_api_key: OpenAI API key for embeddings (uses settings if not provided)
        """
        self.organization_id = organization_id
        self.openai_api_key = openai_api_key or getattr(
            settings, 'OPENAI_API_KEY', None
        )
        self._openai_client = None
        self._pgvector_available = self._check_pgvector()

    def _check_pgvector(self) -> bool:
        """Check if pgvector extension is available."""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.warning(f"pgvector check failed: {e}")
            return False

    @property
    def openai_client(self):
        """Lazy-load OpenAI client."""
        if self._openai_client is None and self.openai_api_key:
            try:
                import openai
                self._openai_client = openai.OpenAI(api_key=self.openai_api_key)
            except ImportError:
                logger.warning("openai package not installed")
        return self._openai_client

    def _get_embedding(self, text: str) -> Optional[list]:
        """
        Get embedding vector for text using OpenAI.

        Args:
            text: Text to embed

        Returns:
            List of floats (1536 dimensions) or None if unavailable
        """
        if not self.openai_client:
            return None

        try:
            truncated = text[:8000]

            response = self.openai_client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=truncated,
                dimensions=self.EMBEDDING_DIMENSIONS
            )

            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    def lookup(
        self,
        query: str,
        request_type: str = 'enhance'
    ) -> Optional[dict]:
        """
        Find semantically similar cached response.

        Tries vector similarity search first, falls back to exact hash match.

        Args:
            query: Query text to find similar cache entry for
            request_type: Type of request (enhance, single_insight, etc.)

        Returns:
            Cached response dict if found, None otherwise
        """
        from .models import SemanticCache

        query_hash = hashlib.sha256(query.encode()).hexdigest()

        exact_match = SemanticCache.objects.filter(
            organization_id=self.organization_id,
            request_type=request_type,
            query_hash=query_hash,
            expires_at__gt=timezone.now()
        ).first()

        if exact_match:
            exact_match.increment_hit_count()
            logger.info(f"Semantic cache exact hit for {request_type}")
            return exact_match.response_json

        if self._pgvector_available and self.openai_client:
            embedding = self._get_embedding(query)
            if embedding:
                similar = self._vector_lookup(embedding, request_type)
                if similar:
                    similar.increment_hit_count()
                    logger.info(
                        f"Semantic cache similarity hit for {request_type} "
                        f"(threshold: {self.SIMILARITY_THRESHOLD})"
                    )
                    return similar.response_json

        return None

    def _vector_lookup(
        self,
        embedding: list,
        request_type: str
    ) -> Optional['SemanticCache']:
        """
        Perform vector similarity search using pgvector.

        Args:
            embedding: Query embedding vector
            request_type: Type of request to filter

        Returns:
            SemanticCache entry if similar found, None otherwise
        """
        from .models import SemanticCache

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, 1 - (query_embedding <=> %s::vector) as similarity
                    FROM analytics_semanticcache
                    WHERE organization_id = %s
                      AND request_type = %s
                      AND expires_at > NOW()
                      AND query_embedding IS NOT NULL
                    ORDER BY query_embedding <=> %s::vector
                    LIMIT 1
                    """,
                    [embedding, self.organization_id, request_type, embedding]
                )
                row = cursor.fetchone()

                if row and row[1] >= self.SIMILARITY_THRESHOLD:
                    return SemanticCache.objects.get(id=row[0])

        except Exception as e:
            logger.error(f"Vector lookup failed: {e}")

        return None

    def store(
        self,
        query: str,
        response: dict,
        request_type: str = 'enhance',
        ttl_hours: int = None
    ) -> Optional['SemanticCache']:
        """
        Store response in cache with embedding.

        Args:
            query: Original query text
            response: Response dict to cache
            request_type: Type of request
            ttl_hours: Time-to-live in hours (uses default if not specified)

        Returns:
            Created SemanticCache entry or None if failed
        """
        from .models import SemanticCache

        ttl = ttl_hours or self.DEFAULT_TTL_HOURS

        embedding = None
        if self._pgvector_available and self.openai_client:
            embedding = self._get_embedding(query)

        try:
            entry = SemanticCache.create_entry(
                organization_id=self.organization_id,
                request_type=request_type,
                query_text=query,
                embedding=embedding,
                response=response,
                ttl_hours=ttl
            )
            logger.info(
                f"Cached {request_type} response "
                f"(embedding: {'yes' if embedding else 'no'}, ttl: {ttl}h)"
            )
            return entry

        except Exception as e:
            logger.error(f"Cache store failed: {e}")
            return None

    def invalidate(
        self,
        request_type: str = None,
        older_than_hours: int = None
    ) -> int:
        """
        Invalidate cache entries.

        Args:
            request_type: Optional type filter (invalidate all if None)
            older_than_hours: Optional age filter

        Returns:
            Number of entries deleted
        """
        from .models import SemanticCache
        from datetime import timedelta

        qs = SemanticCache.objects.filter(organization_id=self.organization_id)

        if request_type:
            qs = qs.filter(request_type=request_type)

        if older_than_hours:
            cutoff = timezone.now() - timedelta(hours=older_than_hours)
            qs = qs.filter(created_at__lt=cutoff)

        result = qs.delete()
        count = result[0] if result else 0
        logger.info(f"Invalidated {count} cache entries")
        return count

    def get_stats(self) -> dict:
        """Get cache statistics for this organization."""
        from .models import SemanticCache
        return SemanticCache.get_cache_stats(self.organization_id)

    @classmethod
    def cleanup_all_expired(cls) -> int:
        """Cleanup expired entries across all organizations."""
        from .models import SemanticCache
        return SemanticCache.cleanup_expired()
