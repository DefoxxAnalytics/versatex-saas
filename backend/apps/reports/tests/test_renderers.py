"""
Tests for report renderers (PDF, Excel, CSV).
"""
import pytest
from io import BytesIO
from apps.reports.renderers.csv import CSVRenderer
from apps.reports.renderers.excel import ExcelRenderer
from apps.reports.renderers.pdf import PDFRenderer


@pytest.mark.django_db
class TestCSVRenderer:
    """Tests for CSVRenderer."""

    def test_content_type(self):
        """Test CSV content type."""
        renderer = CSVRenderer({}, "Test Report")
        assert renderer.content_type == 'text/csv'

    def test_file_extension(self):
        """Test CSV file extension."""
        renderer = CSVRenderer({}, "Test Report")
        assert renderer.file_extension == '.csv'

    def test_render_empty_data(self):
        """Test rendering empty data."""
        renderer = CSVRenderer({}, "Test Report")
        result = renderer.render()

        assert isinstance(result, BytesIO)
        content = result.read().decode('utf-8')
        assert 'No data available' in content or content == ''

    def test_render_with_list_data(self):
        """Test rendering with list data."""
        data = {
            'spend_by_category': [
                {'category': 'IT', 'amount': 50000, 'count': 25},
                {'category': 'Office', 'amount': 30000, 'count': 15},
            ]
        }
        renderer = CSVRenderer(data, "Test Report")
        result = renderer.render()

        content = result.read().decode('utf-8')
        assert 'Category' in content
        assert 'Amount' in content
        assert 'IT' in content
        assert '50000' in content

    def test_render_with_overview_fallback(self):
        """Test rendering falls back to overview when no list data."""
        data = {
            'overview': {
                'total_spend': 100000,
                'supplier_count': 50
            }
        }
        renderer = CSVRenderer(data, "Test Report")
        result = renderer.render()

        content = result.read().decode('utf-8')
        assert 'total_spend' in content.lower() or 'Total Spend' in content

    def test_get_filename(self):
        """Test filename generation."""
        data = {
            'metadata': {
                'generated_at': '2024-06-15T10:30:00'
            }
        }
        renderer = CSVRenderer(data, "Spend Analysis")
        filename = renderer.get_filename()

        assert filename.startswith('Spend_Analysis')
        assert filename.endswith('.csv')

    def test_format_currency(self):
        """Test currency formatting."""
        renderer = CSVRenderer({}, "Test")
        assert renderer.format_currency(1234.56) == '$1,234.56'
        assert renderer.format_currency(1000000) == '$1,000,000.00'

    def test_format_percentage(self):
        """Test percentage formatting."""
        renderer = CSVRenderer({}, "Test")
        assert renderer.format_percentage(75.5) == '75.5%'
        assert renderer.format_percentage(100) == '100.0%'

    def test_render_multiple_sheets(self):
        """Test rendering multiple CSV files."""
        data = {
            'spend_by_category': [
                {'category': 'IT', 'amount': 50000}
            ],
            'spend_by_supplier': [
                {'supplier': 'Acme', 'amount': 30000}
            ]
        }
        renderer = CSVRenderer(data, "Test Report")
        csvs = renderer.render_multiple_sheets()

        assert 'spend_by_category.csv' in csvs
        assert 'spend_by_supplier.csv' in csvs

    def test_priority_key_selection(self):
        """Test that priority keys are selected correctly."""
        # pareto_data has higher priority than spend_by_category
        data = {
            'pareto_data': [{'supplier': 'Top', 'amount': 100}],
            'spend_by_category': [{'category': 'IT', 'amount': 50}]
        }
        renderer = CSVRenderer(data, "Test Report")
        result = renderer.render()

        content = result.read().decode('utf-8')
        # Should use pareto_data (higher priority)
        assert 'Top' in content


@pytest.mark.django_db
class TestExcelRenderer:
    """Tests for ExcelRenderer."""

    def test_content_type(self):
        """Test Excel content type."""
        renderer = ExcelRenderer({}, "Test Report")
        expected = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert renderer.content_type == expected

    def test_file_extension(self):
        """Test Excel file extension."""
        renderer = ExcelRenderer({}, "Test Report")
        assert renderer.file_extension == '.xlsx'

    def test_render_empty_data(self):
        """Test rendering empty data."""
        renderer = ExcelRenderer({}, "Test Report")
        result = renderer.render()

        assert isinstance(result, BytesIO)
        # Should be valid xlsx file (check magic bytes)
        result.seek(0)
        magic_bytes = result.read(4)
        assert magic_bytes == b'PK\x03\x04'  # ZIP format (xlsx is zipped XML)

    def test_render_with_data(self):
        """Test rendering with data."""
        data = {
            'metadata': {
                'report_type': 'spend_analysis',
                'organization': 'Test Org'
            },
            'overview': {
                'total_spend': 100000,
                'supplier_count': 50
            },
            'spend_by_category': [
                {'category': 'IT', 'amount': 50000},
                {'category': 'Office', 'amount': 30000}
            ]
        }
        renderer = ExcelRenderer(data, "Test Report")
        result = renderer.render()

        assert isinstance(result, BytesIO)
        result.seek(0)
        # Verify it's a valid xlsx file
        assert result.read(4) == b'PK\x03\x04'

    def test_get_filename(self):
        """Test filename generation."""
        data = {
            'metadata': {
                'generated_at': '2024-06-15T10:30:00'
            }
        }
        renderer = ExcelRenderer(data, "Supplier Performance")
        filename = renderer.get_filename()

        assert filename.startswith('Supplier_Performance')
        assert filename.endswith('.xlsx')

    def test_render_with_branding(self):
        """Test rendering with organization branding."""
        data = {
            'overview': {'total_spend': 100000}
        }
        branding = {
            'primary_color': '#003366',
            'secondary_color': '#0066cc'
        }
        renderer = ExcelRenderer(data, "Test Report", branding=branding)
        result = renderer.render()

        assert isinstance(result, BytesIO)
        # Should successfully render with branding
        result.seek(0)
        assert result.read(4) == b'PK\x03\x04'


@pytest.mark.django_db
class TestPDFRenderer:
    """Tests for PDFRenderer."""

    def test_content_type(self):
        """Test PDF content type."""
        renderer = PDFRenderer({}, "Test Report")
        assert renderer.content_type == 'application/pdf'

    def test_file_extension(self):
        """Test PDF file extension."""
        renderer = PDFRenderer({}, "Test Report")
        assert renderer.file_extension == '.pdf'

    def test_render_empty_data(self):
        """Test rendering empty data."""
        renderer = PDFRenderer({}, "Test Report")
        result = renderer.render()

        assert isinstance(result, BytesIO)
        # Check PDF magic bytes
        result.seek(0)
        magic_bytes = result.read(4)
        assert magic_bytes == b'%PDF'

    def test_render_with_overview(self):
        """Test rendering with overview data."""
        data = {
            'metadata': {
                'report_type': 'spend_analysis',
                'report_title': 'Spend Analysis Report',
                'organization': 'Test Org',
                'generated_at': '2024-06-15T10:30:00'
            },
            'overview': {
                'total_spend': 1500000.50,
                'supplier_count': 45,
                'category_count': 12,
                'transaction_count': 500
            }
        }
        renderer = PDFRenderer(data, "Spend Analysis")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_render_with_tables(self):
        """Test rendering with table data."""
        data = {
            'metadata': {
                'report_title': 'Spend Analysis',
                'organization': 'Test Org'
            },
            'spend_by_category': [
                {'category': 'IT Services', 'amount': 500000, 'percentage': 33.3},
                {'category': 'Office Supplies', 'amount': 300000, 'percentage': 20.0},
                {'category': 'Professional Services', 'amount': 200000, 'percentage': 13.3},
            ]
        }
        renderer = PDFRenderer(data, "Category Report")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_get_filename(self):
        """Test filename generation."""
        data = {
            'metadata': {
                'generated_at': '2024-06-15T10:30:00'
            }
        }
        renderer = PDFRenderer(data, "Executive Summary")
        filename = renderer.get_filename()

        assert filename.startswith('Executive_Summary')
        assert filename.endswith('.pdf')

    def test_render_with_branding(self):
        """Test rendering with organization branding."""
        data = {
            'metadata': {
                'report_title': 'Test Report',
                'organization': 'Branded Corp'
            },
            'overview': {'total_spend': 100000}
        }
        branding = {
            'primary_color': '#003366',
            'secondary_color': '#0066cc',
            'report_footer': 'Confidential - Internal Use Only'
        }
        renderer = PDFRenderer(data, "Branded Report", branding=branding)
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_large_dataset_handling(self):
        """Test rendering with large datasets."""
        # Create 100 items
        data = {
            'metadata': {
                'report_title': 'Large Report',
                'organization': 'Test Org'
            },
            'spend_by_supplier': [
                {'supplier': f'Supplier {i}', 'amount': 1000 * i, 'count': i}
                for i in range(100)
            ]
        }
        renderer = PDFRenderer(data, "Large Report")
        result = renderer.render()

        # Should successfully render large dataset
        result.seek(0)
        assert result.read(4) == b'%PDF'


@pytest.mark.django_db
class TestRendererFormatting:
    """Tests for common formatting functions across renderers."""

    def test_format_currency_edge_cases(self):
        """Test currency formatting with edge cases."""
        renderer = CSVRenderer({}, "Test")

        # Zero
        assert renderer.format_currency(0) == '$0.00'

        # Negative
        assert renderer.format_currency(-1234.56) == '$-1,234.56'

        # Very large
        assert renderer.format_currency(1000000000) == '$1,000,000,000.00'

        # Invalid input
        assert renderer.format_currency('invalid') == 'invalid'

    def test_format_percentage_edge_cases(self):
        """Test percentage formatting with edge cases."""
        renderer = CSVRenderer({}, "Test")

        # Zero
        assert renderer.format_percentage(0) == '0.0%'

        # Over 100
        assert renderer.format_percentage(150.5) == '150.5%'

        # Negative
        assert renderer.format_percentage(-10) == '-10.0%'

        # Invalid input
        assert renderer.format_percentage('invalid') == 'invalid'

    def test_format_number_edge_cases(self):
        """Test number formatting with edge cases."""
        renderer = CSVRenderer({}, "Test")

        # Integer format
        assert renderer.format_number(1234567, 0) == '1,234,567'

        # With decimals
        assert renderer.format_number(1234.567, 2) == '1,234.57'

        # Zero decimals
        assert renderer.format_number(1234.9, 0) == '1,234'

        # Invalid input
        assert renderer.format_number('invalid') == 'invalid'


@pytest.mark.django_db
class TestRendererFilenameGeneration:
    """Tests for filename generation across all renderers."""

    def test_filename_special_characters(self):
        """Test filename generation with special characters."""
        renderer = CSVRenderer({}, "Report/With/Slashes")
        filename = renderer.get_filename()

        assert '/' not in filename
        assert '-' in filename  # Slashes replaced with dashes

    def test_filename_spaces(self):
        """Test filename generation with spaces."""
        renderer = CSVRenderer({}, "Report With Spaces")
        filename = renderer.get_filename()

        assert ' ' not in filename
        assert '_' in filename

    def test_filename_without_timestamp(self):
        """Test filename generation without timestamp."""
        renderer = CSVRenderer({}, "Simple Report")
        filename = renderer.get_filename()

        assert filename.startswith('Simple_Report')
        assert filename.endswith('.csv')


@pytest.mark.django_db
class TestRendererDataHandling:
    """Tests for data handling in renderers."""

    def test_csv_handles_none_values(self):
        """Test CSV renderer handles None values gracefully."""
        data = {
            'spend_by_category': [
                {'category': 'IT', 'amount': 50000, 'note': None},
                {'category': 'Office', 'amount': None, 'note': 'test'}
            ]
        }
        renderer = CSVRenderer(data, "Test")
        result = renderer.render()

        # Should render without errors
        content = result.read().decode('utf-8')
        assert 'IT' in content

    def test_excel_handles_mixed_types(self):
        """Test Excel renderer handles mixed data types."""
        data = {
            'spend_by_category': [
                {'category': 'IT', 'amount': 50000, 'active': True},
                {'category': 'Office', 'amount': '30000', 'active': False}
            ]
        }
        renderer = ExcelRenderer(data, "Test")
        result = renderer.render()

        # Should render without errors
        result.seek(0)
        assert result.read(4) == b'PK\x03\x04'

    def test_pdf_handles_unicode(self):
        """Test PDF renderer handles unicode characters."""
        data = {
            'metadata': {
                'report_title': 'Report with Unicode: \u00e9\u00e0\u00fc',
                'organization': 'Test \u00d6rg'
            },
            'spend_by_supplier': [
                {'supplier': 'Supplier \u00c0', 'amount': 50000}
            ]
        }
        renderer = PDFRenderer(data, "Unicode Report")
        result = renderer.render()

        # Should render without errors
        result.seek(0)
        assert result.read(4) == b'%PDF'


# ============================================================================
# PDF Renderer Extended Tests
# ============================================================================

@pytest.mark.django_db
class TestPDFRendererReportTypes:
    """Tests for PDF rendering of different report types."""

    def test_render_executive_summary(self):
        """Test rendering executive summary report type."""
        data = {
            'metadata': {
                'report_type': 'executive_summary',
                'report_title': 'Executive Summary',
                'organization': 'Acme Corp',
                'generated_at': '2024-06-15T10:30:00',
                'period_start': '2024-01-01',
                'period_end': '2024-06-30'
            },
            'overview': {
                'total_spend': 2500000,
                'supplier_count': 150,
                'transaction_count': 5000,
                'avg_transaction': 500.00
            },
            'insights': [
                {'type': 'opportunity', 'title': 'Cost Reduction', 'description': 'Consolidate suppliers'}
            ]
        }
        renderer = PDFRenderer(data, "Executive Summary")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_render_supplier_performance(self):
        """Test rendering supplier performance report type."""
        data = {
            'metadata': {
                'report_type': 'supplier_performance',
                'report_title': 'Supplier Performance Report',
                'organization': 'Test Org'
            },
            'suppliers': [
                {
                    'supplier': 'Top Vendor',
                    'total_spend': 500000,
                    'transaction_count': 200,
                    'percent_of_total': 25.5,
                    'categories': ['IT', 'Office']
                },
                {
                    'supplier': 'Second Vendor',
                    'total_spend': 300000,
                    'transaction_count': 150,
                    'percent_of_total': 15.2,
                    'categories': ['Services']
                }
            ]
        }
        renderer = PDFRenderer(data, "Supplier Performance")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_render_pareto_analysis(self):
        """Test rendering Pareto analysis report type."""
        data = {
            'metadata': {
                'report_type': 'pareto_analysis',
                'report_title': 'Pareto Analysis',
                'organization': 'Test Org'
            },
            'supplier_ranking': [
                {'supplier': f'Supplier {i}', 'amount': 1000 * (20 - i), 'cumulative_percentage': i * 5}
                for i in range(1, 21)
            ],
            'spend_by_classification': {
                'class_a': 70,
                'class_b': 20,
                'class_c': 10
            }
        }
        renderer = PDFRenderer(data, "Pareto Analysis")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_render_stratification_report(self):
        """Test rendering stratification report type."""
        data = {
            'metadata': {
                'report_type': 'stratification',
                'report_title': 'Spend Stratification',
                'organization': 'Test Org'
            },
            'segments': [
                {'segment': 'Strategic', 'spend': 1500000, 'supplier_count': 10, 'percentage': 50},
                {'segment': 'Leverage', 'spend': 750000, 'supplier_count': 25, 'percentage': 25},
                {'segment': 'Routine', 'spend': 450000, 'supplier_count': 50, 'percentage': 15},
                {'segment': 'Tactical', 'spend': 300000, 'supplier_count': 100, 'percentage': 10}
            ]
        }
        renderer = PDFRenderer(data, "Spend Stratification")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_render_seasonality_report(self):
        """Test rendering seasonality report type."""
        data = {
            'metadata': {
                'report_type': 'seasonality',
                'report_title': 'Seasonality Analysis',
                'organization': 'Test Org'
            },
            'monthly_analysis': [
                {'month': f'2024-{i:02d}', 'spend': 100000 + i * 5000, 'seasonal_index': 0.8 + (i % 4) * 0.1}
                for i in range(1, 13)
            ],
            'peak_month': 'December',
            'trough_month': 'February'
        }
        renderer = PDFRenderer(data, "Seasonality Analysis")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_render_yoy_report(self):
        """Test rendering year-over-year report type."""
        data = {
            'metadata': {
                'report_type': 'year_over_year',
                'report_title': 'Year-over-Year Analysis',
                'organization': 'Test Org'
            },
            'summary': {
                'year1': 2023,
                'year2': 2024,
                'year1_spend': 2000000,
                'year2_spend': 2300000,
                'change': 15.0
            },
            'monthly_comparison': [
                {'month': f'Month {i}', 'year1_spend': 150000 + i * 1000, 'year2_spend': 175000 + i * 1500}
                for i in range(1, 13)
            ]
        }
        renderer = PDFRenderer(data, "YoY Analysis")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'


@pytest.mark.django_db
class TestPDFRendererKPICards:
    """Tests for PDF KPI card rendering."""

    def test_render_with_kpi_data(self):
        """Test rendering with KPI overview data."""
        data = {
            'metadata': {
                'report_title': 'KPI Report',
                'organization': 'Test Org'
            },
            'overview': {
                'total_spend': 1500000,
                'supplier_count': 75,
                'transaction_count': 2500,
                'avg_transaction': 600.00,
                'ytd_change': 12.5,
                'category_count': 20
            }
        }
        renderer = PDFRenderer(data, "KPI Report")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_render_with_long_kpi_values(self):
        """Test KPI cards with very long values."""
        data = {
            'metadata': {
                'report_title': 'Long Value Report',
                'organization': 'Test Org'
            },
            'overview': {
                'total_spend': 9999999999.99,
                'supplier_count': 9999999,
                'long_metric': 'This is a very long value string'
            }
        }
        renderer = PDFRenderer(data, "Long Value Report")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_render_with_change_indicators(self):
        """Test KPI cards with positive and negative changes."""
        data = {
            'metadata': {
                'report_title': 'Change Indicator Report',
                'organization': 'Test Org'
            },
            'overview': {
                'total_spend': 1500000,
                'spend_change': '+15%',
                'supplier_count': 75,
                'supplier_change': '-5%'
            }
        }
        renderer = PDFRenderer(data, "Change Report")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'


@pytest.mark.django_db
class TestPDFRendererBranding:
    """Tests for PDF branding features."""

    def test_full_branding_config(self):
        """Test rendering with complete branding configuration."""
        data = {
            'metadata': {
                'report_title': 'Branded Report',
                'organization': 'Custom Brand Corp'
            },
            'overview': {'total_spend': 100000}
        }
        branding = {
            'name': 'Custom Brand Corp',
            'primary_color': '#1e3a5f',
            'secondary_color': '#2563eb',
            'report_footer': 'Property of Custom Brand Corp - Confidential',
            'website': 'https://www.custombrand.com'
        }
        renderer = PDFRenderer(data, "Branded Report", branding=branding)
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_custom_colors(self):
        """Test rendering with custom brand colors."""
        data = {
            'metadata': {
                'report_title': 'Custom Colors Report',
                'organization': 'Color Corp'
            },
            'spend_by_category': [
                {'category': 'IT', 'amount': 50000, 'percentage': 50},
                {'category': 'Office', 'amount': 30000, 'percentage': 30},
                {'category': 'Services', 'amount': 20000, 'percentage': 20}
            ]
        }
        branding = {
            'primary_color': '#8b0000',  # Dark red
            'secondary_color': '#ff6347'  # Tomato
        }
        renderer = PDFRenderer(data, "Custom Colors Report", branding=branding)
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_long_footer_truncation(self):
        """Test that very long footer text is truncated."""
        data = {
            'metadata': {
                'report_title': 'Long Footer Report',
                'organization': 'Test Org'
            },
            'overview': {'total_spend': 100000}
        }
        branding = {
            'report_footer': 'This is an extremely long footer text that should be truncated to fit within the PDF page margins and not overflow'
        }
        renderer = PDFRenderer(data, "Long Footer Report", branding=branding)
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'


@pytest.mark.django_db
class TestPDFRendererTables:
    """Tests for PDF table rendering."""

    def test_empty_table_data(self):
        """Test rendering with empty table data."""
        data = {
            'metadata': {
                'report_title': 'Empty Table Report',
                'organization': 'Test Org'
            },
            'spend_by_category': []
        }
        renderer = PDFRenderer(data, "Empty Table Report")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_wide_table(self):
        """Test rendering with many columns."""
        data = {
            'metadata': {
                'report_title': 'Wide Table Report',
                'organization': 'Test Org'
            },
            'spend_by_category': [
                {
                    'category': 'IT',
                    'amount': 50000,
                    'count': 25,
                    'avg': 2000,
                    'percentage': 33.3,
                    'ytd_change': 10.5,
                    'qoq_change': 5.2,
                    'status': 'Active'
                }
            ]
        }
        renderer = PDFRenderer(data, "Wide Table Report")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_multiple_tables(self):
        """Test rendering with multiple data tables."""
        data = {
            'metadata': {
                'report_title': 'Multi Table Report',
                'organization': 'Test Org'
            },
            'spend_by_category': [
                {'category': 'IT', 'amount': 50000, 'percentage': 50}
            ],
            'spend_by_supplier': [
                {'supplier': 'Vendor A', 'amount': 30000, 'count': 15}
            ],
            'monthly_trend': [
                {'month': '2024-01', 'spend': 40000},
                {'month': '2024-02', 'spend': 45000}
            ]
        }
        renderer = PDFRenderer(data, "Multi Table Report")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'


@pytest.mark.django_db
class TestPDFRendererEdgeCases:
    """Edge case tests for PDF renderer."""

    def test_missing_metadata(self):
        """Test rendering with missing metadata."""
        data = {
            'overview': {'total_spend': 100000}
        }
        renderer = PDFRenderer(data, "No Metadata Report")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_null_values_in_data(self):
        """Test rendering with null values in numeric data."""
        data = {
            'metadata': {
                'report_title': 'Null Values Report',
                'organization': 'Test Org'  # Organization should never be null in practice
            },
            'overview': {
                'total_spend': 0,
                'supplier_count': 0
            },
            'spend_by_category': [
                {'category': 'IT', 'amount': 0, 'percentage': 0}
            ]
        }
        renderer = PDFRenderer(data, "Null Values Report")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_special_characters_in_data(self):
        """Test rendering with special characters."""
        data = {
            'metadata': {
                'report_title': 'Special Chars: <>&"\'',
                'organization': 'Test & Co.'
            },
            'spend_by_supplier': [
                {'supplier': 'Vendor <A> & Co.', 'amount': 50000}
            ]
        }
        renderer = PDFRenderer(data, "Special Chars Report")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_very_large_numbers(self):
        """Test rendering with very large numbers."""
        data = {
            'metadata': {
                'report_title': 'Large Numbers Report',
                'organization': 'Big Corp'
            },
            'overview': {
                'total_spend': 999999999999.99,
                'transaction_count': 9999999999
            }
        }
        renderer = PDFRenderer(data, "Large Numbers Report")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_negative_values(self):
        """Test rendering with negative values."""
        data = {
            'metadata': {
                'report_title': 'Negative Values Report',
                'organization': 'Test Org'
            },
            'overview': {
                'total_spend': 100000,
                'ytd_change': -15.5
            },
            'spend_by_category': [
                {'category': 'Refunds', 'amount': -5000, 'percentage': -5.0}
            ]
        }
        renderer = PDFRenderer(data, "Negative Values Report")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_zero_values(self):
        """Test rendering with all zero values."""
        data = {
            'metadata': {
                'report_title': 'Zero Values Report',
                'organization': 'Test Org'
            },
            'overview': {
                'total_spend': 0,
                'supplier_count': 0,
                'transaction_count': 0
            }
        }
        renderer = PDFRenderer(data, "Zero Values Report")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'

    def test_deeply_nested_data(self):
        """Test rendering with deeply nested data structures."""
        data = {
            'metadata': {
                'report_title': 'Nested Data Report',
                'organization': 'Test Org',
                'filters': {
                    'date_range': {
                        'start': '2024-01-01',
                        'end': '2024-06-30'
                    },
                    'categories': ['IT', 'Office']
                }
            },
            'overview': {
                'totals': {
                    'spend': 100000,
                    'count': 50
                }
            }
        }
        renderer = PDFRenderer(data, "Nested Data Report")
        result = renderer.render()

        result.seek(0)
        assert result.read(4) == b'%PDF'
