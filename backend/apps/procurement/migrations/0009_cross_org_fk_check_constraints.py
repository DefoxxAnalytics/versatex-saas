"""Finding C3 - Cross-org FK CHECK constraints via Postgres triggers.

Postgres CHECK constraints cannot subquery another table, so a column-level
CHECK can't enforce ``model.organization_id == supplier.organization_id``.
Instead, install BEFORE INSERT/UPDATE triggers that raise on mismatch. This
defends against any path that bypasses the serializer (admin shell, raw SQL,
bulk imports, ORM ``.update()``).

The trigger fires only when ``supplier_id IS NOT NULL`` so legacy nullable
suppliers (none of these models allow null today, but defensive) and pure
non-supplier UPDATEs are unaffected. Existing rows are *not* validated at
trigger creation time -- DB-level retroactive validation would block the
migration on any historical drift; an audit query is the right tool for
backfill detection and is intentionally out of scope here.

The forward/reverse SQL is gated to Postgres via ``RunPython``. SQLite (used
in ``settings_test``) lacks PL/pgSQL, so the migration is a no-op there and
the matching tests are skipped on non-Postgres backends.

Concurrency hardening (v3.0 Phase 1):

CREATE TRIGGER takes ACCESS EXCLUSIVE on the target table. On a busy
production database, an in-flight long-running query or Celery task holding
even a weaker lock on ``procurement_transaction`` / ``_invoice`` /
``_purchaseorder`` / ``_contract`` will block the migration indefinitely.

Two safeguards:

1. ``SET LOCAL lock_timeout = '5s'`` is issued before each trigger CREATE
   block. If the lock can't be acquired within 5 seconds, Postgres raises
   ``LockNotAvailable`` and the migration aborts cleanly.
2. ``atomic = False`` so each table's trigger creation runs in its own
   transaction. A stuck lock on one table no longer holds up the others;
   the operator can re-run the migration after the contending transaction
   releases its lock and Django will skip the already-installed triggers
   (``CREATE OR REPLACE FUNCTION`` + ``DROP TRIGGER IF EXISTS`` make
   forward execution idempotent).

Deploy during a low-traffic window. If trigger creation times out, retry
the migration after the contending transaction releases its lock.
"""
from django.db import migrations


# (table_name, function_name, trigger_name) for the four supplier FKs
# flagged in Finding C3. Each table owns ``organization_id`` and
# ``supplier_id`` columns by Django convention.
TRIGGER_TARGETS = [
    (
        "procurement_transaction",
        "procurement_transaction_check_supplier_org",
        "procurement_transaction_check_supplier_org_trg",
    ),
    (
        "procurement_contract",
        "procurement_contract_check_supplier_org",
        "procurement_contract_check_supplier_org_trg",
    ),
    (
        "procurement_purchaseorder",
        "procurement_purchaseorder_check_supplier_org",
        "procurement_purchaseorder_check_supplier_org_trg",
    ),
    (
        "procurement_invoice",
        "procurement_invoice_check_supplier_org",
        "procurement_invoice_check_supplier_org_trg",
    ),
]


def _forward_sql(table, function, trigger):
    return f"""
        SET LOCAL lock_timeout = '5s';

        CREATE OR REPLACE FUNCTION {function}()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.supplier_id IS NOT NULL THEN
                PERFORM 1 FROM procurement_supplier
                WHERE id = NEW.supplier_id
                  AND organization_id = NEW.organization_id;
                IF NOT FOUND THEN
                    RAISE EXCEPTION
                        'Cross-org FK violation on {table}: '
                        'organization_id (%) does not match supplier.organization_id '
                        'for supplier_id (%)',
                        NEW.organization_id, NEW.supplier_id
                    USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS {trigger} ON {table};
        CREATE TRIGGER {trigger}
        BEFORE INSERT OR UPDATE ON {table}
        FOR EACH ROW EXECUTE FUNCTION {function}();
    """


def _reverse_sql(table, function, trigger):
    return f"""
        SET LOCAL lock_timeout = '5s';

        DROP TRIGGER IF EXISTS {trigger} ON {table};
        DROP FUNCTION IF EXISTS {function}();
    """


def install_triggers(apps, schema_editor):
    """No-op on non-Postgres backends (e.g., SQLite test DB).

    Each table's trigger is created in its own transaction (atomic=False on
    the Migration class), with ``SET LOCAL lock_timeout = '5s'`` to bound
    the wait for ACCESS EXCLUSIVE.
    """
    if schema_editor.connection.vendor != "postgresql":
        return
    for table, function, trigger in TRIGGER_TARGETS:
        with schema_editor.connection.cursor() as cur:
            cur.execute(_forward_sql(table, function, trigger))


def remove_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table, function, trigger in TRIGGER_TARGETS:
        with schema_editor.connection.cursor() as cur:
            cur.execute(_reverse_sql(table, function, trigger))


class Migration(migrations.Migration):
    # Each table's trigger creation runs in its own transaction so a stuck
    # lock on one table (e.g., a long-running query on procurement_transaction)
    # does not block trigger installation on the other three tables. Combined
    # with SET LOCAL lock_timeout='5s' inside each block, failed acquisitions
    # abort cleanly with LockNotAvailable and can be retried.
    atomic = False

    dependencies = [
        ("procurement", "0008_remove_unique_transaction_constraint"),
    ]

    operations = [
        migrations.RunPython(install_triggers, remove_triggers),
    ]
