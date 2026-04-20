"""
Serializers for procurement data
"""
import logging
from rest_framework import serializers
from .models import (
    Supplier, Category, Transaction, DataUpload,
    PurchaseRequisition, PurchaseOrder, GoodsReceipt, Invoice
)

# Try to import python-magic for robust file type validation
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    logging.warning("python-magic not installed. File type validation will use fallback method.")

logger = logging.getLogger(__name__)


class SupplierSerializer(serializers.ModelSerializer):
    """Serializer for Supplier model"""
    transaction_count = serializers.IntegerField(read_only=True)
    total_spend = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'code', 'contact_email', 'contact_phone',
            'address', 'is_active', 'created_at', 'updated_at',
            'transaction_count', 'total_spend'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model"""
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    transaction_count = serializers.IntegerField(read_only=True)
    total_spend = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'parent', 'parent_name', 'description',
            'is_active', 'created_at', 'updated_at',
            'transaction_count', 'total_spend'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model"""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'supplier', 'supplier_name', 'category', 'category_name',
            'amount', 'date', 'description', 'subcategory', 'location',
            'fiscal_year', 'spend_band', 'payment_method', 'invoice_number',
            'upload_batch', 'uploaded_by', 'uploaded_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at', 'updated_at']


class TransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating transactions"""
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all(), required=False, allow_null=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False, allow_null=True)
    supplier_name = serializers.CharField(write_only=True, required=False)
    category_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Transaction
        fields = [
            'supplier', 'supplier_name', 'category', 'category_name',
            'amount', 'date', 'description', 'subcategory', 'location',
            'fiscal_year', 'spend_band', 'payment_method', 'invoice_number'
        ]

    def validate(self, attrs):
        """Ensure either supplier/category ID or name is provided."""
        if not attrs.get('supplier') and not attrs.get('supplier_name'):
            raise serializers.ValidationError({'supplier': 'Either supplier ID or supplier_name is required.'})
        if not attrs.get('category') and not attrs.get('category_name'):
            raise serializers.ValidationError({'category': 'Either category ID or category_name is required.'})
        return attrs

    def validate_supplier(self, value):
        """Ensure supplier belongs to user's organization"""
        if value is None:
            return value
        user_org = self.context['request'].user.profile.organization
        if value.organization_id != user_org.id:
            raise serializers.ValidationError(
                "Supplier does not belong to your organization"
            )
        return value

    def validate_category(self, value):
        """Ensure category belongs to user's organization"""
        if value is None:
            return value
        user_org = self.context['request'].user.profile.organization
        if value.organization_id != user_org.id:
            raise serializers.ValidationError(
                "Category does not belong to your organization"
            )
        return value

    def create(self, validated_data):
        # Get organization from context
        organization = self.context['request'].user.profile.organization
        
        # Handle supplier creation if name provided
        supplier_name = validated_data.pop('supplier_name', None)
        if supplier_name and 'supplier' not in validated_data:
            supplier, _ = Supplier.objects.get_or_create(
                organization=organization,
                name=supplier_name
            )
            validated_data['supplier'] = supplier
        
        # Handle category creation if name provided
        category_name = validated_data.pop('category_name', None)
        if category_name and 'category' not in validated_data:
            category, _ = Category.objects.get_or_create(
                organization=organization,
                name=category_name
            )
            validated_data['category'] = category
        
        # Set organization and user
        validated_data['organization'] = organization
        validated_data['uploaded_by'] = self.context['request'].user
        
        return super().create(validated_data)


class TransactionBulkDeleteSerializer(serializers.Serializer):
    """Serializer for bulk delete operations"""
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )


class DataUploadSerializer(serializers.ModelSerializer):
    """Serializer for DataUpload model"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    
    class Meta:
        model = DataUpload
        fields = [
            'id', 'file_name', 'file_size', 'batch_id',
            'total_rows', 'successful_rows', 'failed_rows', 'duplicate_rows',
            'status', 'error_log', 'uploaded_by', 'uploaded_by_name',
            'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at', 'completed_at']


class CSVUploadSerializer(serializers.Serializer):
    """
    Serializer for CSV file upload with security validations.

    Security features:
    - File extension validation
    - File size limit (50MB)
    - Content-type validation
    - Magic byte validation for CSV files
    """
    file = serializers.FileField()
    skip_duplicates = serializers.BooleanField(default=True)

    # CSV magic bytes patterns (common file signatures)
    # CSV doesn't have a strict magic number, but we check for text content
    ALLOWED_CONTENT_TYPES = [
        'text/csv',
        'text/plain',
        'application/csv',
        'application/vnd.ms-excel',  # Sometimes Excel sends CSV as this
    ]

    # Characters that indicate binary (non-text) content
    BINARY_INDICATORS = set(bytes(range(0, 9)) + bytes(range(14, 32)))

    def validate_file(self, value):
        # 1. Check file extension
        if not value.name.lower().endswith('.csv'):
            raise serializers.ValidationError("Only CSV files are allowed")

        # 2. Check file size (max 50MB)
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError("File size must be less than 50MB")

        # 3. Check content type from browser
        content_type = getattr(value, 'content_type', 'application/octet-stream')
        if content_type not in self.ALLOWED_CONTENT_TYPES:
            # Some browsers don't set proper content type, continue to magic validation
            logger.debug(f"Unexpected content type '{content_type}', verifying with magic")

        # 4. Magic number validation (if python-magic is available)
        try:
            value.seek(0)
            sample = value.read(8192)
            value.seek(0)  # Reset file pointer

            if HAS_MAGIC:
                # Use python-magic for robust MIME type detection
                detected_mime = magic.from_buffer(sample, mime=True)
                if detected_mime not in self.ALLOWED_CONTENT_TYPES:
                    logger.warning(f"File magic type mismatch: {detected_mime}")
                    raise serializers.ValidationError(
                        f"File content type '{detected_mime}' does not match CSV format. "
                        "Please upload a valid CSV file."
                    )

            # 5. Validate content is text (not binary) - fallback validation
            if isinstance(sample, bytes):
                # Check for null bytes or other binary indicators
                binary_chars = set(sample) & self.BINARY_INDICATORS
                if binary_chars:
                    raise serializers.ValidationError(
                        "File appears to contain binary data. Only text CSV files are allowed."
                    )

                # Try to decode as UTF-8 (or common encodings)
                try:
                    sample.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        sample.decode('latin-1')
                    except UnicodeDecodeError:
                        raise serializers.ValidationError(
                            "File encoding not recognized. Please use UTF-8 encoded CSV files."
                        )

            # 6. Basic CSV structure validation
            # Check if first line looks like a header (contains comma-separated values)
            if isinstance(sample, bytes):
                sample = sample.decode('utf-8', errors='ignore')

            first_line = sample.split('\n')[0] if sample else ''
            if ',' not in first_line and '\t' not in first_line and ';' not in first_line:
                raise serializers.ValidationError(
                    "File does not appear to be a valid CSV file (no delimiter found in header)."
                )

        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.exception("Error validating file content")
            raise serializers.ValidationError("Error validating file content: Unable to read file")

        return value


# =============================================================================
# P2P (Procure-to-Pay) Serializers
# =============================================================================

class PurchaseRequisitionSerializer(serializers.ModelSerializer):
    """Serializer for Purchase Requisition model."""
    requested_by_name = serializers.CharField(source='requested_by.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)
    supplier_suggested_name = serializers.CharField(source='supplier_suggested.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    days_to_approval = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = PurchaseRequisition
        fields = [
            'id', 'uuid', 'pr_number', 'organization',
            'requested_by', 'requested_by_name', 'department', 'cost_center',
            'supplier_suggested', 'supplier_suggested_name', 'category', 'category_name',
            'description', 'estimated_amount', 'currency', 'budget_code',
            'status', 'priority',
            'created_date', 'submitted_date', 'approval_date', 'rejection_date',
            'approved_by', 'approved_by_name', 'rejection_reason',
            'days_to_approval', 'is_overdue',
            'upload_batch', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'uuid', 'organization', 'created_at', 'updated_at',
            'days_to_approval', 'is_overdue'
        ]

    def validate(self, attrs):
        """Validate PR data."""
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            org = request.user.profile.organization

            # Validate supplier belongs to organization
            supplier = attrs.get('supplier_suggested')
            if supplier and supplier.organization_id != org.id:
                raise serializers.ValidationError({
                    'supplier_suggested': 'Supplier does not belong to your organization.'
                })

            # Validate category belongs to organization
            category = attrs.get('category')
            if category and category.organization_id != org.id:
                raise serializers.ValidationError({
                    'category': 'Category does not belong to your organization.'
                })

        return attrs


class PurchaseRequisitionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for PR list views."""
    requested_by_name = serializers.CharField(source='requested_by.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = PurchaseRequisition
        fields = [
            'id', 'uuid', 'pr_number', 'status', 'priority',
            'estimated_amount', 'department', 'category_name',
            'requested_by_name', 'created_date', 'approval_date'
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    """Serializer for Purchase Order model."""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    contract_number = serializers.CharField(source='contract.contract_number', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)
    requisition_number = serializers.CharField(source='requisition.pr_number', read_only=True)
    is_maverick = serializers.BooleanField(read_only=True)
    amount_variance = serializers.FloatField(read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'uuid', 'po_number', 'organization',
            'supplier', 'supplier_name', 'category', 'category_name',
            'total_amount', 'currency', 'tax_amount', 'freight_amount',
            'contract', 'contract_number', 'is_contract_backed',
            'status',
            'created_date', 'approval_date', 'sent_date', 'required_date', 'promised_date',
            'created_by', 'created_by_name', 'approved_by', 'approved_by_name',
            'original_amount', 'amendment_count',
            'requisition', 'requisition_number',
            'is_maverick', 'amount_variance',
            'upload_batch', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'uuid', 'organization', 'created_at', 'updated_at',
            'is_maverick', 'amount_variance'
        ]

    def validate(self, attrs):
        """Validate PO data."""
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            org = request.user.profile.organization

            # Validate supplier belongs to organization
            supplier = attrs.get('supplier')
            if supplier and supplier.organization_id != org.id:
                raise serializers.ValidationError({
                    'supplier': 'Supplier does not belong to your organization.'
                })

            # Validate category belongs to organization
            category = attrs.get('category')
            if category and category.organization_id != org.id:
                raise serializers.ValidationError({
                    'category': 'Category does not belong to your organization.'
                })

            # Validate contract belongs to organization
            contract = attrs.get('contract')
            if contract and contract.organization_id != org.id:
                raise serializers.ValidationError({
                    'contract': 'Contract does not belong to your organization.'
                })

        return attrs


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for PO list views."""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'uuid', 'po_number', 'status', 'supplier_name',
            'total_amount', 'is_contract_backed', 'created_date'
        ]


class GoodsReceiptSerializer(serializers.ModelSerializer):
    """Serializer for Goods Receipt model."""
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    supplier_name = serializers.CharField(source='purchase_order.supplier.name', read_only=True)
    received_by_name = serializers.CharField(source='received_by.username', read_only=True)
    quantity_variance = serializers.FloatField(read_only=True)
    has_variance = serializers.BooleanField(read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = [
            'id', 'uuid', 'gr_number', 'organization',
            'purchase_order', 'po_number', 'supplier_name',
            'received_date', 'received_by', 'received_by_name',
            'quantity_ordered', 'quantity_received', 'quantity_accepted',
            'amount_received', 'status', 'inspection_notes',
            'quantity_variance', 'has_variance',
            'upload_batch', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'uuid', 'organization', 'created_at', 'updated_at',
            'quantity_variance', 'has_variance'
        ]

    def validate_purchase_order(self, value):
        """Validate PO belongs to user's organization."""
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            org = request.user.profile.organization
            if value.organization_id != org.id:
                raise serializers.ValidationError(
                    'Purchase Order does not belong to your organization.'
                )
        return value


class GoodsReceiptListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for GR list views."""
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = [
            'id', 'uuid', 'gr_number', 'status', 'po_number',
            'quantity_received', 'received_date'
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice model."""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    gr_number = serializers.CharField(source='goods_receipt.gr_number', read_only=True)
    exception_resolved_by_name = serializers.CharField(
        source='exception_resolved_by.username', read_only=True
    )
    days_outstanding = serializers.IntegerField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    aging_bucket = serializers.CharField(read_only=True)
    discount_available = serializers.BooleanField(read_only=True)
    price_variance = serializers.FloatField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'uuid', 'invoice_number', 'organization',
            'supplier', 'supplier_name',
            'purchase_order', 'po_number', 'goods_receipt', 'gr_number',
            'invoice_amount', 'tax_amount', 'net_amount', 'currency',
            'payment_terms', 'payment_terms_days', 'discount_percent', 'discount_days',
            'invoice_date', 'received_date', 'due_date', 'approved_date', 'paid_date',
            'status', 'match_status',
            'has_exception', 'exception_type', 'exception_amount',
            'exception_notes', 'exception_resolved',
            'exception_resolved_by', 'exception_resolved_by_name', 'exception_resolved_at',
            'hold_reason',
            'days_outstanding', 'days_overdue', 'is_overdue', 'aging_bucket',
            'discount_available', 'price_variance',
            'upload_batch', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'uuid', 'organization', 'created_at', 'updated_at',
            'days_outstanding', 'days_overdue', 'is_overdue', 'aging_bucket',
            'discount_available', 'price_variance'
        ]

    def validate(self, attrs):
        """Validate Invoice data."""
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            org = request.user.profile.organization

            # Validate supplier belongs to organization
            supplier = attrs.get('supplier')
            if supplier and supplier.organization_id != org.id:
                raise serializers.ValidationError({
                    'supplier': 'Supplier does not belong to your organization.'
                })

            # Validate PO belongs to organization
            po = attrs.get('purchase_order')
            if po and po.organization_id != org.id:
                raise serializers.ValidationError({
                    'purchase_order': 'Purchase Order does not belong to your organization.'
                })

            # Validate GR belongs to organization
            gr = attrs.get('goods_receipt')
            if gr and gr.organization_id != org.id:
                raise serializers.ValidationError({
                    'goods_receipt': 'Goods Receipt does not belong to your organization.'
                })

        return attrs


class InvoiceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Invoice list views."""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    aging_bucket = serializers.CharField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'uuid', 'invoice_number', 'status', 'match_status',
            'supplier_name', 'invoice_amount', 'due_date',
            'has_exception', 'exception_type', 'aging_bucket'
        ]


class InvoiceExceptionResolveSerializer(serializers.Serializer):
    """Serializer for resolving invoice exceptions."""
    resolution_notes = serializers.CharField(required=True, max_length=2000)

    def validate_resolution_notes(self, value):
        """Ensure resolution notes are meaningful."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                'Resolution notes must be at least 10 characters.'
            )
        return value.strip()


class InvoiceBulkExceptionResolveSerializer(serializers.Serializer):
    """Serializer for bulk resolving invoice exceptions."""
    invoice_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        max_length=100
    )
    resolution_notes = serializers.CharField(required=True, max_length=2000)

    def validate_resolution_notes(self, value):
        """Ensure resolution notes are meaningful."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                'Resolution notes must be at least 10 characters.'
            )
        return value.strip()
