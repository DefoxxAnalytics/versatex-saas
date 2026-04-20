"""
AI Insights Service - Intelligent recommendations for procurement analytics.

Provides:
- Cost optimization insights (price variance detection)
- Supplier risk analysis (concentration risk)
- Anomaly detection (statistical outliers)
- Consolidation recommendations

Supports hybrid mode: Built-in ML + Optional External AI (Claude/OpenAI)

Enhancement features:
- Structured AI output via tool calling (predictable response format)
- Redis-based caching to reduce API costs (~70% cost reduction)
- Rich context building for better AI recommendations
- Multi-provider support with automatic failover
"""
import json
import uuid
import logging
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict

from django.db.models import Sum, Count, Avg, StdDev, F, Q
from django.db.models.functions import TruncMonth

from apps.procurement.models import Transaction, Supplier, Category
from .services import AnalyticsService
from .ai_cache import AIInsightsCache
from .ai_providers import AIProviderManager

logger = logging.getLogger(__name__)


# Structured output tool schema for Claude API
# Forces AI to return predictable, parseable JSON
INSIGHT_ENHANCEMENT_TOOL = {
    "name": "provide_procurement_recommendations",
    "description": "Provide structured procurement recommendations based on insights analysis",
    "input_schema": {
        "type": "object",
        "properties": {
            "priority_actions": {
                "type": "array",
                "description": "Ranked list of recommended actions, ordered by impact",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Specific, actionable recommendation"
                        },
                        "impact": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": "Expected business impact"
                        },
                        "effort": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "Implementation effort required"
                        },
                        "savings_estimate": {
                            "type": "number",
                            "description": "Estimated annual savings in USD (optional)"
                        },
                        "timeframe": {
                            "type": "string",
                            "description": "Expected implementation timeframe"
                        },
                        "affected_insight_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "IDs of insights this action addresses"
                        }
                    },
                    "required": ["action", "impact", "effort"]
                }
            },
            "risk_assessment": {
                "type": "object",
                "description": "Overall risk assessment based on insights",
                "properties": {
                    "overall_risk_level": {
                        "type": "string",
                        "enum": ["critical", "high", "moderate", "low"]
                    },
                    "key_risks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Top risk factors identified"
                    },
                    "mitigation_steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Recommended risk mitigation actions"
                    }
                }
            },
            "quick_wins": {
                "type": "array",
                "description": "Actions that can be taken immediately with minimal effort",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "expected_benefit": {"type": "string"}
                    },
                    "required": ["action", "expected_benefit"]
                }
            },
            "strategic_summary": {
                "type": "string",
                "description": "Executive summary of procurement health and top recommendations (2-3 sentences)"
            }
        },
        "required": ["priority_actions", "strategic_summary"]
    }
}

# Tool schema for deep insight analysis
DEEP_ANALYSIS_TOOL = {
    "name": "provide_deep_insight_analysis",
    "description": "Provide comprehensive deep analysis of a specific procurement insight",
    "input_schema": {
        "type": "object",
        "properties": {
            "root_cause_analysis": {
                "type": "object",
                "description": "Analysis of the root cause of the insight",
                "properties": {
                    "primary_cause": {"type": "string"},
                    "contributing_factors": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["primary_cause", "contributing_factors"]
            },
            "implementation_roadmap": {
                "type": "array",
                "description": "Phased implementation plan",
                "items": {
                    "type": "object",
                    "properties": {
                        "phase": {"type": "string"},
                        "tasks": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "timeline": {"type": "string"},
                        "resources_required": {"type": "string"}
                    },
                    "required": ["phase", "tasks", "timeline"]
                }
            },
            "financial_impact": {
                "type": "object",
                "description": "Detailed financial analysis",
                "properties": {
                    "total_savings_potential": {"type": "number"},
                    "implementation_cost": {"type": "number"},
                    "roi_percentage": {"type": "number"},
                    "payback_period": {"type": "string"},
                    "savings_breakdown": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "category": {"type": "string"},
                                "amount": {"type": "number"}
                            }
                        }
                    }
                },
                "required": ["total_savings_potential"]
            },
            "risk_factors": {
                "type": "array",
                "description": "Potential risks and mitigation strategies",
                "items": {
                    "type": "object",
                    "properties": {
                        "risk": {"type": "string"},
                        "likelihood": {
                            "type": "string",
                            "enum": ["low", "medium", "high"]
                        },
                        "impact": {
                            "type": "string",
                            "enum": ["low", "medium", "high"]
                        },
                        "mitigation": {"type": "string"}
                    },
                    "required": ["risk", "mitigation"]
                }
            },
            "success_metrics": {
                "type": "array",
                "description": "KPIs to track implementation success",
                "items": {
                    "type": "object",
                    "properties": {
                        "metric": {"type": "string"},
                        "target": {"type": "string"},
                        "measurement_method": {"type": "string"}
                    },
                    "required": ["metric", "target"]
                }
            },
            "stakeholder_mapping": {
                "type": "array",
                "description": "Key stakeholders and their roles",
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string"},
                        "responsibility": {"type": "string"},
                        "engagement_level": {
                            "type": "string",
                            "enum": ["inform", "consult", "collaborate", "lead"]
                        }
                    },
                    "required": ["role", "responsibility"]
                }
            },
            "industry_context": {
                "type": "object",
                "description": "Industry benchmarks and best practices",
                "properties": {
                    "benchmark_comparison": {"type": "string"},
                    "best_practices": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "market_trends": {"type": "string"}
                }
            },
            "next_steps": {
                "type": "array",
                "description": "Immediate actions to take",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "owner": {"type": "string"},
                        "due_date": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"]
                        }
                    },
                    "required": ["action", "priority"]
                }
            },
            "executive_summary": {
                "type": "string",
                "description": "Brief summary of findings and recommendations"
            }
        },
        "required": ["root_cause_analysis", "implementation_roadmap", "financial_impact", "next_steps", "executive_summary"]
    }
}


class AIInsightsService:
    """
    Service class for AI-powered procurement insights.
    Combines built-in ML algorithms with optional external AI enhancement.
    """

    # Thresholds for insight generation
    PRICE_VARIANCE_THRESHOLD = 0.15  # 15% price variance = insight
    SUPPLIER_CONCENTRATION_THRESHOLD = 0.30  # 30% spend with single supplier = risk
    ANOMALY_Z_SCORE_THRESHOLD = 2.0  # Standard deviations for anomaly
    CONSOLIDATION_MIN_SUPPLIERS = 3  # Minimum suppliers for consolidation insight

    def __init__(
        self,
        organization,
        filters: Optional[Dict] = None,
        use_external_ai: bool = False,
        ai_provider: str = 'anthropic',
        api_key: Optional[str] = None,
        api_keys: Optional[Dict[str, str]] = None,
        enable_fallback: bool = True
    ):
        """
        Initialize AI Insights Service.

        Args:
            organization: Organization object for data scoping
            filters: Optional dict with filter parameters (date_from, date_to,
                     supplier_ids, category_ids, subcategories, locations, years,
                     min_amount, max_amount)
            use_external_ai: Whether to enhance insights with external AI
            ai_provider: Primary AI provider ('anthropic' or 'openai')
            api_key: API key for primary provider (legacy, use api_keys for multi-provider)
            api_keys: Dict mapping provider names to API keys for multi-provider support
            enable_fallback: Whether to enable automatic failover between providers
        """
        self.organization = organization
        self.filters = filters or {}
        self.transactions = self._build_filtered_queryset()
        self.analytics = AnalyticsService(organization, filters)
        self.use_external_ai = use_external_ai
        self.ai_provider = ai_provider
        self.api_key = api_key
        self.enable_fallback = enable_fallback

        # Load configurable savings rates from organization
        savings_config = organization.get_savings_config()
        self.consolidation_rate = savings_config.get('consolidation_rate', 0.03)
        self.anomaly_rate = savings_config.get('anomaly_recovery_rate', 0.008)
        self.variance_capture = savings_config.get('price_variance_capture', 0.40)
        self.enabled_insights = savings_config.get(
            'enabled_insights',
            ['consolidation', 'anomaly', 'cost_optimization', 'risk']
        )

        # Build api_keys dict from legacy api_key if not provided
        if api_keys:
            self.api_keys = api_keys
        elif api_key:
            self.api_keys = {ai_provider: api_key}
        else:
            self.api_keys = {}

        # Initialize provider manager for multi-provider support
        self._provider_manager: Optional[AIProviderManager] = None
        if self.use_external_ai and self.api_keys:
            self._provider_manager = AIProviderManager(
                primary_provider=ai_provider,
                api_keys=self.api_keys,
                enable_fallback=enable_fallback,
                organization_id=self.organization.id,
                enable_logging=True
            )

    def _build_filtered_queryset(self):
        """Build transaction queryset with applied filters."""
        from datetime import datetime as dt
        qs = Transaction.objects.filter(organization=self.organization)

        if date_from := self.filters.get('date_from'):
            if isinstance(date_from, str):
                date_from = dt.strptime(date_from, '%Y-%m-%d').date()
            qs = qs.filter(date__gte=date_from)

        if date_to := self.filters.get('date_to'):
            if isinstance(date_to, str):
                date_to = dt.strptime(date_to, '%Y-%m-%d').date()
            qs = qs.filter(date__lte=date_to)

        if supplier_ids := self.filters.get('supplier_ids'):
            if isinstance(supplier_ids, list) and supplier_ids:
                qs = qs.filter(supplier_id__in=supplier_ids)

        if category_ids := self.filters.get('category_ids'):
            if isinstance(category_ids, list) and category_ids:
                qs = qs.filter(category_id__in=category_ids)

        if subcategories := self.filters.get('subcategories'):
            if isinstance(subcategories, list) and subcategories:
                qs = qs.filter(subcategory__in=subcategories)

        if locations := self.filters.get('locations'):
            if isinstance(locations, list) and locations:
                qs = qs.filter(location__in=locations)

        if years := self.filters.get('years'):
            if isinstance(years, list) and years:
                qs = qs.filter(fiscal_year__in=years)

        if min_amount := self.filters.get('min_amount'):
            qs = qs.filter(amount__gte=min_amount)

        if max_amount := self.filters.get('max_amount'):
            qs = qs.filter(amount__lte=max_amount)

        return qs

    def get_all_insights(self, force_refresh: bool = False) -> dict:
        """
        Get all AI insights combined with optional AI enhancement.

        Args:
            force_refresh: If True, bypass cache and regenerate AI enhancement

        Returns:
            Dictionary with:
            - insights: List of insight objects
            - summary: Summary statistics
            - ai_enhancement: Structured AI recommendations (if enabled)
            - cache_hit: Whether AI enhancement was served from cache
        """
        # Collect raw insights from all generators
        cost_insights = self.get_cost_optimization_insights()
        risk_insights = self.get_supplier_risk_insights()
        anomaly_insights = self.get_anomaly_insights()
        consolidation_insights = self.get_consolidation_recommendations()

        all_insights = cost_insights + risk_insights + anomaly_insights + consolidation_insights

        # Apply deduplication to prevent double-counting savings
        deduplicated_insights, adjusted_total = self.deduplicate_savings(all_insights)

        # Sort by severity, then by adjusted savings
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        deduplicated_insights.sort(key=lambda x: (
            severity_order.get(x['severity'], 4),
            -(x.get('potential_savings', 0) or 0)
        ))

        # Calculate total spend for capping
        total_spend = float(
            self.transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        )

        # Cap at total spend (safety net)
        savings_capped = adjusted_total > total_spend
        final_savings = min(adjusted_total, total_spend) if total_spend > 0 else adjusted_total

        # Calculate overlap summary
        overlap_summary = self._calculate_overlap_summary(deduplicated_insights)

        summary = {
            'total_insights': len(deduplicated_insights),
            'high_priority': len([i for i in deduplicated_insights if i['severity'] in ['critical', 'high']]),
            'total_potential_savings': round(final_savings, 2),
            'total_potential_savings_raw': round(adjusted_total, 2),
            'savings_capped': savings_capped,
            'total_spend': round(total_spend, 2),
            'deduplication_applied': True,
            'overlap_summary': overlap_summary,
            'by_type': {
                'cost_optimization': len(cost_insights),
                'risk': len(risk_insights),
                'anomaly': len(anomaly_insights),
                'consolidation': len(consolidation_insights)
            }
        }

        # Strip internal _attribution before returning (don't expose to API)
        clean_insights = [
            {k: v for k, v in i.items() if not k.startswith('_')}
            for i in deduplicated_insights
        ]

        result = {
            'insights': clean_insights,
            'summary': summary
        }

        if self.use_external_ai and self.api_key:
            cache_hit = False
            ai_enhancement = None

            if not force_refresh:
                ai_enhancement = AIInsightsCache.get_cached_enhancement(
                    self.organization.id,
                    clean_insights
                )
                cache_hit = ai_enhancement is not None

            if not ai_enhancement:
                ai_enhancement = self._enhance_with_external_ai(clean_insights)
                if ai_enhancement:
                    AIInsightsCache.cache_enhancement(
                        self.organization.id,
                        clean_insights,
                        ai_enhancement
                    )

            if ai_enhancement:
                result['ai_enhancement'] = ai_enhancement
                result['cache_hit'] = cache_hit

            # Per-insight enhancement for high-value insights
            per_insight_enhancer = PerInsightEnhancer(
                api_key=self.api_key,
                provider=self.ai_provider,
                api_keys=self.api_keys,
                enable_fallback=self.enable_fallback
            )
            result['insights'] = per_insight_enhancer.enhance_insights(clean_insights)

        return result

    def get_cost_optimization_insights(self) -> list:
        """
        Identify cost optimization opportunities based on price variance.

        Analyzes same items from different suppliers to find price discrepancies.
        """
        insights = []

        # Get spend by category, subcategory, and supplier to find variance
        # Group by subcategory for apples-to-apples comparison
        category_supplier_spend = self.transactions.values(
            'category__name',
            'category__uuid',
            'subcategory',
            'supplier__name',
            'supplier__uuid'
        ).annotate(
            total_amount=Sum('amount'),
            transaction_count=Count('id'),
            avg_transaction=Avg('amount')
        ).order_by('category__name', 'subcategory', '-total_amount')

        # Group by (category, subcategory) for apples-to-apples comparison
        category_data = {}
        for item in category_supplier_spend:
            cat_name = item['category__name']
            subcategory = item['subcategory'] or 'Unspecified'
            group_key = (cat_name, subcategory)
            if group_key not in category_data:
                category_data[group_key] = {
                    'category': cat_name,
                    'subcategory': subcategory,
                    'uuid': str(item['category__uuid']),
                    'suppliers': []
                }
            category_data[group_key]['suppliers'].append({
                'name': item['supplier__name'],
                'uuid': str(item['supplier__uuid']),
                'total': float(item['total_amount']),
                'avg_transaction': float(item['avg_transaction']),
                'count': item['transaction_count']
            })

        # Analyze each (category, subcategory) group for price variance
        for group_key, data in category_data.items():
            if len(data['suppliers']) < 2:
                continue

            # Calculate variance in average transaction
            avg_prices = [s['avg_transaction'] for s in data['suppliers']]
            if not avg_prices or max(avg_prices) == 0:
                continue

            price_variance = (max(avg_prices) - min(avg_prices)) / max(avg_prices)

            if price_variance > self.PRICE_VARIANCE_THRESHOLD:
                total_category_spend = sum(s['total'] for s in data['suppliers'])
                # Potential savings = difference × transactions from expensive suppliers
                # Apply configurable variance capture rate (not 100% realizable)
                expensive_suppliers = [s for s in data['suppliers']
                                       if s['avg_transaction'] > min(avg_prices) * 1.1]
                raw_savings = sum(
                    (s['avg_transaction'] - min(avg_prices)) * s['count']
                    for s in expensive_suppliers
                )
                potential_savings = raw_savings * self.variance_capture

                severity = 'high' if price_variance > 0.30 else 'medium'

                cat_name = data['category']
                subcategory = data['subcategory']
                display_name = f"{cat_name} > {subcategory}" if subcategory != 'Unspecified' else cat_name

                insights.append({
                    'id': str(uuid.uuid4()),
                    'type': 'cost_optimization',
                    'severity': severity,
                    'confidence': min(0.95, 0.70 + (price_variance * 0.5)),
                    'title': f'Price variance detected in {display_name}',
                    'description': (
                        f'Found {len(data["suppliers"])} suppliers with '
                        f'{round(price_variance * 100, 1)}% price variance. '
                        f'Average prices range from ${min(avg_prices):,.2f} to '
                        f'${max(avg_prices):,.2f}.'
                    ),
                    'potential_savings': round(potential_savings, 2),
                    'affected_entities': [display_name] + [s['name'] for s in expensive_suppliers],
                    'recommended_actions': [
                        f'Review pricing from {data["suppliers"][-1]["name"]} (lowest avg: ${min(avg_prices):,.2f})',
                        'Negotiate better rates with higher-priced suppliers',
                        'Consider consolidating purchases to preferred supplier'
                    ],
                    '_attribution': {
                        'subcategory_keys': [(cat_name, subcategory)],
                        'supplier_ids': [s['uuid'] for s in data['suppliers']],
                        'spend_basis': total_category_spend,
                    },
                    'created_at': datetime.now().isoformat()
                })

        return insights

    def get_supplier_risk_insights(self) -> list:
        """
        Identify supplier concentration risks.

        Flags suppliers representing too large a portion of total spend.
        """
        insights = []

        # Get total spend
        total_spend = self.transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        if total_spend == 0:
            return insights

        # Get spend by supplier
        supplier_spend = self.transactions.values(
            'supplier__name',
            'supplier__uuid'
        ).annotate(
            total=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-total')

        for supplier in supplier_spend:
            concentration = float(supplier['total']) / float(total_spend)

            if concentration >= self.SUPPLIER_CONCENTRATION_THRESHOLD:
                severity = 'critical' if concentration > 0.50 else 'high'

                insights.append({
                    'id': str(uuid.uuid4()),
                    'type': 'risk',
                    'severity': severity,
                    'confidence': 0.90,
                    'title': f'High supplier concentration: {supplier["supplier__name"]}',
                    'description': (
                        f'{supplier["supplier__name"]} represents '
                        f'{round(concentration * 100, 1)}% of total spend '
                        f'(${float(supplier["total"]):,.2f} of ${float(total_spend):,.2f}). '
                        f'This creates supply chain vulnerability.'
                    ),
                    'potential_savings': None,  # Risk insight, not cost saving
                    'affected_entities': [supplier['supplier__name']],
                    'recommended_actions': [
                        'Identify alternative suppliers for key categories',
                        'Negotiate backup supply agreements',
                        'Develop supplier diversification strategy',
                        'Review contract terms for flexibility'
                    ],
                    'created_at': datetime.now().isoformat()
                })

        return insights

    def get_anomaly_insights(self, sensitivity: float = None) -> list:
        """
        Detect anomalous transactions using statistical analysis.

        Uses Z-score to identify transactions that deviate significantly from the mean.
        """
        insights = []
        sensitivity = sensitivity or self.ANOMALY_Z_SCORE_THRESHOLD

        # Get statistics by category
        category_stats = self.transactions.values(
            'category__name',
            'category__uuid'
        ).annotate(
            avg_amount=Avg('amount'),
            std_amount=StdDev('amount'),
            transaction_count=Count('id')
        ).filter(transaction_count__gt=5)  # Need enough data for meaningful stats

        for cat_stat in category_stats:
            if not cat_stat['std_amount'] or cat_stat['std_amount'] == 0:
                continue

            avg = float(cat_stat['avg_amount'])
            std = float(cat_stat['std_amount'])
            upper_threshold = avg + (sensitivity * std)
            lower_threshold = max(0, avg - (sensitivity * std))

            # Find anomalous transactions
            anomalies = self.transactions.filter(
                category__name=cat_stat['category__name']
            ).filter(
                Q(amount__gt=upper_threshold) | Q(amount__lt=lower_threshold)
            ).values(
                'uuid',
                'amount',
                'date',
                'supplier__name',
                'description'
            )[:10]  # Limit to top 10

            if anomalies:
                anomalies_list = list(anomalies)
                high_anomalies = [a for a in anomalies_list if float(a['amount']) > upper_threshold]
                low_anomalies = [a for a in anomalies_list if float(a['amount']) < lower_threshold]

                total_anomaly_spend = sum(float(a['amount']) for a in high_anomalies)

                severity = 'high' if len(high_anomalies) > 3 else 'medium'

                insights.append({
                    'id': str(uuid.uuid4()),
                    'type': 'anomaly',
                    'severity': severity,
                    'confidence': 0.75,
                    'title': f'Unusual transactions in {cat_stat["category__name"]}',
                    'description': (
                        f'Found {len(anomalies_list)} transactions outside normal range. '
                        f'Average for category: ${avg:,.2f}, Threshold: ±${sensitivity * std:,.2f}. '
                        f'{len(high_anomalies)} unusually high, {len(low_anomalies)} unusually low.'
                    ),
                    'potential_savings': round(total_anomaly_spend * self.anomaly_rate, 2) if high_anomalies else None,
                    'affected_entities': [f"{a['supplier__name']} (${float(a['amount']):,.2f})" for a in anomalies_list],
                    'recommended_actions': [
                        'Review flagged transactions for accuracy',
                        'Verify pricing and quantities',
                        'Check for duplicate or erroneous entries',
                        'Investigate supplier invoicing practices'
                    ],
                    '_attribution': {
                        'category_ids': [str(cat_stat['category__uuid'])],
                        'transaction_ids': [str(a['uuid']) for a in anomalies_list],
                        'spend_basis': total_anomaly_spend,
                    },
                    'details': {
                        'category': cat_stat['category__name'],
                        'average': avg,
                        'std_deviation': std,
                        'threshold_upper': upper_threshold,
                        'threshold_lower': lower_threshold,
                        'anomaly_count': len(anomalies_list),
                        'sample_anomalies': [
                            {
                                'uuid': str(a['uuid']),
                                'amount': float(a['amount']),
                                'date': str(a['date']),
                                'supplier': a['supplier__name']
                            }
                            for a in anomalies_list[:5]
                        ]
                    },
                    'created_at': datetime.now().isoformat()
                })

        return insights

    def get_consolidation_recommendations(self) -> list:
        """
        Identify supplier consolidation opportunities.

        Finds (category, subcategory) groups with many suppliers that could benefit
        from consolidation. Groups by subcategory for apples-to-apples comparison.
        """
        insights = []

        # Get (category, subcategory) groups with multiple suppliers
        category_subcategory_groups = self.transactions.values(
            'category__name',
            'category__uuid',
            'subcategory'
        ).annotate(
            supplier_count=Count('supplier', distinct=True),
            total_spend=Sum('amount'),
            transaction_count=Count('id')
        ).filter(supplier_count__gte=self.CONSOLIDATION_MIN_SUPPLIERS).order_by('-supplier_count')

        for group in category_subcategory_groups:
            cat_name = group['category__name']
            subcategory = group['subcategory'] or 'Unspecified'
            display_name = f"{cat_name} > {subcategory}" if subcategory != 'Unspecified' else cat_name

            # Get suppliers in this (category, subcategory) group
            suppliers_filter = {'category__name': cat_name}
            if subcategory != 'Unspecified':
                suppliers_filter['subcategory'] = group['subcategory']
            else:
                suppliers_filter['subcategory__isnull'] = True

            suppliers = self.transactions.filter(
                **suppliers_filter
            ).values(
                'supplier__name',
                'supplier__uuid'
            ).annotate(
                spend=Sum('amount'),
                count=Count('id')
            ).order_by('-spend')

            supplier_list = list(suppliers)
            top_supplier = supplier_list[0] if supplier_list else None
            top_supplier_share = (
                float(top_supplier['spend']) / float(group['total_spend'])
                if top_supplier and group['total_spend']
                else 0
            )

            # Potential savings: apply configurable consolidation rate (industry benchmark)
            potential_savings = float(group['total_spend']) * self.consolidation_rate

            severity = 'high' if group['supplier_count'] >= 5 else 'medium'

            insights.append({
                'id': str(uuid.uuid4()),
                'type': 'consolidation',
                'severity': severity,
                'confidence': 0.80,
                'title': f'Consolidation opportunity: {display_name}',
                'description': (
                    f'{group["supplier_count"]} suppliers for {display_name} '
                    f'(${float(group["total_spend"]):,.2f} total). '
                    f'Top supplier ({top_supplier["supplier__name"] if top_supplier else "N/A"}) '
                    f'has {round(top_supplier_share * 100, 1)}% share. '
                    f'Consider consolidating to reduce costs and complexity.'
                ),
                'potential_savings': round(potential_savings, 2),
                'affected_entities': [display_name] + [s['supplier__name'] for s in supplier_list],
                'recommended_actions': [
                    f'Evaluate {top_supplier["supplier__name"] if top_supplier else "primary supplier"} as preferred vendor',
                    'Request volume discount proposals',
                    'Review supplier performance metrics',
                    'Develop preferred supplier program'
                ],
                '_attribution': {
                    'subcategory_keys': [(cat_name, subcategory)],
                    'supplier_ids': [str(s['supplier__uuid']) for s in supplier_list],
                    'spend_basis': float(group['total_spend']),
                },
                'details': {
                    'category': cat_name,
                    'subcategory': subcategory,
                    'supplier_count': group['supplier_count'],
                    'total_spend': float(group['total_spend']),
                    'suppliers': [
                        {
                            'name': s['supplier__name'],
                            'spend': float(s['spend']),
                            'share': round(float(s['spend']) / float(group['total_spend']) * 100, 1)
                        }
                        for s in supplier_list[:5]
                    ]
                },
                'created_at': datetime.now().isoformat()
            })

        return insights

    def _get_entity_keys(self, attribution: dict) -> list:
        """
        Extract entity keys from insight attribution for deduplication.

        Returns a list of hashable keys representing the entities this insight
        is based on.
        """
        keys = []

        # Primary key: subcategory_keys (most specific for grouping)
        if subcategory_keys := attribution.get('subcategory_keys'):
            for key in subcategory_keys:
                if isinstance(key, (list, tuple)) and len(key) == 2:
                    keys.append(('subcat', key[0], key[1]))

        # Secondary: category_ids (for anomaly insights)
        if category_ids := attribution.get('category_ids'):
            for cat_id in category_ids:
                keys.append(('cat', cat_id))

        # Tertiary: supplier_ids (for overlap detection)
        if supplier_ids := attribution.get('supplier_ids'):
            for sup_id in supplier_ids:
                keys.append(('sup', sup_id))

        return keys

    def deduplicate_savings(self, insights: list) -> tuple:
        """
        Deduplicate overlapping savings across insight types.

        Strategy:
        1. Process insights in priority order (anomaly > cost_optimization > consolidation)
        2. Track which entities have been claimed by higher-priority insights
        3. Apply diminishing returns for lower-priority insights on same entities

        Returns:
            tuple: (deduplicated_insights, adjusted_total_savings)
        """
        # Priority order (lower number = higher priority)
        priority = {
            'anomaly': 1,
            'cost_optimization': 2,
            'consolidation': 3,
            'risk': 4,
        }

        # Sort by priority, then by potential_savings descending
        sorted_insights = sorted(
            insights,
            key=lambda i: (priority.get(i['type'], 5), -(i.get('potential_savings') or 0))
        )

        # Track claimed entities and their savings
        claimed_by_entity = {}  # entity_key -> {'type': str, 'savings': float}

        adjusted_insights = []
        for insight in sorted_insights:
            attribution = insight.get('_attribution', {})
            entity_keys = self._get_entity_keys(attribution)

            original_savings = insight.get('potential_savings') or 0

            # Skip deduplication for risk insights (no savings) or missing attribution
            if insight['type'] == 'risk' or not entity_keys:
                adjusted_insight = {**insight}
                adjusted_insight['_original_savings'] = original_savings
                adjusted_insight['_overlap_reduction'] = 0
                adjusted_insights.append(adjusted_insight)
                continue

            # Calculate overlap with already-claimed entities
            overlap_savings = 0
            overlapping_types = set()
            for key in entity_keys:
                if key in claimed_by_entity:
                    overlap_savings += claimed_by_entity[key]['savings']
                    overlapping_types.add(claimed_by_entity[key]['type'])

            # Reduce savings by overlap
            adjusted_savings = max(0, original_savings - overlap_savings)

            # Apply diminishing returns if there's overlap with different insight types
            if overlap_savings > 0 and adjusted_savings > 0:
                adjusted_savings *= 0.30  # 30% of remaining is achievable

            # Update insight
            adjusted_insight = {**insight}
            adjusted_insight['potential_savings'] = round(adjusted_savings, 2)
            adjusted_insight['_original_savings'] = original_savings
            adjusted_insight['_overlap_reduction'] = round(overlap_savings, 2)
            adjusted_insights.append(adjusted_insight)

            # Mark entities as claimed (distribute savings proportionally)
            if entity_keys and adjusted_savings > 0:
                savings_per_key = adjusted_savings / len(entity_keys)
                for key in entity_keys:
                    if key not in claimed_by_entity:
                        claimed_by_entity[key] = {
                            'type': insight['type'],
                            'savings': savings_per_key,
                        }

        total_savings = sum(i.get('potential_savings') or 0 for i in adjusted_insights)
        return adjusted_insights, total_savings

    def _calculate_overlap_summary(self, insights: list) -> dict:
        """Calculate summary of overlap adjustments."""
        total_original = sum(i.get('_original_savings') or 0 for i in insights)
        total_adjusted = sum(i.get('potential_savings') or 0 for i in insights)
        total_reduction = sum(i.get('_overlap_reduction') or 0 for i in insights)

        insights_with_overlap = len([i for i in insights if i.get('_overlap_reduction', 0) > 0])

        return {
            'total_original_savings': round(total_original, 2),
            'total_adjusted_savings': round(total_adjusted, 2),
            'total_overlap_reduction': round(total_reduction, 2),
            'insights_with_overlap': insights_with_overlap,
            'deduplication_percentage': round((total_reduction / total_original * 100) if total_original > 0 else 0, 1),
        }

    def _build_comprehensive_context(self, insights: list) -> dict:
        """
        Build rich context for AI analysis.

        Provides the AI with comprehensive data including organization context,
        spending patterns, historical feedback, and detailed insight information.

        Returns:
            Dict with organization, spending, top_categories, top_suppliers, insights, historical
        """
        total_spend = self.transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        avg_transaction = self.transactions.aggregate(avg=Avg('amount'))['avg'] or Decimal('0')

        top_categories = list(
            self.transactions.values('category__name')
            .annotate(spend=Sum('amount'))
            .order_by('-spend')[:5]
        )

        top_suppliers = list(
            self.transactions.values('supplier__name')
            .annotate(spend=Sum('amount'))
            .order_by('-spend')[:5]
        )

        date_range = {
            "earliest": None,
            "latest": None
        }
        if self.transactions.exists():
            earliest = self.transactions.order_by('date').first()
            latest = self.transactions.order_by('-date').first()
            if earliest:
                date_range["earliest"] = str(earliest.date)
            if latest:
                date_range["latest"] = str(latest.date)

        insights_context = [
            {
                "id": i["id"],
                "type": i["type"],
                "severity": i["severity"],
                "confidence": i["confidence"],
                "title": i["title"],
                "description": i["description"],
                "potential_savings": i.get("potential_savings"),
                "affected_entities": i.get("affected_entities", [])[:5],
                "details": {
                    k: v for k, v in i.get("details", {}).items()
                    if k in ["category", "supplier_count", "average", "suppliers", "total_spend"]
                } if i.get("details") else {}
            }
            for i in insights[:15]
        ]

        historical_context = self._get_historical_insight_patterns()

        return {
            "organization": {
                "name": self.organization.name,
                "procurement_maturity": self._assess_procurement_maturity(),
            },
            "spending": {
                "total_ytd": float(total_spend),
                "supplier_count": self.transactions.values('supplier').distinct().count(),
                "category_count": self.transactions.values('category').distinct().count(),
                "transaction_count": self.transactions.count(),
                "avg_transaction": float(avg_transaction),
                "date_range": date_range,
            },
            "top_categories": [
                {"name": c["category__name"], "spend": float(c["spend"])}
                for c in top_categories
            ],
            "top_suppliers": [
                {"name": s["supplier__name"], "spend": float(s["spend"])}
                for s in top_suppliers
            ],
            "insights": insights_context,
            "historical": historical_context,
        }

    def _assess_procurement_maturity(self) -> str:
        """
        Assess organization's procurement maturity level.

        Returns one of: 'early_stage', 'basic', 'developing', 'mature'
        """
        supplier_count = self.transactions.values('supplier').distinct().count()
        category_count = self.transactions.values('category').distinct().count()
        transaction_count = self.transactions.count()

        if transaction_count < 100:
            return "early_stage"
        elif supplier_count > 50 and category_count > 20:
            return "mature"
        elif supplier_count > 20:
            return "developing"
        else:
            return "basic"

    def _get_historical_insight_patterns(self) -> dict:
        """
        Get patterns from historical insight feedback.

        Returns summary of past actions taken on insights and their outcomes.
        """
        try:
            from .models import InsightFeedback

            feedback = InsightFeedback.objects.filter(
                organization=self.organization
            ).order_by('-created_at')[:50]

            if not feedback.exists():
                return {}

            implemented_count = feedback.filter(action_taken='implemented').count()
            total_predicted = feedback.filter(
                action_taken='implemented',
                predicted_savings__isnull=False
            ).aggregate(total=Sum('predicted_savings'))['total'] or 0

            total_actual = feedback.filter(
                outcome='success',
                actual_savings__isnull=False
            ).aggregate(total=Sum('actual_savings'))['total'] or 0

            most_actioned = list(
                feedback.filter(action_taken='implemented')
                .values('insight_type')
                .annotate(count=Count('id'))
                .order_by('-count')[:3]
            )

            return {
                "total_feedback": feedback.count(),
                "implemented_count": implemented_count,
                "total_predicted_savings": float(total_predicted),
                "total_realized_savings": float(total_actual),
                "most_actioned_types": [
                    {"type": item["insight_type"], "count": item["count"]}
                    for item in most_actioned
                ]
            }
        except Exception as e:
            logger.debug(f"Could not fetch historical patterns: {e}")
            return {}

    def _enhance_with_external_ai(self, insights: list) -> Optional[dict]:
        """
        Enhance insights with external AI analysis.

        Uses the provider manager with automatic failover to provide
        structured recommendations.

        Returns:
            Dict with priority_actions, risk_assessment, quick_wins, strategic_summary
            or None if all providers fail
        """
        if not self.api_keys:
            return None

        # Use provider manager for automatic failover
        if self._provider_manager:
            context = self._build_comprehensive_context(insights)
            return self._provider_manager.enhance_insights(
                insights=insights,
                context=context,
                tool_schema=INSIGHT_ENHANCEMENT_TOOL
            )

        # Fallback to legacy single-provider behavior
        if not self.api_key:
            return None

        try:
            if self.ai_provider == 'anthropic':
                return self._enhance_with_claude_structured(insights)
            elif self.ai_provider == 'openai':
                return self._enhance_with_openai_structured(insights)
            else:
                logger.warning(f"Unknown AI provider: {self.ai_provider}")
                return None
        except Exception as e:
            logger.error(f"External AI enhancement failed: {e}")
            return None

    def _enhance_with_claude_structured(self, insights: list) -> Optional[dict]:
        """
        Enhance insights using Claude API with structured tool calling.

        Uses tool calling to ensure predictable, parseable JSON output.

        Returns:
            Structured enhancement dict or None on failure
        """
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            context = self._build_comprehensive_context(insights)

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                tools=[INSIGHT_ENHANCEMENT_TOOL],
                tool_choice={"type": "tool", "name": "provide_procurement_recommendations"},
                messages=[{
                    "role": "user",
                    "content": f"""Analyze these procurement insights and provide structured recommendations.

Organization: {context['organization']['name']}

Spending Summary:
- Total YTD Spend: ${context['spending']['total_ytd']:,.2f}
- Supplier Count: {context['spending']['supplier_count']}
- Category Count: {context['spending']['category_count']}
- Transaction Count: {context['spending']['transaction_count']}

Top Categories:
{json.dumps(context['top_categories'], indent=2)}

Top Suppliers:
{json.dumps(context['top_suppliers'], indent=2)}

Current Insights ({len(insights)} total):
{json.dumps(context['insights'], indent=2)}

Provide actionable recommendations prioritized by impact and effort.
Focus on quick wins and high-impact actions that address the identified issues."""
                }]
            )

            for block in message.content:
                if block.type == "tool_use" and block.name == "provide_procurement_recommendations":
                    enhancement = block.input
                    enhancement['provider'] = 'anthropic'
                    enhancement['generated_at'] = datetime.now().isoformat()
                    return enhancement

            logger.warning("Claude did not return tool_use response")
            return None

        except ImportError:
            logger.warning("anthropic package not installed, skipping Claude enhancement")
            return None
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return None

    def _enhance_with_openai_structured(self, insights: list) -> Optional[dict]:
        """
        Enhance insights using OpenAI API with structured output.

        Uses function calling for predictable JSON output.

        Returns:
            Structured enhancement dict or None on failure
        """
        try:
            import openai

            client = openai.OpenAI(api_key=self.api_key)
            context = self._build_comprehensive_context(insights)

            openai_tool = {
                "type": "function",
                "function": {
                    "name": INSIGHT_ENHANCEMENT_TOOL["name"],
                    "description": INSIGHT_ENHANCEMENT_TOOL["description"],
                    "parameters": INSIGHT_ENHANCEMENT_TOOL["input_schema"]
                }
            }

            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a procurement analytics expert. Analyze the insights and provide structured, actionable recommendations."
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze these procurement insights and provide structured recommendations.

Organization: {context['organization']['name']}

Spending Summary:
- Total YTD Spend: ${context['spending']['total_ytd']:,.2f}
- Supplier Count: {context['spending']['supplier_count']}
- Category Count: {context['spending']['category_count']}

Current Insights ({len(insights)} total):
{json.dumps(context['insights'], indent=2)}

Provide actionable recommendations prioritized by impact and effort."""
                    }
                ],
                tools=[openai_tool],
                tool_choice={"type": "function", "function": {"name": "provide_procurement_recommendations"}},
                max_tokens=2048
            )

            if response.choices and response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                enhancement = json.loads(tool_call.function.arguments)
                enhancement['provider'] = 'openai'
                enhancement['generated_at'] = datetime.now().isoformat()
                return enhancement

            logger.warning("OpenAI did not return function call response")
            return None

        except ImportError:
            logger.warning("openai package not installed, skipping OpenAI enhancement")
            return None
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None

    def get_insights_by_type(self, insight_type: str) -> list:
        """
        Get insights filtered by type.

        Args:
            insight_type: One of 'cost_optimization', 'risk', 'anomaly', 'consolidation'
        """
        type_methods = {
            'cost': self.get_cost_optimization_insights,
            'cost_optimization': self.get_cost_optimization_insights,
            'risk': self.get_supplier_risk_insights,
            'anomaly': self.get_anomaly_insights,
            'anomalies': self.get_anomaly_insights,
            'consolidation': self.get_consolidation_recommendations,
        }

        method = type_methods.get(insight_type.lower())
        if method:
            return method()
        else:
            raise ValueError(f"Unknown insight type: {insight_type}")

    def perform_deep_analysis(self, insight_data: dict) -> Optional[dict]:
        """
        Perform comprehensive deep analysis on a specific insight.

        Uses the provider manager with automatic failover to provide:
        - Root cause analysis
        - Detailed implementation roadmap
        - Financial impact assessment
        - Risk factors
        - Success metrics
        - Stakeholder mapping

        Args:
            insight_data: The insight dictionary to analyze

        Returns:
            Deep analysis results dict or None on failure
        """
        if not self.api_keys:
            logger.warning("Deep analysis requires API keys")
            return None

        # Use provider manager for automatic failover
        if self._provider_manager:
            context = self._build_deep_analysis_context(insight_data)
            return self._provider_manager.deep_analysis(
                insight_data=insight_data,
                context=context,
                tool_schema=DEEP_ANALYSIS_TOOL
            )

        # Fallback to legacy single-provider behavior
        if not self.api_key:
            logger.warning("Deep analysis requires API key")
            return None

        try:
            if self.ai_provider == 'anthropic':
                return self._deep_analysis_with_claude(insight_data)
            elif self.ai_provider == 'openai':
                return self._deep_analysis_with_openai(insight_data)
            else:
                logger.warning(f"Unknown AI provider for deep analysis: {self.ai_provider}")
                return None
        except Exception as e:
            logger.error(f"Deep analysis failed: {e}")
            return None

    def _deep_analysis_with_claude(self, insight_data: dict) -> Optional[dict]:
        """Perform deep analysis using Claude Sonnet (higher quality for detailed analysis)."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            context = self._build_deep_analysis_context(insight_data)

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                tools=[DEEP_ANALYSIS_TOOL],
                tool_choice={"type": "tool", "name": "provide_deep_insight_analysis"},
                messages=[{
                    "role": "user",
                    "content": f"""Perform a comprehensive deep analysis of this procurement insight.

INSIGHT DETAILS:
- ID: {insight_data.get('id', 'N/A')}
- Type: {insight_data.get('type', 'N/A')}
- Title: {insight_data.get('title', 'N/A')}
- Description: {insight_data.get('description', 'N/A')}
- Severity: {insight_data.get('severity', 'N/A')}
- Confidence: {insight_data.get('confidence', 0) * 100:.0f}%
- Potential Savings: ${insight_data.get('potential_savings', 0):,.2f}

ADDITIONAL DETAILS:
{json.dumps(insight_data.get('details', {}), indent=2)}

RECOMMENDED ACTIONS (from initial analysis):
{json.dumps(insight_data.get('recommended_actions', []), indent=2)}

ORGANIZATION CONTEXT:
{json.dumps(context, indent=2)}

Provide a thorough analysis including:
1. Root cause analysis - identify the primary cause and contributing factors
2. Implementation roadmap - phased approach with specific tasks and timelines
3. Financial impact - detailed savings breakdown and ROI calculation
4. Risk factors - potential risks and mitigation strategies
5. Success metrics - KPIs to track implementation success
6. Stakeholder mapping - who needs to be involved
7. Industry context - benchmarks and best practices
8. Clear next steps - immediate actions to take"""
                }]
            )

            for block in message.content:
                if block.type == "tool_use" and block.name == "provide_deep_insight_analysis":
                    result = block.input
                    result['insight_id'] = insight_data.get('id')
                    result['provider'] = 'anthropic'
                    result['model'] = 'claude-sonnet-4'
                    result['generated_at'] = datetime.now().isoformat()
                    return result

            logger.warning("Claude did not return deep analysis tool response")
            return None

        except ImportError:
            logger.warning("anthropic package not installed")
            return None
        except Exception as e:
            logger.error(f"Claude API error in deep analysis: {e}")
            return None

    def _deep_analysis_with_openai(self, insight_data: dict) -> Optional[dict]:
        """Perform deep analysis using GPT-4 Turbo."""
        try:
            import openai

            client = openai.OpenAI(api_key=self.api_key)

            context = self._build_deep_analysis_context(insight_data)

            openai_tool = {
                "type": "function",
                "function": {
                    "name": DEEP_ANALYSIS_TOOL["name"],
                    "description": DEEP_ANALYSIS_TOOL["description"],
                    "parameters": DEEP_ANALYSIS_TOOL["input_schema"]
                }
            }

            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior procurement consultant providing comprehensive analysis. Be thorough, specific, and actionable."
                    },
                    {
                        "role": "user",
                        "content": f"""Perform a comprehensive deep analysis of this procurement insight.

INSIGHT DETAILS:
- Type: {insight_data.get('type', 'N/A')}
- Title: {insight_data.get('title', 'N/A')}
- Description: {insight_data.get('description', 'N/A')}
- Severity: {insight_data.get('severity', 'N/A')}
- Potential Savings: ${insight_data.get('potential_savings', 0):,.2f}

CONTEXT:
{json.dumps(context, indent=2)}

Provide thorough analysis with root cause, implementation roadmap, financial impact, risks, and next steps."""
                    }
                ],
                tools=[openai_tool],
                tool_choice={"type": "function", "function": {"name": "provide_deep_insight_analysis"}},
                max_tokens=4096
            )

            if response.choices and response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                result = json.loads(tool_call.function.arguments)
                result['insight_id'] = insight_data.get('id')
                result['provider'] = 'openai'
                result['model'] = 'gpt-4-turbo'
                result['generated_at'] = datetime.now().isoformat()
                return result

            logger.warning("OpenAI did not return deep analysis function call")
            return None

        except ImportError:
            logger.warning("openai package not installed")
            return None
        except Exception as e:
            logger.error(f"OpenAI API error in deep analysis: {e}")
            return None

    def _build_deep_analysis_context(self, insight_data: dict) -> dict:
        """Build context for deep analysis including related data."""
        context = {
            "organization": {
                "name": self.organization.name,
                "maturity": self._assess_procurement_maturity(),
            },
            "spending": {
                "total_ytd": float(self.transactions.aggregate(total=Sum('amount'))['total'] or 0),
                "supplier_count": self.transactions.values('supplier').distinct().count(),
                "category_count": self.transactions.values('category').distinct().count(),
            }
        }

        if insight_data.get('affected_entities'):
            entity_ids = insight_data['affected_entities'][:5]
            related_spend = self.transactions.filter(
                Q(supplier__uuid__in=entity_ids) | Q(category__uuid__in=entity_ids)
            ).aggregate(
                total=Sum('amount'),
                count=Count('id'),
                avg=Avg('amount')
            )
            context['related_spend'] = {
                'total': float(related_spend['total'] or 0),
                'transaction_count': related_spend['count'] or 0,
                'avg_transaction': float(related_spend['avg'] or 0),
            }

        if insight_data.get('details', {}).get('suppliers'):
            context['supplier_details'] = insight_data['details']['suppliers'][:10]

        return context

    def _enhance_with_external_ai_structured(self, insights: list) -> Optional[dict]:
        """
        Public method for external AI enhancement (used by async task).

        Wrapper around _enhance_with_external_ai for async task usage.
        """
        return self._enhance_with_external_ai(insights)

    def get_provider_status(self) -> dict:
        """
        Get AI provider status for monitoring and alerting.

        Returns:
            Dict with provider health information
        """
        if self._provider_manager:
            return self._provider_manager.get_status()

        # Legacy single-provider status
        return {
            "primary_provider": self.ai_provider,
            "fallback_enabled": False,
            "last_successful_provider": None,
            "available_providers": [self.ai_provider] if self.api_key else [],
            "provider_errors": {},
            "providers": {
                self.ai_provider: {
                    "available": bool(self.api_key),
                    "last_error": None
                }
            }
        }

    def health_check_providers(self) -> dict:
        """
        Perform health check on all configured providers.

        Returns:
            Dict mapping provider names to health status
        """
        if self._provider_manager:
            return self._provider_manager.health_check_all()
        return {}


# Tool schema for single insight analysis (used with Haiku for cost efficiency)
SINGLE_INSIGHT_TOOL = {
    "name": "analyze_insight",
    "description": "Provide detailed analysis for a single procurement insight",
    "input_schema": {
        "type": "object",
        "properties": {
            "root_cause": {
                "type": "string",
                "description": "Likely root cause of this pattern or issue"
            },
            "industry_benchmark": {
                "type": "string",
                "description": "How this compares to industry standards or best practices"
            },
            "action_plan": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Step-by-step remediation plan (3-5 steps)"
            },
            "risk_of_inaction": {
                "type": "string",
                "description": "Consequences of not addressing this issue"
            },
            "success_metrics": {
                "type": "array",
                "items": {"type": "string"},
                "description": "KPIs to track improvement (2-3 metrics)"
            }
        },
        "required": ["root_cause", "action_plan"]
    }
}


class PerInsightEnhancer:
    """
    Enhances individual high-value insights with detailed AI analysis.

    Uses Claude Haiku or GPT-4o-mini for cost efficiency while providing
    per-insight root cause analysis, benchmarks, and action plans.

    Supports automatic failover between providers.
    """

    # Thresholds for determining which insights to enhance
    MIN_SAVINGS_THRESHOLD = 5000  # Only enhance insights with >$5K potential savings
    MAX_INSIGHTS_TO_ENHANCE = 5   # Limit API calls

    def __init__(
        self,
        api_key: str = None,
        provider: str = 'anthropic',
        api_keys: Optional[Dict[str, str]] = None,
        enable_fallback: bool = True,
        organization_id: Optional[int] = None
    ):
        self.api_key = api_key
        self.provider = provider
        self.enable_fallback = enable_fallback
        self.organization_id = organization_id

        # Build api_keys dict from legacy api_key if not provided
        if api_keys:
            self.api_keys = api_keys
        elif api_key:
            self.api_keys = {provider: api_key}
        else:
            self.api_keys = {}

        # Initialize provider manager for multi-provider support
        self._provider_manager: Optional[AIProviderManager] = None
        if self.api_keys:
            self._provider_manager = AIProviderManager(
                primary_provider=provider,
                api_keys=self.api_keys,
                enable_fallback=enable_fallback,
                organization_id=organization_id,
                enable_logging=True
            )

    def enhance_insights(self, insights: list) -> list:
        """
        Enhance individual high-value insights with AI analysis.

        Only enhances insights that meet the value threshold to control costs.
        Uses Haiku model for cost-efficient processing.

        Args:
            insights: List of insight dictionaries

        Returns:
            List of insights with ai_analysis added to qualifying insights
        """
        if not self.api_key:
            return insights

        high_value = self._filter_high_value_insights(insights)

        if not high_value:
            logger.info("No high-value insights to enhance")
            return insights

        logger.info(f"Enhancing {len(high_value)} high-value insights")

        for insight in high_value:
            try:
                enhancement = self._get_single_insight_enhancement(insight)
                if enhancement:
                    insight['ai_analysis'] = enhancement
                    insight['ai_enhanced'] = True
            except Exception as e:
                logger.warning(f"Failed to enhance insight {insight['id']}: {e}")

        return insights

    def _filter_high_value_insights(self, insights: list) -> list:
        """Filter insights that warrant AI enhancement based on value and severity."""
        high_value = [
            i for i in insights
            if (i.get('potential_savings') or 0) >= self.MIN_SAVINGS_THRESHOLD
            or i.get('severity') in ['critical', 'high']
        ]
        return high_value[:self.MAX_INSIGHTS_TO_ENHANCE]

    def _get_single_insight_enhancement(self, insight: dict) -> Optional[dict]:
        """Get AI enhancement for a single insight using cost-efficient model."""
        # Use provider manager for automatic failover
        if self._provider_manager:
            return self._provider_manager.analyze_single_insight(
                insight=insight,
                tool_schema=SINGLE_INSIGHT_TOOL
            )

        # Fallback to legacy single-provider behavior
        if self.provider == 'anthropic':
            return self._enhance_with_claude_haiku(insight)
        elif self.provider == 'openai':
            return self._enhance_with_openai_mini(insight)
        return None

    def _enhance_with_claude_haiku(self, insight: dict) -> Optional[dict]:
        """Enhance single insight using Claude Haiku (cost-efficient)."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            message = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=500,
                tools=[SINGLE_INSIGHT_TOOL],
                tool_choice={"type": "tool", "name": "analyze_insight"},
                messages=[{
                    "role": "user",
                    "content": f"""Analyze this procurement insight and provide detailed analysis:

Type: {insight['type']}
Title: {insight['title']}
Description: {insight['description']}
Severity: {insight['severity']}
Potential Savings: ${insight.get('potential_savings', 0):,.2f}
Confidence: {insight.get('confidence', 0) * 100:.0f}%

Additional Details:
{json.dumps(insight.get('details', {}), indent=2)}

Provide root cause analysis, industry benchmarks, and actionable remediation steps."""
                }]
            )

            for block in message.content:
                if block.type == "tool_use" and block.name == "analyze_insight":
                    result = block.input
                    result['provider'] = 'anthropic'
                    result['model'] = 'claude-3-5-haiku'
                    result['generated_at'] = datetime.now().isoformat()
                    return result

            return None

        except ImportError:
            logger.warning("anthropic package not installed")
            return None
        except Exception as e:
            logger.error(f"Claude Haiku API error: {e}")
            return None

    def _enhance_with_openai_mini(self, insight: dict) -> Optional[dict]:
        """Enhance single insight using GPT-4o-mini (cost-efficient)."""
        try:
            import openai

            client = openai.OpenAI(api_key=self.api_key)

            openai_tool = {
                "type": "function",
                "function": {
                    "name": SINGLE_INSIGHT_TOOL["name"],
                    "description": SINGLE_INSIGHT_TOOL["description"],
                    "parameters": SINGLE_INSIGHT_TOOL["input_schema"]
                }
            }

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a procurement analytics expert. Provide concise, actionable analysis."
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze this procurement insight:

Type: {insight['type']}
Title: {insight['title']}
Description: {insight['description']}
Severity: {insight['severity']}
Potential Savings: ${insight.get('potential_savings', 0):,.2f}

Provide root cause analysis and actionable remediation steps."""
                    }
                ],
                tools=[openai_tool],
                tool_choice={"type": "function", "function": {"name": "analyze_insight"}},
                max_tokens=500
            )

            if response.choices and response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                result = json.loads(tool_call.function.arguments)
                result['provider'] = 'openai'
                result['model'] = 'gpt-4o-mini'
                result['generated_at'] = datetime.now().isoformat()
                return result

            return None

        except ImportError:
            logger.warning("openai package not installed")
            return None
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None
