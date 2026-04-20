"""
LLM Response Validation Layer for Hallucination Prevention.

Validates AI-generated responses against source data to ensure:
- Monetary values don't exceed actual spend
- Referenced suppliers/categories exist in the organization
- Date ranges are valid and within data bounds
- Percentages and ratios are mathematically consistent

Adjusts confidence scores based on validation results.
"""
import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional, Any, Set

from django.db.models import Sum, Min, Max

logger = logging.getLogger(__name__)


class LLMResponseValidator:
    """
    Post-LLM validation to prevent hallucinations and fabricated data.

    Validates AI responses against actual database data, flagging
    errors by severity and adjusting confidence scores accordingly.

    Severity levels:
    - critical: Factual error that would mislead decisions (blocks recommendation)
    - error: Significant inaccuracy (reduces confidence significantly)
    - warning: Minor issue or unverifiable claim (reduces confidence slightly)
    """

    SEVERITY_WEIGHTS = {
        'critical': 0.30,
        'error': 0.15,
        'warning': 0.05,
    }

    def __init__(self, organization_id: int):
        """
        Initialize validator for an organization.

        Args:
            organization_id: Organization to validate against
        """
        self.organization_id = organization_id
        self._supplier_names: Optional[Set[str]] = None
        self._category_names: Optional[Set[str]] = None
        self._data_bounds: Optional[Dict] = None

    @property
    def supplier_names(self) -> Set[str]:
        """Lazy-load supplier names for this organization."""
        if self._supplier_names is None:
            from apps.procurement.models import Supplier
            self._supplier_names = set(
                Supplier.objects.filter(
                    organization_id=self.organization_id,
                    is_active=True
                ).values_list('name', flat=True)
            )
            self._supplier_names.update(
                name.lower() for name in self._supplier_names
            )
        return self._supplier_names

    @property
    def category_names(self) -> Set[str]:
        """Lazy-load category names for this organization."""
        if self._category_names is None:
            from apps.procurement.models import Category
            self._category_names = set(
                Category.objects.filter(
                    organization_id=self.organization_id,
                    is_active=True
                ).values_list('name', flat=True)
            )
            self._category_names.update(
                name.lower() for name in self._category_names
            )
        return self._category_names

    @property
    def data_bounds(self) -> Dict:
        """Lazy-load transaction data bounds."""
        if self._data_bounds is None:
            from apps.procurement.models import Transaction
            bounds = Transaction.objects.filter(
                organization_id=self.organization_id
            ).aggregate(
                total_spend=Sum('amount'),
                min_date=Min('date'),
                max_date=Max('date'),
            )
            self._data_bounds = {
                'total_spend': float(bounds['total_spend'] or 0),
                'min_date': bounds['min_date'],
                'max_date': bounds['max_date'],
            }
        return self._data_bounds

    def validate(
        self,
        response: Dict,
        source_data: Optional[Dict] = None
    ) -> Dict:
        """
        Validate an LLM response against source data.

        Args:
            response: The AI-generated response dictionary
            source_data: Optional source data context for validation

        Returns:
            Validation result with errors, adjusted confidence, and status
        """
        errors = []
        source_data = source_data or {}

        errors.extend(self._validate_monetary_values(response, source_data))
        errors.extend(self._validate_suppliers(response))
        errors.extend(self._validate_categories(response))
        errors.extend(self._validate_dates(response))
        errors.extend(self._validate_percentages(response))
        errors.extend(self._validate_savings_estimates(response, source_data))

        critical_count = len([e for e in errors if e['severity'] == 'critical'])
        error_count = len([e for e in errors if e['severity'] == 'error'])
        warning_count = len([e for e in errors if e['severity'] == 'warning'])

        original_confidence = self._extract_confidence(response)
        adjusted_confidence = self._calculate_adjusted_confidence(
            original_confidence, critical_count, error_count, warning_count
        )

        is_valid = critical_count == 0 and error_count == 0

        if errors:
            logger.warning(
                f"LLM response validation found {len(errors)} issues "
                f"(critical={critical_count}, error={error_count}, warning={warning_count})"
            )

        return {
            'validated': is_valid,
            'errors': errors,
            'confidence_original': original_confidence,
            'confidence_adjusted': adjusted_confidence,
            'critical_count': critical_count,
            'error_count': error_count,
            'warning_count': warning_count,
            'total_issues': len(errors),
        }

    def _validate_monetary_values(
        self,
        response: Dict,
        source_data: Dict
    ) -> List[Dict]:
        """Validate monetary values against database bounds."""
        errors = []
        total_spend = source_data.get('total_spend', self.data_bounds['total_spend'])

        if total_spend == 0:
            return errors

        monetary_fields = [
            ('total_savings', 'Total savings'),
            ('savings_estimate', 'Savings estimate'),
            ('total_savings_potential', 'Total savings potential'),
            ('implementation_cost', 'Implementation cost'),
        ]

        for field, label in monetary_fields:
            value = self._extract_nested_value(response, field)
            if value is not None:
                try:
                    amount = float(value)
                    if amount > total_spend:
                        errors.append({
                            'field': field,
                            'issue': f"{label} ${amount:,.2f} exceeds total spend ${total_spend:,.2f}",
                            'severity': 'critical',
                            'claimed_value': amount,
                            'max_allowed': total_spend,
                        })
                    elif amount > total_spend * 0.5:
                        errors.append({
                            'field': field,
                            'issue': f"{label} ${amount:,.2f} is >50% of total spend - verify accuracy",
                            'severity': 'warning',
                            'claimed_value': amount,
                            'threshold': total_spend * 0.5,
                        })
                except (ValueError, TypeError):
                    pass

        for action in response.get('priority_actions', []):
            savings = action.get('savings_estimate')
            if savings is not None:
                try:
                    amount = float(savings)
                    if amount > total_spend:
                        errors.append({
                            'field': 'priority_actions.savings_estimate',
                            'issue': f"Action savings ${amount:,.2f} exceeds total spend",
                            'severity': 'critical',
                            'action': action.get('action', 'unknown')[:50],
                        })
                except (ValueError, TypeError):
                    pass

        return errors

    def _validate_suppliers(self, response: Dict) -> List[Dict]:
        """Validate that referenced suppliers exist in the organization."""
        errors = []
        mentioned_suppliers = self._extract_entity_names(response, 'supplier')

        for supplier in mentioned_suppliers:
            if supplier.lower() not in self.supplier_names and supplier not in self.supplier_names:
                errors.append({
                    'field': 'suppliers',
                    'issue': f"Unknown supplier referenced: {supplier}",
                    'severity': 'warning',
                    'entity': supplier,
                })

        return errors

    def _validate_categories(self, response: Dict) -> List[Dict]:
        """Validate that referenced categories exist in the organization."""
        errors = []
        mentioned_categories = self._extract_entity_names(response, 'category')

        for category in mentioned_categories:
            if category.lower() not in self.category_names and category not in self.category_names:
                errors.append({
                    'field': 'categories',
                    'issue': f"Unknown category referenced: {category}",
                    'severity': 'warning',
                    'entity': category,
                })

        return errors

    def _validate_dates(self, response: Dict) -> List[Dict]:
        """Validate date ranges in the response."""
        errors = []

        date_range = response.get('date_range') or response.get('analysis_period')
        if isinstance(date_range, dict):
            start = date_range.get('start')
            end = date_range.get('end')

            if start and end:
                try:
                    start_date = self._parse_date(start)
                    end_date = self._parse_date(end)

                    if start_date and end_date and start_date > end_date:
                        errors.append({
                            'field': 'date_range',
                            'issue': 'Start date is after end date',
                            'severity': 'error',
                            'start': str(start),
                            'end': str(end),
                        })

                    if self.data_bounds['min_date'] and self.data_bounds['max_date']:
                        if start_date and start_date < self.data_bounds['min_date']:
                            errors.append({
                                'field': 'date_range',
                                'issue': f"Date {start} is before earliest data ({self.data_bounds['min_date']})",
                                'severity': 'warning',
                            })
                        if end_date and end_date > self.data_bounds['max_date']:
                            errors.append({
                                'field': 'date_range',
                                'issue': f"Date {end} is after latest data ({self.data_bounds['max_date']})",
                                'severity': 'warning',
                            })
                except (ValueError, TypeError):
                    pass

        return errors

    def _validate_percentages(self, response: Dict) -> List[Dict]:
        """Validate percentage values are within valid ranges."""
        errors = []

        percentage_fields = [
            'roi_percentage', 'savings_percentage', 'compliance_rate',
            'concentration_percentage', 'match_rate',
        ]

        for field in percentage_fields:
            value = self._extract_nested_value(response, field)
            if value is not None:
                try:
                    pct = float(value)
                    if pct < 0 or pct > 100:
                        errors.append({
                            'field': field,
                            'issue': f"Percentage {pct}% is outside valid range (0-100)",
                            'severity': 'error',
                            'value': pct,
                        })
                    elif pct > 50 and field in ['roi_percentage', 'savings_percentage']:
                        errors.append({
                            'field': field,
                            'issue': f"Unusually high {field}: {pct}% - verify accuracy",
                            'severity': 'warning',
                            'value': pct,
                        })
                except (ValueError, TypeError):
                    pass

        return errors

    def _validate_savings_estimates(
        self,
        response: Dict,
        source_data: Dict
    ) -> List[Dict]:
        """Cross-validate savings estimates against insight predictions."""
        errors = []

        insights = source_data.get('insights', [])
        if not insights:
            return errors

        total_predicted = sum(
            float(i.get('estimated_savings', 0) or 0)
            for i in insights
        )

        total_claimed = 0
        for action in response.get('priority_actions', []):
            savings = action.get('savings_estimate')
            if savings:
                try:
                    total_claimed += float(savings)
                except (ValueError, TypeError):
                    pass

        if total_predicted > 0 and total_claimed > total_predicted * 2:
            errors.append({
                'field': 'priority_actions',
                'issue': f"Total claimed savings ${total_claimed:,.2f} exceeds 2x insight predictions ${total_predicted:,.2f}",
                'severity': 'warning',
                'claimed': total_claimed,
                'predicted': total_predicted,
            })

        return errors

    def _extract_nested_value(self, obj: Any, key: str) -> Any:
        """Extract a value from nested dict/list structures."""
        if isinstance(obj, dict):
            if key in obj:
                return obj[key]
            for v in obj.values():
                result = self._extract_nested_value(v, key)
                if result is not None:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = self._extract_nested_value(item, key)
                if result is not None:
                    return result
        return None

    def _extract_entity_names(
        self,
        response: Dict,
        entity_type: str
    ) -> Set[str]:
        """Extract entity names (suppliers/categories) from response text."""
        entities = set()

        def extract_from_obj(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    key_lower = k.lower()
                    if entity_type in key_lower:
                        if isinstance(v, str):
                            entities.add(v)
                        elif isinstance(v, list):
                            for item in v:
                                if isinstance(item, str):
                                    entities.add(item)
                    extract_from_obj(v)
            elif isinstance(obj, list):
                for item in obj:
                    extract_from_obj(item)

        extract_from_obj(response)
        return entities

    def _extract_confidence(self, response: Dict) -> float:
        """Extract confidence score from response."""
        confidence = self._extract_nested_value(response, 'confidence')
        if confidence is not None:
            try:
                conf = float(confidence)
                return conf if 0 <= conf <= 1 else 0.8
            except (ValueError, TypeError):
                pass
        return 0.8

    def _calculate_adjusted_confidence(
        self,
        original: float,
        critical: int,
        error: int,
        warning: int
    ) -> float:
        """Calculate adjusted confidence based on validation errors."""
        penalty = (
            critical * self.SEVERITY_WEIGHTS['critical'] +
            error * self.SEVERITY_WEIGHTS['error'] +
            warning * self.SEVERITY_WEIGHTS['warning']
        )
        adjusted = original * (1 - penalty)
        return max(0.0, min(1.0, adjusted))

    def _parse_date(self, date_str: Any) -> Optional[datetime]:
        """Parse a date string into a datetime object."""
        if isinstance(date_str, datetime):
            return date_str
        if not isinstance(date_str, str):
            return None

        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%m/%d/%Y',
            '%d/%m/%Y',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def validate_insight(self, insight: Dict) -> Dict:
        """
        Validate a single insight dictionary.

        Args:
            insight: Individual insight to validate

        Returns:
            Validation result for the insight
        """
        errors = []

        if insight.get('estimated_savings'):
            try:
                savings = float(insight['estimated_savings'])
                if savings > self.data_bounds['total_spend']:
                    errors.append({
                        'field': 'estimated_savings',
                        'issue': f"Savings ${savings:,.2f} exceeds total spend",
                        'severity': 'critical',
                    })
                elif savings < 0:
                    errors.append({
                        'field': 'estimated_savings',
                        'issue': 'Negative savings value',
                        'severity': 'error',
                    })
            except (ValueError, TypeError):
                errors.append({
                    'field': 'estimated_savings',
                    'issue': 'Invalid savings value',
                    'severity': 'error',
                })

        attribution = insight.get('attribution', {})
        if attribution.get('supplier_names'):
            for supplier in attribution['supplier_names']:
                if supplier.lower() not in self.supplier_names:
                    errors.append({
                        'field': 'attribution.supplier_names',
                        'issue': f"Unknown supplier: {supplier}",
                        'severity': 'warning',
                    })

        if attribution.get('category_names'):
            for category in attribution['category_names']:
                if category.lower() not in self.category_names:
                    errors.append({
                        'field': 'attribution.category_names',
                        'issue': f"Unknown category: {category}",
                        'severity': 'warning',
                    })

        original_confidence = insight.get('confidence', 0.8)
        try:
            original_confidence = float(original_confidence)
        except (ValueError, TypeError):
            original_confidence = 0.8

        critical = len([e for e in errors if e['severity'] == 'critical'])
        error_count = len([e for e in errors if e['severity'] == 'error'])
        warning = len([e for e in errors if e['severity'] == 'warning'])

        return {
            'validated': critical == 0 and error_count == 0,
            'errors': errors,
            'confidence_original': original_confidence,
            'confidence_adjusted': self._calculate_adjusted_confidence(
                original_confidence, critical, error_count, warning
            ),
        }


def validate_llm_response(
    organization_id: int,
    response: Dict,
    source_data: Optional[Dict] = None
) -> Dict:
    """
    Convenience function to validate an LLM response.

    Args:
        organization_id: Organization to validate against
        response: AI-generated response
        source_data: Optional source data context

    Returns:
        Validation result dictionary
    """
    validator = LLMResponseValidator(organization_id)
    return validator.validate(response, source_data)
