"""
CSV Renderer for reports.
Uses pandas for efficient CSV generation.
"""
import csv
from io import BytesIO, StringIO
from .base import BaseRenderer

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class CSVRenderer(BaseRenderer):
    """
    Renders reports as CSV files.
    Flattens nested data structures for CSV export.
    """

    @property
    def content_type(self) -> str:
        return 'text/csv'

    @property
    def file_extension(self) -> str:
        return '.csv'

    def render(self) -> BytesIO:
        """Render report data as CSV."""
        buffer = BytesIO()

        # Find the main data to export
        main_data = self._find_main_data()

        if PANDAS_AVAILABLE and main_data:
            self._render_with_pandas(buffer, main_data)
        else:
            self._render_with_csv(buffer, main_data)

        buffer.seek(0)
        return buffer

    def _find_main_data(self):
        """Find the main data array in the report."""
        # Priority order for finding exportable data
        priority_keys = [
            'pareto_data',
            'spend_by_category',
            'spend_by_supplier',
            'top_suppliers',
            'top_categories',
            'monthly_trend',
            'tail_suppliers',
            'consolidation_opportunities',
            'category_opportunities',
            'stratification',
            'violations',
            'savings_by_type',
            'suppliers',
            'categories',
        ]

        for key in priority_keys:
            data = self.report_data.get(key, [])
            if data and isinstance(data, list) and len(data) > 0:
                return data

        # Fallback: find any list in the data
        for key, value in self.report_data.items():
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                return value

        # If no list found, try to flatten the overview/summary
        overview = self.report_data.get('overview', {})
        if not overview:
            overview = self.report_data.get('summary', {})

        if overview:
            return [{'metric': k, 'value': v} for k, v in overview.items()]

        return []

    def _render_with_pandas(self, buffer, data):
        """Render CSV using pandas."""
        if not data:
            buffer.write(b"No data available")
            return

        df = pd.DataFrame(data)

        # Format column names
        df.columns = [col.replace('_', ' ').title() for col in df.columns]

        # Convert to CSV
        csv_string = df.to_csv(index=False)
        buffer.write(csv_string.encode('utf-8'))

    def _render_with_csv(self, buffer, data):
        """Render CSV using stdlib csv module."""
        if not data:
            buffer.write(b"No data available")
            return

        # Use StringIO for csv writer, then encode to BytesIO
        string_buffer = StringIO()
        writer = None

        for item in data:
            if isinstance(item, dict):
                if writer is None:
                    # Write headers
                    headers = [k.replace('_', ' ').title() for k in item.keys()]
                    writer = csv.DictWriter(
                        string_buffer,
                        fieldnames=list(item.keys()),
                        extrasaction='ignore'
                    )
                    # Write custom header row
                    string_buffer.write(','.join(headers) + '\n')

                # Write row
                writer.writerow(item)

        buffer.write(string_buffer.getvalue().encode('utf-8'))

    def render_multiple_sheets(self) -> dict:
        """
        Render multiple CSV files for different data sections.
        Returns a dict of {filename: BytesIO buffer}
        """
        csvs = {}

        # Data sections to export
        data_sections = {
            'spend_by_category': 'spend_by_category',
            'spend_by_supplier': 'spend_by_supplier',
            'top_suppliers': 'top_suppliers',
            'monthly_trend': 'monthly_trend',
            'pareto_data': 'pareto_analysis',
            'tail_suppliers': 'tail_suppliers',
            'consolidation_opportunities': 'consolidation',
            'stratification': 'stratification',
            'violations': 'violations',
        }

        for key, filename in data_sections.items():
            data = self.report_data.get(key, [])
            if data and isinstance(data, list) and len(data) > 0:
                buffer = BytesIO()
                if PANDAS_AVAILABLE:
                    self._render_with_pandas(buffer, data)
                else:
                    self._render_with_csv(buffer, data)
                buffer.seek(0)
                csvs[f"{filename}.csv"] = buffer

        return csvs
