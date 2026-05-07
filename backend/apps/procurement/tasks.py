"""
Celery tasks for procurement data processing.
Handles background CSV upload processing for large files.
"""
import csv
import io
import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.authentication.models import UserOrganizationMembership

from .models import DataUpload, Transaction, Supplier, Category
from .services import get_or_create_supplier, get_or_create_category

logger = logging.getLogger(__name__)

MEMBERSHIP_REVOKED_ERROR = (
    "User no longer an active member of organization at execution time"
)

# Number of CSV rows committed per `transaction.atomic()` block. Exposed at
# module scope so tests can patch a smaller value without inflating fixtures.
CSV_BATCH_SIZE = 1000


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

    # Finding C4: re-verify the uploader's organization membership at execution
    # time. Between `delay()` and execution, the user may have been removed,
    # had their membership deactivated, or had their role/access revoked. If
    # they are no longer an active member, abort before any rows are written.
    if not UserOrganizationMembership.objects.filter(
        user=upload.uploaded_by,
        organization=upload.organization,
        is_active=True,
    ).exists():
        logger.warning(
            "process_csv_upload aborted: user_id=%s no longer an active member "
            "of organization_id=%s (upload_id=%s, batch_id=%s)",
            getattr(upload.uploaded_by, 'id', None),
            upload.organization_id,
            upload.id,
            upload.batch_id,
        )
        upload.status = 'failed'
        upload.error_log = json.dumps([{'message': MEMBERSHIP_REVOKED_ERROR}])
        upload.progress_message = MEMBERSHIP_REVOKED_ERROR
        upload.completed_at = timezone.now()
        upload.save()
        return {
            'status': 'failed',
            'error': MEMBERSHIP_REVOKED_ERROR,
            'upload_id': upload.id,
        }

    try:
        # Idempotency checkpoint (v3.0 Phase 1 task 1.7).
        # If `last_processed_batch_index > 0`, this invocation is a Celery
        # retry resuming after a worker crash. Skip already-processed batches.
        # Counter records the NEXT batch to attempt, so it equals the count
        # of fully-handled batches (succeeded or rolled-back-under-skip).
        resume_from_batch = upload.last_processed_batch_index
        is_resumed_run = resume_from_batch > 0

        # Update status
        upload.status = 'processing'
        upload.progress_percent = 0
        upload.progress_message = (
            f'Resuming from batch {resume_from_batch}...'
            if is_resumed_run else 'Starting processing...'
        )
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

        # On a resumed run, seed in-memory accumulators from what the
        # previous invocation persisted at its last checkpoint. Without
        # this, the final upload record would only reflect rows ingested
        # after the resume point, dropping all evidence of pre-crash work.
        if is_resumed_run:
            successful = upload.successful_rows
            failed = upload.failed_rows
            duplicates = upload.duplicate_rows
            prior_log = upload.error_log
            if prior_log:
                if isinstance(prior_log, list):
                    decoded = prior_log
                else:
                    try:
                        decoded = json.loads(prior_log)
                    except (TypeError, ValueError):
                        decoded = []
                if not isinstance(decoded, list):
                    decoded = []
                batch_log = [e for e in decoded if e.get('kind') == 'batch']
                errors = [
                    {k: v for k, v in e.items() if k != 'kind'}
                    for e in decoded if e.get('kind') == 'row'
                ]
            else:
                batch_log = []
                errors = []
            batches_succeeded = sum(
                1 for b in batch_log if b.get('status') == 'succeeded'
            )
            batches_failed = sum(
                1 for b in batch_log if b.get('status') == 'failed'
            )
            failed_entries = [b for b in batch_log if b.get('status') == 'failed']
            if failed_entries:
                first = min(failed_entries, key=lambda b: b.get('batch_index', 0))
                first_failed_batch_index = first.get('batch_index')
                first_failed_batch_rows = (
                    first.get('first_row_number'),
                    first.get('last_row_number'),
                )
            else:
                first_failed_batch_index = None
                first_failed_batch_rows = None
        else:
            successful = 0
            failed = 0
            duplicates = 0
            errors = []
            batch_log = []
            batches_succeeded = 0
            batches_failed = 0
            first_failed_batch_index = None
            first_failed_batch_rows = None

        # Process in batches
        batch_size = CSV_BATCH_SIZE
        total_batches = (total_rows + batch_size - 1) // batch_size

        for batch_index, batch_start in enumerate(range(0, total_rows, batch_size)):
            # Idempotency: on a resumed run, skip batches the previous
            # invocation already handled. Their per-row outcomes were
            # finalized in `error_log` before the checkpoint advanced;
            # re-processing would double-insert (now caught by the
            # canonical-case unique constraint, but counts/audit/status
            # would diverge from reality).
            if batch_index < resume_from_batch:
                continue

            batch_end = min(batch_start + batch_size, total_rows)
            batch_rows = rows[batch_start:batch_end]
            batch_first_row_number = batch_start + 2  # +2 for 1-indexed and header row
            batch_last_row_number = batch_end + 1

            # Update progress. Use targeted .update() instead of .save():
            # .save() writes ALL fields from the in-memory `upload` object,
            # which would clobber the checkpoint columns (last_processed_
            # batch_index, successful_rows, etc.) that previous batches
            # advanced via direct UPDATE. Targeted update preserves them.
            progress = int((batch_start / total_rows) * 100)
            DataUpload.objects.filter(pk=upload.pk).update(
                progress_percent=progress,
                progress_message=(
                    f'Processing rows {batch_start + 1} to {batch_end} '
                    f'of {total_rows}'
                ),
            )

            batch_successful = 0
            batch_failed = 0
            batch_duplicates = 0
            batch_row_errors = []
            first_failed_row_in_batch = None
            failure_exception = None
            abort_after_batch = False

            try:
                with transaction.atomic():
                    for i, row in enumerate(batch_rows):
                        row_num = batch_start + i + 2  # +2 for 1-indexed and header row

                        try:
                            # Validate row
                            row_errors = _validate_row(row, mapping, row_num)
                            if row_errors:
                                batch_row_errors.extend(row_errors)
                                if not skip_invalid:
                                    raise ValueError(f'Row {row_num} has validation errors')
                                batch_failed += 1
                                if first_failed_row_in_batch is None:
                                    first_failed_row_in_batch = row_num
                                continue

                            # Check for duplicates (unless skip_duplicates is enabled)
                            if not skip_duplicates and _is_duplicate_row(row, mapping, organization, strict_mode=strict_duplicates):
                                batch_duplicates += 1
                                continue

                            # Get or create supplier (canonical-case race-safe)
                            supplier_name = row.get(supplier_col, '').strip()
                            supplier, _ = get_or_create_supplier(
                                organization=organization,
                                name=supplier_name,
                            )

                            # Get or create category (canonical-case race-safe)
                            category_name = row.get(category_col, '').strip()
                            category, _ = get_or_create_category(
                                organization=organization,
                                name=category_name,
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
                            batch_successful += 1

                        except Exception as e:
                            batch_failed += 1
                            if first_failed_row_in_batch is None:
                                first_failed_row_in_batch = row_num
                            batch_row_errors.append({
                                'row': row_num,
                                'field': 'general',
                                'message': str(e)[:500],
                                'value': ''
                            })
                            if not skip_invalid:
                                raise
            except Exception as e:
                # Atomic block rolled back the entire batch. Discard any
                # in-memory per-row counters/errors from this batch (they
                # do not reflect committed state) and record the batch
                # as failed for observability.
                failure_exception = e
                abort_after_batch = not skip_invalid

            if failure_exception is not None:
                batches_failed += 1
                if first_failed_batch_index is None:
                    first_failed_batch_index = batch_index
                    first_failed_batch_rows = (batch_first_row_number, batch_last_row_number)
                batch_log.append({
                    'kind': 'batch',
                    'batch_index': batch_index,
                    'first_row_number': batch_first_row_number,
                    'last_row_number': batch_last_row_number,
                    'rows_in_batch': len(batch_rows),
                    'status': 'failed',
                    'rolled_back': True,
                    'first_failed_row_number': first_failed_row_in_batch,
                    'error_class': type(failure_exception).__name__,
                    'message': str(failure_exception)[:500],
                })
                if abort_after_batch:
                    # Hard abort under skip_invalid=False. Checkpoint stays
                    # at the failed batch index so a retry resumes here
                    # rather than re-running prior batches.
                    DataUpload.objects.filter(pk=upload.pk).update(
                        last_processed_batch_index=batch_index,
                        successful_rows=successful,
                        failed_rows=failed,
                        duplicate_rows=duplicates,
                        error_log=json.dumps(
                            batch_log + [{'kind': 'row', **e} for e in errors]
                        ),
                    )
                    break
                # skip_invalid=True: this batch is fully handled (rolled
                # back, logged); advance the checkpoint past it before
                # moving to the next batch.
                DataUpload.objects.filter(pk=upload.pk).update(
                    last_processed_batch_index=batch_index + 1,
                    successful_rows=successful,
                    failed_rows=failed,
                    duplicate_rows=duplicates,
                    error_log=json.dumps(
                        batch_log + [{'kind': 'row', **e} for e in errors]
                    ),
                )
                continue

            # Batch committed successfully. Promote per-batch counters
            # and per-row errors to the upload-level totals.
            batches_succeeded += 1
            successful += batch_successful
            failed += batch_failed
            duplicates += batch_duplicates
            errors.extend(batch_row_errors)
            batch_log.append({
                'kind': 'batch',
                'batch_index': batch_index,
                'first_row_number': batch_first_row_number,
                'last_row_number': batch_last_row_number,
                'rows_in_batch': len(batch_rows),
                'status': 'succeeded',
                'rolled_back': False,
                'rows_ingested': batch_successful,
                'rows_skipped_invalid': batch_failed,
                'rows_skipped_duplicate': batch_duplicates,
            })

            # Checkpoint advance after a clean batch commit. Use .update()
            # to bypass model signals (post_save fires Redis cache
            # invalidation; we only want signals on terminal status
            # transitions, not on every batch). Running counts persist
            # alongside the index so a crash after this point preserves
            # this batch's tally for the next invocation to seed from.
            DataUpload.objects.filter(pk=upload.pk).update(
                last_processed_batch_index=batch_index + 1,
                successful_rows=successful,
                failed_rows=failed,
                duplicate_rows=duplicates,
                error_log=json.dumps(
                    batch_log + [{'kind': 'row', **e} for e in errors]
                ),
            )

        batches_unprocessed = max(total_batches - batches_succeeded - batches_failed, 0)

        # Finalize upload record. error_log carries both per-batch summaries
        # (kind='batch') and per-row errors (kind='row') so users can drill
        # from batch-level outcome down to the failing row.
        upload.successful_rows = successful
        upload.failed_rows = failed
        upload.duplicate_rows = duplicates
        combined_log = batch_log + [{'kind': 'row', **err} for err in errors]
        upload.error_log = json.dumps(combined_log) if combined_log else ''
        upload.completed_at = timezone.now()
        upload.progress_percent = 100

        if batches_failed:
            first_failed_start, first_failed_end = first_failed_batch_rows
            summary = (
                f'{batches_succeeded} of {total_batches} batches succeeded; '
                f'first failed batch: {first_failed_batch_index} '
                f'(rows {first_failed_start}-{first_failed_end}); '
                f'{batches_unprocessed} unprocessed; see error_log for details.'
            )
        else:
            summary = (
                f'Processing complete: {batches_succeeded} of '
                f'{total_batches} batches succeeded.'
            )
        upload.progress_message = summary[:255]

        if batches_failed == 0 and failed == 0 and duplicates == 0:
            upload.status = 'completed'
        elif successful > 0:
            upload.status = 'partial'
        else:
            upload.status = 'failed'

        # Reset idempotency checkpoint on terminal completion. Any future
        # invocation of this task with the same upload_id is treated as a
        # fresh run rather than a resume.
        upload.last_processed_batch_index = 0
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
        # Retry on transient errors. Preserve the checkpoint and any
        # already-persisted batch tallies so the next attempt resumes
        # from the last committed batch rather than overwriting state.
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        # Retries exhausted: finalize as failed. Do NOT clobber the
        # error_log if checkpointed data is already present (resume
        # state has higher diagnostic value than a single bare message).
        upload.status = 'failed'
        if not upload.error_log:
            upload.error_log = json.dumps([{'message': str(e)}])
        upload.progress_message = f'Error: {str(e)}'[:255]
        upload.completed_at = timezone.now()
        upload.save()
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
