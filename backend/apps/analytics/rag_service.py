"""
RAG (Retrieval-Augmented Generation) Service for AI Insights.

Provides vector similarity search to find relevant documents (supplier profiles,
contracts, policies, historical insights) that can augment LLM context for
more accurate and grounded AI-generated insights.

Uses OpenAI text-embedding-3-small (1536 dimensions) for embeddings
and pgvector for efficient similarity search.
"""
import logging
from typing import Optional, List

from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)


class RAGService:
    """
    Retrieval-Augmented Generation service for document search.

    Features:
    - Vector similarity search with configurable threshold
    - Document type filtering for targeted retrieval
    - Fallback to keyword search when pgvector unavailable
    - Context augmentation for LLM prompts
    """

    TOP_K = 5
    SIMILARITY_THRESHOLD = 0.70
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536

    def __init__(self, organization_id: int, openai_api_key: str = None):
        """
        Initialize the RAG service.

        Args:
            organization_id: Organization to scope document search
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

    def search(
        self,
        query: str,
        doc_types: List[str] = None,
        top_k: int = None,
        threshold: float = None
    ) -> List[dict]:
        """
        Search for documents relevant to the query.

        Uses vector similarity search if pgvector is available,
        otherwise falls back to keyword-based search.

        Args:
            query: Search query text
            doc_types: Optional list of document types to filter
            top_k: Number of results to return (default: 5)
            threshold: Minimum similarity threshold (default: 0.70)

        Returns:
            List of document dicts with title, content, type, metadata, similarity
        """
        top_k = top_k or self.TOP_K
        threshold = threshold or self.SIMILARITY_THRESHOLD

        if self._pgvector_available and self.openai_client:
            embedding = self._get_embedding(query)
            if embedding:
                return self._vector_search(embedding, doc_types, top_k, threshold)

        return self._keyword_search(query, doc_types, top_k)

    def _vector_search(
        self,
        embedding: list,
        doc_types: List[str],
        top_k: int,
        threshold: float
    ) -> List[dict]:
        """Perform vector similarity search using pgvector."""
        from .models import EmbeddedDocument

        try:
            type_filter = ""
            params = [embedding, self.organization_id]

            if doc_types:
                placeholders = ', '.join(['%s'] * len(doc_types))
                type_filter = f"AND document_type IN ({placeholders})"
                params.extend(doc_types)

            params.extend([embedding, threshold, top_k])

            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        id,
                        document_type,
                        title,
                        content,
                        metadata,
                        1 - (content_embedding <=> %s::vector) as similarity
                    FROM analytics_embeddeddocument
                    WHERE organization_id = %s
                      AND is_active = TRUE
                      AND content_embedding IS NOT NULL
                      {type_filter}
                    ORDER BY content_embedding <=> %s::vector
                    LIMIT %s
                    """,
                    params[:-1] + [params[-2], params[-1]]
                )

                columns = [col[0] for col in cursor.description]
                results = []

                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    if row_dict['similarity'] >= threshold:
                        results.append({
                            'id': str(row_dict['id']),
                            'document_type': row_dict['document_type'],
                            'title': row_dict['title'],
                            'content': row_dict['content'],
                            'metadata': row_dict['metadata'],
                            'similarity': round(row_dict['similarity'], 4),
                        })

                logger.info(
                    f"RAG vector search: {len(results)} docs found "
                    f"(threshold: {threshold}, top_k: {top_k})"
                )
                return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return self._keyword_search(
                "fallback", doc_types, top_k
            )

    def _keyword_search(
        self,
        query: str,
        doc_types: List[str],
        top_k: int
    ) -> List[dict]:
        """Fallback keyword-based search when vector search unavailable."""
        from .models import EmbeddedDocument

        qs = EmbeddedDocument.objects.filter(
            organization_id=self.organization_id,
            is_active=True
        )

        if doc_types:
            qs = qs.filter(document_type__in=doc_types)

        words = query.lower().split()[:5]
        from django.db.models import Q
        q_filter = Q()
        for word in words:
            if len(word) > 2:
                q_filter |= Q(title__icontains=word) | Q(content__icontains=word)

        if q_filter:
            qs = qs.filter(q_filter)

        results = []
        for doc in qs[:top_k]:
            results.append({
                'id': str(doc.id),
                'document_type': doc.document_type,
                'title': doc.title,
                'content': doc.content,
                'metadata': doc.metadata,
                'similarity': 0.5,
            })

        logger.info(f"RAG keyword search: {len(results)} docs found")
        return results

    def augment_context(
        self,
        query: str,
        base_context: dict,
        doc_types: List[str] = None,
        max_content_length: int = 500
    ) -> dict:
        """
        Augment LLM context with relevant documents.

        Searches for relevant documents and adds them to the context
        dict for use in LLM prompts.

        Args:
            query: Query to find relevant documents for
            base_context: Base context dict to augment
            doc_types: Optional document type filter
            max_content_length: Max chars of content to include per doc

        Returns:
            Augmented context dict with 'relevant_documents' key
        """
        docs = self.search(query, doc_types)

        if docs:
            base_context['relevant_documents'] = [
                {
                    'type': d['document_type'],
                    'title': d['title'],
                    'content': d['content'][:max_content_length],
                    'relevance': f"{d['similarity']:.0%}",
                    'metadata': d.get('metadata', {}),
                }
                for d in docs
            ]
            logger.info(f"Augmented context with {len(docs)} relevant documents")

        return base_context

    def get_supplier_context(
        self,
        supplier_ids: List[int],
        include_contracts: bool = True
    ) -> List[dict]:
        """
        Get document context for specific suppliers.

        Args:
            supplier_ids: List of supplier IDs to get context for
            include_contracts: Whether to include contract documents

        Returns:
            List of relevant document dicts
        """
        from .models import EmbeddedDocument

        doc_types = ['supplier_profile']
        if include_contracts:
            doc_types.append('contract')

        results = []
        for supplier_id in supplier_ids:
            docs = EmbeddedDocument.objects.filter(
                organization_id=self.organization_id,
                document_type__in=doc_types,
                is_active=True,
                metadata__supplier_id=supplier_id
            )[:3]

            for doc in docs:
                results.append({
                    'id': str(doc.id),
                    'document_type': doc.document_type,
                    'title': doc.title,
                    'content': doc.content[:500],
                    'metadata': doc.metadata,
                })

        return results

    def get_category_context(self, category_ids: List[int]) -> List[dict]:
        """
        Get document context for specific categories.

        Args:
            category_ids: List of category IDs to get context for

        Returns:
            List of relevant document dicts (policies, best practices)
        """
        from .models import EmbeddedDocument

        results = []
        for category_id in category_ids:
            docs = EmbeddedDocument.objects.filter(
                organization_id=self.organization_id,
                document_type__in=['policy', 'best_practice'],
                is_active=True,
                metadata__category_id=category_id
            )[:2]

            for doc in docs:
                results.append({
                    'id': str(doc.id),
                    'document_type': doc.document_type,
                    'title': doc.title,
                    'content': doc.content[:500],
                    'metadata': doc.metadata,
                })

        return results

    def get_historical_insights(
        self,
        insight_type: str = None,
        limit: int = 5
    ) -> List[dict]:
        """
        Get historical successful insights for context.

        Args:
            insight_type: Optional filter by insight type
            limit: Max number of insights to return

        Returns:
            List of historical insight document dicts
        """
        from .models import EmbeddedDocument

        qs = EmbeddedDocument.objects.filter(
            organization_id=self.organization_id,
            document_type='historical_insight',
            is_active=True
        )

        if insight_type:
            qs = qs.filter(metadata__insight_type=insight_type)

        results = []
        for doc in qs.order_by('-updated_at')[:limit]:
            results.append({
                'id': str(doc.id),
                'document_type': doc.document_type,
                'title': doc.title,
                'content': doc.content[:500],
                'metadata': doc.metadata,
            })

        return results

    def get_stats(self) -> dict:
        """Get RAG service statistics."""
        from .models import EmbeddedDocument

        stats = EmbeddedDocument.get_document_stats(self.organization_id)
        stats['pgvector_available'] = self._pgvector_available
        stats['openai_configured'] = self.openai_client is not None

        return stats
