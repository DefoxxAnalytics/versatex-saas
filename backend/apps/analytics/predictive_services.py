"""
Predictive Analytics Services

Provides spending forecasts and trend predictions using statistical methods:
- Simple Moving Average for organizations with limited data
- Linear Regression for trend detection
- Seasonal decomposition for organizations with sufficient history
- Confidence intervals for forecast uncertainty
"""

import uuid
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth, TruncYear
from apps.procurement.models import Transaction, Supplier, Category


class PredictiveAnalyticsService:
    """
    Service class for spending forecasts and predictive analytics.

    Uses statistical methods appropriate to the data available:
    - < 6 months: Simple average
    - 6-12 months: Moving average
    - 12-24 months: Linear regression
    - > 24 months: Seasonal decomposition + regression
    """

    def __init__(self, organization):
        self.organization = organization
        self.transactions = Transaction.objects.filter(organization=organization)

    def _get_monthly_data(self, months=None):
        """
        Get monthly spending data.

        Args:
            months: Optional limit on number of months to retrieve

        Returns:
            List of dicts with month and amount
        """
        queryset = self.transactions.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('month')

        if months:
            cutoff_date = datetime.now().date() - timedelta(days=months * 31)
            queryset = queryset.filter(month__gte=cutoff_date)

        return list(queryset)

    def _calculate_moving_average(self, values, window=3):
        """
        Calculate moving average with given window size.
        """
        if len(values) < window:
            return float(np.mean(values)) if values else 0

        return float(np.mean(values[-window:]))

    def _calculate_linear_regression(self, values):
        """
        Perform simple linear regression to find trend.

        Returns:
            slope: Rate of change per period
            intercept: Starting value
            r_squared: Model fit quality
        """
        if len(values) < 2:
            return 0, values[0] if values else 0, 0

        x = np.arange(len(values))
        y = np.array(values, dtype=float)

        # Calculate regression coefficients
        n = len(values)
        sum_x = np.sum(x)
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        sum_x2 = np.sum(x * x)

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0, float(np.mean(y)), 0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n

        # Calculate R-squared
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return float(slope), float(intercept), float(r_squared)

    def _detect_seasonality(self, monthly_values):
        """
        Detect seasonal patterns in monthly data.

        Args:
            monthly_values: List of (month, value) tuples

        Returns:
            Dict mapping month number (1-12) to seasonal factor
        """
        if len(monthly_values) < 12:
            return {}

        # Group by month of year
        monthly_avg = {}
        monthly_counts = {}

        for month_date, value in monthly_values:
            month_num = month_date.month
            if month_num not in monthly_avg:
                monthly_avg[month_num] = 0
                monthly_counts[month_num] = 0
            monthly_avg[month_num] += value
            monthly_counts[month_num] += 1

        # Calculate average per month
        for month_num in monthly_avg:
            if monthly_counts[month_num] > 0:
                monthly_avg[month_num] /= monthly_counts[month_num]

        # Calculate seasonal factors relative to overall average
        overall_avg = np.mean(list(monthly_avg.values())) if monthly_avg else 1
        if overall_avg == 0:
            return {}

        seasonal_factors = {}
        for month_num, avg in monthly_avg.items():
            seasonal_factors[month_num] = avg / overall_avg

        return seasonal_factors

    def _calculate_confidence_intervals(self, values, forecast_value, confidence=0.95):
        """
        Calculate confidence intervals for a forecast.

        Args:
            values: Historical values
            forecast_value: Predicted value
            confidence: Confidence level (default 0.95 for 95%)

        Returns:
            Tuple of (lower_80, upper_80, lower_95, upper_95)
        """
        if len(values) < 2:
            return forecast_value, forecast_value, forecast_value, forecast_value

        std_dev = float(np.std(values))

        # 80% confidence interval (z = 1.28)
        lower_80 = max(0, forecast_value - 1.28 * std_dev)
        upper_80 = forecast_value + 1.28 * std_dev

        # 95% confidence interval (z = 1.96)
        lower_95 = max(0, forecast_value - 1.96 * std_dev)
        upper_95 = forecast_value + 1.96 * std_dev

        return lower_80, upper_80, lower_95, upper_95

    def get_spending_forecast(self, months=6):
        """
        Get spending forecast for the next N months.

        Args:
            months: Number of months to forecast (default 6)

        Returns:
            Dict with forecast data, trend info, and model accuracy
        """
        monthly_data = self._get_monthly_data()

        if not monthly_data:
            return {
                'forecast': [],
                'trend': {
                    'direction': 'stable',
                    'monthly_change_rate': 0,
                    'seasonality_detected': False,
                    'peak_months': []
                },
                'model_accuracy': {
                    'mape': None,
                    'data_points_used': 0
                }
            }

        # Extract values
        values = [float(d['total']) for d in monthly_data]
        months_dates = [(d['month'], float(d['total'])) for d in monthly_data]

        # Determine forecasting method based on data availability
        data_points = len(values)

        # Detect trend
        slope, intercept, r_squared = self._calculate_linear_regression(values)

        # Detect seasonality
        seasonal_factors = self._detect_seasonality(months_dates)
        seasonality_detected = bool(seasonal_factors) and data_points >= 12

        # Determine trend direction
        if abs(slope) < np.mean(values) * 0.01:  # Less than 1% change
            direction = 'stable'
        elif slope > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'

        # Find peak months
        peak_months = []
        if seasonal_factors:
            sorted_months = sorted(seasonal_factors.items(), key=lambda x: x[1], reverse=True)
            month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            peak_months = [month_names[m[0]] for m in sorted_months[:3] if m[1] > 1.1]

        # Generate forecasts
        forecasts = []
        last_date = monthly_data[-1]['month'] if monthly_data else datetime.now().date()

        for i in range(1, months + 1):
            forecast_date = last_date + relativedelta(months=i)

            # Base forecast using trend
            base_forecast = intercept + slope * (data_points + i - 1)

            # Apply seasonality if detected
            if seasonality_detected and forecast_date.month in seasonal_factors:
                base_forecast *= seasonal_factors[forecast_date.month]

            # Ensure non-negative
            base_forecast = max(0, base_forecast)

            # Calculate confidence intervals
            lower_80, upper_80, lower_95, upper_95 = self._calculate_confidence_intervals(
                values, base_forecast
            )

            forecasts.append({
                'month': forecast_date.strftime('%Y-%m'),
                'predicted_spend': round(base_forecast, 2),
                'lower_bound_80': round(lower_80, 2),
                'upper_bound_80': round(upper_80, 2),
                'lower_bound_95': round(lower_95, 2),
                'upper_bound_95': round(upper_95, 2)
            })

        # Calculate model accuracy (MAPE) using last 3 points as validation
        mape = None
        if data_points >= 6:
            # Use first n-3 points to predict last 3
            train_values = values[:-3]
            test_values = values[-3:]
            train_slope, train_intercept, _ = self._calculate_linear_regression(train_values)

            predictions = [train_intercept + train_slope * (len(train_values) + i) for i in range(3)]
            errors = [abs((pred - actual) / actual) * 100 for pred, actual in zip(predictions, test_values) if actual > 0]
            mape = round(np.mean(errors), 1) if errors else None

        return {
            'forecast': forecasts,
            'trend': {
                'direction': direction,
                'monthly_change_rate': round(slope / np.mean(values) if np.mean(values) > 0 else 0, 4),
                'seasonality_detected': seasonality_detected,
                'peak_months': peak_months
            },
            'model_accuracy': {
                'mape': mape,
                'data_points_used': data_points,
                'r_squared': round(r_squared, 3) if r_squared else None
            }
        }

    def get_category_forecast(self, category_id, months=6):
        """
        Get spending forecast for a specific category.
        """
        category_transactions = self.transactions.filter(category_id=category_id)

        if not category_transactions.exists():
            return {
                'category_id': category_id,
                'forecast': [],
                'trend': {'direction': 'stable', 'monthly_change_rate': 0},
                'model_accuracy': {'mape': None, 'data_points_used': 0}
            }

        monthly_data = category_transactions.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')

        values = [float(d['total']) for d in monthly_data]

        if not values:
            return {
                'category_id': category_id,
                'forecast': [],
                'trend': {'direction': 'stable', 'monthly_change_rate': 0},
                'model_accuracy': {'mape': None, 'data_points_used': 0}
            }

        slope, intercept, r_squared = self._calculate_linear_regression(values)

        direction = 'stable'
        if abs(slope) >= np.mean(values) * 0.01:
            direction = 'increasing' if slope > 0 else 'decreasing'

        forecasts = []
        last_date = list(monthly_data)[-1]['month'] if monthly_data else datetime.now().date()

        for i in range(1, months + 1):
            forecast_date = last_date + relativedelta(months=i)
            base_forecast = max(0, intercept + slope * (len(values) + i - 1))
            lower_80, upper_80, lower_95, upper_95 = self._calculate_confidence_intervals(values, base_forecast)

            forecasts.append({
                'month': forecast_date.strftime('%Y-%m'),
                'predicted_spend': round(base_forecast, 2),
                'lower_bound_80': round(lower_80, 2),
                'upper_bound_80': round(upper_80, 2),
                'lower_bound_95': round(lower_95, 2),
                'upper_bound_95': round(upper_95, 2)
            })

        return {
            'category_id': category_id,
            'forecast': forecasts,
            'trend': {
                'direction': direction,
                'monthly_change_rate': round(slope / np.mean(values) if np.mean(values) > 0 else 0, 4)
            },
            'model_accuracy': {
                'mape': None,
                'data_points_used': len(values),
                'r_squared': round(r_squared, 3) if r_squared else None
            }
        }

    def get_supplier_forecast(self, supplier_id, months=6):
        """
        Get spending forecast for a specific supplier.
        """
        supplier_transactions = self.transactions.filter(supplier_id=supplier_id)

        if not supplier_transactions.exists():
            return {
                'supplier_id': supplier_id,
                'forecast': [],
                'trend': {'direction': 'stable', 'monthly_change_rate': 0},
                'model_accuracy': {'mape': None, 'data_points_used': 0}
            }

        monthly_data = supplier_transactions.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')

        values = [float(d['total']) for d in monthly_data]

        if not values:
            return {
                'supplier_id': supplier_id,
                'forecast': [],
                'trend': {'direction': 'stable', 'monthly_change_rate': 0},
                'model_accuracy': {'mape': None, 'data_points_used': 0}
            }

        slope, intercept, r_squared = self._calculate_linear_regression(values)

        direction = 'stable'
        if abs(slope) >= np.mean(values) * 0.01:
            direction = 'increasing' if slope > 0 else 'decreasing'

        forecasts = []
        last_date = list(monthly_data)[-1]['month'] if monthly_data else datetime.now().date()

        for i in range(1, months + 1):
            forecast_date = last_date + relativedelta(months=i)
            base_forecast = max(0, intercept + slope * (len(values) + i - 1))
            lower_80, upper_80, lower_95, upper_95 = self._calculate_confidence_intervals(values, base_forecast)

            forecasts.append({
                'month': forecast_date.strftime('%Y-%m'),
                'predicted_spend': round(base_forecast, 2),
                'lower_bound_80': round(lower_80, 2),
                'upper_bound_80': round(upper_80, 2),
                'lower_bound_95': round(lower_95, 2),
                'upper_bound_95': round(upper_95, 2)
            })

        return {
            'supplier_id': supplier_id,
            'forecast': forecasts,
            'trend': {
                'direction': direction,
                'monthly_change_rate': round(slope / np.mean(values) if np.mean(values) > 0 else 0, 4)
            },
            'model_accuracy': {
                'mape': None,
                'data_points_used': len(values),
                'r_squared': round(r_squared, 3) if r_squared else None
            }
        }

    def get_trend_analysis(self):
        """
        Get comprehensive trend analysis across all dimensions.
        """
        monthly_data = self._get_monthly_data()

        if not monthly_data:
            return {
                'overall_trend': {'direction': 'stable', 'change_rate': 0},
                'category_trends': [],
                'supplier_trends': [],
                'growth_metrics': {}
            }

        values = [float(d['total']) for d in monthly_data]
        slope, intercept, r_squared = self._calculate_linear_regression(values)

        # Overall trend
        direction = 'stable'
        if abs(slope) >= np.mean(values) * 0.01:
            direction = 'increasing' if slope > 0 else 'decreasing'

        # Category trends
        category_trends = []
        categories = self.transactions.values('category_id', 'category__name').distinct()

        for cat in categories[:10]:  # Top 10 categories
            cat_data = self.transactions.filter(category_id=cat['category_id']).annotate(
                month=TruncMonth('date')
            ).values('month').annotate(total=Sum('amount')).order_by('month')

            cat_values = [float(d['total']) for d in cat_data]
            if len(cat_values) >= 2:
                cat_slope, _, _ = self._calculate_linear_regression(cat_values)
                cat_direction = 'stable'
                if abs(cat_slope) >= np.mean(cat_values) * 0.01:
                    cat_direction = 'increasing' if cat_slope > 0 else 'decreasing'

                category_trends.append({
                    'category_id': cat['category_id'],
                    'category_name': cat['category__name'],
                    'direction': cat_direction,
                    'change_rate': round(cat_slope / np.mean(cat_values) if np.mean(cat_values) > 0 else 0, 4)
                })

        # Supplier trends
        supplier_trends = []
        suppliers = self.transactions.values('supplier_id', 'supplier__name').annotate(
            total=Sum('amount')
        ).order_by('-total')[:10]  # Top 10 suppliers

        for sup in suppliers:
            sup_data = self.transactions.filter(supplier_id=sup['supplier_id']).annotate(
                month=TruncMonth('date')
            ).values('month').annotate(total=Sum('amount')).order_by('month')

            sup_values = [float(d['total']) for d in sup_data]
            if len(sup_values) >= 2:
                sup_slope, _, _ = self._calculate_linear_regression(sup_values)
                sup_direction = 'stable'
                if abs(sup_slope) >= np.mean(sup_values) * 0.01:
                    sup_direction = 'increasing' if sup_slope > 0 else 'decreasing'

                supplier_trends.append({
                    'supplier_id': sup['supplier_id'],
                    'supplier_name': sup['supplier__name'],
                    'direction': sup_direction,
                    'change_rate': round(sup_slope / np.mean(sup_values) if np.mean(sup_values) > 0 else 0, 4)
                })

        # Growth metrics
        growth_metrics = {}
        if len(values) >= 12:
            # Year-over-year growth
            current_year = sum(values[-12:])
            prev_year = sum(values[-24:-12]) if len(values) >= 24 else sum(values[:-12])
            yoy_growth = ((current_year - prev_year) / prev_year * 100) if prev_year > 0 else 0
            growth_metrics['yoy_growth'] = round(yoy_growth, 2)

        if len(values) >= 6:
            # 6-month trend
            recent = sum(values[-6:])
            previous = sum(values[-12:-6]) if len(values) >= 12 else sum(values[:-6])
            six_month_growth = ((recent - previous) / previous * 100) if previous > 0 else 0
            growth_metrics['six_month_growth'] = round(six_month_growth, 2)

        if len(values) >= 3:
            # 3-month trend
            recent_3 = sum(values[-3:])
            previous_3 = sum(values[-6:-3]) if len(values) >= 6 else sum(values[:-3])
            three_month_growth = ((recent_3 - previous_3) / previous_3 * 100) if previous_3 > 0 else 0
            growth_metrics['three_month_growth'] = round(three_month_growth, 2)

        return {
            'overall_trend': {
                'direction': direction,
                'change_rate': round(slope / np.mean(values) if np.mean(values) > 0 else 0, 4),
                'r_squared': round(r_squared, 3)
            },
            'category_trends': category_trends,
            'supplier_trends': supplier_trends,
            'growth_metrics': growth_metrics
        }

    def get_budget_projection(self, annual_budget):
        """
        Compare forecast against budget and project year-end position.

        Args:
            annual_budget: Annual budget amount

        Returns:
            Budget projection with variance analysis
        """
        if annual_budget <= 0:
            return {'error': 'Annual budget must be positive'}

        annual_budget = float(annual_budget)
        monthly_budget = annual_budget / 12

        # Get current year's data
        current_year = datetime.now().year
        ytd_data = self.transactions.filter(
            date__year=current_year
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')

        ytd_values = [float(d['total']) for d in ytd_data]
        ytd_spend = sum(ytd_values)
        months_elapsed = len(ytd_values)

        if months_elapsed == 0:
            return {
                'annual_budget': annual_budget,
                'ytd_spend': 0,
                'ytd_budget': 0,
                'variance': 0,
                'variance_percentage': 0,
                'projected_year_end': 0,
                'projected_variance': annual_budget,
                'status': 'no_data'
            }

        ytd_budget = monthly_budget * months_elapsed
        variance = ytd_budget - ytd_spend
        variance_percentage = (variance / ytd_budget * 100) if ytd_budget > 0 else 0

        # Project year-end spend
        months_remaining = 12 - months_elapsed

        # Get forecast for remaining months
        forecast_result = self.get_spending_forecast(months=months_remaining)
        projected_remaining = sum(f['predicted_spend'] for f in forecast_result['forecast'])
        projected_year_end = ytd_spend + projected_remaining
        projected_variance = annual_budget - projected_year_end

        # Determine status
        if variance_percentage >= 10:
            status = 'under_budget'
        elif variance_percentage <= -10:
            status = 'over_budget'
        else:
            status = 'on_track'

        return {
            'annual_budget': annual_budget,
            'monthly_budget': round(monthly_budget, 2),
            'ytd_spend': round(ytd_spend, 2),
            'ytd_budget': round(ytd_budget, 2),
            'variance': round(variance, 2),
            'variance_percentage': round(variance_percentage, 2),
            'projected_year_end': round(projected_year_end, 2),
            'projected_variance': round(projected_variance, 2),
            'months_elapsed': months_elapsed,
            'months_remaining': months_remaining,
            'status': status,
            'monthly_forecast': forecast_result['forecast']
        }
