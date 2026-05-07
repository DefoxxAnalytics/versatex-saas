"""
Year-over-year analytics service.

Provides year-over-year comparison analysis with fiscal year support,
category/supplier breakdowns, and growth metrics.
"""

from collections import defaultdict

from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncMonth, TruncYear

from apps.procurement.models import Category, Supplier

from .base import BaseAnalyticsService

# Minimum distinct months a calendar year must contain before its YoY growth
# is considered to have a "full window" of data. Mirrors the Predictive
# growth-metrics precedent (>=12 months per window) and accuracy convention §4.
FULL_YEAR_MONTH_COUNT = 12


CALENDAR_MONTH_NAMES = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
FISCAL_MONTH_NAMES = [
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
]


def _yoy_change(y1_spend, y2_spend):
    """
    Compute YoY change percentage with explicit new/discontinued flags.

    Returns a tuple (change_pct, is_new, is_discontinued) where:
    - is_new = category existed only in year2 (y1 was zero). change_pct
      defaults to 100 for back-compat but callers should prefer the flag.
    - is_discontinued = category existed only in year1 (y2 is zero).
      change_pct is -100 (a real -100% drop is the same number but not
      flagged, which is intentional — -100 always means "lost everything").
    - Otherwise the standard (y2 - y1)/y1 * 100 formula.
    """
    is_new = y1_spend == 0 and y2_spend > 0
    is_discontinued = y1_spend > 0 and y2_spend == 0
    if y1_spend > 0:
        change_pct = (y2_spend - y1_spend) / y1_spend * 100
    elif y2_spend > 0:
        change_pct = 100  # Placeholder; UI should render "New" via is_new flag
    else:
        change_pct = 0
    return change_pct, is_new, is_discontinued


class YearOverYearAnalyticsService(BaseAnalyticsService):
    """
    Service for year-over-year comparison analytics.

    Methods:
        get_year_over_year_comparison: Basic YoY spend comparison
        get_detailed_year_over_year: Comprehensive YoY with category/supplier breakdowns
        get_yoy_category_drilldown: Category-level YoY drill-down
        get_yoy_supplier_drilldown: Supplier-level YoY drill-down
    """

    def get_year_over_year_comparison(self):
        """
        Compare spending year over year.

        growth_percentage is emitted only when the current AND previous calendar
        years each have a full window of data (12 distinct months). Without
        equal-and-full spans the formula degenerates: a 12-month current vs.
        1-month prior produces ~1100% nonsense (same root cause as the
        Predictive 13-month YoY anomaly — accuracy convention §4). When the
        guard fails we set ``insufficient_data_for_growth: true`` and OMIT
        ``growth_percentage`` so the frontend can render an explicit state
        rather than a misleading number.

        Returns:
            list: Yearly spend dicts with optional growth_percentage
        """
        data = list(
            self.transactions.annotate(year=TruncYear("date"))
            .values("year")
            .annotate(total=Sum("amount"), count=Count("id"), avg=Avg("amount"))
            .order_by("year")
        )

        # Per-year distinct-month coverage. Used as the equal-span gate before
        # emitting any growth_percentage. Keyed by calendar year (int).
        # v3.1 Phase 2 (AN-M4): Count(TruncMonth('date'), distinct=True)
        # references the function directly rather than the named annotation.
        # Django can fold the named-annotation form into the GROUP BY in
        # ways that vary across versions; the direct expression is
        # version-stable.
        month_coverage = {
            row["year"].year: row["month_count"]
            for row in self.transactions.annotate(
                year=TruncYear("date"),
            )
            .values("year")
            .annotate(month_count=Count(TruncMonth("date"), distinct=True))
        }

        result = []
        for i, item in enumerate(data):
            year_value = item["year"].year
            year_data = {
                "year": year_value,
                "total_spend": float(item["total"]),
                "transaction_count": item["count"],
                "avg_transaction": float(item["avg"]),
            }

            if i > 0:
                prev_year_value = data[i - 1]["year"].year
                cur_months = month_coverage.get(year_value, 0)
                prev_months = month_coverage.get(prev_year_value, 0)
                has_full_windows = (
                    cur_months >= FULL_YEAR_MONTH_COUNT
                    and prev_months >= FULL_YEAR_MONTH_COUNT
                )

                if has_full_windows:
                    prev_total = float(data[i - 1]["total"])
                    growth = (
                        ((float(item["total"]) - prev_total) / prev_total * 100)
                        if prev_total > 0
                        else 0
                    )
                    year_data["growth_percentage"] = round(growth, 2)
                else:
                    year_data["insufficient_data_for_growth"] = True

            result.append(year_data)

        return result

    def get_detailed_year_over_year(self, year1=None, year2=None, use_fiscal_year=True):
        """
        Get detailed year-over-year comparison with category and supplier breakdowns.
        Returns comprehensive data for the Year-over-Year dashboard page.

        v3.1 Phase 4 (AN-M3): refactored from full transaction materialisation
        + Python-side defaultdict accumulation to DB-side grouped aggregation.
        Uses the BaseAnalyticsService.fiscal_year_db_expr / fiscal_month_db_expr
        helpers so the FY math matches the Python `_get_fiscal_year` /
        `_get_fiscal_month` semantics exactly. Per-tenant transaction count
        was the bottleneck; now it stays O(years × categories) regardless
        of row volume.

        Args:
            year1: First fiscal year to compare (optional, defaults to previous FY)
            year2: Second fiscal year to compare (optional, defaults to current FY)
            use_fiscal_year: Whether to use fiscal year (Jul-Jun) or calendar year

        Returns:
            dict: Comprehensive YoY comparison with summary, monthly, category, supplier data
        """
        from django.db.models import Count, Sum

        fy_expr = self.fiscal_year_db_expr(use_fiscal_year)
        fm_expr = self.fiscal_month_db_expr(use_fiscal_year)

        # ── Available years ────────────────────────────────────────────
        # Note: `.values_list(...).distinct()` on a Case/When-annotated field
        # is not reliably deduplicated on SQLite (returns duplicates because
        # DISTINCT is applied to the SELECT projection, not the annotation
        # value). Wrap with `set()` to enforce uniqueness in Python.
        available_years = sorted(
            set(self.transactions.annotate(fy=fy_expr).values_list("fy", flat=True))
        )

        if not available_years:
            return {
                "summary": {
                    "year1": "FY2024" if use_fiscal_year else "2024",
                    "year2": "FY2025" if use_fiscal_year else "2025",
                    "year1_total_spend": 0,
                    "year2_total_spend": 0,
                    "spend_change": 0,
                    "spend_change_pct": 0,
                    "year1_transactions": 0,
                    "year2_transactions": 0,
                    "year1_suppliers": 0,
                    "year2_suppliers": 0,
                    "year1_avg_transaction": 0,
                    "year2_avg_transaction": 0,
                    "insufficient_data_for_yoy": True,
                },
                "monthly_comparison": [],
                "category_comparison": [],
                "supplier_comparison": [],
                "top_gainers": [],
                "top_decliners": [],
                "available_years": [],
            }

        # ── Resolve year1 / year2 ──────────────────────────────────────
        insufficient_data_for_yoy = False
        if year1 is None or year2 is None:
            if len(available_years) >= 2:
                year1 = year1 or available_years[-2]
                year2 = year2 or available_years[-1]
            elif len(available_years) == 1:
                year1 = year1 or available_years[0]
                year2 = year2 or available_years[0]
                insufficient_data_for_yoy = True
            else:
                year1, year2 = 2024, 2025
                insufficient_data_for_yoy = True

        year_prefix = "FY" if use_fiscal_year else ""
        month_names = FISCAL_MONTH_NAMES if use_fiscal_year else CALENDAR_MONTH_NAMES

        # Restrict subsequent aggregations to year1+year2 to keep them small.
        scoped_qs = self.transactions.annotate(fy=fy_expr).filter(fy__in={year1, year2})

        # ── Summary per year ───────────────────────────────────────────
        year_summary_rows = scoped_qs.values("fy").annotate(
            total=Sum("amount"),
            count=Count("id"),
            suppliers=Count("supplier_id", distinct=True),
        )
        year_summary = {row["fy"]: row for row in year_summary_rows}

        def _get(year, key, default=0):
            row = year_summary.get(year)
            return row[key] if row and row.get(key) is not None else default

        year1_total = float(_get(year1, "total", 0))
        year2_total = float(_get(year2, "total", 0))
        year1_count = int(_get(year1, "count", 0))
        year2_count = int(_get(year2, "count", 0))
        year1_suppliers = int(_get(year1, "suppliers", 0))
        year2_suppliers = int(_get(year2, "suppliers", 0))

        spend_change = year2_total - year1_total
        spend_change_pct = (
            ((year2_total - year1_total) / year1_total * 100) if year1_total > 0 else 0
        )

        # ── Monthly comparison ─────────────────────────────────────────
        monthly_rows = (
            scoped_qs.annotate(fm=fm_expr)
            .values("fy", "fm")
            .annotate(spend=Sum("amount"))
        )
        monthly_year1 = {
            row["fm"]: float(row["spend"] or 0)
            for row in monthly_rows
            if row["fy"] == year1
        }
        monthly_year2 = {
            row["fm"]: float(row["spend"] or 0)
            for row in monthly_rows
            if row["fy"] == year2
        }

        monthly_comparison = []
        for i in range(1, 13):
            y1_spend = monthly_year1.get(i, 0)
            y2_spend = monthly_year2.get(i, 0)
            change_pct, is_new, is_discontinued = _yoy_change(y1_spend, y2_spend)
            monthly_comparison.append(
                {
                    "month": month_names[i - 1],
                    "fiscal_month": i,
                    "year1_spend": round(y1_spend, 2),
                    "year2_spend": round(y2_spend, 2),
                    "change_pct": round(change_pct, 2),
                    "is_new": is_new,
                    "is_discontinued": is_discontinued,
                }
            )

        # ── Category comparison ────────────────────────────────────────
        category_rows = list(
            scoped_qs.values("fy", "category_id", "category__name").annotate(
                spend=Sum("amount")
            )
        )
        cat_year1 = {}
        cat_year2 = {}
        for row in category_rows:
            cat_name = row["category__name"] or "Uncategorized"
            entry = {
                "spend": float(row["spend"] or 0),
                "id": row["category_id"],
                "name": cat_name,
            }
            if row["fy"] == year1:
                cat_year1[cat_name] = entry
            elif row["fy"] == year2:
                cat_year2[cat_name] = entry

        all_categories = set(cat_year1.keys()) | set(cat_year2.keys())
        category_comparison = []
        for cat_name in all_categories:
            y1_data = cat_year1.get(
                cat_name, {"spend": 0, "id": None, "name": cat_name}
            )
            y2_data = cat_year2.get(
                cat_name, {"spend": 0, "id": None, "name": cat_name}
            )
            y1_spend = y1_data["spend"]
            y2_spend = y2_data["spend"]
            change = y2_spend - y1_spend
            change_pct, is_new, is_discontinued = _yoy_change(y1_spend, y2_spend)
            category_comparison.append(
                {
                    "category": cat_name,
                    "category_id": y1_data["id"] or y2_data["id"],
                    "year1_spend": round(y1_spend, 2),
                    "year2_spend": round(y2_spend, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "is_new": is_new,
                    "is_discontinued": is_discontinued,
                    "year1_pct_of_total": round(
                        (y1_spend / year1_total * 100) if year1_total > 0 else 0, 2
                    ),
                    "year2_pct_of_total": round(
                        (y2_spend / year2_total * 100) if year2_total > 0 else 0, 2
                    ),
                }
            )

        category_comparison.sort(key=lambda x: x["year2_spend"], reverse=True)

        comparable_cats = [c for c in category_comparison if c["year1_spend"] > 0]
        top_gainers = sorted(
            comparable_cats, key=lambda x: x["change_pct"], reverse=True
        )[:5]
        top_decliners = sorted(comparable_cats, key=lambda x: x["change_pct"])[:5]

        # ── Supplier comparison ────────────────────────────────────────
        supplier_rows = list(
            scoped_qs.values("fy", "supplier_id", "supplier__name").annotate(
                spend=Sum("amount"), txn_count=Count("id")
            )
        )
        sup_year1 = {}
        sup_year2 = {}
        for row in supplier_rows:
            sup_name = row["supplier__name"] or "Unknown"
            entry = {
                "spend": float(row["spend"] or 0),
                "id": row["supplier_id"],
                "name": sup_name,
                "count": int(row["txn_count"] or 0),
            }
            if row["fy"] == year1:
                sup_year1[sup_name] = entry
            elif row["fy"] == year2:
                sup_year2[sup_name] = entry

        all_suppliers = set(sup_year1.keys()) | set(sup_year2.keys())
        supplier_comparison = []
        for sup_name in all_suppliers:
            y1_data = sup_year1.get(
                sup_name, {"spend": 0, "id": None, "name": sup_name, "count": 0}
            )
            y2_data = sup_year2.get(
                sup_name, {"spend": 0, "id": None, "name": sup_name, "count": 0}
            )
            y1_spend = y1_data["spend"]
            y2_spend = y2_data["spend"]
            change = y2_spend - y1_spend
            change_pct, is_new, is_discontinued = _yoy_change(y1_spend, y2_spend)
            supplier_comparison.append(
                {
                    "supplier": sup_name,
                    "supplier_id": y1_data["id"] or y2_data["id"],
                    "year1_spend": round(y1_spend, 2),
                    "year2_spend": round(y2_spend, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "is_new": is_new,
                    "is_discontinued": is_discontinued,
                    "year1_transactions": y1_data["count"],
                    "year2_transactions": y2_data["count"],
                }
            )

        supplier_comparison.sort(
            key=lambda x: x["year1_spend"] + x["year2_spend"], reverse=True
        )
        supplier_comparison = supplier_comparison[:50]

        return {
            "summary": {
                "year1": f"{year_prefix}{year1}",
                "year2": f"{year_prefix}{year2}",
                "year1_total_spend": round(year1_total, 2),
                "year2_total_spend": round(year2_total, 2),
                "spend_change": round(spend_change, 2),
                "spend_change_pct": round(spend_change_pct, 2),
                "year1_transactions": year1_count,
                "year2_transactions": year2_count,
                "year1_suppliers": year1_suppliers,
                "year2_suppliers": year2_suppliers,
                "year1_avg_transaction": (
                    round(year1_total / year1_count, 2) if year1_count > 0 else 0
                ),
                "year2_avg_transaction": (
                    round(year2_total / year2_count, 2) if year2_count > 0 else 0
                ),
                "insufficient_data_for_yoy": insufficient_data_for_yoy,
            },
            "monthly_comparison": monthly_comparison,
            "category_comparison": category_comparison,
            "supplier_comparison": supplier_comparison,
            "top_gainers": top_gainers,
            "top_decliners": top_decliners,
            "available_years": available_years,
        }

    def get_yoy_category_drilldown(
        self, category_id, year1=None, year2=None, use_fiscal_year=True
    ):
        """
        Get detailed YoY comparison for a specific category.
        Returns supplier-level breakdowns within the category.

        Args:
            category_id: The category ID to drill into
            year1: First fiscal year to compare
            year2: Second fiscal year to compare
            use_fiscal_year: Whether to use fiscal year (Jul-Jun) or calendar year

        Returns:
            dict: Category YoY with supplier breakdowns and monthly data
            None: If category not found
        """
        # Verify category exists
        try:
            category = Category.objects.get(
                id=category_id, organization=self.organization
            )
            category_name = category.name
        except Category.DoesNotExist:
            return None

        # Get transactions for this category
        cat_transactions = list(
            self.transactions.filter(category_id=category_id)
            .select_related("supplier")
            .values("id", "amount", "date", "supplier__name", "supplier_id")
        )

        if not cat_transactions:
            return {
                "category": category_name,
                "category_id": category_id,
                "year1": "FY2024" if use_fiscal_year else "2024",
                "year2": "FY2025" if use_fiscal_year else "2025",
                "year1_total": 0,
                "year2_total": 0,
                "change_pct": 0,
                "suppliers": [],
                "monthly_breakdown": [],
            }

        # Calculate fiscal years (month honors the calendar toggle post-Cluster 2)
        for t in cat_transactions:
            t["fiscal_year"] = self._get_fiscal_year(t["date"], use_fiscal_year)
            t["fiscal_month"] = self._get_fiscal_month(t["date"], use_fiscal_year)

        # Determine years
        insufficient_data_for_yoy = False
        available_years = sorted(set(t["fiscal_year"] for t in cat_transactions))
        if year1 is None or year2 is None:
            if len(available_years) >= 2:
                year1 = year1 or available_years[-2]
                year2 = year2 or available_years[-1]
            else:
                year1 = year1 or (available_years[0] if available_years else 2024)
                year2 = year2 or (available_years[0] if available_years else 2025)
                insufficient_data_for_yoy = True

        year_prefix = "FY" if use_fiscal_year else ""
        month_names = FISCAL_MONTH_NAMES if use_fiscal_year else CALENDAR_MONTH_NAMES

        year1_txns = [t for t in cat_transactions if t["fiscal_year"] == year1]
        year2_txns = [t for t in cat_transactions if t["fiscal_year"] == year2]

        year1_total = sum(float(t["amount"] or 0) for t in year1_txns)
        year2_total = sum(float(t["amount"] or 0) for t in year2_txns)
        change_pct, _is_new, _is_discontinued = _yoy_change(year1_total, year2_total)

        # Supplier breakdown
        sup_year1 = defaultdict(lambda: {"spend": 0, "id": None, "name": ""})
        sup_year2 = defaultdict(lambda: {"spend": 0, "id": None, "name": ""})
        for t in year1_txns:
            sup_name = t["supplier__name"] or "Unknown"
            sup_year1[sup_name]["spend"] += float(t["amount"] or 0)
            sup_year1[sup_name]["id"] = t["supplier_id"]
            sup_year1[sup_name]["name"] = sup_name
        for t in year2_txns:
            sup_name = t["supplier__name"] or "Unknown"
            sup_year2[sup_name]["spend"] += float(t["amount"] or 0)
            sup_year2[sup_name]["id"] = t["supplier_id"]
            sup_year2[sup_name]["name"] = sup_name

        all_suppliers = set(sup_year1.keys()) | set(sup_year2.keys())
        suppliers = []
        for sup_name in all_suppliers:
            y1_data = sup_year1.get(
                sup_name, {"spend": 0, "id": None, "name": sup_name}
            )
            y2_data = sup_year2.get(
                sup_name, {"spend": 0, "id": None, "name": sup_name}
            )
            y1_spend = y1_data["spend"]
            y2_spend = y2_data["spend"]
            change = y2_spend - y1_spend
            sup_change_pct, sup_is_new, sup_is_discontinued = _yoy_change(
                y1_spend, y2_spend
            )
            suppliers.append(
                {
                    "name": sup_name,
                    "supplier_id": y1_data["id"] or y2_data["id"],
                    "year1_spend": round(y1_spend, 2),
                    "year2_spend": round(y2_spend, 2),
                    "change": round(change, 2),
                    "change_pct": round(sup_change_pct, 2),
                    "is_new": sup_is_new,
                    "is_discontinued": sup_is_discontinued,
                }
            )

        suppliers.sort(key=lambda x: x["year1_spend"] + x["year2_spend"], reverse=True)

        # Monthly breakdown (month_names already honors use_fiscal_year)
        monthly_year1 = defaultdict(float)
        monthly_year2 = defaultdict(float)
        for t in year1_txns:
            monthly_year1[t["fiscal_month"]] += float(t["amount"] or 0)
        for t in year2_txns:
            monthly_year2[t["fiscal_month"]] += float(t["amount"] or 0)

        monthly_breakdown = []
        for i in range(1, 13):
            monthly_breakdown.append(
                {
                    "month": month_names[i - 1],
                    "year1_spend": round(monthly_year1.get(i, 0), 2),
                    "year2_spend": round(monthly_year2.get(i, 0), 2),
                }
            )

        return {
            "category": category_name,
            "category_id": category_id,
            "year1": f"{year_prefix}{year1}",
            "year2": f"{year_prefix}{year2}",
            "year1_total": round(year1_total, 2),
            "year2_total": round(year2_total, 2),
            "change_pct": round(change_pct, 2),
            "insufficient_data_for_yoy": insufficient_data_for_yoy,
            "suppliers": suppliers,
            "monthly_breakdown": monthly_breakdown,
        }

    def get_yoy_supplier_drilldown(
        self, supplier_id, year1=None, year2=None, use_fiscal_year=True
    ):
        """
        Get detailed YoY comparison for a specific supplier.
        Returns category-level breakdowns for the supplier.

        Args:
            supplier_id: The supplier ID to drill into
            year1: First fiscal year to compare
            year2: Second fiscal year to compare
            use_fiscal_year: Whether to use fiscal year (Jul-Jun) or calendar year

        Returns:
            dict: Supplier YoY with category breakdowns and monthly data
            None: If supplier not found
        """
        # Verify supplier exists
        try:
            supplier = Supplier.objects.get(
                id=supplier_id, organization=self.organization
            )
            supplier_name = supplier.name
        except Supplier.DoesNotExist:
            return None

        # Get transactions for this supplier
        sup_transactions = list(
            self.transactions.filter(supplier_id=supplier_id)
            .select_related("category")
            .values("id", "amount", "date", "category__name", "category_id")
        )

        if not sup_transactions:
            return {
                "supplier": supplier_name,
                "supplier_id": supplier_id,
                "year1": "FY2024" if use_fiscal_year else "2024",
                "year2": "FY2025" if use_fiscal_year else "2025",
                "year1_total": 0,
                "year2_total": 0,
                "change_pct": 0,
                "categories": [],
                "monthly_breakdown": [],
            }

        # Calculate fiscal years (month honors the calendar toggle post-Cluster 2)
        for t in sup_transactions:
            t["fiscal_year"] = self._get_fiscal_year(t["date"], use_fiscal_year)
            t["fiscal_month"] = self._get_fiscal_month(t["date"], use_fiscal_year)

        # Determine years
        insufficient_data_for_yoy = False
        available_years = sorted(set(t["fiscal_year"] for t in sup_transactions))
        if year1 is None or year2 is None:
            if len(available_years) >= 2:
                year1 = year1 or available_years[-2]
                year2 = year2 or available_years[-1]
            else:
                year1 = year1 or (available_years[0] if available_years else 2024)
                year2 = year2 or (available_years[0] if available_years else 2025)
                insufficient_data_for_yoy = True

        year_prefix = "FY" if use_fiscal_year else ""
        month_names = FISCAL_MONTH_NAMES if use_fiscal_year else CALENDAR_MONTH_NAMES

        year1_txns = [t for t in sup_transactions if t["fiscal_year"] == year1]
        year2_txns = [t for t in sup_transactions if t["fiscal_year"] == year2]

        year1_total = sum(float(t["amount"] or 0) for t in year1_txns)
        year2_total = sum(float(t["amount"] or 0) for t in year2_txns)
        change_pct, _is_new, _is_discontinued = _yoy_change(year1_total, year2_total)

        # Category breakdown
        cat_year1 = defaultdict(lambda: {"spend": 0, "id": None, "name": ""})
        cat_year2 = defaultdict(lambda: {"spend": 0, "id": None, "name": ""})
        for t in year1_txns:
            cat_name = t["category__name"] or "Uncategorized"
            cat_year1[cat_name]["spend"] += float(t["amount"] or 0)
            cat_year1[cat_name]["id"] = t["category_id"]
            cat_year1[cat_name]["name"] = cat_name
        for t in year2_txns:
            cat_name = t["category__name"] or "Uncategorized"
            cat_year2[cat_name]["spend"] += float(t["amount"] or 0)
            cat_year2[cat_name]["id"] = t["category_id"]
            cat_year2[cat_name]["name"] = cat_name

        all_categories = set(cat_year1.keys()) | set(cat_year2.keys())
        categories = []
        for cat_name in all_categories:
            y1_data = cat_year1.get(
                cat_name, {"spend": 0, "id": None, "name": cat_name}
            )
            y2_data = cat_year2.get(
                cat_name, {"spend": 0, "id": None, "name": cat_name}
            )
            y1_spend = y1_data["spend"]
            y2_spend = y2_data["spend"]
            change = y2_spend - y1_spend
            cat_change_pct, cat_is_new, cat_is_discontinued = _yoy_change(
                y1_spend, y2_spend
            )
            categories.append(
                {
                    "name": cat_name,
                    "category_id": y1_data["id"] or y2_data["id"],
                    "year1_spend": round(y1_spend, 2),
                    "year2_spend": round(y2_spend, 2),
                    "change": round(change, 2),
                    "change_pct": round(cat_change_pct, 2),
                    "is_new": cat_is_new,
                    "is_discontinued": cat_is_discontinued,
                }
            )

        categories.sort(key=lambda x: x["year1_spend"] + x["year2_spend"], reverse=True)

        # Monthly breakdown (month_names already honors use_fiscal_year)
        monthly_year1 = defaultdict(float)
        monthly_year2 = defaultdict(float)
        for t in year1_txns:
            monthly_year1[t["fiscal_month"]] += float(t["amount"] or 0)
        for t in year2_txns:
            monthly_year2[t["fiscal_month"]] += float(t["amount"] or 0)

        monthly_breakdown = []
        for i in range(1, 13):
            monthly_breakdown.append(
                {
                    "month": month_names[i - 1],
                    "year1_spend": round(monthly_year1.get(i, 0), 2),
                    "year2_spend": round(monthly_year2.get(i, 0), 2),
                }
            )

        return {
            "supplier": supplier_name,
            "supplier_id": supplier_id,
            "year1": f"{year_prefix}{year1}",
            "year2": f"{year_prefix}{year2}",
            "year1_total": round(year1_total, 2),
            "year2_total": round(year2_total, 2),
            "change_pct": round(change_pct, 2),
            "insufficient_data_for_yoy": insufficient_data_for_yoy,
            "categories": categories,
            "monthly_breakdown": monthly_breakdown,
        }
