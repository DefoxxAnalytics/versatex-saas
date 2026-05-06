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
        DROP TRIGGER IF EXISTS {trigger} ON {table};
        DROP FUNCTION IF EXISTS {function}();
    """


def install_triggers(apps, schema_editor):
    """No-op on non-Postgres backends (e.g., SQLite test DB)."""
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cur:
        for table, function, trigger in TRIGGER_TARGETS:
            cur.execute(_forward_sql(table, function, trigger))


def remove_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cur:
        for table, function, trigger in TRIGGER_TARGETS:
            cur.execute(_reverse_sql(table, function, trigger))


class Migration(migrations.Migration):

    dependencies = [
        ("procurement", "0008_remove_unique_transaction_constraint"),
    ]

    operations = [
        migrations.RunPython(install_triggers, remove_triggers),
    ]
