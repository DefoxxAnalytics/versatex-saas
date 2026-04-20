"""
Compliance and Maverick Spend Analytics Service

Provides analysis for:
- Policy violation detection and tracking
- Maverick (off-contract) spend identification
- Supplier compliance scoring
- Violation trend analysis
"""
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncMonth
from apps.procurement.models import (
    Transaction,
    Supplier,
    Category,
    Contract,
    SpendingPolicy,
    PolicyViolation
)


class ComplianceService:
    """
    Service class for compliance and maverick spend analytics.
    """

    def __init__(self, organization):
        """
        Initialize the compliance service.

        Args:
            organization: The organization to analyze
        """
        self.organization = organization
        self.transactions = Transaction.objects.filter(organization=organization)
        self.contracts = Contract.objects.filter(organization=organization)
        self.policies = SpendingPolicy.objects.filter(
            organization=organization,
            is_active=True
        )
        self.violations = PolicyViolation.objects.filter(organization=organization)

    def get_compliance_overview(self):
        """
        Get compliance overview statistics.

        Returns:
            dict: Compliance metrics including violation counts, compliance rate, maverick spend
        """
        total_transactions = self.transactions.count()
        total_spend = float(self.transactions.aggregate(Sum('amount'))['amount__sum'] or 0)

        # Get violations stats
        total_violations = self.violations.count()
        unresolved_violations = self.violations.filter(is_resolved=False).count()
        resolved_today = self.violations.filter(
            is_resolved=True,
            resolved_at__date=datetime.now().date()
        ).count()

        # Violation severity breakdown
        severity_counts = dict(
            self.violations.values('severity').annotate(count=Count('id')).values_list('severity', 'count')
        )

        # Calculate compliance rate (transactions without violations)
        violating_transaction_ids = self.violations.values_list('transaction_id', flat=True).distinct()
        compliant_transactions = total_transactions - len(violating_transaction_ids)
        compliance_rate = (compliant_transactions / total_transactions * 100) if total_transactions > 0 else 100

        # Calculate maverick spend (off-contract)
        contracted_suppliers = self.contracts.filter(
            status='active'
        ).values_list('supplier_id', flat=True)

        on_contract_spend = float(self.transactions.filter(
            supplier_id__in=contracted_suppliers
        ).aggregate(Sum('amount'))['amount__sum'] or 0)

        maverick_spend = total_spend - on_contract_spend
        maverick_percentage = (maverick_spend / total_spend * 100) if total_spend > 0 else 0

        return {
            'total_transactions': total_transactions,
            'total_spend': total_spend,
            'compliance_rate': round(compliance_rate, 1),
            'total_violations': total_violations,
            'unresolved_violations': unresolved_violations,
            'resolved_today': resolved_today,
            'severity_breakdown': {
                'critical': severity_counts.get('critical', 0),
                'high': severity_counts.get('high', 0),
                'medium': severity_counts.get('medium', 0),
                'low': severity_counts.get('low', 0),
            },
            'maverick_spend': maverick_spend,
            'maverick_percentage': round(maverick_percentage, 1),
            'on_contract_spend': on_contract_spend,
            'active_policies': self.policies.count(),
        }

    def get_maverick_spend_analysis(self):
        """
        Analyze maverick (off-contract) spending patterns.

        Returns:
            dict: Detailed maverick spend analysis by category and supplier
        """
        # Get contracted suppliers
        contracted_suppliers = set(self.contracts.filter(
            status='active'
        ).values_list('supplier_id', flat=True))

        # Get contracted categories
        contracted_categories = set()
        for contract in self.contracts.filter(status='active').prefetch_related('categories'):
            contracted_categories.update(contract.categories.values_list('id', flat=True))

        # Analyze by supplier
        supplier_spend = self.transactions.values(
            'supplier_id',
            'supplier__name'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')

        maverick_suppliers = []
        on_contract_suppliers = []

        for item in supplier_spend:
            supplier_data = {
                'supplier_id': item['supplier_id'],
                'supplier_name': item['supplier__name'],
                'spend': float(item['total']),
                'transaction_count': item['count'],
            }

            if item['supplier_id'] in contracted_suppliers:
                on_contract_suppliers.append(supplier_data)
            else:
                maverick_suppliers.append(supplier_data)

        # Analyze by category
        category_spend = self.transactions.values(
            'category_id',
            'category__name'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')

        maverick_categories = []
        for item in category_spend:
            # Check if category has no contract coverage
            if item['category_id'] not in contracted_categories:
                maverick_categories.append({
                    'category_id': item['category_id'],
                    'category_name': item['category__name'],
                    'spend': float(item['total']),
                    'transaction_count': item['count'],
                })

        total_maverick_spend = sum(s['spend'] for s in maverick_suppliers)
        total_spend = float(self.transactions.aggregate(Sum('amount'))['amount__sum'] or 0)

        return {
            'total_maverick_spend': total_maverick_spend,
            'total_on_contract_spend': total_spend - total_maverick_spend,
            'maverick_percentage': round((total_maverick_spend / total_spend * 100) if total_spend > 0 else 0, 1),
            'maverick_suppliers': maverick_suppliers[:20],  # Top 20
            'maverick_supplier_count': len(maverick_suppliers),
            'maverick_categories': maverick_categories[:10],
            'on_contract_suppliers': on_contract_suppliers[:10],
            'recommendations': self._generate_maverick_recommendations(
                maverick_suppliers, maverick_categories, total_maverick_spend
            ),
        }

    def _generate_maverick_recommendations(self, maverick_suppliers, maverick_categories, total_maverick_spend):
        """Generate recommendations for reducing maverick spend."""
        recommendations = []

        # High maverick spend suppliers
        high_spend_suppliers = [s for s in maverick_suppliers if s['spend'] > 10000]
        if high_spend_suppliers:
            recommendations.append({
                'type': 'contract_negotiation',
                'title': 'Negotiate contracts with high-spend maverick suppliers',
                'description': f'{len(high_spend_suppliers)} suppliers have significant off-contract spend',
                'potential_savings': sum(s['spend'] * 0.1 for s in high_spend_suppliers),  # 10% savings estimate
                'affected_suppliers': [s['supplier_name'] for s in high_spend_suppliers[:5]],
                'priority': 'high',
            })

        # Uncovered categories
        if maverick_categories:
            recommendations.append({
                'type': 'category_coverage',
                'title': 'Establish contracts for uncovered categories',
                'description': f'{len(maverick_categories)} spending categories have no contract coverage',
                'potential_savings': sum(c['spend'] * 0.05 for c in maverick_categories),  # 5% savings estimate
                'affected_categories': [c['category_name'] for c in maverick_categories[:5]],
                'priority': 'medium',
            })

        # Overall maverick spend threshold
        if total_maverick_spend > 50000:
            recommendations.append({
                'type': 'spend_consolidation',
                'title': 'Consolidate maverick spend under contracts',
                'description': 'Total maverick spend exceeds recommended threshold',
                'potential_savings': total_maverick_spend * 0.08,  # 8% savings estimate
                'priority': 'high',
            })

        return recommendations

    def get_policy_violations(self, resolved=None, severity=None, limit=100):
        """
        Get policy violations with optional filtering.

        Args:
            resolved: Filter by resolution status (True/False/None for all)
            severity: Filter by severity level
            limit: Maximum number of violations to return

        Returns:
            list: Policy violations with details
        """
        violations = self.violations.select_related(
            'transaction',
            'transaction__supplier',
            'transaction__category',
            'policy'
        )

        if resolved is not None:
            violations = violations.filter(is_resolved=resolved)

        if severity:
            violations = violations.filter(severity=severity)

        violations = violations.order_by('-created_at')[:limit]

        return [
            {
                'id': v.id,
                'uuid': str(v.uuid),
                'transaction_id': v.transaction_id,
                'transaction_date': v.transaction.date.isoformat(),
                'transaction_amount': float(v.transaction.amount),
                'supplier_name': v.transaction.supplier.name,
                'category_name': v.transaction.category.name,
                'policy_name': v.policy.name,
                'violation_type': v.violation_type,
                'violation_type_display': v.get_violation_type_display(),
                'severity': v.severity,
                'details': v.details,
                'is_resolved': v.is_resolved,
                'resolved_at': v.resolved_at.isoformat() if v.resolved_at else None,
                'resolution_notes': v.resolution_notes,
                'created_at': v.created_at.isoformat(),
            }
            for v in violations
        ]

    def get_violation_trends(self, months=12):
        """
        Analyze violation trends over time.

        Args:
            months: Number of months to analyze

        Returns:
            dict: Violation trends by month and type
        """
        cutoff_date = datetime.now().date() - timedelta(days=months * 30)

        monthly_violations = self.violations.filter(
            created_at__date__gte=cutoff_date
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total=Count('id'),
            resolved=Count('id', filter=Q(is_resolved=True)),
            critical=Count('id', filter=Q(severity='critical')),
            high=Count('id', filter=Q(severity='high')),
        ).order_by('month')

        # Violations by type
        by_type = dict(
            self.violations.filter(
                created_at__date__gte=cutoff_date
            ).values('violation_type').annotate(
                count=Count('id')
            ).values_list('violation_type', 'count')
        )

        return {
            'monthly_trend': [
                {
                    'month': item['month'].strftime('%Y-%m'),
                    'total': item['total'],
                    'resolved': item['resolved'],
                    'resolution_rate': round((item['resolved'] / item['total'] * 100) if item['total'] > 0 else 0, 1),
                    'critical': item['critical'],
                    'high': item['high'],
                }
                for item in monthly_violations
            ],
            'by_type': {
                'amount_exceeded': by_type.get('amount_exceeded', 0),
                'non_preferred_supplier': by_type.get('non_preferred_supplier', 0),
                'restricted_category': by_type.get('restricted_category', 0),
                'no_contract': by_type.get('no_contract', 0),
                'approval_missing': by_type.get('approval_missing', 0),
            },
        }

    def evaluate_transaction(self, transaction_id):
        """
        Evaluate a single transaction against all active policies.

        Args:
            transaction_id: ID of the transaction to evaluate

        Returns:
            list: Detected violations for the transaction
        """
        try:
            transaction = self.transactions.select_related('supplier', 'category').get(id=transaction_id)
        except Transaction.DoesNotExist:
            return []

        violations = []

        for policy in self.policies:
            rules = policy.rules or {}

            # Check maximum transaction amount
            max_amount = rules.get('max_transaction_amount')
            if max_amount and float(transaction.amount) > max_amount:
                violations.append({
                    'policy_id': policy.id,
                    'policy_name': policy.name,
                    'violation_type': 'amount_exceeded',
                    'severity': 'high' if float(transaction.amount) > max_amount * 2 else 'medium',
                    'details': {
                        'limit': max_amount,
                        'actual': float(transaction.amount),
                        'excess': float(transaction.amount) - max_amount,
                    },
                })

            # Check preferred suppliers
            preferred_suppliers = rules.get('preferred_suppliers', [])
            if preferred_suppliers and str(transaction.supplier.uuid) not in preferred_suppliers:
                violations.append({
                    'policy_id': policy.id,
                    'policy_name': policy.name,
                    'violation_type': 'non_preferred_supplier',
                    'severity': 'low',
                    'details': {
                        'supplier': transaction.supplier.name,
                    },
                })

            # Check restricted categories
            restricted_categories = rules.get('restricted_categories', [])
            if str(transaction.category.uuid) in restricted_categories:
                violations.append({
                    'policy_id': policy.id,
                    'policy_name': policy.name,
                    'violation_type': 'restricted_category',
                    'severity': 'high',
                    'details': {
                        'category': transaction.category.name,
                    },
                })

            # Check contract requirement
            if rules.get('require_contract'):
                has_contract = self.contracts.filter(
                    supplier=transaction.supplier,
                    status='active',
                    start_date__lte=transaction.date,
                    end_date__gte=transaction.date,
                ).exists()

                if not has_contract:
                    violations.append({
                        'policy_id': policy.id,
                        'policy_name': policy.name,
                        'violation_type': 'no_contract',
                        'severity': 'medium',
                        'details': {
                            'supplier': transaction.supplier.name,
                        },
                    })

        return violations

    def resolve_violation(self, violation_id, user, resolution_notes):
        """
        Resolve a policy violation.

        Args:
            violation_id: ID of the violation to resolve
            user: User resolving the violation
            resolution_notes: Notes explaining the resolution

        Returns:
            dict: Updated violation data or None if not found
        """
        try:
            violation = self.violations.get(id=violation_id)
        except PolicyViolation.DoesNotExist:
            return None

        violation.is_resolved = True
        violation.resolved_by = user
        violation.resolved_at = datetime.now()
        violation.resolution_notes = resolution_notes
        violation.save()

        return {
            'id': violation.id,
            'is_resolved': violation.is_resolved,
            'resolved_at': violation.resolved_at.isoformat(),
            'resolution_notes': violation.resolution_notes,
        }

    def get_supplier_compliance_scores(self):
        """
        Calculate compliance scores for each supplier.

        Returns:
            list: Suppliers with compliance scores
        """
        suppliers = Supplier.objects.filter(organization=self.organization, is_active=True)

        scores = []
        for supplier in suppliers:
            # Get supplier transactions
            supplier_transactions = self.transactions.filter(supplier=supplier)
            transaction_count = supplier_transactions.count()

            if transaction_count == 0:
                continue

            # Get violations for this supplier's transactions
            supplier_violations = self.violations.filter(
                transaction__supplier=supplier
            )
            violation_count = supplier_violations.count()
            unresolved_count = supplier_violations.filter(is_resolved=False).count()

            # Calculate score (100 - penalty for violations)
            violation_rate = (violation_count / transaction_count) if transaction_count > 0 else 0
            base_score = 100 - (violation_rate * 100)

            # Additional penalty for unresolved violations
            unresolved_penalty = min(unresolved_count * 2, 20)
            score = max(0, base_score - unresolved_penalty)

            # Check contract status
            has_active_contract = self.contracts.filter(
                supplier=supplier,
                status='active'
            ).exists()

            scores.append({
                'supplier_id': supplier.id,
                'supplier_name': supplier.name,
                'compliance_score': round(score, 1),
                'transaction_count': transaction_count,
                'violation_count': violation_count,
                'unresolved_violations': unresolved_count,
                'has_contract': has_active_contract,
                'total_spend': float(supplier_transactions.aggregate(Sum('amount'))['amount__sum'] or 0),
                'risk_level': 'high' if score < 70 else ('medium' if score < 85 else 'low'),
            })

        # Sort by score ascending (worst first)
        scores.sort(key=lambda x: x['compliance_score'])

        return scores

    def get_policies_list(self):
        """
        Get list of all spending policies.

        Returns:
            list: Active spending policies with rule summaries
        """
        policies = self.policies.all()

        return [
            {
                'id': p.id,
                'uuid': str(p.uuid),
                'name': p.name,
                'description': p.description,
                'is_active': p.is_active,
                'rules_summary': self._summarize_rules(p.rules),
                'violation_count': self.violations.filter(policy=p).count(),
                'created_at': p.created_at.isoformat(),
            }
            for p in policies
        ]

    def _summarize_rules(self, rules):
        """Summarize policy rules for display."""
        if not rules:
            return []

        summary = []

        if 'max_transaction_amount' in rules:
            summary.append(f"Max transaction: ${rules['max_transaction_amount']:,.0f}")

        if 'required_approval_threshold' in rules:
            summary.append(f"Approval required above: ${rules['required_approval_threshold']:,.0f}")

        if rules.get('require_contract'):
            summary.append("Contract required")

        if rules.get('preferred_suppliers'):
            count = len(rules['preferred_suppliers'])
            summary.append(f"{count} preferred supplier(s)")

        if rules.get('restricted_categories'):
            count = len(rules['restricted_categories'])
            summary.append(f"{count} restricted category(ies)")

        return summary
