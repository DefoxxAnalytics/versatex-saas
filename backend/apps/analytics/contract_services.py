"""
Contract Analytics Services

Provides contract performance tracking, renewal alerts, and savings opportunities:
- Contract overview and statistics
- Expiring contracts alerts
- Contract vs actual spend analysis
- Savings opportunities identification
- Renewal recommendations
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import TruncMonth

from apps.procurement.models import Category, Contract, Supplier, Transaction


class ContractAnalyticsService:
    """
    Service class for contract analytics and optimization.

    Provides insights on:
    - Contract utilization and performance
    - Expiring contracts and renewal recommendations
    - Off-contract spending identification
    - Savings opportunities
    """

    def __init__(self, organization):
        self.organization = organization
        self.contracts = Contract.objects.filter(organization=organization)
        self.transactions = Transaction.objects.filter(organization=organization)

    def get_contract_overview(self):
        """
        Get overview statistics for all contracts.

        Returns:
            Dict with contract summary statistics
        """
        today = date.today()

        # Basic counts
        total_contracts = self.contracts.count()
        active_contracts = self.contracts.filter(status="active").count()

        # Value statistics
        value_stats = self.contracts.filter(status="active").aggregate(
            sum_total_value=Sum("total_value"),
            sum_annual_value=Sum("annual_value"),
            avg_contract_value=Avg("total_value"),
        )

        # Expiring soon (within 90 days)
        expiring_date = today + timedelta(days=90)
        expiring_soon = self.contracts.filter(
            status="active", end_date__lte=expiring_date, end_date__gte=today
        ).count()

        # Expired contracts
        expired = self.contracts.filter(
            end_date__lt=today, status__in=["active", "expiring"]
        ).count()

        # Contract coverage (% of recent spend from contracted suppliers).
        # Scoped to the trailing 12 months so pre-contract history doesn't
        # inflate coverage: previously, ALL-TIME spend from a supplier who
        # recently became contracted counted as "covered", which made long-
        # tenured orgs appear ~100% covered the moment they signed any
        # contract.
        coverage_window_start = today - timedelta(days=365)
        recent_txns = self.transactions.filter(date__gte=coverage_window_start)

        contract_supplier_ids = self.contracts.filter(status="active").values_list(
            "supplier_id", flat=True
        )

        total_spend = recent_txns.aggregate(total=Sum("amount"))["total"] or Decimal(
            "0"
        )
        contracted_spend = recent_txns.filter(
            supplier_id__in=contract_supplier_ids
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        coverage_percentage = (
            float(contracted_spend / total_spend * 100) if total_spend > 0 else 0
        )

        return {
            "total_contracts": total_contracts,
            "active_contracts": active_contracts,
            "expiring_soon": expiring_soon,
            "expired": expired,
            "total_value": float(value_stats["sum_total_value"] or 0),
            "total_annual_value": float(value_stats["sum_annual_value"] or 0),
            "avg_contract_value": float(value_stats["avg_contract_value"] or 0),
            "contract_coverage_percentage": round(coverage_percentage, 1),
            "contract_coverage_window_days": 365,
            "contracted_spend": float(contracted_spend),
            "total_spend": float(total_spend),
        }

    def get_contracts_list(self):
        """
        Get list of all contracts with basic info.

        Returns:
            List of contract dictionaries

        Note: `utilization_percentage` is computed using only transactions that
        fell inside each contract's own [start_date, min(end_date, today)]
        window. Earlier versions summed the supplier's ALL-TIME transaction
        spend (via a single precomputed supplier→total dict) and divided by
        the contract's total_value — which meant a supplier with years of
        pre-contract history appeared as "1200% utilized" the week they
        signed a new contract. The per-contract date filter below is the
        correct scoping.
        """
        contracts = self.contracts.select_related("supplier").order_by("end_date")

        today = date.today()
        if not contracts.exists():
            return []

        # Build per-contract spend in a single query: group transactions that
        # fall within ANY of the contracts we care about, keyed on both
        # supplier and date so each contract can be resolved to its own slice.
        supplier_ids = [c.supplier_id for c in contracts]
        relevant_txns = list(
            self.transactions.filter(supplier_id__in=supplier_ids).values(
                "supplier_id", "date", "amount"
            )
        )

        result = []
        for contract in contracts:
            days_to_expiry = (
                (contract.end_date - today).days if contract.end_date else None
            )
            window_end = min(contract.end_date, today)
            actual_spend = Decimal("0")
            for t in relevant_txns:
                if (
                    t["supplier_id"] == contract.supplier_id
                    and contract.start_date <= t["date"] <= window_end
                ):
                    actual_spend += t["amount"]

            utilization = (
                float(actual_spend / contract.total_value * 100)
                if contract.total_value and contract.total_value > 0
                else 0
            )

            result.append(
                {
                    "id": contract.id,
                    "uuid": str(contract.uuid),
                    "contract_number": contract.contract_number,
                    "title": contract.title,
                    "supplier_id": contract.supplier_id,
                    "supplier_name": contract.supplier.name,
                    "total_value": float(contract.total_value),
                    "annual_value": (
                        float(contract.annual_value) if contract.annual_value else None
                    ),
                    "start_date": contract.start_date.isoformat(),
                    "end_date": contract.end_date.isoformat(),
                    "days_to_expiry": days_to_expiry,
                    "status": contract.status,
                    "auto_renew": contract.auto_renew,
                    "renewal_notice_days": contract.renewal_notice_days,
                    "utilization_percentage": round(utilization, 1),
                }
            )

        return result

    def get_contract_detail(self, contract_id):
        """
        Get detailed information for a specific contract.

        Args:
            contract_id: Contract ID

        Returns:
            Dict with contract details and performance metrics
        """
        try:
            contract = self.contracts.select_related("supplier").get(id=contract_id)
        except Contract.DoesNotExist:
            return {"error": "Contract not found"}

        today = date.today()
        days_to_expiry = (contract.end_date - today).days if contract.end_date else None

        # Calculate actual spend against this contract's supplier
        actual_spend = self.transactions.filter(
            supplier_id=contract.supplier_id,
            date__gte=contract.start_date,
            date__lte=min(contract.end_date, today),
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        # Calculate utilization
        utilization = (
            float(actual_spend / contract.total_value * 100)
            if contract.total_value > 0
            else 0
        )

        # Get monthly spend trend
        monthly_spend = (
            self.transactions.filter(
                supplier_id=contract.supplier_id, date__gte=contract.start_date
            )
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )

        # Get categories covered
        categories = list(contract.categories.values_list("name", flat=True))

        return {
            "id": contract.id,
            "uuid": str(contract.uuid),
            "contract_number": contract.contract_number,
            "title": contract.title,
            "description": contract.description,
            "supplier_id": contract.supplier_id,
            "supplier_name": contract.supplier.name,
            "total_value": float(contract.total_value),
            "annual_value": (
                float(contract.annual_value) if contract.annual_value else None
            ),
            "start_date": contract.start_date.isoformat(),
            "end_date": contract.end_date.isoformat(),
            "days_to_expiry": days_to_expiry,
            "status": contract.status,
            "auto_renew": contract.auto_renew,
            "renewal_notice_days": contract.renewal_notice_days,
            "categories": categories,
            "performance": {
                "actual_spend": float(actual_spend),
                "utilization_percentage": round(utilization, 1),
                "remaining_value": float(contract.total_value - actual_spend),
                "monthly_spend": [
                    {"month": m["month"].strftime("%Y-%m"), "amount": float(m["total"])}
                    for m in monthly_spend
                ],
            },
        }

    def get_expiring_contracts(self, days=90):
        """
        Get contracts expiring within the specified number of days.

        Args:
            days: Number of days to look ahead (default 90)

        Returns:
            List of expiring contracts with recommendations
        """
        today = date.today()
        expiring_date = today + timedelta(days=days)

        expiring = (
            self.contracts.filter(
                status="active", end_date__lte=expiring_date, end_date__gte=today
            )
            .select_related("supplier")
            .order_by("end_date")
        )

        result = []
        for contract in expiring:
            days_remaining = (contract.end_date - today).days

            # Calculate spend to date
            actual_spend = self.transactions.filter(
                supplier_id=contract.supplier_id,
                date__gte=contract.start_date,
                date__lte=today,
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

            utilization = (
                float(actual_spend / contract.total_value * 100)
                if contract.total_value > 0
                else 0
            )

            # Generate recommendation
            if utilization > 90:
                recommendation = "Renew with increased value"
                priority = "high"
            elif utilization > 70:
                recommendation = "Renew at current terms"
                priority = "medium"
            elif utilization > 50:
                recommendation = "Review and potentially reduce scope"
                priority = "medium"
            else:
                recommendation = "Evaluate need for renewal"
                priority = "low"

            # Check if within renewal notice period
            within_notice_period = days_remaining <= contract.renewal_notice_days

            result.append(
                {
                    "id": contract.id,
                    "uuid": str(contract.uuid),
                    "contract_number": contract.contract_number,
                    "title": contract.title,
                    "supplier_name": contract.supplier.name,
                    "end_date": contract.end_date.isoformat(),
                    "days_remaining": days_remaining,
                    "total_value": float(contract.total_value),
                    "actual_spend": float(actual_spend),
                    "utilization_percentage": round(utilization, 1),
                    "auto_renew": contract.auto_renew,
                    "within_notice_period": within_notice_period,
                    "recommendation": recommendation,
                    "priority": priority,
                }
            )

        return result

    def get_contract_performance(self, contract_id):
        """
        Get detailed performance metrics for a contract.

        Args:
            contract_id: Contract ID

        Returns:
            Dict with performance metrics
        """
        try:
            contract = self.contracts.get(id=contract_id)
        except Contract.DoesNotExist:
            return {"error": "Contract not found"}

        today = date.today()

        # Get all transactions for this supplier during contract period
        transactions = self.transactions.filter(
            supplier_id=contract.supplier_id,
            date__gte=contract.start_date,
            date__lte=min(contract.end_date, today),
        )

        # Calculate metrics
        total_spend = transactions.aggregate(total=Sum("amount"))["total"] or Decimal(
            "0"
        )
        transaction_count = transactions.count()

        # Monthly breakdown
        monthly_data = (
            transactions.annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("month")
        )

        # Calculate contract duration in months (elapsed-to-date, minimum 1).
        window_end = min(contract.end_date, today)
        duration_months = (
            (window_end.year - contract.start_date.year) * 12
            + (window_end.month - contract.start_date.month)
            + 1
        )

        expected_monthly = (
            float(contract.total_value / duration_months) if duration_months > 0 else 0
        )
        # Use the full elapsed contract duration as the denominator, not the
        # count of months with at least one transaction. Previously this
        # excluded gap-months, inflating the per-month average and producing
        # a misleading over-spend variance for contracts with sporadic usage.
        monthly_data_list = list(monthly_data)
        actual_monthly = (
            float(total_spend / duration_months) if duration_months > 0 else 0
        )

        # Variance analysis
        variance = actual_monthly - expected_monthly
        variance_percentage = (
            (variance / expected_monthly * 100) if expected_monthly > 0 else 0
        )

        return {
            "contract_id": contract_id,
            "total_spend": float(total_spend),
            "transaction_count": transaction_count,
            "utilization_percentage": round(
                (
                    float(total_spend / contract.total_value * 100)
                    if contract.total_value > 0
                    else 0
                ),
                1,
            ),
            "expected_monthly_spend": round(expected_monthly, 2),
            "actual_monthly_spend": round(actual_monthly, 2),
            "variance": round(variance, 2),
            "variance_percentage": round(variance_percentage, 1),
            "active_spend_months": len(monthly_data_list),
            "duration_months": duration_months,
            "monthly_breakdown": [
                {
                    "month": m["month"].strftime("%Y-%m"),
                    "amount": float(m["total"]),
                    "transaction_count": m["count"],
                }
                for m in monthly_data_list
            ],
        }

    def get_savings_opportunities(self):
        """
        Identify potential savings opportunities from contract analysis.

        Returns:
            List of savings opportunities
        """
        opportunities = []
        today = date.today()

        # 1. Underutilized contracts (< 50% utilization with > 6 months remaining)
        active_contracts = self.contracts.filter(status="active")

        for contract in active_contracts:
            days_remaining = (contract.end_date - today).days
            if days_remaining < 180:  # Skip contracts expiring soon
                continue

            actual_spend = self.transactions.filter(
                supplier_id=contract.supplier_id,
                date__gte=contract.start_date,
                date__lte=today,
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

            # Calculate expected spend to date
            total_days = (contract.end_date - contract.start_date).days
            # Clamp to 0 so future-dated contracts don't emit negative expected spend.
            elapsed_days = max(0, (today - contract.start_date).days)
            expected_spend = (
                contract.total_value * Decimal(str(elapsed_days / total_days))
                if total_days > 0
                else Decimal("0")
            )

            utilization = (
                float(actual_spend / expected_spend * 100) if expected_spend > 0 else 0
            )

            if utilization < 50:
                potential_savings = float(expected_spend - actual_spend)
                opportunities.append(
                    {
                        "type": "underutilized_contract",
                        "severity": "medium",
                        "contract_id": contract.id,
                        "contract_number": contract.contract_number,
                        "supplier_name": contract.supplier.name,
                        "title": f"Underutilized contract: {contract.title}",
                        "description": f"Contract is only {utilization:.0f}% utilized. Consider renegotiating terms.",
                        "potential_savings": round(potential_savings, 2),
                        "utilization_percentage": round(utilization, 1),
                    }
                )

        # 2. Off-contract spending (suppliers with spend but no active contract)
        contract_supplier_ids = set(
            self.contracts.filter(status="active").values_list("supplier_id", flat=True)
        )

        # Find suppliers with significant spend but no contract
        supplier_spend = (
            self.transactions.filter(date__gte=today - timedelta(days=365))  # Last year
            .exclude(supplier_id__in=contract_supplier_ids)
            .values("supplier_id", "supplier__name")
            .annotate(total=Sum("amount"), count=Count("id"))
            .filter(total__gte=10000)
            .order_by("-total")
        )  # Only significant spend

        for supplier in supplier_spend[:10]:  # Top 10 opportunities
            # Estimate savings (typically 5-15% from contract negotiation)
            estimated_savings = float(supplier["total"]) * 0.10

            opportunities.append(
                {
                    "type": "off_contract_spend",
                    "severity": (
                        "high" if float(supplier["total"]) > 50000 else "medium"
                    ),
                    "supplier_id": supplier["supplier_id"],
                    "supplier_name": supplier["supplier__name"],
                    "title": f'Off-contract spending: {supplier["supplier__name"]}',
                    "description": f'${supplier["total"]:,.0f} spent without a contract. Negotiate terms for savings.',
                    "annual_spend": float(supplier["total"]),
                    "transaction_count": supplier["count"],
                    "potential_savings": round(estimated_savings, 2),
                }
            )

        # 3. Duplicate supplier coverage (multiple suppliers for same category)
        # Check categories with multiple contracted suppliers
        category_suppliers = {}
        for contract in active_contracts.prefetch_related("categories"):
            for category in contract.categories.all():
                if category.id not in category_suppliers:
                    category_suppliers[category.id] = {
                        "name": category.name,
                        "suppliers": [],
                    }
                category_suppliers[category.id]["suppliers"].append(
                    {
                        "id": contract.supplier_id,
                        "name": contract.supplier.name,
                        "contract_value": float(contract.total_value),
                    }
                )

        for cat_id, data in category_suppliers.items():
            if len(data["suppliers"]) > 2:
                total_value = sum(s["contract_value"] for s in data["suppliers"])
                potential_savings = total_value * 0.15  # 15% consolidation savings

                opportunities.append(
                    {
                        "type": "supplier_consolidation",
                        "severity": "medium",
                        "category_id": cat_id,
                        "category_name": data["name"],
                        "title": f'Consolidation opportunity: {data["name"]}',
                        "description": f'{len(data["suppliers"])} suppliers for this category. Consider consolidation.',
                        "supplier_count": len(data["suppliers"]),
                        "total_contract_value": round(total_value, 2),
                        "potential_savings": round(potential_savings, 2),
                    }
                )

        # Sort by potential savings
        opportunities.sort(key=lambda x: x.get("potential_savings", 0), reverse=True)

        return opportunities

    def get_renewal_recommendations(self):
        """
        Get renewal recommendations for contracts.

        Returns:
            List of contracts with renewal recommendations
        """
        today = date.today()
        recommendations = []

        # Get contracts expiring in next 180 days
        upcoming = self.contracts.filter(
            status="active",
            end_date__lte=today + timedelta(days=180),
            end_date__gte=today,
        ).select_related("supplier")

        for contract in upcoming:
            days_remaining = (contract.end_date - today).days

            # Calculate performance metrics
            actual_spend = self.transactions.filter(
                supplier_id=contract.supplier_id,
                date__gte=contract.start_date,
                date__lte=today,
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

            utilization = (
                float(actual_spend / contract.total_value * 100)
                if contract.total_value > 0
                else 0
            )

            # Calculate trend (last 3 months vs previous 3 months)
            three_months_ago = today - timedelta(days=90)
            six_months_ago = today - timedelta(days=180)

            recent_spend = self.transactions.filter(
                supplier_id=contract.supplier_id,
                date__gte=three_months_ago,
                date__lte=today,
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

            previous_spend = self.transactions.filter(
                supplier_id=contract.supplier_id,
                date__gte=six_months_ago,
                date__lt=three_months_ago,
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

            trend = (
                "increasing"
                if recent_spend > previous_spend
                else "decreasing" if recent_spend < previous_spend else "stable"
            )

            # Generate recommendation
            if utilization > 100:
                action = "renew_increase"
                recommendation = "Renew with 20-30% increased value"
                priority = "high"
                suggested_value = float(contract.total_value) * 1.25
            elif utilization > 80:
                action = "renew_same"
                recommendation = "Renew at current or slightly increased terms"
                priority = "high"
                suggested_value = float(contract.total_value) * 1.1
            elif utilization > 50:
                action = "renew_decrease"
                recommendation = "Renew with reduced value or shorter term"
                priority = "medium"
                suggested_value = float(contract.total_value) * 0.8
            else:
                action = "evaluate"
                recommendation = (
                    "Evaluate need - consider not renewing or consolidating"
                )
                priority = "low"
                suggested_value = float(contract.total_value) * 0.5

            recommendations.append(
                {
                    "contract_id": contract.id,
                    "contract_number": contract.contract_number,
                    "title": contract.title,
                    "supplier_name": contract.supplier.name,
                    "end_date": contract.end_date.isoformat(),
                    "days_remaining": days_remaining,
                    "current_value": float(contract.total_value),
                    "actual_spend": float(actual_spend),
                    "utilization_percentage": round(utilization, 1),
                    "spend_trend": trend,
                    "action": action,
                    "recommendation": recommendation,
                    "priority": priority,
                    "suggested_new_value": round(suggested_value, 2),
                    "auto_renew": contract.auto_renew,
                }
            )

        # Sort by priority and days remaining
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(
            key=lambda x: (priority_order.get(x["priority"], 3), x["days_remaining"])
        )

        return recommendations

    def get_contract_vs_actual_spend(self, contract_id=None):
        """
        Compare contracted values vs actual spending.

        Args:
            contract_id: Optional specific contract ID

        Returns:
            Comparison data
        """
        today = date.today()

        if contract_id:
            contracts = self.contracts.filter(id=contract_id)
        else:
            contracts = self.contracts.filter(status="active")

        comparisons = []

        for contract in contracts.select_related("supplier"):
            # Calculate actual spend
            actual_spend = self.transactions.filter(
                supplier_id=contract.supplier_id,
                date__gte=contract.start_date,
                date__lte=min(contract.end_date, today),
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

            # Calculate expected spend to date (prorated). Clamp elapsed_days
            # to 0 so future-dated contracts don't produce negative expected
            # spend (which flipped the variance sign in consumers).
            total_days = (contract.end_date - contract.start_date).days
            elapsed_days = max(
                0, (min(today, contract.end_date) - contract.start_date).days
            )

            if total_days > 0:
                expected_spend = contract.total_value * Decimal(
                    str(elapsed_days / total_days)
                )
            else:
                expected_spend = contract.total_value

            variance = float(actual_spend - expected_spend)
            variance_percentage = (
                (variance / float(expected_spend) * 100) if expected_spend > 0 else 0
            )

            status = "on_track"
            if variance_percentage > 10:
                status = "over_contract"
            elif variance_percentage < -20:
                status = "under_contract"

            comparisons.append(
                {
                    "contract_id": contract.id,
                    "contract_number": contract.contract_number,
                    "title": contract.title,
                    "supplier_name": contract.supplier.name,
                    "contract_value": float(contract.total_value),
                    "expected_spend_to_date": round(float(expected_spend), 2),
                    "actual_spend": float(actual_spend),
                    "variance": round(variance, 2),
                    "variance_percentage": round(variance_percentage, 1),
                    "status": status,
                    "days_elapsed": elapsed_days,
                    "days_remaining": (
                        (contract.end_date - today).days
                        if contract.end_date > today
                        else 0
                    ),
                }
            )

        return comparisons
