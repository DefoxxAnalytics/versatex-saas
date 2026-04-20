"""
URL patterns for the reports module.
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Report templates
    path('templates/', views.report_templates, name='templates'),
    path('templates/<str:template_id>/', views.report_template_detail, name='template-detail'),

    # Report generation and preview
    path('generate/', views.generate_report, name='generate'),
    path('preview/', views.report_preview, name='preview'),

    # Report list and detail
    path('', views.report_list, name='list'),
    path('<uuid:report_id>/', views.report_detail, name='detail'),
    path('<uuid:report_id>/status/', views.report_status, name='status'),
    path('<uuid:report_id>/download/', views.report_download, name='download'),
    path('<uuid:report_id>/delete/', views.report_delete, name='delete'),
    path('<uuid:report_id>/share/', views.report_share, name='share'),

    # Scheduled reports
    path('schedules/', views.report_schedules, name='schedules'),
    path('schedules/<uuid:schedule_id>/', views.report_schedule_detail, name='schedule-detail'),
    path('schedules/<uuid:schedule_id>/run-now/', views.schedule_run_now, name='schedule-run-now'),
]
