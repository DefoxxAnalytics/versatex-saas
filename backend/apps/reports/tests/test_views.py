"""
Tests for Report API views.
"""
import pytest
import uuid
from datetime import date
from django.urls import reverse
from rest_framework import status
from apps.reports.models import Report


@pytest.mark.django_db
class TestReportTemplates:
    """Tests for report templates endpoint."""

    def test_list_templates(self, authenticated_client):
        """Test listing available report templates."""
        url = reverse('reports:templates')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) >= 10  # At least 10 templates defined

        # Check template structure
        template = response.data[0]
        assert 'id' in template
        assert 'name' in template
        assert 'description' in template
        assert 'report_type' in template

    def test_templates_require_auth(self, api_client):
        """Test that templates endpoint requires authentication."""
        url = reverse('reports:templates')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_template_detail(self, authenticated_client):
        """Test getting a specific template."""
        url = reverse('reports:template-detail', kwargs={'template_id': 'executive_summary'})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == 'executive_summary'
        assert response.data['name'] == 'Executive Summary'

    def test_template_detail_not_found(self, authenticated_client):
        """Test getting a non-existent template."""
        url = reverse('reports:template-detail', kwargs={'template_id': 'nonexistent'})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestReportGeneration:
    """Tests for report generation endpoint."""

    def test_generate_report_sync(self, admin_client, organization, admin_user, transaction):
        """Test generating a report synchronously."""
        url = reverse('reports:generate')
        data = {
            'report_type': 'spend_analysis',
            'report_format': 'pdf',
            'name': 'Test Spend Report',
            'async_generation': False
        }
        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data
        assert response.data['status'] == 'completed'
        assert response.data['report_type'] == 'spend_analysis'

    def test_generate_report_async(self, admin_client, organization, admin_user, transaction):
        """Test generating a report asynchronously."""
        url = reverse('reports:generate')
        data = {
            'report_type': 'executive_summary',
            'report_format': 'xlsx',
            'async_generation': True
        }
        response = admin_client.post(url, data, format='json')

        # Async returns 202 Accepted
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert 'id' in response.data
        assert response.data['status'] == 'generating'

    def test_generate_report_with_filters(self, admin_client, organization, supplier, category, transaction):
        """Test generating a report with filters."""
        url = reverse('reports:generate')
        data = {
            'report_type': 'spend_analysis',
            'report_format': 'pdf',
            'filters': {
                'supplier_ids': [supplier.id],
                'category_ids': [category.id]
            },
            'async_generation': False
        }
        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_generate_report_with_date_range(self, admin_client, transaction):
        """Test generating a report with date range."""
        url = reverse('reports:generate')
        data = {
            'report_type': 'spend_analysis',
            'period_start': '2024-01-01',
            'period_end': '2024-12-31',
            'async_generation': False
        }
        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_generate_report_invalid_type(self, admin_client):
        """Test generating with invalid report type."""
        url = reverse('reports:generate')
        data = {
            'report_type': 'invalid_type',
            'async_generation': False
        }
        response = admin_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_generate_report_missing_type(self, admin_client):
        """Test generating without report type."""
        url = reverse('reports:generate')
        data = {}
        response = admin_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_generate_requires_auth(self, api_client):
        """Test that generation requires authentication."""
        url = reverse('reports:generate')
        response = api_client.post(url, {}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestReportPreview:
    """Tests for report preview endpoint."""

    def test_preview_report(self, admin_client, transaction):
        """Test previewing a report."""
        url = reverse('reports:preview')
        data = {
            'report_type': 'spend_analysis'
        }
        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert '_preview' in response.data
        assert response.data['_preview'] is True
        assert response.data['_truncated'] is True

    def test_preview_invalid_type(self, admin_client):
        """Test previewing with invalid type."""
        url = reverse('reports:preview')
        data = {
            'report_type': 'invalid'
        }
        response = admin_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestReportList:
    """Tests for report list endpoint."""

    def test_list_reports(self, admin_client, organization, admin_user):
        """Test listing reports."""
        # Create some reports
        for i in range(3):
            Report.objects.create(
                organization=organization,
                created_by=admin_user,
                report_type='spend_analysis',
                name=f'Test Report {i}'
            )

        url = reverse('reports:list')
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'total' in response.data
        assert response.data['total'] == 3

    def test_list_reports_filter_status(self, admin_client, organization, admin_user):
        """Test filtering reports by status."""
        Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            status='completed'
        )
        Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            status='draft'
        )

        url = reverse('reports:list')
        response = admin_client.get(url, {'status': 'completed'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 1
        assert response.data['results'][0]['status'] == 'completed'

    def test_list_reports_filter_type(self, admin_client, organization, admin_user):
        """Test filtering reports by type."""
        Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis'
        )
        Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='executive_summary'
        )

        url = reverse('reports:list')
        response = admin_client.get(url, {'report_type': 'executive_summary'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 1

    def test_list_reports_pagination(self, admin_client, organization, admin_user):
        """Test report list pagination."""
        for i in range(15):
            Report.objects.create(
                organization=organization,
                created_by=admin_user,
                report_type='spend_analysis',
                name=f'Report {i}'
            )

        url = reverse('reports:list')
        response = admin_client.get(url, {'limit': 5, 'offset': 0})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5
        assert response.data['total'] == 15
        assert response.data['limit'] == 5

    def test_list_reports_organization_scoped(self, admin_client, organization, other_organization, admin_user):
        """Test that reports are scoped by organization."""
        # Create a user for the other org directly to avoid api_client collision
        from apps.authentication.models import UserProfile
        from django.contrib.auth.models import User
        other_user = User.objects.create_user(
            username='otheruser_isolated',
            email='other_isolated@example.com',
            password='TestPass123!'
        )
        UserProfile.objects.create(
            user=other_user,
            organization=other_organization,
            role='admin',
            is_active=True
        )

        Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            name='Org 1 Report'
        )
        Report.objects.create(
            organization=other_organization,
            created_by=other_user,
            report_type='spend_analysis',
            name='Org 2 Report'
        )

        # User 1 should only see org 1 report
        url = reverse('reports:list')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 1
        assert response.data['results'][0]['name'] == 'Org 1 Report'


@pytest.mark.django_db
class TestReportDetail:
    """Tests for report detail endpoint."""

    def test_get_report_detail(self, admin_client, organization, admin_user):
        """Test getting report details."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            name='Detailed Report',
            status='completed',
            summary_data={'total_spend': 100000}
        )

        url = reverse('reports:detail', kwargs={'report_id': str(report.id)})
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Detailed Report'
        assert response.data['summary_data']['total_spend'] == 100000

    def test_get_report_not_found(self, admin_client):
        """Test getting non-existent report."""
        fake_id = uuid.uuid4()
        url = reverse('reports:detail', kwargs={'report_id': str(fake_id)})
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_report_access_denied(self, authenticated_client, other_organization, other_org_user):
        """Test accessing report from another org."""
        report = Report.objects.create(
            organization=other_organization,
            created_by=other_org_user,
            report_type='spend_analysis'
        )

        url = reverse('reports:detail', kwargs={'report_id': str(report.id)})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestReportStatus:
    """Tests for report status endpoint."""

    def test_get_report_status(self, admin_client, organization, admin_user):
        """Test getting report generation status."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            status='generating'
        )

        url = reverse('reports:status', kwargs={'report_id': str(report.id)})
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'generating'

    def test_status_not_found(self, admin_client):
        """Test status for non-existent report."""
        fake_id = uuid.uuid4()
        url = reverse('reports:status', kwargs={'report_id': str(fake_id)})
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestReportDelete:
    """Tests for report delete endpoint."""

    def test_delete_own_report(self, admin_client, organization, admin_user):
        """Test deleting own report."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis'
        )
        report_id = str(report.id)

        url = reverse('reports:delete', kwargs={'report_id': report_id})
        response = admin_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Report.objects.filter(id=report_id).exists()

    def test_delete_not_creator(self, authenticated_client, organization, admin_user):
        """Test that non-creator cannot delete report."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis'
        )

        url = reverse('reports:delete', kwargs={'report_id': str(report.id)})
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_not_found(self, admin_client):
        """Test deleting non-existent report."""
        fake_id = uuid.uuid4()
        url = reverse('reports:delete', kwargs={'report_id': str(fake_id)})
        response = admin_client.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestReportDownload:
    """Tests for report download endpoint."""

    def test_download_completed_report(self, admin_client, organization, admin_user, transaction):
        """Test downloading a completed report."""
        # First generate a report
        gen_url = reverse('reports:generate')
        gen_response = admin_client.post(gen_url, {
            'report_type': 'spend_analysis',
            'report_format': 'csv',
            'async_generation': False
        }, format='json')

        report_id = gen_response.data['id']

        # Then download it
        url = reverse('reports:download', kwargs={'report_id': report_id})
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'attachment' in response['Content-Disposition']

    def test_download_incomplete_report(self, admin_client, organization, admin_user):
        """Test downloading an incomplete report."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            status='generating'
        )

        url = reverse('reports:download', kwargs={'report_id': str(report.id)})
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_download_with_format_override(self, admin_client, organization, admin_user, transaction):
        """Test downloading with format override."""
        # Generate PDF report
        gen_url = reverse('reports:generate')
        gen_response = admin_client.post(gen_url, {
            'report_type': 'spend_analysis',
            'report_format': 'pdf',
            'async_generation': False
        }, format='json')

        report_id = gen_response.data['id']

        # Download as CSV instead
        url = reverse('reports:download', kwargs={'report_id': report_id})
        response = admin_client.get(url, {'output_format': 'csv'})

        assert response.status_code == status.HTTP_200_OK
        assert 'text/csv' in response['Content-Type']


@pytest.mark.django_db
class TestReportSchedules:
    """Tests for scheduled reports endpoints."""

    def test_list_schedules(self, admin_client, organization, admin_user):
        """Test listing scheduled reports."""
        Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            is_scheduled=True,
            schedule_frequency='weekly',
            status='scheduled'
        )

        url = reverse('reports:schedules')
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_create_schedule(self, admin_client):
        """Test creating a scheduled report."""
        url = reverse('reports:schedules')
        data = {
            'report_type': 'executive_summary',
            'report_format': 'pdf',
            'name': 'Weekly Executive Report',
            'is_scheduled': True,
            'schedule_frequency': 'weekly'
        }
        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['is_scheduled'] is True
        assert response.data['schedule_frequency'] == 'weekly'
        assert response.data['next_run'] is not None

    def test_update_schedule(self, admin_client, organization, admin_user):
        """Test updating a schedule."""
        schedule = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            is_scheduled=True,
            schedule_frequency='weekly',
            status='scheduled'
        )

        url = reverse('reports:schedule-detail', kwargs={'schedule_id': str(schedule.id)})
        response = admin_client.put(url, {
            'schedule_frequency': 'daily'
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        schedule.refresh_from_db()
        assert schedule.schedule_frequency == 'daily'

    def test_delete_schedule(self, admin_client, organization, admin_user):
        """Test deleting a schedule."""
        schedule = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            is_scheduled=True,
            schedule_frequency='weekly',
            status='scheduled'
        )
        schedule_id = str(schedule.id)

        url = reverse('reports:schedule-detail', kwargs={'schedule_id': schedule_id})
        response = admin_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Report.objects.filter(id=schedule_id).exists()

    def test_run_schedule_now(self, admin_client, organization, admin_user):
        """Test triggering immediate schedule execution."""
        schedule = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            is_scheduled=True,
            schedule_frequency='weekly',
            status='scheduled'
        )

        url = reverse('reports:schedule-run-now', kwargs={'schedule_id': str(schedule.id)})
        response = admin_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'Report generation triggered' in response.data['message']


@pytest.mark.django_db
class TestReportShare:
    """Tests for report sharing endpoint."""

    def test_share_report_public(self, admin_client, organization, admin_user):
        """Test making a report public."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            is_public=False
        )

        url = reverse('reports:share', kwargs={'report_id': str(report.id)})
        response = admin_client.post(url, {'is_public': True}, format='json')

        assert response.status_code == status.HTTP_200_OK
        report.refresh_from_db()
        assert report.is_public is True

    def test_share_with_users(self, admin_client, organization, admin_user, user):
        """Test sharing report with specific users."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis'
        )

        url = reverse('reports:share', kwargs={'report_id': str(report.id)})
        response = admin_client.post(url, {'user_ids': [user.id]}, format='json')

        assert response.status_code == status.HTTP_200_OK
        report.refresh_from_db()
        assert user in report.shared_with.all()

    def test_share_only_creator_can_share(self, authenticated_client, organization, admin_user):
        """Test that only creator can share a report."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis'
        )

        url = reverse('reports:share', kwargs={'report_id': str(report.id)})
        response = authenticated_client.post(url, {'is_public': True}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestReportAuthentication:
    """Tests for authentication on all report endpoints."""

    def test_all_endpoints_require_auth(self, api_client, organization, admin_user):
        """Test that all endpoints require authentication."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            is_scheduled=True,
            schedule_frequency='weekly',
            status='scheduled'
        )
        report_id = str(report.id)

        endpoints = [
            ('reports:templates', 'get', {}),
            ('reports:generate', 'post', {}),
            ('reports:preview', 'post', {}),
            ('reports:list', 'get', {}),
            ('reports:detail', 'get', {'report_id': report_id}),
            ('reports:status', 'get', {'report_id': report_id}),
            ('reports:download', 'get', {'report_id': report_id}),
            ('reports:delete', 'delete', {'report_id': report_id}),
            ('reports:share', 'post', {'report_id': report_id}),
            ('reports:schedules', 'get', {}),
            ('reports:schedule-detail', 'get', {'schedule_id': report_id}),
            ('reports:schedule-run-now', 'post', {'schedule_id': report_id}),
        ]

        for endpoint_name, method, kwargs in endpoints:
            url = reverse(endpoint_name, kwargs=kwargs) if kwargs else reverse(endpoint_name)
            if method == 'get':
                response = api_client.get(url)
            elif method == 'post':
                response = api_client.post(url, {})
            elif method == 'delete':
                response = api_client.delete(url)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
                f"Endpoint {endpoint_name} did not require authentication"
