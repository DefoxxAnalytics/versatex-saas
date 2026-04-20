# Demo Data Seeding

Versatex Analytics ships with two management commands that generate realistic, industry-specific demo data end-to-end — from transactions up through P2P, contracts, and policy violations. Use these to stand up demo environments quickly or to repopulate empty dashboards after a data wipe.

## Commands at a Glance

| Command | Purpose |
|---------|---------|
| `seed_industry_data` | Creates/renames an organization and populates the base layer (Categories, Suppliers, Transactions) using an industry profile |
| `seed_demo_data` | Adds the P2P layer (Contracts, Policies, Violations, PRs, POs, GRs, Invoices) on top of an existing org |

Both commands are idempotent via `--wipe` and deterministic via `--seed`.

## Supported Industry Profiles

| Profile | Default Org Name | Characteristics |
|---------|------------------|-----------------|
| `healthcare` | Mercy Regional Medical Center | 15 categories (Pharma, Med/Surg, Implants, Imaging, Lab...), real-world vendors (GE Healthcare, Philips, Siemens Healthineers, Cardinal Health, McKesson), flu-season seasonality, 340B and GPO policies |
| `higher-ed` | Pacific State University | 16 categories (Research Lab, Library, Facilities, Athletics...), real-world vendors (Turner Construction, Skanska, Thermo Fisher, Elsevier), fiscal-year + semester seasonality, NSF/NIH grant compliance policies |
| `manufacturing` | Apex Manufacturing Co. (profile default) / Bolt & Nuts Manufacturing (slug `eaton` in this deployment) | 15 categories (Raw Materials, Components & Parts, MRO Supplies, Industrial Equipment, Tooling & Dies, Contract Manufacturing...), real-world vendors (DMG Mori, Haas Automation, Makino, Fanuc Robotics, Rockwell Automation, Nucor, Fastenal, Grainger, Jabil, Flex), July-shutdown + December-capex seasonality, PPAP/ISO 9001 + conflict minerals + capital authorization policies |

Every org created or updated by these commands gets `is_demo=True` automatically — the flag drives the amber "Demo" chip in the frontend OrganizationSwitcher and gates the admin "Export seeded dataset as ZIP" action.

Profile data lives in [backend/apps/procurement/management/commands/_industry_profiles.py](../backend/apps/procurement/management/commands/_industry_profiles.py). Each profile specifies:

- Category list with `spend_share` and log-normal amount distribution (`amount_mu`, `amount_sigma`)
- Named suppliers per category (real industry vendors)
- Tail supplier templates for synthetic regional vendors
- Monthly seasonality multipliers (12-element array)
- Industry-specific departments, cost-center prefix, payment terms, and spending policies

## Quick Start

### Seed a Healthcare org
```bash
docker-compose exec backend python manage.py seed_industry_data \
  --industry healthcare --org-slug uch --wipe

docker-compose exec backend python manage.py seed_demo_data \
  --org uch --industry healthcare --wipe
```

### Seed a Higher-Ed org
```bash
docker-compose exec backend python manage.py seed_industry_data \
  --industry higher-ed --org-slug tsu --wipe

docker-compose exec backend python manage.py seed_demo_data \
  --org tsu --industry higher-ed --wipe
```

### Seed a Manufacturing org

Against the profile default slug:

```bash
docker-compose exec backend python manage.py seed_industry_data \
  --industry manufacturing --org-slug apex-mfg --wipe

docker-compose exec backend python manage.py seed_demo_data \
  --org apex-mfg --industry manufacturing --wipe
```

Against the `eaton` slug (Bolt & Nuts Manufacturing) — pass `--org-name` so the display name survives re-seeds:

```bash
docker-compose exec backend python manage.py seed_industry_data \
  --industry manufacturing --org-slug eaton --org-name "Bolt & Nuts Manufacturing" --wipe

docker-compose exec backend python manage.py seed_demo_data \
  --org eaton --industry manufacturing --wipe
```

### Seed an existing org with generic defaults

If you already have an org with base transaction data (e.g., uploaded via CSV) and just want the P2P/contract/policy layer, run `seed_demo_data` without `--industry`:

```bash
docker-compose exec backend python manage.py seed_demo_data \
  --org <slug> --wipe
```

Note: running `seed_demo_data` against any slug flips `is_demo=True` on the target org (the command treats anything it touches as demo data).

## Command Reference

### `seed_industry_data`

Creates/updates an organization, wipes its existing procurement data if requested, and populates Categories, Suppliers, and Transactions using an industry profile.

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--industry` | Yes | — | `healthcare`, `higher-ed`, or `manufacturing` |
| `--org-slug` | Yes | — | Target organization slug (created if missing) |
| `--org-name` | No | profile default | Override display name for the organization |
| `--wipe` | No | false | Delete ALL procurement data for the org before seeding (transactions, suppliers, categories, P2P, contracts, policies, violations) |
| `--seed` | No | 42 | Random seed for reproducibility |
| `--transactions` | No | 25000 | Target transaction count |
| `--start-year` | No | 2022 | First calendar year for transaction dates |
| `--end-date` | No | today | Last transaction date (`YYYY-MM-DD`) |

**What it creates:**
- Organization (or updates name if `--org-name` provided)
- 15-16 categories from the profile
- ~500-600 suppliers (100+ named industry vendors + ~475 synthetic tail)
- 25,000 transactions with:
  - Log-normal amount distribution per category (matches real spend patterns — small consumables vs large capital)
  - Supplier weighting (75% to named top-tier, 25% to tail)
  - Monthly seasonality matching the industry

### `seed_demo_data`

Adds the P2P layer on top of an existing org that already has Categories, Suppliers, and Transactions.

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--org` | Yes | — | Organization slug (must exist with base data) |
| `--wipe` | No | false | Delete existing P2P/Contract/Policy data before seeding |
| `--seed` | No | 42 | Random seed for reproducibility |
| `--industry` | No | — | `healthcare`, `higher-ed`, or `manufacturing` — swaps in industry-specific departments, cost-center prefix, payment terms, and policies. Omit for generic defaults. |

**What it creates:**
| Entity | Count | Story |
|--------|-------|-------|
| Contracts | 80 | Linked to top-spend suppliers; 70% active / 15% expiring / 15% expired |
| Spending Policies | 4 | Industry-specific (340B, GPO, capital approval, etc.) |
| Policy Violations | 150 | Linked to high-value transactions; severity-weighted; 25% resolved |
| Purchase Requisitions | 500 | Status mix, ~60% conversion to PO, ~7% rejection |
| Purchase Orders | 400 | ~40% contract-backed, 22% amendment rate |
| Goods Receipts | ~275 | 80% accepted, 12% partial, mix of variance/rejection |
| Invoices | ~275 | 55% 3-way matched, 20% exceptions, aging buckets distributed |

**Date chain:** PR created → approved → PO created → PO sent → GR received (7-45 days later) → Invoice issued (0-14 days after GR) → Due date per payment terms → Paid date when matched and current-bucket.

## Numbering Conventions

All generated documents use org-scoped, year-qualified numbers so demos look professional:

| Type | Format | Example |
|------|--------|---------|
| Contract | `CT-{ORG}-{YYYY}-{NNNN}` | `CT-UCH-2024-0042` |
| Purchase Requisition | `PR-{ORG}-{YYYY}-{NNNNN}` | `PR-UCH-2024-00157` |
| Purchase Order | `PO-{ORG}-{YYYY}-{NNNNN}` | `PO-UCH-2024-00283` |
| Goods Receipt | `GR-{ORG}-{YYYY}-{NNNNN}` | `GR-UCH-2024-00128` |
| Invoice | `INV-{ORG}-{YYYY}-{NNNNNN}` | `INV-UCH-2024-000091` |

## Typical Output Volumes

With default settings against an industry profile, the final state looks like:

**Mercy Regional Medical Center (healthcare)**
- ~$650M total spend, 2022-present
- 603 suppliers (428 with transactions), 15 categories
- Top vendors: GE Healthcare, Philips Healthcare, Siemens Healthineers, Stryker, Mindray
- 80 contracts, 500 PRs, 400 POs, 277 GRs, 277 invoices

**Pacific State University (higher-ed)**
- ~$1.68B total spend, 2022-present
- 541 suppliers (393 with transactions), 16 categories
- Top vendors: Turner Construction, Skanska, Whiting-Turner, Gilbane, Grainger, Thermo Fisher
- 80 contracts, 500 PRs, 400 POs, 277 GRs, 277 invoices

**Apex Manufacturing Co. (manufacturing)**
- ~$785M total spend, 2022-present
- 576 suppliers (426 with transactions), 15 categories
- Top vendors: DMG Mori, Haas Automation, Makino, ABB Robotics, Mazak, Fanuc, Okuma, KUKA, Jabil, Flex
- 80 contracts, 500 PRs, 400 POs, 285 GRs, 285 invoices

## Verifying a Seed

After seeding, sanity-check the result in the browser:

1. Switch to the target org in the top-right organization switcher
2. **Overview** — confirm total spend, supplier count, category count
3. **Suppliers** — top-10 should be recognizable industry vendors
4. **P2P Cycle** — stage metrics should be non-zero (PR→PO, PO→GR, GR→Invoice, Invoice→Pay)
5. **3-Way Matching** — match rate ~50-60%, some open exceptions
6. **Contract Optimization** — 80 contracts visible with utilization %
7. **Maverick Spend** — violations populated, policies listed

Or via shell:
```bash
docker-compose exec backend python manage.py shell -c "
from apps.authentication.models import Organization
from apps.procurement.models import Transaction, PurchaseRequisition, Invoice, Contract
org = Organization.objects.get(slug='uch')
print('Transactions:', Transaction.objects.filter(organization=org).count())
print('PRs:', PurchaseRequisition.objects.filter(organization=org).count())
print('Invoices:', Invoice.objects.filter(organization=org).count())
print('Contracts:', Contract.objects.filter(organization=org).count())
"
```

## Adding a New Industry Profile

1. Open [_industry_profiles.py](../backend/apps/procurement/management/commands/_industry_profiles.py)
2. Add a new profile dict with the same shape as `HEALTHCARE` / `HIGHER_ED`:
   - `name`, `categories`, `tail_supplier_templates`, `departments`, `cost_center_prefix`, `payment_terms`, `seasonality` (12 floats), `policies`, `tail_cities`, `tail_regions`
3. Register it in the `PROFILES` dict at the bottom of the module
4. The new industry will automatically be a valid choice for both commands' `--industry` argument

**Tuning tips:**
- `spend_share` across all categories should sum close to 1.0 (normalized internally)
- `amount_mu`/`amount_sigma` control log-normal distribution. Median = `exp(mu)`. Larger `sigma` = wider spread. Capital-equipment categories want `mu=10+` and `sigma=1.8+`. Consumables want `mu=5-7` and `sigma=1.0-1.3`.
- `seasonality` is a 12-element array (Jan..Dec). Mean should hover near 1.0. Peaks above 1.5 create strong visible spikes in the Seasonality dashboard.

## Exporting a Seeded Dataset

Django admin has a superuser-only action that snapshots any `is_demo=True` org to a ZIP of round-trippable CSVs — the import counterpart to the seed commands above.

### How to use

1. Log in as a Django superuser
2. Go to `/admin/authentication/organization/`
3. Tick one or more demo orgs (each is marked with an amber DEMO badge in the list)
4. **Actions → "Export seeded dataset as ZIP (demo orgs only)" → Go**
5. Browser downloads `seeded-datasets-YYYYMMDD-HHMMSS.zip`

Inside: one `<slug>-dataset.zip` per selected org. Each inner zip contains a `<slug>/` folder with 10 CSVs + a `README.txt` listing the exact row counts and the `seed_industry_data` / `seed_demo_data` commands to reproduce the state from scratch.

### Round-trip tiers

| Tier | Files | How to re-import |
|------|-------|------------------|
| **A — Admin Import CSV** | `purchase_requisitions.csv`, `purchase_orders.csv`, `goods_receipts.csv`, `invoices.csv` | `/admin/procurement/<model>/import/` — columns match the existing Import CSV templates verbatim |
| **B — DataUpload wizard** | `transactions.csv` | Admin DataUpload wizard — headers (`supplier`, `category`, `amount`, `date`, ...) are recognized without a column-mapping step |
| **C — Reference only** | `suppliers.csv`, `categories.csv`, `contracts.csv`, `spending_policies.csv`, `policy_violations.csv` | No importer — regenerate via `seed_industry_data` / `seed_demo_data` |

Column schemas for Tier A/B are pinned to the importer source-of-truth by a drift-guard test (`test_admin_export.py::TestColumnDriftGuard`) — if anyone edits `P2PImportMixin.p2p_import_fields` or `CSVProcessor.REQUIRED_COLUMNS`/`OPTIONAL_COLUMNS` without updating the exporter, CI fails loudly.

### Safety rails

- **Non-superusers don't see the action** — `OrganizationAdmin.get_actions()` filters it out of the dropdown entirely.
- **Mixed demo/non-demo selection is rejected** — if any selected org has `is_demo=False`, the whole batch errors out with `messages.error` rather than silently partial-exporting. Flip `is_demo=True` in admin first, or remove the org from the selection.
- **Every export writes an `AuditLog` row** — `action='export'`, `resource='organization_dataset'`, `resource_id=<slug>`, with row counts, zip size, and org name in `details`.

### Performance envelope

Bolt & Nuts (25K transactions, 576 suppliers, 400 POs, 500 PRs, etc.) exports to a ~311 KB compressed ZIP in ~1 second. Synchronous `HttpResponse` — no Celery queue needed at current seed sizes. If a profile ever grows past ~200K transactions, revisit with `StreamingHttpResponse`.

## Notes

- Seeding is wrapped in a single `transaction.atomic()` block — if anything fails, the DB rolls back cleanly
- `bulk_create` is used for all mass inserts with `batch_size=2000`
- `Transaction` post-save signals invalidate the AI insights cache; this fires automatically
- The `--wipe` flag on `seed_industry_data` deletes ALL procurement data (including contracts and P2P), while `--wipe` on `seed_demo_data` only deletes P2P/Contract/Policy rows (preserving Transactions and Suppliers)
