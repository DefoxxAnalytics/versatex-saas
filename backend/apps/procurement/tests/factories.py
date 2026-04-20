"""
Factory classes for generating test data for procurement models.
"""
import factory
import random
from factory.django import DjangoModelFactory
from decimal import Decimal
from datetime import date, timedelta
from apps.procurement.models import Supplier, Category, Transaction, DataUpload
from apps.authentication.tests.factories import OrganizationFactory, UserFactory


class SupplierFactory(DjangoModelFactory):
    """Factory for creating Supplier instances."""

    class Meta:
        model = Supplier

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f'Supplier {n}')
    code = factory.Sequence(lambda n: f'SUP{n:04d}')
    contact_email = factory.LazyAttribute(lambda obj: f'{obj.name.lower().replace(" ", ".")}@example.com')
    contact_phone = factory.Faker('phone_number')
    address = factory.Faker('address')
    is_active = True


class CategoryFactory(DjangoModelFactory):
    """Factory for creating Category instances."""

    class Meta:
        model = Category

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f'Category {n}')
    parent = None
    description = factory.Faker('sentence')
    is_active = True


class TransactionFactory(DjangoModelFactory):
    """Factory for creating Transaction instances."""

    class Meta:
        model = Transaction

    organization = factory.SubFactory(OrganizationFactory)
    uploaded_by = factory.SubFactory(UserFactory)
    supplier = factory.SubFactory(SupplierFactory, organization=factory.SelfAttribute('..organization'))
    category = factory.SubFactory(CategoryFactory, organization=factory.SelfAttribute('..organization'))
    amount = factory.LazyFunction(lambda: Decimal(str(round(1000 + 9000 * random.random(), 2))))
    date = factory.LazyFunction(lambda: date.today() - timedelta(days=random.randint(0, 365)))
    description = factory.Faker('sentence')
    subcategory = factory.Faker('word')
    location = factory.Faker('city')
    fiscal_year = factory.LazyFunction(lambda: date.today().year)
    spend_band = factory.Iterator(['<1K', '1K-10K', '10K-50K', '50K-100K', '>100K'])
    payment_method = factory.Iterator(['Credit Card', 'Bank Transfer', 'Check', 'ACH'])
    invoice_number = factory.Sequence(lambda n: f'INV-{n:06d}')
    upload_batch = factory.Sequence(lambda n: f'batch-{n}')


class DataUploadFactory(DjangoModelFactory):
    """Factory for creating DataUpload instances."""

    class Meta:
        model = DataUpload

    organization = factory.SubFactory(OrganizationFactory)
    uploaded_by = factory.SubFactory(UserFactory)
    file_name = factory.Sequence(lambda n: f'upload_{n}.csv')
    original_file_name = factory.LazyAttribute(lambda obj: obj.file_name)
    file_size = factory.LazyFunction(lambda: random.randint(1000, 1000000))
    batch_id = factory.Sequence(lambda n: f'batch-{n:08d}')
    total_rows = factory.LazyFunction(lambda: random.randint(10, 1000))
    successful_rows = factory.LazyAttribute(lambda obj: int(obj.total_rows * 0.95))
    failed_rows = factory.LazyAttribute(lambda obj: obj.total_rows - obj.successful_rows - obj.duplicate_rows)
    duplicate_rows = factory.LazyFunction(lambda: random.randint(0, 10))
    status = 'completed'
    error_log = []


class LargeTransactionFactory(TransactionFactory):
    """Factory for creating large transactions (>100K)."""

    amount = factory.LazyFunction(lambda: Decimal(str(round(100000 + 900000 * random.random(), 2))))
    spend_band = '>100K'


class SmallTransactionFactory(TransactionFactory):
    """Factory for creating small transactions (<1K)."""

    amount = factory.LazyFunction(lambda: Decimal(str(round(10 + 990 * random.random(), 2))))
    spend_band = '<1K'
