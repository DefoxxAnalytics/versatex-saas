"""
Tests for procurement views.
"""
import pytest
import io
from decimal import Decimal
from datetime import date
from django.urls import reverse
from rest_framework import status
from apps.procurement.models import Supplier, Category, Transaction, DataUpload
from apps.authentication.models import AuditLog
from .factories import SupplierFactory, CategoryFactory, TransactionFactory, DataUploadFactory


def get_results(response_data):
    """Extract results from paginated or non-paginated response."""
    if isinstance(response_data, dict) and 'results' in response_data:
        return response_data['results']
    return response_data


@pytest.mark.django_db
class TestSupplierViewSet:
    """Tests for Supplier CRUD operations."""

    def test_list_suppliers(self, authenticated_client, organization, supplier):
        """Test listing suppliers for user's organization."""
        url = reverse('supplier-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) >= 1
        supplier_names = [s['name'] for s in results]
        assert supplier.name in supplier_names

    def test_list_suppliers_organization_scoped(self, authenticated_client, other_organization):
        """Test that suppliers from other orgs are not visible."""
        other_supplier = SupplierFactory(organization=other_organization)

        url = reverse('supplier-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        results = get_results(response.data)
        supplier_names = [s['name'] for s in results]
        assert other_supplier.name not in supplier_names

    def test_create_supplier(self, admin_client, organization):
        """Test creating a supplier."""
        url = reverse('supplier-list')
        data = {
            'name': 'New Supplier',
            'code': 'NEW001',
            'contact_email': 'new@supplier.com'
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Supplier.objects.filter(name='New Supplier').exists()

    def test_create_supplier_creates_audit_log(self, admin_client, admin_user):
        """Test that creating a supplier creates an audit log."""
        url = reverse('supplier-list')
        data = {'name': 'Audit Test Supplier'}
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

        log = AuditLog.objects.filter(
            user=admin_user,
            action='create',
            resource='supplier'
        ).first()
        assert log is not None

    def test_update_supplier(self, admin_client, supplier):
        """Test updating a supplier."""
        url = reverse('supplier-detail', args=[supplier.id])
        data = {'name': 'Updated Supplier Name'}
        response = admin_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK

        supplier.refresh_from_db()
        assert supplier.name == 'Updated Supplier Name'

    def test_delete_supplier(self, admin_client, organization):
        """Test deleting a supplier (without transactions)."""
        supplier = SupplierFactory(organization=organization)
        url = reverse('supplier-detail', args=[supplier.id])
        response = admin_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Supplier.objects.filter(id=supplier.id).exists()

    def test_cannot_access_other_org_supplier(self, authenticated_client, other_organization):
        """Test that users cannot access suppliers from other orgs."""
        other_supplier = SupplierFactory(organization=other_organization)
        url = reverse('supplier-detail', args=[other_supplier.id])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_search_suppliers(self, authenticated_client, organization):
        """Test searching suppliers."""
        SupplierFactory(organization=organization, name='Acme Corporation')
        SupplierFactory(organization=organization, name='Beta Industries')

        url = reverse('supplier-list')
        response = authenticated_client.get(url, {'search': 'Acme'})
        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) == 1
        assert results[0]['name'] == 'Acme Corporation'


@pytest.mark.django_db
class TestCategoryViewSet:
    """Tests for Category CRUD operations."""

    def test_list_categories(self, authenticated_client, organization, category):
        """Test listing categories for user's organization."""
        url = reverse('category-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) >= 1

    def test_create_category(self, admin_client, organization):
        """Test creating a category."""
        url = reverse('category-list')
        data = {
            'name': 'New Category',
            'description': 'A new category for testing'
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_category_with_parent(self, admin_client, category):
        """Test creating a category with parent."""
        url = reverse('category-list')
        data = {
            'name': 'Child Category',
            'parent': category.id
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['parent'] == category.id

    def test_category_organization_scoped(self, authenticated_client, other_organization):
        """Test that categories from other orgs are not visible."""
        other_category = CategoryFactory(organization=other_organization)

        url = reverse('category-list')
        response = authenticated_client.get(url)
        results = get_results(response.data)
        category_names = [c['name'] for c in results]
        assert other_category.name not in category_names


@pytest.mark.django_db
class TestTransactionViewSet:
    """Tests for Transaction CRUD operations."""

    def test_list_transactions(self, authenticated_client, transaction):
        """Test listing transactions."""
        url = reverse('transaction-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_transaction(self, admin_client, supplier, category):
        """Test creating a transaction."""
        url = reverse('transaction-list')
        data = {
            'supplier': supplier.id,
            'category': category.id,
            'amount': '1500.00',
            'date': '2024-01-15',
            'description': 'Test transaction'
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_transaction_by_name(self, admin_client, organization):
        """Test creating a transaction using supplier/category names."""
        url = reverse('transaction-list')
        data = {
            'supplier_name': 'New Supplier via Name',
            'category_name': 'New Category via Name',
            'amount': '2000.00',
            'date': '2024-02-20',
            'description': 'Transaction with new entities'
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Supplier.objects.filter(name='New Supplier via Name').exists()
        assert Category.objects.filter(name='New Category via Name').exists()

    def test_transaction_organization_scoped(self, authenticated_client, other_organization, other_org_user):
        """Test that transactions from other orgs are not visible."""
        other_supplier = SupplierFactory(organization=other_organization)
        other_category = CategoryFactory(organization=other_organization)
        other_transaction = TransactionFactory(
            organization=other_organization,
            supplier=other_supplier,
            category=other_category,
            uploaded_by=other_org_user
        )

        url = reverse('transaction-list')
        response = authenticated_client.get(url)
        results = get_results(response.data)
        tx_ids = [t['id'] for t in results]
        assert other_transaction.id not in tx_ids

    def test_filter_transactions_by_supplier(self, authenticated_client, organization, supplier, category, admin_user):
        """Test filtering transactions by supplier."""
        # Create another supplier with transactions
        other_supplier = SupplierFactory(organization=organization)
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user
        )
        TransactionFactory(
            organization=organization,
            supplier=other_supplier,
            category=category,
            uploaded_by=admin_user
        )

        url = reverse('transaction-list')
        response = authenticated_client.get(url, {'supplier': supplier.id})
        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        for tx in results:
            assert tx['supplier'] == supplier.id


@pytest.mark.django_db
class TestCSVUpload:
    """Tests for CSV upload functionality."""

    def test_upload_csv_success(self, manager_client, organization, manager_user):
        """Test successful CSV upload."""
        csv_content = """supplier,category,amount,date,description
Test Supplier,Test Category,1000.00,2024-01-15,Test transaction 1
Test Supplier,Test Category,2000.00,2024-01-16,Test transaction 2"""

        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = 'test.csv'

        url = reverse('transaction-upload-csv')
        response = manager_client.post(url, {'file': csv_file}, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] in ['completed', 'partial']
        assert response.data['successful_rows'] >= 1

    def test_upload_csv_viewer_forbidden(self, authenticated_client):
        """Test that viewers cannot upload CSV files."""
        csv_content = """supplier,category,amount,date
Test,Test,100.00,2024-01-01"""
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = 'test.csv'

        url = reverse('transaction-upload-csv')
        response = authenticated_client.post(url, {'file': csv_file}, format='multipart')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_upload_csv_invalid_file_type(self, manager_client):
        """Test that non-CSV files are rejected."""
        # Create a file with PDF-like content
        pdf_content = b'%PDF-1.4 fake pdf content'
        pdf_file = io.BytesIO(pdf_content)
        pdf_file.name = 'test.pdf'

        url = reverse('transaction-upload-csv')
        response = manager_client.post(url, {'file': pdf_file}, format='multipart')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_csv_creates_audit_log(self, manager_client, manager_user):
        """Test that CSV upload creates an audit log."""
        csv_content = """supplier,category,amount,date
Test Supplier,Test Category,500.00,2024-03-01"""
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = 'audit_test.csv'

        url = reverse('transaction-upload-csv')
        response = manager_client.post(url, {'file': csv_file}, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED

        log = AuditLog.objects.filter(
            user=manager_user,
            action='upload',
            resource='transactions'
        ).first()
        assert log is not None
        assert 'successful' in log.details


@pytest.mark.django_db
class TestBulkDelete:
    """Tests for bulk delete functionality."""

    def test_bulk_delete_success(self, admin_client, organization, supplier, category, admin_user):
        """Test successful bulk delete."""
        tx1 = TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            invoice_number='BULK-001'
        )
        tx2 = TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            invoice_number='BULK-002'
        )

        url = reverse('transaction-bulk-delete')
        response = admin_client.post(url, {'ids': [tx1.id, tx2.id]}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2
        assert not Transaction.objects.filter(id__in=[tx1.id, tx2.id]).exists()

    def test_bulk_delete_manager_forbidden(self, manager_client, transaction):
        """Test that managers cannot bulk delete."""
        url = reverse('transaction-bulk-delete')
        response = manager_client.post(url, {'ids': [transaction.id]}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_bulk_delete_viewer_forbidden(self, authenticated_client, transaction):
        """Test that viewers cannot bulk delete."""
        url = reverse('transaction-bulk-delete')
        response = authenticated_client.post(url, {'ids': [transaction.id]}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_bulk_delete_empty_ids_rejected(self, admin_client):
        """Test that empty ID list is rejected."""
        url = reverse('transaction-bulk-delete')
        response = admin_client.post(url, {'ids': []}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_delete_creates_audit_log(self, admin_client, admin_user, organization, supplier, category):
        """Test that bulk delete creates an audit log."""
        tx = TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            invoice_number='AUDIT-BULK'
        )

        url = reverse('transaction-bulk-delete')
        admin_client.post(url, {'ids': [tx.id]}, format='json')

        log = AuditLog.objects.filter(
            user=admin_user,
            action='delete',
            resource='transactions'
        ).first()
        assert log is not None
        assert log.details['count'] == 1


@pytest.mark.django_db
class TestExport:
    """Tests for transaction export functionality."""

    def test_export_csv(self, authenticated_client, transaction):
        """Test exporting transactions to CSV."""
        url = reverse('transaction-export')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'text/csv'
        assert 'attachment' in response['Content-Disposition']

    def test_export_with_date_filters(self, authenticated_client, organization, supplier, category, admin_user):
        """Test exporting with date filters."""
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            date=date(2024, 1, 15),
            invoice_number='DATE-001'
        )
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            date=date(2024, 6, 15),
            invoice_number='DATE-002'
        )

        url = reverse('transaction-export')
        response = authenticated_client.get(url, {
            'start_date': '2024-01-01',
            'end_date': '2024-03-31'
        })
        assert response.status_code == status.HTTP_200_OK

    def test_export_creates_audit_log(self, authenticated_client, user, transaction):
        """Test that export creates an audit log."""
        url = reverse('transaction-export')
        authenticated_client.get(url)

        log = AuditLog.objects.filter(
            user=user,
            action='export',
            resource='transactions'
        ).first()
        assert log is not None


@pytest.mark.django_db
class TestDataUploadViewSet:
    """Tests for DataUpload viewing."""

    def test_list_uploads(self, authenticated_client, organization, admin_user):
        """Test listing upload history."""
        DataUploadFactory(organization=organization, uploaded_by=admin_user)

        url = reverse('upload-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) >= 1

    def test_uploads_organization_scoped(self, authenticated_client, other_organization, other_org_user):
        """Test that uploads from other orgs are not visible."""
        other_upload = DataUploadFactory(
            organization=other_organization,
            uploaded_by=other_org_user
        )

        url = reverse('upload-list')
        response = authenticated_client.get(url)
        results = get_results(response.data)
        upload_ids = [u['id'] for u in results]
        assert other_upload.id not in upload_ids

    def test_uploads_readonly(self, admin_client, organization, admin_user):
        """Test that uploads cannot be created via API."""
        url = reverse('upload-list')
        data = {
            'file_name': 'test.csv',
            'file_size': 1024,
            'batch_id': 'test-batch'
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestOrganizationIsolation:
    """Tests for multi-tenant organization isolation."""

    def test_cannot_update_other_org_supplier(self, admin_client, other_organization):
        """Test that users cannot update suppliers from other orgs."""
        other_supplier = SupplierFactory(organization=other_organization)
        url = reverse('supplier-detail', args=[other_supplier.id])
        response = admin_client.patch(url, {'name': 'Hacked Name'})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_delete_other_org_transaction(self, admin_client, other_organization, other_org_user):
        """Test that users cannot delete transactions from other orgs."""
        other_supplier = SupplierFactory(organization=other_organization)
        other_category = CategoryFactory(organization=other_organization)
        other_tx = TransactionFactory(
            organization=other_organization,
            supplier=other_supplier,
            category=other_category,
            uploaded_by=other_org_user
        )
        url = reverse('transaction-detail', args=[other_tx.id])
        response = admin_client.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Transaction.objects.filter(id=other_tx.id).exists()

    def test_bulk_delete_ignores_other_org_transactions(self, admin_client, organization, other_organization, supplier, category, admin_user, other_org_user):
        """Test that bulk delete only affects user's org transactions."""
        # Create transaction in user's org
        own_tx = TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            invoice_number='OWN-001'
        )
        # Create transaction in other org
        other_supplier = SupplierFactory(organization=other_organization)
        other_category = CategoryFactory(organization=other_organization)
        other_tx = TransactionFactory(
            organization=other_organization,
            supplier=other_supplier,
            category=other_category,
            uploaded_by=other_org_user
        )

        url = reverse('transaction-bulk-delete')
        response = admin_client.post(
            url,
            {'ids': [own_tx.id, other_tx.id]},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        # Only own transaction should be deleted
        assert response.data['count'] == 1
        assert not Transaction.objects.filter(id=own_tx.id).exists()
        assert Transaction.objects.filter(id=other_tx.id).exists()
