"""
Base renderer for report output formats.
"""
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Any


class BaseRenderer(ABC):
    """
    Abstract base class for report renderers.
    Each renderer handles a specific output format (PDF, Excel, CSV).
    """

    def __init__(self, report_data: dict, report_name: str = "Report", branding: dict = None):
        """
        Initialize renderer with report data.

        Args:
            report_data: Dictionary containing the report data from generators
            report_name: Name of the report for file naming
            branding: Optional organization branding configuration
        """
        self.report_data = report_data
        self.report_name = report_name
        self.metadata = report_data.get('metadata', {})
        self.branding = branding or {}

    @property
    @abstractmethod
    def content_type(self) -> str:
        """Return the MIME content type for this format."""
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Return the file extension for this format."""
        pass

    @abstractmethod
    def render(self) -> BytesIO:
        """
        Render the report data to the output format.

        Returns:
            BytesIO buffer containing the rendered report
        """
        pass

    def get_filename(self) -> str:
        """Generate filename for the rendered report."""
        timestamp = self.metadata.get('generated_at', '')
        if timestamp:
            timestamp = timestamp.replace(':', '-').replace(' ', '_')[:19]
        safe_name = self.report_name.replace(' ', '_').replace('/', '-')
        return f"{safe_name}_{timestamp}{self.file_extension}"

    def format_currency(self, value: Any) -> str:
        """Format a number as currency."""
        try:
            return f"${float(value):,.2f}"
        except (ValueError, TypeError):
            return str(value)

    def format_percentage(self, value: Any) -> str:
        """Format a number as percentage."""
        try:
            return f"{float(value):.1f}%"
        except (ValueError, TypeError):
            return str(value)

    def format_number(self, value: Any, decimals: int = 0) -> str:
        """Format a number with thousand separators."""
        try:
            if decimals == 0:
                return f"{int(float(value)):,}"
            return f"{float(value):,.{decimals}f}"
        except (ValueError, TypeError):
            return str(value)
