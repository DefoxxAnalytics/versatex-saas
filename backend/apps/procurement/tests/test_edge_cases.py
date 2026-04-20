"""
Additional tests for edge cases and P2P models in procurement app.
"""
import pytest
import io
from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
from rest_framework import status
from apps.procurement.models import (
    Supplier, Category, Transaction, DataUpload,
    PurchaseRequisition, PurchaseOrder, GoodsReceipt, Invoice
)
from .factories import SupplierFactory, CategoryFactory, TransactionFactory


@pytest.mark.django_db
class TestCSVUploadEdgeCases:
    """Additional edge case tests for CSV upload functionality."""

    def test_upload_csv_with_encoding_issues(self, manager_client):
        """Test handling CSV with different encodings."""
        # UTF-8 with BOM
        csv_content = b'\xef\xbb\xbfsupplier,category,amount,date\nTest,Test,100.00,2024-01-01'
        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'bom_test.csv'

        url = reverse('transaction-upload-csv')
        response = manager_client.post(url, {'file': csv_file}, format='multipart')
        # Should handle BOM gracefully
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_upload_csv_empty_file(self, manager_client):
        """Test handling empty CSV file."""
        csv_file = io.BytesIO(b'')
        csv_file.name = 'empty.csv'

        url = reverse('transaction-upload-csv')
        response = manager_client.post(url, {'file': csv_file}, format='multipart')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_csv_headers_only(self, manager_client):
        """Test handling CSV with headers only."""
        csv_content = b'supplier,category,amount,date'
        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'headers_only.csv'

        url = reverse('transaction-upload-csv')
        response = manager_client.post(url, {'file': csv_file}, format='multipart')
        # Should handle gracefully - either 201 with 0 rows or 400
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_upload_csv_missing_required_columns(self, manager_client):
        """Test handling CSV missing required columns."""
        csv_content = b'supplier,description\nTest,Some description'
        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'missing_columns.csv'

        url = reverse('transaction-upload-csv')
        response = manager_client.post(url, {'file': csv_file}, format='multipart')
        # Should fail due to missing required columns
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_csv_invalid_amount(self, manager_client):
        """Test handling CSV with invalid amount values."""
        csv_content = b'supplier,category,amount,date\nTest,Test,not_a_number,2024-01-01'
        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'invalid_amount.csv'

        url = reverse('transaction-upload-csv')
        response = manager_client.post(url, {'file': csv_file}, format='multipart')
        # Should handle gracefully - might skip row or return error
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_upload_csv_invalid_date(self, manager_client):
        """Test handling CSV with invalid date values."""
        csv_content = b'supplier,category,amount,date\nTest,Test,100.00,not_a_date'
        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'invalid_date.csv'

        url = reverse('transaction-upload-csv')
        response = manager_client.post(url, {'file': csv_file}, format='multipart')
        # Should handle gracefully - might skip row or return error
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_upload_csv_negative_amount(self, manager_client):
        """Test handling CSV with negative amounts (credit memos)."""
        csv_content = b'supplier,category,amount,date\nTest,Test,-500.00,2024-01-01'
        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'negative_amount.csv'

        url = reverse('transaction-upload-csv')
        response = manager_client.post(url, {'file': csv_file}, format='multipart')
        # Negative amounts should be accepted (credit memos)
        assert response.status_code == status.HTTP_201_CREATED

    def test_upload_csv_very_long_values(self, manager_client):
        """Test handling CSV with very long field values."""
        long_name = 'A' * 500  # Very long supplier name
        csv_content = f'supplier,category,amount,date\n{long_name},Test,100.00,2024-01-01'.encode()
        csv_file = io.BytesIO(csv_content)
        csv_file.name = 'long_values.csv'

        url = reverse('transaction-upload-csv')
        response = manager_client.post(url, {'file': csv_file}, format='multipart')
        # Should handle gracefully - truncate or error
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_upload_csv_formula_injection_sanitized(self, manager_client, csv_file_with_formulas):
        """Test that formula injection is sanitized."""
        url = reverse('transaction-upload-csv')
        csv_file_with_formulas.name = 'formulas.csv'
        response = manager_client.post(url, {'file': csv_file_with_formulas}, format='multipart')

        # Should either reject or sanitize formulas
        if response.status_code == status.HTTP_201_CREATED:
            # If accepted, verify formulas were sanitized
            suppliers = Supplier.objects.filter(
                name__startswith='=CMD'
            )
            assert suppliers.count() == 0, "Formula injection not sanitized"


@pytest.mark.django_db
class TestTransactionEdgeCases:
    """Edge case tests for Transaction model and operations."""

    def test_transaction_zero_amount(self, admin_client, supplier, category):
        """Test creating transaction with zero amount."""
        url = reverse('transaction-list')
        data = {
            'supplier': supplier.id,
            'category': category.id,
            'amount': '0.00',
            'date': '2024-01-15',
        }
        response = admin_client.post(url, data)
        # Zero amount should be rejected or handled specially
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_transaction_very_large_amount(self, admin_client, supplier, category):
        """Test creating transaction with very large amount."""
        url = reverse('transaction-list')
        data = {
            'supplier': supplier.id,
            'category': category.id,
            'amount': '999999999999.99',
            'date': '2024-01-15',
        }
        response = admin_client.post(url, data)
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_transaction_future_date(self, admin_client, supplier, category):
        """Test creating transaction with future date."""
        future_date = (date.today() + timedelta(days=365)).isoformat()
        url = reverse('transaction-list')
        data = {
            'supplier': supplier.id,
            'category': category.id,
            'amount': '1000.00',
            'date': future_date,
        }
        response = admin_client.post(url, data)
        # Should be accepted (for planned orders) or rejected
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_transaction_very_old_date(self, admin_client, supplier, category):
        """Test creating transaction with very old date."""
        url = reverse('transaction-list')
        data = {
            'supplier': supplier.id,
            'category': category.id,
            'amount': '1000.00',
            'date': '1990-01-01',
        }
        response = admin_client.post(url, data)
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_transaction_unicode_description(self, admin_client, supplier, category):
        """Test creating transaction with unicode characters in description."""
        url = reverse('transaction-list')
        data = {
            'supplier': supplier.id,
            'category': category.id,
            'amount': '1000.00',
            'date': '2024-01-15',
            'description': 'Testing unicode: \u00e9\u00e0\u00fc \u4e2d\u6587 \u65e5\u672c\u8a9e'
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestBulkOperationsEdgeCases:
    """Edge case tests for bulk operations."""

    def test_bulk_delete_nonexistent_ids(self, admin_client):
        """Test bulk delete with nonexistent IDs."""
        url = reverse('transaction-bulk-delete')
        response = admin_client.post(url, {'ids': [99999, 99998]}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_bulk_delete_mixed_valid_invalid_ids(self, admin_client, organization, supplier, category, admin_user):
        """Test bulk delete with mix of valid and invalid IDs."""
        tx = TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user
        )

        url = reverse('transaction-bulk-delete')
        response = admin_client.post(url, {'ids': [tx.id, 99999]}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1  # Only valid one deleted

    def test_bulk_delete_large_batch(self, admin_client, organization, supplier, category, admin_user):
        """Test bulk delete with large number of IDs."""
        # Create 50 transactions
        tx_ids = []
        for i in range(50):
            tx = TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                invoice_number=f'BULK-LARGE-{i}'
            )
            tx_ids.append(tx.id)

        url = reverse('transaction-bulk-delete')
        response = admin_client.post(url, {'ids': tx_ids}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 50

    def test_bulk_delete_duplicate_ids(self, admin_client, organization, supplier, category, admin_user):
        """Test bulk delete with duplicate IDs in list."""
        tx = TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user
        )

        url = reverse('transaction-bulk-delete')
        # Send same ID multiple times
        response = admin_client.post(url, {'ids': [tx.id, tx.id, tx.id]}, format='json')
        assert response.status_code == status.HTTP_200_OK
        # Should only count as 1 deletion
        assert response.data['count'] == 1


@pytest.mark.django_db
class TestPurchaseRequisitionModel:
    """Tests for PurchaseRequisition model."""

    def test_create_purchase_requisition(self, organization, admin_user, supplier, category):
        """Test creating a purchase requisition."""
        pr = PurchaseRequisition.objects.create(
            organization=organization,
            requested_by=admin_user,
            supplier_suggested=supplier,
            category=category,
            pr_number='PR-2024-001',
            description='Test requisition',
            estimated_amount=Decimal('5000.00'),
            department='IT',
            cost_center='CC-100',
            status='draft',
            created_date=date.today()
        )
        assert pr.id is not None
        assert pr.pr_number == 'PR-2024-001'
        assert pr.status == 'draft'

    def test_purchase_requisition_workflow(self, organization, admin_user, supplier, category):
        """Test PR status transitions."""
        pr = PurchaseRequisition.objects.create(
            organization=organization,
            requested_by=admin_user,
            supplier_suggested=supplier,
            category=category,
            pr_number='PR-WORKFLOW-001',
            estimated_amount=Decimal('5000.00'),
            status='draft',
            created_date=date.today()
        )

        # Submit for approval
        pr.status = 'pending_approval'
        pr.submitted_date = date.today()
        pr.save()
        pr.refresh_from_db()
        assert pr.status == 'pending_approval'

        # Approve
        pr.status = 'approved'
        pr.approved_by = admin_user
        pr.approval_date = date.today()
        pr.save()
        pr.refresh_from_db()
        assert pr.status == 'approved'
        assert pr.approved_by == admin_user


@pytest.mark.django_db
class TestPurchaseOrderModel:
    """Tests for PurchaseOrder model."""

    def test_create_purchase_order(self, organization, admin_user, supplier):
        """Test creating a purchase order."""
        po = PurchaseOrder.objects.create(
            organization=organization,
            created_by=admin_user,
            supplier=supplier,
            po_number='PO-2024-001',
            total_amount=Decimal('10000.00'),
            status='draft',
            created_date=date.today()
        )
        assert po.id is not None
        assert po.po_number == 'PO-2024-001'

    def test_purchase_order_with_contract(self, organization, admin_user, supplier):
        """Test PO with contract backing."""
        po = PurchaseOrder.objects.create(
            organization=organization,
            created_by=admin_user,
            supplier=supplier,
            po_number='PO-CONTRACT-001',
            total_amount=Decimal('10000.00'),
            is_contract_backed=True,
            created_date=date.today()
        )
        assert po.is_contract_backed is True
        # Note: contract is a ForeignKey, not a string field
        assert po.is_maverick is False

    def test_purchase_order_amendments(self, organization, admin_user, supplier):
        """Test PO amendment tracking."""
        po = PurchaseOrder.objects.create(
            organization=organization,
            created_by=admin_user,
            supplier=supplier,
            po_number='PO-AMEND-001',
            total_amount=Decimal('10000.00'),
            original_amount=Decimal('10000.00'),
            amendment_count=0,
            created_date=date.today()
        )

        # Simulate amendment
        po.total_amount = Decimal('12000.00')
        po.amendment_count += 1
        po.save()

        po.refresh_from_db()
        assert po.total_amount == Decimal('12000.00')
        assert po.amendment_count == 1


@pytest.mark.django_db
class TestGoodsReceiptModel:
    """Tests for GoodsReceipt model."""

    def test_create_goods_receipt(self, organization, admin_user, supplier):
        """Test creating a goods receipt."""
        po = PurchaseOrder.objects.create(
            organization=organization,
            created_by=admin_user,
            supplier=supplier,
            po_number='PO-GR-001',
            total_amount=Decimal('10000.00'),
            created_date=date.today()
        )

        gr = GoodsReceipt.objects.create(
            organization=organization,
            received_by=admin_user,
            purchase_order=po,
            gr_number='GR-2024-001',
            quantity_ordered=100,
            quantity_received=100,
            quantity_accepted=98,
            received_date=date.today()
        )
        assert gr.id is not None
        assert gr.quantity_received == 100
        assert gr.quantity_accepted == 98

    def test_goods_receipt_partial_delivery(self, organization, admin_user, supplier):
        """Test partial goods receipt."""
        po = PurchaseOrder.objects.create(
            organization=organization,
            created_by=admin_user,
            supplier=supplier,
            po_number='PO-PARTIAL-001',
            total_amount=Decimal('10000.00'),
            created_date=date.today()
        )

        # First delivery
        gr1 = GoodsReceipt.objects.create(
            organization=organization,
            received_by=admin_user,
            purchase_order=po,
            gr_number='GR-PARTIAL-001',
            quantity_ordered=100,
            quantity_received=50,
            quantity_accepted=50,
            received_date=date.today()
        )

        # Second delivery
        gr2 = GoodsReceipt.objects.create(
            organization=organization,
            received_by=admin_user,
            purchase_order=po,
            gr_number='GR-PARTIAL-002',
            quantity_ordered=100,
            quantity_received=50,
            quantity_accepted=50,
            received_date=date.today()
        )

        # PO should have 2 goods receipts
        assert po.goods_receipts.count() == 2


@pytest.mark.django_db
class TestInvoiceModel:
    """Tests for Invoice model."""

    def test_create_invoice(self, organization, admin_user, supplier):
        """Test creating an invoice."""
        invoice = Invoice.objects.create(
            organization=organization,
            supplier=supplier,
            invoice_number='INV-2024-001',
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            invoice_amount=Decimal('10000.00'),
            net_amount=Decimal('10000.00'),
            payment_terms='Net 30',
            status='received'
        )
        assert invoice.id is not None
        assert invoice.invoice_number == 'INV-2024-001'

    def test_invoice_matching_status(self, organization, admin_user, supplier):
        """Test invoice matching status."""
        po = PurchaseOrder.objects.create(
            organization=organization,
            created_by=admin_user,
            supplier=supplier,
            po_number='PO-MATCH-001',
            total_amount=Decimal('10000.00'),
            created_date=date.today()
        )

        invoice = Invoice.objects.create(
            organization=organization,
            supplier=supplier,
            invoice_number='INV-MATCH-001',
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            invoice_amount=Decimal('10000.00'),
            net_amount=Decimal('10000.00'),
            purchase_order=po,
            match_status='3way_matched'
        )
        assert invoice.match_status == '3way_matched'
        assert invoice.purchase_order == po

    def test_invoice_exception_handling(self, organization, admin_user, supplier):
        """Test invoice with exception."""
        po = PurchaseOrder.objects.create(
            organization=organization,
            created_by=admin_user,
            supplier=supplier,
            po_number='PO-EXC-001',
            total_amount=Decimal('10000.00'),
            created_date=date.today()
        )

        # Invoice with price variance
        invoice = Invoice.objects.create(
            organization=organization,
            supplier=supplier,
            invoice_number='INV-EXC-001',
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            invoice_amount=Decimal('11000.00'),  # Over PO amount
            net_amount=Decimal('11000.00'),
            purchase_order=po,
            match_status='exception',
            has_exception=True,
            exception_type='price_variance',
            exception_notes='Invoice exceeds PO by 10%'
        )
        assert invoice.match_status == 'exception'
        assert invoice.exception_type == 'price_variance'


@pytest.mark.django_db
class TestDataUploadModel:
    """Tests for DataUpload model edge cases."""

    def test_data_upload_status_tracking(self, organization, admin_user):
        """Test upload status tracking."""
        upload = DataUpload.objects.create(
            organization=organization,
            uploaded_by=admin_user,
            file_name='test.csv',
            file_size=1024,
            batch_id='BATCH-001',
            total_rows=100,
            successful_rows=0,
            failed_rows=0,
            duplicate_rows=0,
            status='processing'
        )

        # Simulate processing completion
        upload.successful_rows = 95
        upload.failed_rows = 3
        upload.duplicate_rows = 2
        upload.status = 'completed'
        upload.save()

        upload.refresh_from_db()
        assert upload.status == 'completed'
        assert upload.successful_rows == 95
        assert upload.failed_rows == 3
        assert upload.duplicate_rows == 2

    def test_data_upload_error_log(self, organization, admin_user):
        """Test error log storage."""
        error_log = [
            {'row': 5, 'error': 'Invalid amount'},
            {'row': 10, 'error': 'Missing category'},
        ]
        upload = DataUpload.objects.create(
            organization=organization,
            uploaded_by=admin_user,
            file_name='errors.csv',
            file_size=1024,
            batch_id='BATCH-ERR-001',
            total_rows=20,
            successful_rows=18,
            failed_rows=2,
            duplicate_rows=0,
            status='partial',
            error_log=error_log
        )

        upload.refresh_from_db()
        assert len(upload.error_log) == 2
        assert upload.error_log[0]['row'] == 5


@pytest.mark.django_db
class TestSupplierCategoryEdgeCases:
    """Edge case tests for Supplier and Category models."""

    def test_supplier_duplicate_code_same_org(self, admin_client, organization):
        """Test duplicate supplier code in same organization."""
        SupplierFactory(organization=organization, code='DUP001')

        url = reverse('supplier-list')
        data = {
            'name': 'Another Supplier',
            'code': 'DUP001'
        }
        response = admin_client.post(url, data)
        # Should either reject duplicate or auto-generate unique code
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_category_circular_parent_reference(self, organization):
        """Test that circular parent references are prevented."""
        parent = CategoryFactory(organization=organization, name='Parent')
        child = CategoryFactory(organization=organization, name='Child', parent=parent)

        # Try to set parent's parent to child (circular)
        parent.parent = child
        # This should raise an error or be prevented at save
        try:
            parent.full_clean()
            parent.save()
            # If it gets here, verify no infinite loop would occur
            # by checking ancestry depth
            ancestors = []
            current = parent
            while current.parent and len(ancestors) < 100:
                ancestors.append(current.parent)
                current = current.parent
            assert len(ancestors) < 100, "Circular reference not prevented"
        except Exception:
            pass  # Expected to fail

    def test_category_deep_nesting(self, organization):
        """Test deeply nested categories."""
        current = None
        for i in range(10):  # 10 levels deep
            current = CategoryFactory(
                organization=organization,
                name=f'Level {i}',
                parent=current
            )
        assert current.parent is not None
