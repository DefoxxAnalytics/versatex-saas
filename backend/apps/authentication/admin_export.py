"""
Build a ZIP bundle of seeded-org CSVs matching the admin Import CSV templates
and the DataUpload wizard's recognized Transaction headers.

Closes the round-trip opened by:
  - apps.procurement.admin.P2PImportMixin (PR / PO / GR / Invoice)
  - apps.procurement.services.CSVProcessor (Transactions)
"""
import csv
import io
import json
import zipfile

from django.utils import timezone


PR_COLUMNS = [
    'pr_number', 'department', 'cost_center', 'description', 'estimated_amount',
    'currency', 'budget_code', 'status', 'priority', 'created_date',
    'submitted_date', 'approval_date', 'supplier_suggested', 'category',
]
PO_COLUMNS = [
    'po_number', 'supplier_name', 'total_amount', 'currency', 'tax_amount',
    'freight_amount', 'status', 'category', 'created_date', 'approval_date',
    'sent_date', 'required_date', 'promised_date', 'pr_number', 'is_contract_backed',
]
GR_COLUMNS = [
    'gr_number', 'po_number', 'received_date', 'quantity_ordered',
    'quantity_received', 'quantity_accepted', 'amount_received', 'status',
    'inspection_notes',
]
INVOICE_COLUMNS = [
    'invoice_number', 'supplier_name', 'invoice_amount', 'invoice_date', 'due_date',
    'currency', 'tax_amount', 'net_amount', 'payment_terms', 'payment_terms_days',
    'status', 'match_status', 'po_number', 'gr_number', 'received_date',
    'approved_date', 'paid_date', 'has_exception', 'exception_type',
    'exception_amount', 'exception_notes',
]

TRANSACTION_COLUMNS = [
    'date', 'supplier', 'category', 'amount', 'description',
    'subcategory', 'location', 'fiscal_year', 'spend_band', 'payment_method',
    'invoice_number',
]

SUPPLIER_COLUMNS = ['name', 'code', 'contact_email', 'contact_phone', 'address', 'is_active']
CATEGORY_COLUMNS = ['name', 'parent_name', 'description', 'is_active']
CONTRACT_COLUMNS = [
    'contract_number', 'supplier_name', 'title', 'description', 'total_value',
    'annual_value', 'start_date', 'end_date', 'renewal_notice_days', 'status',
    'auto_renew', 'categories',
]
POLICY_COLUMNS = ['name', 'description', 'rules_json', 'is_active']
VIOLATION_COLUMNS = [
    'transaction_uuid', 'policy_name', 'violation_type', 'severity',
    'details_json', 'is_resolved', 'resolution_notes',
]


README_TEMPLATE = """\
Seeded dataset export — {org_name} (slug={slug}, is_demo={is_demo})
Generated: {timestamp}

---

ROUND-TRIP PATHS

Tier A — drop into /admin/procurement/<model>/import/ unchanged:
  purchase_requisitions.csv
  purchase_orders.csv
  goods_receipts.csv
  invoices.csv

Tier B — drop into the DataUpload wizard; headers are recognized without mapping:
  transactions.csv

Tier C — reference only (no importer). Regenerate via seed commands:
  suppliers.csv, categories.csv, contracts.csv,
  spending_policies.csv, policy_violations.csv

REPRODUCE FROM SCRATCH
(This wipes and recreates everything for this slug.)

  python manage.py seed_industry_data \\
      --industry <manufacturing|healthcare|higher-ed> \\
      --org-slug {slug} \\
      --org-name "{org_name}" \\
      --wipe
  python manage.py seed_demo_data \\
      --org {slug} --industry <same> --wipe

ROW COUNTS AT EXPORT
{row_counts}
"""


def _fmt_date(value):
    return value.isoformat() if value else ''


def _fmt_dec(value):
    return str(value) if value is not None else ''


def _fmt_bool(value):
    return 'true' if value else 'false'


def _fmt_json(value):
    if value is None or value == {}:
        return ''
    return json.dumps(value, default=str, sort_keys=True)


def build_org_zip(org):
    """
    Assemble the full seeded-dataset ZIP for one Organization.
    Returns (zip_bytes, row_counts) so the caller can audit-log the export.
    """
    counts = {}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        counts['suppliers'] = _write(zf, org, 'suppliers.csv', SUPPLIER_COLUMNS, _supplier_rows(org))
        counts['categories'] = _write(zf, org, 'categories.csv', CATEGORY_COLUMNS, _category_rows(org))
        counts['transactions'] = _write(zf, org, 'transactions.csv', TRANSACTION_COLUMNS, _transaction_rows(org))
        counts['prs'] = _write(zf, org, 'purchase_requisitions.csv', PR_COLUMNS, _pr_rows(org))
        counts['pos'] = _write(zf, org, 'purchase_orders.csv', PO_COLUMNS, _po_rows(org))
        counts['grs'] = _write(zf, org, 'goods_receipts.csv', GR_COLUMNS, _gr_rows(org))
        counts['invoices'] = _write(zf, org, 'invoices.csv', INVOICE_COLUMNS, _invoice_rows(org))
        counts['contracts'] = _write(zf, org, 'contracts.csv', CONTRACT_COLUMNS, _contract_rows(org))
        counts['policies'] = _write(zf, org, 'spending_policies.csv', POLICY_COLUMNS, _policy_rows(org))
        counts['violations'] = _write(zf, org, 'policy_violations.csv', VIOLATION_COLUMNS, _violation_rows(org))
        zf.writestr(
            f'{org.slug}/README.txt',
            README_TEMPLATE.format(
                org_name=org.name,
                slug=org.slug,
                is_demo=org.is_demo,
                timestamp=timezone.now().isoformat(),
                row_counts='\n'.join(f'  {k}: {v:,}' for k, v in counts.items()),
            ),
        )
    return buf.getvalue(), counts


def _write(zf, org, filename, columns, row_iter):
    text_buf = io.StringIO()
    writer = csv.DictWriter(text_buf, fieldnames=columns, extrasaction='ignore')
    writer.writeheader()
    count = 0
    for row in row_iter:
        writer.writerow(row)
        count += 1
    zf.writestr(f'{org.slug}/{filename}', text_buf.getvalue())
    return count


def _supplier_rows(org):
    for s in org.suppliers.all().order_by('name'):
        yield {
            'name': s.name,
            'code': s.code or '',
            'contact_email': s.contact_email or '',
            'contact_phone': s.contact_phone or '',
            'address': s.address or '',
            'is_active': _fmt_bool(s.is_active),
        }


def _category_rows(org):
    for c in org.categories.select_related('parent').all().order_by('name'):
        yield {
            'name': c.name,
            'parent_name': c.parent.name if c.parent_id else '',
            'description': c.description or '',
            'is_active': _fmt_bool(c.is_active),
        }


def _transaction_rows(org):
    qs = org.transactions.select_related('supplier', 'category').all().order_by('date', 'id')
    for t in qs.iterator(chunk_size=2000):
        yield {
            'date': _fmt_date(t.date),
            'supplier': t.supplier.name if t.supplier_id else '',
            'category': t.category.name if t.category_id else '',
            'amount': _fmt_dec(t.amount),
            'description': t.description or '',
            'subcategory': t.subcategory or '',
            'location': t.location or '',
            'fiscal_year': t.fiscal_year if t.fiscal_year is not None else '',
            'spend_band': t.spend_band or '',
            'payment_method': t.payment_method or '',
            'invoice_number': t.invoice_number or '',
        }


def _pr_rows(org):
    qs = org.purchase_requisitions.select_related('supplier_suggested', 'category').all().order_by('pr_number')
    for pr in qs:
        yield {
            'pr_number': pr.pr_number,
            'department': pr.department or '',
            'cost_center': pr.cost_center or '',
            'description': pr.description or '',
            'estimated_amount': _fmt_dec(pr.estimated_amount),
            'currency': pr.currency or '',
            'budget_code': pr.budget_code or '',
            'status': pr.status,
            'priority': pr.priority or '',
            'created_date': _fmt_date(pr.created_date),
            'submitted_date': _fmt_date(pr.submitted_date),
            'approval_date': _fmt_date(pr.approval_date),
            'supplier_suggested': pr.supplier_suggested.name if pr.supplier_suggested_id else '',
            'category': pr.category.name if pr.category_id else '',
        }


def _po_rows(org):
    qs = org.purchase_orders.select_related('supplier', 'category', 'requisition').all().order_by('po_number')
    for po in qs:
        yield {
            'po_number': po.po_number,
            'supplier_name': po.supplier.name if po.supplier_id else '',
            'total_amount': _fmt_dec(po.total_amount),
            'currency': po.currency or '',
            'tax_amount': _fmt_dec(po.tax_amount),
            'freight_amount': _fmt_dec(po.freight_amount),
            'status': po.status,
            'category': po.category.name if po.category_id else '',
            'created_date': _fmt_date(po.created_date),
            'approval_date': _fmt_date(po.approval_date),
            'sent_date': _fmt_date(po.sent_date),
            'required_date': _fmt_date(po.required_date),
            'promised_date': _fmt_date(po.promised_date),
            'pr_number': po.requisition.pr_number if po.requisition_id else '',
            'is_contract_backed': _fmt_bool(po.is_contract_backed),
        }


def _gr_rows(org):
    qs = org.goods_receipts.select_related('purchase_order').all().order_by('gr_number')
    for gr in qs:
        yield {
            'gr_number': gr.gr_number,
            'po_number': gr.purchase_order.po_number if gr.purchase_order_id else '',
            'received_date': _fmt_date(gr.received_date),
            'quantity_ordered': _fmt_dec(gr.quantity_ordered),
            'quantity_received': _fmt_dec(gr.quantity_received),
            'quantity_accepted': _fmt_dec(gr.quantity_accepted),
            'amount_received': _fmt_dec(gr.amount_received),
            'status': gr.status,
            'inspection_notes': gr.inspection_notes or '',
        }


def _invoice_rows(org):
    qs = org.invoices.select_related('supplier', 'purchase_order', 'goods_receipt').all().order_by('invoice_number')
    for inv in qs:
        yield {
            'invoice_number': inv.invoice_number,
            'supplier_name': inv.supplier.name if inv.supplier_id else '',
            'invoice_amount': _fmt_dec(inv.invoice_amount),
            'invoice_date': _fmt_date(inv.invoice_date),
            'due_date': _fmt_date(inv.due_date),
            'currency': inv.currency or '',
            'tax_amount': _fmt_dec(inv.tax_amount),
            'net_amount': _fmt_dec(inv.net_amount),
            'payment_terms': inv.payment_terms or '',
            'payment_terms_days': inv.payment_terms_days if inv.payment_terms_days is not None else '',
            'status': inv.status,
            'match_status': inv.match_status or '',
            'po_number': inv.purchase_order.po_number if inv.purchase_order_id else '',
            'gr_number': inv.goods_receipt.gr_number if inv.goods_receipt_id else '',
            'received_date': _fmt_date(inv.received_date),
            'approved_date': _fmt_date(inv.approved_date),
            'paid_date': _fmt_date(inv.paid_date),
            'has_exception': _fmt_bool(inv.has_exception),
            'exception_type': inv.exception_type or '',
            'exception_amount': _fmt_dec(inv.exception_amount),
            'exception_notes': inv.exception_notes or '',
        }


def _contract_rows(org):
    qs = org.contracts.select_related('supplier').prefetch_related('categories').all().order_by('contract_number')
    for c in qs:
        yield {
            'contract_number': c.contract_number,
            'supplier_name': c.supplier.name if c.supplier_id else '',
            'title': c.title or '',
            'description': c.description or '',
            'total_value': _fmt_dec(c.total_value),
            'annual_value': _fmt_dec(c.annual_value),
            'start_date': _fmt_date(c.start_date),
            'end_date': _fmt_date(c.end_date),
            'renewal_notice_days': c.renewal_notice_days if c.renewal_notice_days is not None else '',
            'status': c.status,
            'auto_renew': _fmt_bool(c.auto_renew),
            'categories': '; '.join(cat.name for cat in c.categories.all()),
        }


def _policy_rows(org):
    for p in org.spending_policies.all().order_by('name'):
        yield {
            'name': p.name,
            'description': p.description or '',
            'rules_json': _fmt_json(p.rules),
            'is_active': _fmt_bool(p.is_active),
        }


def _violation_rows(org):
    qs = org.policy_violations.select_related('transaction', 'policy').all().order_by('created_at')
    for v in qs:
        yield {
            'transaction_uuid': str(v.transaction.uuid) if v.transaction_id else '',
            'policy_name': v.policy.name if v.policy_id else '',
            'violation_type': v.violation_type or '',
            'severity': v.severity or '',
            'details_json': _fmt_json(v.details),
            'is_resolved': _fmt_bool(v.is_resolved),
            'resolution_notes': v.resolution_notes or '',
        }
