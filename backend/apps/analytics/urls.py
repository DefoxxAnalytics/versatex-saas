"""
URL patterns for analytics
"""
from django.urls import path, include
from . import views

urlpatterns = [
    # Core Analytics
    path('overview/', views.overview_stats, name='overview-stats'),
    path('spend-by-category/', views.spend_by_category, name='spend-by-category'),
    path('categories/detailed/', views.detailed_category_stats, name='detailed-category-stats'),
    path('spend-by-supplier/', views.spend_by_supplier, name='spend-by-supplier'),
    path('suppliers/detailed/', views.detailed_supplier_stats, name='detailed-supplier-stats'),
    path('monthly-trend/', views.monthly_trend, name='monthly-trend'),
    path('pareto/', views.pareto_analysis, name='pareto-analysis'),
    path('pareto/supplier/<int:supplier_id>/', views.supplier_drilldown, name='supplier-drilldown'),
    path('category/<int:category_id>/drilldown/', views.category_drilldown, name='category-drilldown'),
    path('tail-spend/', views.tail_spend_analysis, name='tail-spend'),
    path('tail-spend/detailed/', views.detailed_tail_spend, name='detailed-tail-spend'),
    path('tail-spend/category/<int:category_id>/', views.tail_spend_category_drilldown, name='tail-spend-category-drilldown'),
    path('tail-spend/vendor/<int:supplier_id>/', views.tail_spend_vendor_drilldown, name='tail-spend-vendor-drilldown'),
    path('stratification/', views.spend_stratification, name='stratification'),
    path('stratification/detailed/', views.detailed_stratification, name='detailed-stratification'),
    path('stratification/segment/<str:segment_name>/', views.stratification_segment_drilldown, name='stratification-segment-drilldown'),
    path('stratification/band/<str:band_name>/', views.stratification_band_drilldown, name='stratification-band-drilldown'),
    path('seasonality/', views.seasonality_analysis, name='seasonality'),
    path('seasonality/detailed/', views.detailed_seasonality, name='detailed-seasonality'),
    path('seasonality/category/<int:category_id>/', views.seasonality_category_drilldown, name='seasonality-category-drilldown'),
    path('year-over-year/', views.year_over_year, name='year-over-year'),
    path('year-over-year/detailed/', views.detailed_year_over_year, name='detailed-year-over-year'),
    path('year-over-year/category/<int:category_id>/', views.yoy_category_drilldown, name='yoy-category-drilldown'),
    path('year-over-year/supplier/<int:supplier_id>/', views.yoy_supplier_drilldown, name='yoy-supplier-drilldown'),
    path('consolidation/', views.consolidation_opportunities, name='consolidation'),

    # AI Insights
    path('ai-insights/', views.ai_insights, name='ai-insights'),
    path('ai-insights/cost/', views.ai_insights_cost, name='ai-insights-cost'),
    path('ai-insights/risk/', views.ai_insights_risk, name='ai-insights-risk'),
    path('ai-insights/anomalies/', views.ai_insights_anomalies, name='ai-insights-anomalies'),

    # Async AI Enhancement
    path('ai-insights/enhance/request/', views.request_ai_enhancement, name='request-ai-enhancement'),
    path('ai-insights/enhance/status/', views.get_ai_enhancement_status, name='ai-enhancement-status'),

    # Deep Analysis
    path('ai-insights/deep-analysis/request/', views.request_deep_analysis, name='request-deep-analysis'),
    path('ai-insights/deep-analysis/status/<str:insight_id>/', views.get_deep_analysis_status, name='deep-analysis-status'),

    # AI Insight Feedback
    path('ai-insights/feedback/', views.record_insight_feedback, name='record-insight-feedback'),
    path('ai-insights/feedback/list/', views.list_insight_feedback, name='list-insight-feedback'),
    path('ai-insights/feedback/effectiveness/', views.get_insight_effectiveness, name='insight-effectiveness'),
    path('ai-insights/feedback/<uuid:feedback_id>/', views.update_insight_outcome, name='update-insight-outcome'),
    path('ai-insights/feedback/<uuid:feedback_id>/delete/', views.delete_insight_feedback, name='delete-insight-feedback'),

    # AI Insights Metrics & Monitoring (for Prometheus/Grafana integration)
    path('ai-insights/metrics/', views.ai_insights_metrics, name='ai-insights-metrics'),
    path('ai-insights/metrics/prometheus/', views.ai_insights_metrics_prometheus, name='ai-insights-metrics-prometheus'),
    path('ai-insights/cache/invalidate/', views.ai_insights_cache_invalidate, name='ai-insights-cache-invalidate'),

    # AI Insights LLM Usage & Cost Tracking
    path('ai-insights/usage/', views.ai_insights_usage, name='ai-insights-usage'),
    path('ai-insights/usage/daily/', views.ai_insights_usage_daily, name='ai-insights-usage-daily'),

    # AI Chat Streaming
    path('ai-insights/chat/stream/', views.ai_chat_stream, name='ai-chat-stream'),
    path('ai-insights/chat/quick/', views.ai_quick_query, name='ai-quick-query'),

    # Predictive Analytics
    path('predictions/spending/', views.spending_forecast, name='spending-forecast'),
    path('predictions/category/<int:category_id>/', views.category_forecast, name='category-forecast'),
    path('predictions/supplier/<int:supplier_id>/', views.supplier_forecast, name='supplier-forecast'),
    path('predictions/trends/', views.trend_analysis, name='trend-analysis'),
    path('predictions/budget/', views.budget_projection, name='budget-projection'),

    # Contract Analytics
    path('contracts/overview/', views.contract_overview, name='contract-overview'),
    path('contracts/', views.contracts_list, name='contracts-list'),
    path('contracts/<int:contract_id>/', views.contract_detail, name='contract-detail'),
    path('contracts/expiring/', views.expiring_contracts, name='expiring-contracts'),
    path('contracts/<int:contract_id>/performance/', views.contract_performance, name='contract-performance'),
    path('contracts/savings/', views.contract_savings_opportunities, name='contract-savings'),
    path('contracts/renewals/', views.contract_renewals, name='contract-renewals'),
    path('contracts/vs-actual/', views.contract_vs_actual, name='contract-vs-actual'),

    # Compliance & Maverick Spend
    path('compliance/overview/', views.compliance_overview, name='compliance-overview'),
    path('compliance/maverick-spend/', views.maverick_spend_analysis, name='maverick-spend'),
    path('compliance/violations/', views.policy_violations, name='policy-violations'),
    path('compliance/violations/<int:violation_id>/resolve/', views.resolve_violation, name='resolve-violation'),
    path('compliance/trends/', views.violation_trends, name='violation-trends'),
    path('compliance/supplier-scores/', views.supplier_compliance_scores, name='supplier-compliance-scores'),
    path('compliance/policies/', views.spending_policies, name='spending-policies'),

    # P2P (Procure-to-Pay) Analytics
    path('', include('apps.analytics.p2p_urls')),

    # RAG Document Management
    path('rag/documents/', views.list_rag_documents, name='rag-documents-list'),
    path('rag/documents/<uuid:document_id>/', views.get_rag_document, name='rag-document-detail'),
    path('rag/documents/create/', views.create_rag_document, name='rag-document-create'),
    path('rag/documents/<uuid:document_id>/delete/', views.delete_rag_document, name='rag-document-delete'),
    path('rag/search/', views.search_rag_documents, name='rag-search'),
    path('rag/ingest/suppliers/', views.ingest_supplier_profiles, name='rag-ingest-suppliers'),
    path('rag/ingest/insights/', views.ingest_historical_insights, name='rag-ingest-insights'),
    path('rag/refresh/', views.refresh_rag_documents, name='rag-refresh'),
    path('rag/cleanup/', views.cleanup_orphaned_documents, name='rag-cleanup'),
    path('rag/stats/', views.get_rag_stats, name='rag-stats'),
]
