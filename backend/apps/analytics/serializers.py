"""
Serializers for analytics API endpoints.
"""
from rest_framework import serializers
from .models import EmbeddedDocument


class EmbeddedDocumentSerializer(serializers.ModelSerializer):
    """Serializer for EmbeddedDocument model."""

    class Meta:
        model = EmbeddedDocument
        fields = [
            'id', 'document_type', 'title', 'content', 'metadata',
            'source_model', 'source_id', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmbeddedDocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for document listings."""

    class Meta:
        model = EmbeddedDocument
        fields = [
            'id', 'document_type', 'title', 'metadata',
            'source_model', 'source_id', 'is_active', 'created_at'
        ]
        read_only_fields = fields


class DocumentIngestionSerializer(serializers.Serializer):
    """Serializer for document ingestion requests."""
    document_type = serializers.ChoiceField(
        choices=['policy', 'contract', 'best_practice'],
        help_text="Type of document to ingest"
    )
    title = serializers.CharField(max_length=255)
    content = serializers.CharField()
    metadata = serializers.JSONField(required=False, default=dict)

    supplier_id = serializers.IntegerField(
        required=False,
        help_text="Required for contract documents"
    )
    category_id = serializers.IntegerField(required=False)
    effective_date = serializers.CharField(required=False, max_length=20)
    contract_start = serializers.CharField(required=False, max_length=20)
    contract_end = serializers.CharField(required=False, max_length=20)
    contract_value = serializers.DecimalField(
        required=False, max_digits=15, decimal_places=2
    )
    source = serializers.CharField(required=False, max_length=255)

    def validate(self, data):
        doc_type = data.get('document_type')
        if doc_type == 'contract' and not data.get('supplier_id'):
            raise serializers.ValidationError({
                'supplier_id': 'Required for contract documents'
            })
        return data


class RAGSearchSerializer(serializers.Serializer):
    """Serializer for RAG search requests."""
    query = serializers.CharField(
        max_length=2000,
        help_text="Search query text"
    )
    document_types = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            'supplier_profile', 'contract', 'policy',
            'best_practice', 'historical_insight'
        ]),
        required=False,
        help_text="Filter by document types"
    )
    top_k = serializers.IntegerField(
        required=False, min_value=1, max_value=20, default=5,
        help_text="Maximum number of results"
    )
    threshold = serializers.FloatField(
        required=False, min_value=0.0, max_value=1.0, default=0.70,
        help_text="Minimum similarity threshold"
    )


class RAGSearchResultSerializer(serializers.Serializer):
    """Serializer for RAG search results."""
    id = serializers.UUIDField()
    title = serializers.CharField()
    content = serializers.CharField()
    document_type = serializers.CharField()
    metadata = serializers.JSONField()
    similarity = serializers.FloatField()


class IngestionResultSerializer(serializers.Serializer):
    """Serializer for ingestion operation results."""
    created = serializers.IntegerField()
    updated = serializers.IntegerField()
    failed = serializers.IntegerField()
    total = serializers.IntegerField()


class DocumentStatsSerializer(serializers.Serializer):
    """Serializer for document statistics."""
    total_documents = serializers.IntegerField()
    active_documents = serializers.IntegerField()
    documents_with_embeddings = serializers.IntegerField()
    by_type = serializers.DictField()
    openai_configured = serializers.BooleanField(required=False)
