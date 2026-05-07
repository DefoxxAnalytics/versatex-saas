"""Finding B12: vector-search failure must fall back to keyword search
with the ORIGINAL query, not the literal string 'fallback'.

When `RAGService._vector_search` raises (or vector search otherwise fails),
the recovery path must invoke `_keyword_search(query, ...)` so the user's
actual question still drives retrieval. The previous code passed the
literal string "fallback", which made keyword search look for documents
containing the word "fallback" -- silent degradation, noise into LLM
context.
"""

from unittest.mock import patch

from django.test import TestCase

from apps.analytics.rag_service import RAGService


class TestRAGVectorFallback(TestCase):
    """Vector-search failure must preserve the original query through fallback."""

    ORIGINAL_QUERY = "What is the supplier with highest spend?"

    def _make_service(self):
        """Build a RAGService bypassing pgvector + OpenAI checks."""
        service = RAGService.__new__(RAGService)
        service.organization_id = 1
        service.openai_api_key = "sk-test"
        service._openai_client = object()
        service._pgvector_available = True
        return service

    def test_vector_failure_falls_back_with_original_query(self):
        service = self._make_service()

        with (
            patch.object(service, "_get_embedding") as mock_embed,
            patch.object(service, "_vector_search") as mock_vec,
            patch.object(service, "_keyword_search") as mock_kw,
        ):
            mock_embed.return_value = [0.1] * 1536
            mock_vec.side_effect = RuntimeError("vector backend unavailable")
            mock_kw.return_value = []

            service.search(
                query=self.ORIGINAL_QUERY,
                doc_types=None,
                top_k=5,
            )

        mock_kw.assert_called_once()
        call_args = mock_kw.call_args
        first_positional = (
            call_args.args[0] if call_args.args else call_args.kwargs.get("query")
        )
        self.assertEqual(
            first_positional,
            self.ORIGINAL_QUERY,
            f"Fallback called with {first_positional!r} instead of the "
            f"original query.",
        )
        self.assertNotEqual(
            first_positional,
            "fallback",
            "Fallback called with literal 'fallback' string -- Finding B12.",
        )
