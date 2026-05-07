"""v3.1 Phase 1 (P-H3) — Cross-org FK CHECK trigger for GoodsReceipt.

Migration 0009 installed BEFORE INSERT/UPDATE triggers on the four
``supplier``-bearing tables (transaction, contract, purchaseorder, invoice)
to enforce ``organization_id == supplier.organization_id``. GoodsReceipt
was excluded because it has no direct ``supplier_id`` — but it carries
``purchase_order_id`` and the P2P chain invariant requires GR's org to
match its parent PO's org. Without this trigger, a raw ``.update()`` or
admin shell can silently set ``goodsreceipt.organization = OrgA`` while
``purchase_order.organization = OrgB``, breaking 3-way matching queries
that scope by ``organization``.

Same hardening as 0009: ``SET LOCAL lock_timeout = '5s'`` to bound the
ACCESS EXCLUSIVE wait, ``atomic = False`` so a stuck lock doesn't block
unrelated migrations, and ``CREATE OR REPLACE FUNCTION`` + ``DROP TRIGGER
IF EXISTS`` make forward execution idempotent.

The serializer path (``GoodsReceiptSerializer.validate_purchase_order``)
already enforces this — the trigger is defense-in-depth for shell / raw-
SQL / bulk paths.
"""

from django.db import migrations

TABLE = "procurement_goodsreceipt"
FUNCTION = "procurement_goodsreceipt_check_po_org"
TRIGGER = "procurement_goodsreceipt_check_po_org_trg"


FORWARD_SQL = f"""
    SET LOCAL lock_timeout = '5s';

    CREATE OR REPLACE FUNCTION {FUNCTION}()
    RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.purchase_order_id IS NOT NULL THEN
            PERFORM 1 FROM procurement_purchaseorder
            WHERE id = NEW.purchase_order_id
              AND organization_id = NEW.organization_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION
                    'Cross-org FK violation on {TABLE}: '
                    'organization_id (%) does not match purchase_order.organization_id '
                    'for purchase_order_id (%)',
                    NEW.organization_id, NEW.purchase_order_id
                USING ERRCODE = 'check_violation';
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS {TRIGGER} ON {TABLE};
    CREATE TRIGGER {TRIGGER}
    BEFORE INSERT OR UPDATE ON {TABLE}
    FOR EACH ROW EXECUTE FUNCTION {FUNCTION}();
"""


REVERSE_SQL = f"""
    SET LOCAL lock_timeout = '5s';

    DROP TRIGGER IF EXISTS {TRIGGER} ON {TABLE};
    DROP FUNCTION IF EXISTS {FUNCTION}();
"""


def install_trigger(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cur:
        cur.execute(FORWARD_SQL)


def remove_trigger(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cur:
        cur.execute(REVERSE_SQL)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("procurement", "0011_drop_redundant_indexes"),
    ]

    operations = [
        migrations.RunPython(install_trigger, remove_trigger),
    ]
