"""
Celery tasks for procurement data processing.
Handles background CSV upload processing for large files.
"""
import csv
import io
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import DataUpload, Transaction, Supplier, Category


@shared_task(bind=True, soft_time_limit=600, max_retries=3, retry_backoff=True)
def process_csv_upload(self, upload_id, mapping, skip_invalid=True, skip_duplicates=False, strict_duplicates=False):
    """
    Background task for processing large CSV files.

    Args:
        upload_id: ID of the DataUpload record
        mapping: Dict mapping CSV columns to target fields
        skip_invalid: Whether to skip invalid rows or abort
        skip_duplicates: If True, skip all duplicate checking
        strict_duplicates: If True, use all mapped fields for duplicate detection

    Returns:
        Dict with processing results
    """
    try:
        upload = DataUpload.objects.get(id=upload_id)
    except DataUpload.DoesNotExist:
        return {'error': 'Upload not found'}

    try:
        # Update status
        upload.status = 'processing'
        upload.progress_percent = 0
        upload.progress_message = 'Starting processing...'
        upload.save()

        # Read file content
        if not upload.stored_file:
            raise ValueError('No file stored for processing')

        content = upload.stored_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        total_rows = len(rows)

        if total_rows == 0:
            upload.status = 'failed'
            upload.error_log = json.dumps([{'message': 'File contains no data rows'}])
            upload.save()
            return {'error': 'No data rows'}

        upload.total_rows = total_rows
        upload.save()

        # Get column mappings
        supplier_col = next((k for k, v in mapping.items() if v == 'supplier'), None)
        category_col = next((k for k, v in mapping.items() if v == 'category'), None)
        amount_col = next((k for k, v in mapping.items() if v == 'amount'), None)
        date_col = next((k for k, v in mapping.items() if v == 'date'), None)
        description_col = next((k for k, v in mapping.items() if v == 'description'), None)
        invoice_col = next((k for k, v in mapping.items() if v == 'invoice_number'), None)
        fiscal_year_col = next((k for k, v in mapping.items() if v == 'fiscal_year'), None)
        subcategory_col = next((k for k, v in mapping.items() if v == 'subcategory'), None)
        location_col = next((k for k, v in mapping.items() if v == 'location'), None)
        spend_band_col = next((k for k, v in mapping.items() if v == 'spend_band'), None)
        payment_method_col = next((k for k, v in mapping.items() if v == 'payment_method'), None)

        organization = upload.organization
        user = upload.uploaded_by

        successful = 0
        failed = 0
        duplicates = 0
        errors = []

        # Process in batches
        batch_size = 1000
        for batch_start in range(0, total_rows, batch_size):
            batch_end = min(batch_start + batch_size, total_rows)
            batch_rows = rows[batch_start:batch_end]

            # Update progress
            progress = int((batch_start / total_rows) * 100)
            upload.progress_percent = progress
            upload.progress_message = f'Processing rows {batch_start + 1} to {batch_end} of {total_rows}'
            upload.save()

            with transaction.atomic():
                for i, row in enumerate(batch_rows):
                    row_num = batch_start + i + 2  # +2 for 1-indexed and header row

                    try:
                        # Validate row
                        row_errors = _validate_row(row, mapping, row_num)
                        if row_errors:
                            errors.extend(row_errors)
                            if not skip_invalid:
                                raise ValueError(f'Row {row_num} has validation errors')
                            failed += 1
                            continue

                        # Check for duplicates (unless skip_duplicates is enabled)
                        if not skip_duplicates and _is_duplicate_row(row, mapping, organization, strict_mode=strict_duplicates):
                            duplicates += 1
                            continue

                        # Get or create supplier
                        supplier_name = row.get(supplier_col, '').strip()
                        supplier, _ = Supplier.objects.get_or_create(
                            organization=organization,
                            name__iexact=supplier_name,
                            defaults={'name': supplier_name}
                        )

                        # Get or create category
                        category_name = row.get(category_col, '').strip()
                        category, _ = Category.objects.get_or_create(
                            organization=organization,
                            name__iexact=category_name,
                            defaults={'name': category_name}
                        )

                        # Parse amount
                        amount_str = row.get(amount_col, '').strip().replace('$', '').replace(',', '')
                        amount = Decimal(amount_str)

                        # Parse date
                        date_str = row.get(date_col, '').strip()
                        date = _parse_date(date_str)

                        # Create transaction
                        Transaction.objects.create(
                            organization=organization,
                            supplier=supplier,
                            category=category,
                            amount=amount,
                            date=date,
                            description=row.get(description_col, '').strip() if description_col else '',
                            invoice_number=row.get(invoice_col, '').strip() if invoice_col else '',
                            fiscal_year=row.get(fiscal_year_col, '').strip() if fiscal_year_col else str(date.year),
                            subcategory=row.get(subcategory_col, '').strip() if subcategory_col else '',
                            location=row.get(location_col, '').strip() if location_col else '',
                            spend_band=row.get(spend_band_col, '').strip() if spend_band_col else '',
                            payment_method=row.get(payment_method_col, '').strip() if payment_method_col else '',
                            uploaded_by=user,
                            upload_batch=upload.batch_id
                        )
                        successful += 1

                    except Exception as e:
                        failed += 1
                        errors.append({
                            'row': row_num,
                            'field': 'general',
                            'message': str(e),
                            'value': ''
                        })
                        if not skip_invalid:
                            raise

        # Finalize upload record
        upload.successful_rows = successful
        upload.failed_rows = failed
        upload.duplicate_rows = duplicates
        upload.error_log = json.dumps(errors) if errors else ''
        upload.completed_at = timezone.now()
        upload.progress_percent = 100
        upload.progress_message = 'Processing complete'

        if failed == 0 and duplicates == 0:
            upload.status = 'completed'
        elif successful > 0:
            upload.status = 'partial'
        else:
            upload.status = 'failed'

        upload.save()

        # Clean up stored file
        if upload.stored_file:
            upload.stored_file.delete(save=True)

        return {
            'status': upload.status,
            'successful_rows': successful,
            'failed_rows': failed,
            'duplicate_rows': duplicates
        }

    except Exception as e:
        upload.status = 'failed'
        upload.error_log = json.dumps([{'message': str(e)}])
        upload.progress_message = f'Error: {str(e)}'
        upload.completed_at = timezone.now()
        upload.save()

        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {'error': str(e)}


def _validate_row(row, mapping, row_num):
    """Validate a single row and return list of errors."""
    errors = []

    supplier_col = next((k for k, v in mapping.items() if v == 'supplier'), None)
    category_col = next((k for k, v in mapping.items() if v == 'category'), None)
    amount_col = next((k for k, v in mapping.items() if v == 'amount'), None)
    date_col = next((k for k, v in mapping.items() if v == 'date'), None)

    # Validate supplier
    if supplier_col:
        supplier_val = row.get(supplier_col, '').strip()
        if not supplier_val:
            errors.append({
                'row': row_num,
                'field': 'supplier',
                'message': 'Supplier is required',
                'value': ''
            })

    # Validate category
    if category_col:
        category_val = row.get(category_col, '').strip()
        if not category_val:
            errors.append({
                'row': row_num,
                'field': 'category',
                'message': 'Category is required',
                'value': ''
            })

    # Validate amount
    if amount_col:
        amount_val = row.get(amount_col, '').strip()
        if not amount_val:
            errors.append({
                'row': row_num,
                'field': 'amount',
                'message': 'Amount is required',
                'value': ''
            })
        else:
            try:
                clean_amount = amount_val.replace('$', '').replace(',', '').strip()
                Decimal(clean_amount)
            except (InvalidOperation, ValueError):
                errors.append({
                    'row': row_num,
                    'field': 'amount',
                    'message': 'Invalid amount format',
                    'value': amount_val
                })

    # Validate date
    if date_col:
        date_val = row.get(date_col, '').strip()
        if not date_val:
            errors.append({
                'row': row_num,
                'field': 'date',
                'message': 'Date is required',
                'value': ''
            })
        else:
            if not _parse_date(date_val):
                errors.append({
                    'row': row_num,
                    'field': 'date',
                    'message': 'Invalid date format',
                    'value': date_val
                })

    return errors


def _parse_date(date_str):
    """Try to parse a date string in various formats."""
    formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%m-%d-%Y',
        '%d-%m-%Y',
        '%Y/%m/%d',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue

    return None


def _is_duplicate_row(row, mapping, organization, strict_mode=False):
    """Check if a row would create a duplicate transaction.

    Args:
        row: The CSV row data
        mapping: Column to field mapping
        organization: Target organization
        strict_mode: If True, use all mapped fields for duplicate detection.
                    If False (default), use only core fields.
    """
    supplier_col = next((k for k, v in mapping.items() if v == 'supplier'), None)
    category_col = next((k for k, v in mapping.items() if v == 'category'), None)
    amount_col = next((k for k, v in mapping.items() if v == 'amount'), None)
    date_col = next((k for k, v in mapping.items() if v == 'date'), None)
    invoice_col = next((k for k, v in mapping.items() if v == 'invoice_number'), None)

    if not all([supplier_col, category_col, amount_col, date_col]):
        return False

    supplier_name = row.get(supplier_col, '').strip()
    category_name = row.get(category_col, '').strip()
    amount_str = row.get(amount_col, '').strip().replace('$', '').replace(',', '')
    date_str = row.get(date_col, '').strip()
    invoice_number = row.get(invoice_col, '').strip() if invoice_col else ''

    try:
        amount = Decimal(amount_str)
        date = _parse_date(date_str)

        if not date:
            return False

        query = Transaction.objects.filter(
            organization=organization,
            supplier__name__iexact=supplier_name,
            category__name__iexact=category_name,
            amount=amount,
            date=date
        )

        if invoice_number:
            query = query.filter(invoice_number=invoice_number)

        # In strict mode, also check all other mapped fields
        if strict_mode:
            description_col = next((k for k, v in mapping.items() if v == 'description'), None)
            fiscal_year_col = next((k for k, v in mapping.items() if v == 'fiscal_year'), None)
            subcategory_col = next((k for k, v in mapping.items() if v == 'subcategory'), None)
            location_col = next((k for k, v in mapping.items() if v == 'location'), None)
            spend_band_col = next((k for k, v in mapping.items() if v == 'spend_band'), None)
            payment_method_col = next((k for k, v in mapping.items() if v == 'payment_method'), None)

            if description_col:
                description = row.get(description_col, '').strip()
                query = query.filter(description=description)

            if fiscal_year_col:
                fiscal_year = row.get(fiscal_year_col, '').strip()
                if fiscal_year:
                    query = query.filter(fiscal_year=fiscal_year)

            if subcategory_col:
                subcategory = row.get(subcategory_col, '').strip()
                query = query.filter(subcategory=subcategory)

            if location_col:
                location = row.get(location_col, '').strip()
                query = query.filter(location=location)

            if spend_band_col:
                spend_band = row.get(spend_band_col, '').strip()
                query = query.filter(spend_band=spend_band)

            if payment_method_col:
                payment_method = row.get(payment_method_col, '').strip()
                query = query.filter(payment_method=payment_method)

        return query.exists()

    except (InvalidOperation, ValueError):
        return False
