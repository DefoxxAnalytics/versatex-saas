"""
Add pgvector IVFFlat indexes on SemanticCache.query_embedding and
EmbeddedDocument.content_embedding.

Without this, every similarity lookup does a sequential scan — tolerable at
<1K rows, catastrophic at ~20K+ (gunicorn timeouts under concurrent load).

Postgres-only migration: the IVFFlat operator requires the pgvector extension
and is not available in SQLite, which backs the pytest test settings. We use
RunPython with a vendor guard so SQLite-backed tests skip cleanly and only
Postgres deployments get the indexes.

`lists` is env-tunable via PGVECTOR_IVFFLAT_LISTS. Postgres docs recommend
lists ≈ sqrt(rows). Default 100 is right around the 10K-row crossover point.
At launch (<1K vectors) 100 is higher than optimal — queries scan more
partitions than necessary — but the overhead is small and avoids a re-index
later. Tune post-launch if pg_stat_user_indexes shows low hit ratio.

The indexes are intentionally NOT declared on the model's Meta.indexes because
the model classes only add the vector field conditionally (see
apps/analytics/models.py:370 and :554 — guarded by `if PGVECTOR_AVAILABLE`).
Keeping the index in a raw migration decouples index management from the
conditional-field setup and avoids `makemigrations` noise when devs run
without pgvector installed.
"""
import os

from django.db import migrations


def _lists():
    """PGVECTOR_IVFFLAT_LISTS env (int), default 100."""
    raw = os.environ.get('PGVECTOR_IVFFLAT_LISTS', '100')
    try:
        value = int(raw)
    except ValueError:
        return 100
    return value if value > 0 else 100


def add_vector_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    lists = _lists()
    schema_editor.execute(
        f"CREATE INDEX IF NOT EXISTS analytics_semanticcache_query_embedding_ivfflat "
        f"ON analytics_semanticcache USING ivfflat (query_embedding vector_cosine_ops) "
        f"WITH (lists = {lists})"
    )
    schema_editor.execute(
        f"CREATE INDEX IF NOT EXISTS analytics_embeddeddocument_content_embedding_ivfflat "
        f"ON analytics_embeddeddocument USING ivfflat (content_embedding vector_cosine_ops) "
        f"WITH (lists = {lists})"
    )


def remove_vector_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute(
        "DROP INDEX IF EXISTS analytics_semanticcache_query_embedding_ivfflat"
    )
    schema_editor.execute(
        "DROP INDEX IF EXISTS analytics_embeddeddocument_content_embedding_ivfflat"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0005_embeddeddocument'),
    ]

    operations = [
        migrations.RunPython(
            code=add_vector_indexes,
            reverse_code=remove_vector_indexes,
            elidable=False,
        ),
    ]
