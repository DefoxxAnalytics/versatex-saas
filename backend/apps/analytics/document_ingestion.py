"""
Document Ingestion Pipeline for RAG.

Provides automated ingestion of documents from various sources into
the EmbeddedDocument model for RAG-enhanced AI insights:
- Supplier profiles from Supplier model
- Historical successful insights from InsightFeedback model
- Manual ingestion for policies, contracts, best practices

Uses OpenAI text-embedding-3-small for generating embeddings.
"""
import logging
from typing import Optional, List, TYPE_CHECKING

from django.conf import settings
from django.db import transaction

if TYPE_CHECKING:
    from .models import EmbeddedDocument

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """
    Ingests documents from various sources into EmbeddedDocument.

    Features:
    - Automatic embedding generation
    - Deduplication via content hashing
    - Source tracking for updates
    - Batch processing for efficiency
    """

    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536
    MAX_CONTENT_LENGTH = 8000
    BATCH_SIZE = 10

    def __init__(self, organization_id: int, openai_api_key: str = None):
        """
        Initialize the ingestion service.

        Args:
            organization_id: Organization to ingest documents for
            openai_api_key: OpenAI API key for embeddings
        """
        self.organization_id = organization_id
        self.openai_api_key = openai_api_key or getattr(
            settings, 'OPENAI_API_KEY', None
        )
        self._openai_client = None

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
        """Generate embedding for text."""
        if not self.openai_client:
            return None

        try:
            truncated = text[:self.MAX_CONTENT_LENGTH]

            response = self.openai_client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=truncated,
                dimensions=self.EMBEDDING_DIMENSIONS
            )

            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    def _get_batch_embeddings(self, texts: List[str]) -> List[Optional[list]]:
        """Generate embeddings for multiple texts in a batch."""
        if not self.openai_client or not texts:
            return [None] * len(texts)

        try:
            truncated = [t[:self.MAX_CONTENT_LENGTH] for t in texts]

            response = self.openai_client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=truncated,
                dimensions=self.EMBEDDING_DIMENSIONS
            )

            return [item.embedding for item in response.data]

        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            return [None] * len(texts)

    def ingest_supplier_profiles(self, supplier_ids: List[int] = None) -> dict:
        """
        Ingest supplier profiles into EmbeddedDocument.

        Creates or updates documents for each supplier with their
        profile information for RAG context.

        Args:
            supplier_ids: Optional list of specific supplier IDs to ingest.
                         If None, ingests all suppliers for the organization.

        Returns:
            Dict with counts of created, updated, and failed documents
        """
        from apps.procurement.models import Supplier
        from .models import EmbeddedDocument

        qs = Supplier.objects.filter(
            organization_id=self.organization_id,
            is_active=True
        )

        if supplier_ids:
            qs = qs.filter(id__in=supplier_ids)

        suppliers = list(qs)
        created = 0
        updated = 0
        failed = 0

        for i in range(0, len(suppliers), self.BATCH_SIZE):
            batch = suppliers[i:i + self.BATCH_SIZE]
            contents = [self._build_supplier_content(s) for s in batch]
            embeddings = self._get_batch_embeddings(contents)

            for supplier, content, embedding in zip(batch, contents, embeddings):
                try:
                    existing = EmbeddedDocument.objects.filter(
                        organization_id=self.organization_id,
                        source_model='Supplier',
                        source_id=str(supplier.id)
                    ).first()

                    doc = EmbeddedDocument.create_or_update(
                        organization_id=self.organization_id,
                        document_type='supplier_profile',
                        title=f"Supplier Profile: {supplier.name}",
                        content=content,
                        embedding=embedding,
                        metadata={
                            'supplier_id': supplier.id,
                            'supplier_name': supplier.name,
                            'supplier_code': supplier.code,
                        },
                        source_model='Supplier',
                        source_id=str(supplier.id)
                    )

                    if existing:
                        updated += 1
                    else:
                        created += 1

                except Exception as e:
                    logger.error(f"Failed to ingest supplier {supplier.id}: {e}")
                    failed += 1

        logger.info(
            f"Supplier ingestion complete: {created} created, "
            f"{updated} updated, {failed} failed"
        )

        return {
            'created': created,
            'updated': updated,
            'failed': failed,
            'total': len(suppliers),
        }

    def _build_supplier_content(self, supplier) -> str:
        """Build searchable content from supplier data."""
        from apps.procurement.models import Transaction
        from django.db.models import Sum, Count, Avg

        stats = Transaction.objects.filter(
            supplier=supplier
        ).aggregate(
            total_spend=Sum('amount'),
            transaction_count=Count('id'),
            avg_transaction=Avg('amount')
        )

        content = f"""SUPPLIER PROFILE: {supplier.name}

Supplier Code: {supplier.code or 'N/A'}
Contact Email: {supplier.contact_email or 'N/A'}
Contact Phone: {supplier.contact_phone or 'N/A'}
Address: {supplier.address or 'N/A'}
Status: {'Active' if supplier.is_active else 'Inactive'}

SPENDING STATISTICS:
Total Historical Spend: ${stats['total_spend'] or 0:,.2f}
Transaction Count: {stats['transaction_count'] or 0}
Average Transaction: ${stats['avg_transaction'] or 0:,.2f}

Created: {supplier.created_at.strftime('%Y-%m-%d')}
Last Updated: {supplier.updated_at.strftime('%Y-%m-%d')}"""

        return content

    def ingest_historical_insights(
        self,
        outcomes: List[str] = None,
        limit: int = 100
    ) -> dict:
        """
        Ingest successful historical insights into EmbeddedDocument.

        Args:
            outcomes: Filter by outcome types. Default: ['success', 'partial_success']
            limit: Max number of insights to ingest

        Returns:
            Dict with counts of created, updated, and failed documents
        """
        from .models import InsightFeedback, EmbeddedDocument

        outcomes = outcomes or ['success', 'partial_success']

        feedbacks = InsightFeedback.objects.filter(
            organization_id=self.organization_id,
            outcome__in=outcomes
        ).order_by('-action_date')[:limit]

        feedbacks = list(feedbacks)
        created = 0
        updated = 0
        failed = 0

        for i in range(0, len(feedbacks), self.BATCH_SIZE):
            batch = feedbacks[i:i + self.BATCH_SIZE]
            contents = [self._build_insight_content(f) for f in batch]
            embeddings = self._get_batch_embeddings(contents)

            for feedback, content, embedding in zip(batch, contents, embeddings):
                try:
                    existing = EmbeddedDocument.objects.filter(
                        organization_id=self.organization_id,
                        source_model='InsightFeedback',
                        source_id=str(feedback.id)
                    ).first()

                    doc = EmbeddedDocument.create_or_update(
                        organization_id=self.organization_id,
                        document_type='historical_insight',
                        title=f"Historical Insight: {feedback.insight_title[:100]}",
                        content=content,
                        embedding=embedding,
                        metadata={
                            'insight_id': feedback.insight_id,
                            'insight_type': feedback.insight_type,
                            'action_taken': feedback.action_taken,
                            'outcome': feedback.outcome,
                            'predicted_savings': float(feedback.predicted_savings or 0),
                            'actual_savings': float(feedback.actual_savings or 0),
                        },
                        source_model='InsightFeedback',
                        source_id=str(feedback.id)
                    )

                    if existing:
                        updated += 1
                    else:
                        created += 1

                except Exception as e:
                    logger.error(f"Failed to ingest insight {feedback.id}: {e}")
                    failed += 1

        logger.info(
            f"Historical insight ingestion complete: {created} created, "
            f"{updated} updated, {failed} failed"
        )

        return {
            'created': created,
            'updated': updated,
            'failed': failed,
            'total': len(feedbacks),
        }

    def _build_insight_content(self, feedback) -> str:
        """Build searchable content from insight feedback."""
        content = f"""HISTORICAL INSIGHT: {feedback.insight_title}

Type: {feedback.insight_type}
Severity: {feedback.insight_severity}

ACTION TAKEN: {feedback.get_action_taken_display()}
Action Date: {feedback.action_date.strftime('%Y-%m-%d')}
Action Notes: {feedback.action_notes or 'N/A'}

OUTCOME: {feedback.get_outcome_display()}
Predicted Savings: ${feedback.predicted_savings or 0:,.2f}
Actual Savings: ${feedback.actual_savings or 0:,.2f}
Outcome Notes: {feedback.outcome_notes or 'N/A'}

This insight was successfully implemented and achieved
{'the expected' if feedback.outcome == 'success' else 'partial'} savings."""

        return content

    def ingest_manual_document(
        self,
        document_type: str,
        title: str,
        content: str,
        metadata: dict = None
    ) -> 'EmbeddedDocument':
        """
        Manually ingest a document (policy, contract, best practice).

        Args:
            document_type: Type of document (policy, contract, best_practice)
            title: Document title
            content: Document content
            metadata: Optional metadata dict

        Returns:
            Created EmbeddedDocument instance
        """
        from .models import EmbeddedDocument

        embedding = self._get_embedding(content)

        doc = EmbeddedDocument.create_or_update(
            organization_id=self.organization_id,
            document_type=document_type,
            title=title,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
        )

        logger.info(f"Ingested manual document: {title}")
        return doc

    def ingest_policy(
        self,
        title: str,
        content: str,
        category_id: int = None,
        effective_date: str = None
    ) -> 'EmbeddedDocument':
        """
        Ingest a procurement policy document.

        Args:
            title: Policy title
            content: Policy content
            category_id: Optional category this policy applies to
            effective_date: Optional effective date string

        Returns:
            Created EmbeddedDocument instance
        """
        metadata = {}
        if category_id:
            metadata['category_id'] = category_id
        if effective_date:
            metadata['effective_date'] = effective_date

        return self.ingest_manual_document(
            document_type='policy',
            title=title,
            content=content,
            metadata=metadata
        )

    def ingest_contract_summary(
        self,
        supplier_id: int,
        title: str,
        content: str,
        contract_start: str = None,
        contract_end: str = None,
        contract_value: float = None
    ) -> 'EmbeddedDocument':
        """
        Ingest a contract summary document.

        Args:
            supplier_id: Supplier this contract is with
            title: Contract title/name
            content: Contract summary content
            contract_start: Optional start date string
            contract_end: Optional end date string
            contract_value: Optional total contract value

        Returns:
            Created EmbeddedDocument instance
        """
        metadata = {
            'supplier_id': supplier_id,
        }
        if contract_start:
            metadata['contract_start'] = contract_start
        if contract_end:
            metadata['contract_end'] = contract_end
        if contract_value:
            metadata['contract_value'] = contract_value

        return self.ingest_manual_document(
            document_type='contract',
            title=title,
            content=content,
            metadata=metadata
        )

    def ingest_best_practice(
        self,
        title: str,
        content: str,
        category_id: int = None,
        source: str = None
    ) -> 'EmbeddedDocument':
        """
        Ingest a best practice document.

        Args:
            title: Best practice title
            content: Best practice content
            category_id: Optional category this applies to
            source: Optional source attribution

        Returns:
            Created EmbeddedDocument instance
        """
        metadata = {}
        if category_id:
            metadata['category_id'] = category_id
        if source:
            metadata['source'] = source

        return self.ingest_manual_document(
            document_type='best_practice',
            title=title,
            content=content,
            metadata=metadata
        )

    @transaction.atomic
    def refresh_all(self) -> dict:
        """
        Refresh all automatically generated documents.

        Re-ingests supplier profiles and historical insights.
        Manual documents (policies, contracts) are not affected.

        Returns:
            Dict with results from each ingestion type
        """
        results = {
            'suppliers': self.ingest_supplier_profiles(),
            'historical_insights': self.ingest_historical_insights(),
        }

        logger.info(f"Full RAG document refresh complete for org {self.organization_id}")
        return results

    def cleanup_orphaned(self) -> int:
        """
        Remove documents whose source objects no longer exist.

        Returns:
            Number of documents deleted
        """
        from apps.procurement.models import Supplier
        from .models import InsightFeedback, EmbeddedDocument

        deleted = 0

        supplier_docs = EmbeddedDocument.objects.filter(
            organization_id=self.organization_id,
            source_model='Supplier'
        )
        for doc in supplier_docs:
            if not Supplier.objects.filter(id=doc.source_id).exists():
                doc.delete()
                deleted += 1

        insight_docs = EmbeddedDocument.objects.filter(
            organization_id=self.organization_id,
            source_model='InsightFeedback'
        )
        for doc in insight_docs:
            if not InsightFeedback.objects.filter(id=doc.source_id).exists():
                doc.delete()
                deleted += 1

        logger.info(f"Cleaned up {deleted} orphaned documents")
        return deleted

    def get_stats(self) -> dict:
        """Get ingestion statistics."""
        from .models import EmbeddedDocument

        stats = EmbeddedDocument.get_document_stats(self.organization_id)
        stats['openai_configured'] = self.openai_client is not None

        return stats
