"""
PDF Renderer for reports.
Uses ReportLab for PDF generation with professional styled layouts,
charts, KPI cards, and executive-quality formatting.

Features:
- Executive header with organization branding
- KPI summary cards with icons and visual hierarchy
- Data tables with alternating rows and professional styling
- Pie/Bar charts for data visualization
- Professional footer with page numbers
- Color-coded status indicators
"""
from io import BytesIO
from datetime import datetime
from .base import BaseRenderer

# ReportLab imports - handle gracefully if not installed
REPORTLAB_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, KeepTogether, HRFlowable, Image
    )
    from reportlab.platypus.flowables import Flowable
    from reportlab.graphics.shapes import Drawing, Rect, String, Line
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.legends import Legend
    from reportlab.graphics.widgets.markers import makeMarker
    REPORTLAB_AVAILABLE = True
except ImportError:
    pass


class RoundedRect(Flowable):
    """A rounded rectangle flowable for KPI cards."""

    def __init__(self, width, height, radius=10, fill_color=None, stroke_color=None,
                 stroke_width=1, content=None):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.radius = radius
        self.fill_color = fill_color or colors.white
        self.stroke_color = stroke_color or colors.HexColor('#e5e7eb')
        self.stroke_width = stroke_width
        self.content = content or []

    def draw(self):
        self.canv.saveState()
        self.canv.setStrokeColor(self.stroke_color)
        self.canv.setLineWidth(self.stroke_width)
        self.canv.setFillColor(self.fill_color)
        self.canv.roundRect(0, 0, self.width, self.height, self.radius,
                           stroke=1, fill=1)
        self.canv.restoreState()


class KPICard(Flowable):
    """A styled KPI card with label, value, and optional change indicator."""

    def __init__(self, label, value, change=None, change_positive=True,
                 width=150, height=80, accent_color=None):
        Flowable.__init__(self)
        self.label = label
        self.value = value
        self.change = change
        self.change_positive = change_positive
        self.width = width
        self.height = height
        self.accent_color = accent_color or colors.HexColor('#2563eb')

    def draw(self):
        canvas = self.canv
        canvas.saveState()

        # Card background with shadow effect
        canvas.setFillColor(colors.HexColor('#f8fafc'))
        canvas.roundRect(2, -2, self.width, self.height, 8, stroke=0, fill=1)

        # Main card
        canvas.setFillColor(colors.white)
        canvas.setStrokeColor(colors.HexColor('#e2e8f0'))
        canvas.setLineWidth(1)
        canvas.roundRect(0, 0, self.width, self.height, 8, stroke=1, fill=1)

        # Accent bar at top
        canvas.setFillColor(self.accent_color)
        canvas.roundRect(0, self.height - 4, self.width, 4, 2, stroke=0, fill=1)

        # Label
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.setFont('Helvetica', 9)
        canvas.drawString(12, self.height - 24, self.label)

        # Value - auto-size font based on length
        canvas.setFillColor(colors.HexColor('#1e293b'))
        display_value = str(self.value)

        # Determine font size based on value length to fit in card
        if len(display_value) > 16:
            font_size = 14
        elif len(display_value) > 12:
            font_size = 16
        else:
            font_size = 18

        canvas.setFont('Helvetica-Bold', font_size)
        canvas.drawString(12, self.height - 50, display_value)

        # Change indicator
        if self.change is not None:
            if self.change_positive:
                canvas.setFillColor(colors.HexColor('#10b981'))
                arrow = '▲'
            else:
                canvas.setFillColor(colors.HexColor('#ef4444'))
                arrow = '▼'
            canvas.setFont('Helvetica', 10)
            canvas.drawString(12, 12, f"{arrow} {self.change}")

        canvas.restoreState()


class PDFRenderer(BaseRenderer):
    """
    Renders reports as professional PDF documents with:
    - Executive header with organization branding and logo
    - Dynamic color theming from organization settings
    - KPI summary cards
    - Styled data tables
    - Charts (pie, bar)
    - Professional footer with page numbers and custom text
    """

    # Default brand colors (can be overridden by organization branding)
    DEFAULT_NAVY = '#1e3a5f'
    DEFAULT_BLUE = '#2563eb'
    LIGHT_BLUE = '#3b82f6'
    TEAL = '#0d9488'
    GREEN = '#10b981'
    AMBER = '#f59e0b'
    RED = '#ef4444'
    GRAY_50 = '#f8fafc'
    GRAY_100 = '#f1f5f9'
    GRAY_200 = '#e2e8f0'
    GRAY_500 = '#64748b'
    GRAY_700 = '#334155'
    GRAY_900 = '#0f172a'

    # Chart colors palette
    CHART_COLORS = [
        '#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
        '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1'
    ]

    def __init__(self, report_data: dict, report_name: str = "Report", branding: dict = None):
        """
        Initialize PDF renderer with optional organization branding.

        Args:
            report_data: Report data dictionary
            report_name: Name of the report
            branding: Optional branding config with keys:
                - name: Organization name
                - logo_path: Path to logo image file
                - primary_color: Primary brand color (hex)
                - secondary_color: Secondary brand color (hex)
                - footer: Custom footer text
                - website: Organization website
        """
        super().__init__(report_data, report_name, branding)

        # Apply branding colors if provided
        self.NAVY = self.branding.get('primary_color') or self.DEFAULT_NAVY
        self.BLUE = self.branding.get('secondary_color') or self.DEFAULT_BLUE

    @property
    def content_type(self) -> str:
        return 'application/pdf'

    @property
    def file_extension(self) -> str:
        return '.pdf'

    def _get_hex_color(self, hex_str):
        """Convert hex string to ReportLab color."""
        return colors.HexColor(hex_str)

    def render(self) -> BytesIO:
        """Render report data as professional PDF."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "reportlab is required for PDF rendering. "
                "Install it with: pip install reportlab"
            )

        buffer = BytesIO()

        # Create document with custom page template
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )

        # Build the PDF content
        story = self._build_story()

        # Build with page template
        doc.build(
            story,
            onFirstPage=self._add_page_header_footer,
            onLaterPages=self._add_page_header_footer
        )

        buffer.seek(0)
        return buffer

    def _add_page_header_footer(self, canvas, doc):
        """Add branded header and footer to each page."""
        import os
        canvas.saveState()

        page_width = letter[0]
        page_height = letter[1]

        # =================== HEADER ===================
        # Header background gradient effect (subtle)
        canvas.setFillColor(self._get_hex_color(self.NAVY))
        canvas.rect(0, page_height - 0.6 * inch, page_width, 0.6 * inch, stroke=0, fill=1)

        # Try to add logo if available
        logo_path = self.branding.get('logo_path')
        header_x = 0.5 * inch

        if logo_path and os.path.exists(logo_path):
            try:
                # Add logo image (max height 0.4 inch)
                logo_img = Image(logo_path, height=0.4 * inch, kind='proportional')
                logo_img.drawOn(canvas, header_x, page_height - 0.5 * inch)
                header_x += 2.0 * inch  # Shift text after logo
            except Exception:
                pass  # Skip logo if there's an error

        # Organization name in header
        org_name = self.branding.get('name') or self.metadata.get('organization', 'Versatex Analytics')
        canvas.setFont('Helvetica-Bold', 12)
        canvas.setFillColor(colors.white)
        canvas.drawString(header_x, page_height - 0.38 * inch, org_name)

        # Report type in header right
        report_type = self.metadata.get('report_type_display',
                                        self.metadata.get('report_type', 'Report'))
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(colors.white)
        canvas.drawRightString(page_width - 0.5 * inch, page_height - 0.38 * inch,
                               report_type)

        # =================== FOOTER ===================
        # Footer accent line
        canvas.setStrokeColor(self._get_hex_color(self.NAVY))
        canvas.setLineWidth(2)
        canvas.line(0.5 * inch, 0.55 * inch, page_width - 0.5 * inch, 0.55 * inch)

        # Page number (centered)
        page_num = canvas.getPageNumber()
        canvas.setFont('Helvetica-Bold', 9)
        canvas.setFillColor(self._get_hex_color(self.NAVY))
        canvas.drawCentredString(page_width / 2, 0.35 * inch, f"Page {page_num}")

        # Generation date (left)
        generated = self.metadata.get('generated_at', datetime.now().strftime('%Y-%m-%d'))
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(self._get_hex_color(self.GRAY_500))
        canvas.drawString(0.5 * inch, 0.35 * inch, f"Generated: {generated}")

        # Custom footer text or default confidential notice (right)
        footer_text = self.branding.get('footer') or "Confidential - Internal Use Only"
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(self._get_hex_color(self.GRAY_500))
        # Truncate if too long
        if len(footer_text) > 50:
            footer_text = footer_text[:47] + "..."
        canvas.drawRightString(page_width - 0.5 * inch, 0.35 * inch, footer_text)

        # Website URL if provided (very bottom, centered)
        website = self.branding.get('website')
        if website:
            canvas.setFont('Helvetica', 7)
            canvas.setFillColor(self._get_hex_color(self.BLUE))
            canvas.drawCentredString(page_width / 2, 0.2 * inch, website)

        canvas.restoreState()

    def _build_story(self):
        """Build the document story (content)."""
        story = []
        styles = self._get_styles()

        # Executive Header
        story.extend(self._create_executive_header(styles))
        story.append(Spacer(1, 20))

        # KPI Cards Section
        kpi_section = self._create_kpi_section(styles)
        if kpi_section:
            story.extend(kpi_section)
            story.append(Spacer(1, 20))

        # Charts Section
        charts_section = self._create_charts_section(styles)
        if charts_section:
            story.extend(charts_section)
            story.append(Spacer(1, 20))

        # Data Tables
        tables_section = self._create_data_tables_section(styles)
        if tables_section:
            story.extend(tables_section)

        # Recommendations/Action Plan
        recommendations = self._create_recommendations_section(styles)
        if recommendations:
            story.append(PageBreak())
            story.extend(recommendations)

        return story

    def _get_styles(self):
        """Create custom paragraph styles."""
        styles = getSampleStyleSheet()

        # Title style
        styles.add(ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=6,
            textColor=self._get_hex_color(self.NAVY),
            fontName='Helvetica-Bold'
        ))

        # Subtitle
        styles.add(ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=self._get_hex_color(self.GRAY_500),
            spaceAfter=20
        ))

        # Section Header
        styles.add(ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=12,
            textColor=self._get_hex_color(self.NAVY),
            fontName='Helvetica-Bold',
            borderPadding=(0, 0, 8, 0),
            borderWidth=0,
            borderColor=self._get_hex_color(self.BLUE)
        ))

        # Subsection Header
        styles.add(ParagraphStyle(
            'SubsectionHeader',
            parent=styles['Heading3'],
            fontSize=13,
            spaceBefore=15,
            spaceAfter=8,
            textColor=self._get_hex_color(self.GRAY_700),
            fontName='Helvetica-Bold'
        ))

        # Body text (using custom name to avoid conflict with default BodyText)
        styles.add(ParagraphStyle(
            'ReportBody',
            parent=styles['Normal'],
            fontSize=10,
            textColor=self._get_hex_color(self.GRAY_700),
            spaceAfter=8,
            leading=14
        ))

        # Highlight text
        styles.add(ParagraphStyle(
            'Highlight',
            parent=styles['Normal'],
            fontSize=10,
            textColor=self._get_hex_color(self.BLUE),
            fontName='Helvetica-Bold'
        ))

        return styles

    def _create_executive_header(self, styles):
        """Create executive summary header."""
        elements = []

        # Report title
        report_title = self.metadata.get('report_title', self.report_name)
        elements.append(Paragraph(report_title, styles['ReportTitle']))

        # Subtitle with metadata
        org_name = self.metadata.get('organization', 'N/A')
        period_start = self.metadata.get('period_start', 'N/A')
        period_end = self.metadata.get('period_end', 'N/A')

        subtitle_parts = [f"<b>Organization:</b> {org_name}"]
        if period_start != 'N/A' or period_end != 'N/A':
            subtitle_parts.append(f"<b>Period:</b> {period_start} to {period_end}")

        subtitle_text = " &nbsp;|&nbsp; ".join(subtitle_parts)
        elements.append(Paragraph(subtitle_text, styles['ReportSubtitle']))

        # Horizontal rule
        elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=self._get_hex_color(self.NAVY),
            spaceBefore=0,
            spaceAfter=15
        ))

        return elements

    def _create_kpi_section(self, styles):
        """Create KPI cards section."""
        overview = self.report_data.get('overview', {})
        if not overview:
            overview = self.report_data.get('summary', {})
        if not overview:
            overview = self.report_data.get('kpis', {})

        if not overview:
            return None

        elements = []
        elements.append(Paragraph("Key Performance Indicators", styles['SectionHeader']))

        # Create KPI cards
        kpi_cards = []
        card_colors = [self.BLUE, self.TEAL, self.GREEN, self.AMBER, self.NAVY, self.LIGHT_BLUE]

        for idx, (key, value) in enumerate(list(overview.items())[:6]):
            label = key.replace('_', ' ').title()

            # Format value
            if 'spend' in key.lower() or 'amount' in key.lower() or 'savings' in key.lower():
                formatted_value = self.format_currency(value)
            elif 'percentage' in key.lower() or 'rate' in key.lower():
                formatted_value = self.format_percentage(value)
            elif isinstance(value, (int, float)):
                formatted_value = self.format_number(value)
            else:
                formatted_value = str(value)

            accent = self._get_hex_color(card_colors[idx % len(card_colors)])
            kpi_cards.append(KPICard(
                label=label,
                value=formatted_value,
                width=160,
                height=75,
                accent_color=accent
            ))

        # Arrange cards in rows of 3
        rows = []
        for i in range(0, len(kpi_cards), 3):
            row_cards = kpi_cards[i:i+3]
            # Pad with empty cells if needed
            while len(row_cards) < 3:
                row_cards.append(Spacer(160, 75))
            rows.append(row_cards)

        if rows:
            kpi_table = Table(rows, colWidths=[170, 170, 170])
            kpi_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            elements.append(kpi_table)

        return elements

    def _create_charts_section(self, styles):
        """Create charts section with pie and bar charts."""
        elements = []

        # Try to find chartable data
        spend_by_category = self.report_data.get('spend_by_category', [])
        spend_by_supplier = self.report_data.get('spend_by_supplier', [])
        monthly_trend = self.report_data.get('monthly_trend', [])
        pareto_data = self.report_data.get('pareto_data', [])

        charts_added = False

        # Category pie chart
        if spend_by_category and len(spend_by_category) >= 2:
            elements.append(Paragraph("Spend Distribution by Category", styles['SectionHeader']))
            pie_chart = self._create_pie_chart(
                spend_by_category[:8],  # Top 8 categories
                label_key='category',
                value_key='spend'
            )
            if pie_chart:
                elements.append(pie_chart)
                elements.append(Spacer(1, 15))
                charts_added = True

        # Monthly trend bar chart
        if monthly_trend and len(monthly_trend) >= 2:
            elements.append(Paragraph("Monthly Spending Trend", styles['SectionHeader']))
            bar_chart = self._create_bar_chart(
                monthly_trend[:12],  # Last 12 months
                label_key='month',
                value_key='spend'
            )
            if bar_chart:
                elements.append(bar_chart)
                elements.append(Spacer(1, 15))
                charts_added = True

        # Pareto analysis - supplier concentration
        if pareto_data and len(pareto_data) >= 2:
            if not charts_added or len(elements) < 5:
                elements.append(Paragraph("Supplier Concentration (Pareto)", styles['SectionHeader']))
                pareto_chart = self._create_pareto_chart(pareto_data[:10])
                if pareto_chart:
                    elements.append(pareto_chart)
                    charts_added = True

        return elements if charts_added else None

    def _create_pie_chart(self, data, label_key='name', value_key='value'):
        """Create a professional pie chart."""
        if not data:
            return None

        try:
            drawing = Drawing(500, 250)

            # Create pie
            pie = Pie()
            pie.x = 100
            pie.y = 25
            pie.width = 180
            pie.height = 180

            # Extract data
            labels = []
            values = []
            for item in data:
                label = item.get(label_key, item.get('name', item.get('category', 'Unknown')))
                value = item.get(value_key, item.get('amount', item.get('spend', 0)))
                if isinstance(label, str) and len(label) > 20:
                    label = label[:18] + '...'
                labels.append(label)
                values.append(float(value) if value else 0)

            if not values or sum(values) == 0:
                return None

            pie.data = values
            pie.labels = labels

            # Style the pie
            pie.slices.strokeWidth = 1
            pie.slices.strokeColor = colors.white

            for i, _ in enumerate(data):
                color_hex = self.CHART_COLORS[i % len(self.CHART_COLORS)]
                pie.slices[i].fillColor = self._get_hex_color(color_hex)

            pie.sideLabels = True
            pie.simpleLabels = False
            pie.slices.fontName = 'Helvetica'
            pie.slices.fontSize = 8
            pie.slices.labelRadius = 1.3

            drawing.add(pie)

            # Add legend
            legend = Legend()
            legend.x = 320
            legend.y = 150
            legend.dx = 8
            legend.dy = 8
            legend.fontName = 'Helvetica'
            legend.fontSize = 8
            legend.boxAnchor = 'nw'
            legend.columnMaximum = 8
            legend.strokeWidth = 0.5
            legend.strokeColor = self._get_hex_color(self.GRAY_200)
            legend.deltax = 75
            legend.deltay = 10
            legend.autoXPadding = 5
            legend.yGap = 0
            legend.dxTextSpace = 5
            legend.alignment = 'right'
            legend.dividerLines = 1|2|4
            legend.dividerOffsY = 4.5
            legend.subCols.rpad = 30

            # Add legend entries
            legend_items = []
            total = sum(values)
            for i, (label, value) in enumerate(zip(labels, values)):
                pct = (value / total * 100) if total > 0 else 0
                color_hex = self.CHART_COLORS[i % len(self.CHART_COLORS)]
                legend_items.append((self._get_hex_color(color_hex), f"{label} ({pct:.1f}%)"))

            legend.colorNamePairs = legend_items
            drawing.add(legend)

            return drawing
        except Exception as e:
            # Return None if chart creation fails
            return None

    def _create_bar_chart(self, data, label_key='month', value_key='spend'):
        """Create a professional bar chart."""
        if not data:
            return None

        try:
            drawing = Drawing(500, 200)

            bc = VerticalBarChart()
            bc.x = 50
            bc.y = 50
            bc.height = 125
            bc.width = 400

            # Extract data
            labels = []
            values = []
            for item in data:
                label = item.get(label_key, item.get('name', ''))
                value = item.get(value_key, item.get('amount', 0))
                # Shorten month labels
                if isinstance(label, str) and len(label) > 7:
                    label = label[:7]
                labels.append(label)
                values.append(float(value) if value else 0)

            if not values:
                return None

            bc.data = [values]
            bc.categoryAxis.categoryNames = labels

            # Style
            bc.bars[0].fillColor = self._get_hex_color(self.BLUE)
            bc.bars[0].strokeColor = self._get_hex_color(self.NAVY)
            bc.bars[0].strokeWidth = 0.5

            bc.valueAxis.valueMin = 0
            bc.valueAxis.valueMax = max(values) * 1.1 if values else 100
            bc.valueAxis.valueStep = max(values) / 5 if values and max(values) > 0 else 20

            bc.categoryAxis.labels.boxAnchor = 'ne'
            bc.categoryAxis.labels.dx = -5
            bc.categoryAxis.labels.dy = -2
            bc.categoryAxis.labels.angle = 30
            bc.categoryAxis.labels.fontName = 'Helvetica'
            bc.categoryAxis.labels.fontSize = 7

            bc.valueAxis.labels.fontName = 'Helvetica'
            bc.valueAxis.labels.fontSize = 8

            bc.barWidth = 20
            bc.groupSpacing = 10

            drawing.add(bc)

            return drawing
        except Exception as e:
            return None

    def _create_pareto_chart(self, data):
        """Create a Pareto analysis visualization."""
        if not data or len(data) < 2:
            return None

        try:
            drawing = Drawing(500, 200)

            bc = VerticalBarChart()
            bc.x = 50
            bc.y = 50
            bc.height = 120
            bc.width = 400

            # Extract supplier names and spend
            labels = []
            values = []
            for item in data:
                name = item.get('supplier', item.get('name', 'Unknown'))
                spend = item.get('spend', item.get('amount', 0))
                if isinstance(name, str) and len(name) > 15:
                    name = name[:13] + '...'
                labels.append(name)
                values.append(float(spend) if spend else 0)

            if not values:
                return None

            bc.data = [values]
            bc.categoryAxis.categoryNames = labels

            # Gradient-like coloring (darker for top suppliers)
            for i in range(len(values)):
                intensity = 1 - (i / len(values)) * 0.5
                r = int(37 * intensity)
                g = int(99 * intensity)
                b = int(235 * intensity)
                bc.bars[0].fillColor = colors.Color(r/255, g/255, b/255)

            bc.bars[0].fillColor = self._get_hex_color(self.BLUE)
            bc.categoryAxis.labels.angle = 45
            bc.categoryAxis.labels.boxAnchor = 'ne'
            bc.categoryAxis.labels.fontSize = 7
            bc.categoryAxis.labels.fontName = 'Helvetica'
            bc.valueAxis.labels.fontSize = 8
            bc.barWidth = 25

            drawing.add(bc)

            return drawing
        except Exception as e:
            return None

    def _create_data_tables_section(self, styles):
        """Create data tables section."""
        elements = []

        # Map of data keys to section titles
        data_sections = {
            'spend_by_category': ('Spend by Category', 15),
            'spend_by_supplier': ('Top Suppliers by Spend', 15),
            'top_suppliers': ('Supplier Analysis', 15),
            'top_categories': ('Category Analysis', 15),
            'monthly_trend': ('Monthly Spending Details', 12),
            'pareto_data': ('Pareto Analysis Details', 15),
            'tail_suppliers': ('Tail Spend Suppliers', 20),
            'consolidation_opportunities': ('Consolidation Opportunities', 10),
            'stratification': ('Spend Stratification', 10),
            'compliance_summary': ('Compliance Summary', 10),
            'violations': ('Policy Violations', 15),
            'savings_by_type': ('Savings by Type', 10),
        }

        tables_added = 0

        for key, (title, max_rows) in data_sections.items():
            data = self.report_data.get(key, [])
            if data and isinstance(data, list) and len(data) > 0:
                # Add page break every 2-3 tables to prevent overflow
                if tables_added > 0 and tables_added % 2 == 0:
                    elements.append(PageBreak())

                elements.append(Paragraph(title, styles['SectionHeader']))
                table = self._create_styled_data_table(data[:max_rows])
                if table:
                    elements.append(table)
                    elements.append(Spacer(1, 15))
                    tables_added += 1

        return elements if tables_added > 0 else None

    def _create_styled_data_table(self, data):
        """Create a professionally styled data table."""
        if not data or not isinstance(data[0], dict):
            return None

        # Get headers
        headers = list(data[0].keys())

        # Identify text columns for wrapping
        text_columns = set()
        for i, header in enumerate(headers):
            h_lower = header.lower()
            if not any(kw in h_lower for kw in ['amount', 'count', 'percentage', 'avg', 'total', 'spend', 'savings', 'rate', 'pct']):
                text_columns.add(i)

        # Create paragraph style for table cells
        cell_style = ParagraphStyle(
            'TableCell',
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=self._get_hex_color(self.GRAY_700)
        )

        # Format header names
        header_row = [h.replace('_', ' ').title() for h in headers]
        table_data = [header_row]

        # Add data rows
        for item in data:
            row = []
            for col_idx, header in enumerate(headers):
                value = item.get(header, '')

                # Format based on field type
                if 'amount' in header.lower() or 'spend' in header.lower() or 'savings' in header.lower():
                    row.append(self.format_currency(value))
                elif 'percentage' in header.lower() or 'rate' in header.lower() or 'pct' in header.lower():
                    row.append(self.format_percentage(value))
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    row.append(self.format_number(value, 2 if isinstance(value, float) else 0))
                else:
                    str_value = str(value) if value is not None else ''
                    # For text columns, use Paragraph for wrapping
                    if col_idx in text_columns and len(str_value) > 30:
                        row.append(Paragraph(str_value, cell_style))
                    else:
                        row.append(str_value[:45] + '...' if len(str_value) > 45 else str_value)

            table_data.append(row)

        # Calculate column widths based on column type
        num_cols = len(headers)
        available_width = 7.0 * inch  # Total available width

        # Identify text-heavy vs numeric columns
        col_widths = []
        text_col_indices = []
        numeric_col_indices = []

        for i, header in enumerate(headers):
            h_lower = header.lower()
            # Numeric columns typically have these keywords
            if any(kw in h_lower for kw in ['amount', 'count', 'percentage', 'avg', 'total', 'spend', 'savings', 'rate', 'pct']):
                numeric_col_indices.append(i)
            else:
                text_col_indices.append(i)

        # Allocate widths: text columns get 2x weight vs numeric
        total_weight = len(text_col_indices) * 2.0 + len(numeric_col_indices) * 1.0
        text_col_width = (available_width / total_weight) * 2.0
        numeric_col_width = (available_width / total_weight) * 1.0

        # Ensure minimum widths
        text_col_width = max(text_col_width, 1.5 * inch)
        numeric_col_width = max(numeric_col_width, 0.8 * inch)

        for i in range(num_cols):
            if i in text_col_indices:
                col_widths.append(text_col_width)
            else:
                col_widths.append(numeric_col_width)

        # Create table
        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Apply professional styling
        style_commands = [
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), self._get_hex_color(self.NAVY)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Data row styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

            # Grid styling
            ('LINEBELOW', (0, 0), (-1, 0), 2, self._get_hex_color(self.BLUE)),
            ('LINEBELOW', (0, 1), (-1, -1), 0.5, self._get_hex_color(self.GRAY_200)),
            ('LINEBEFORE', (0, 0), (0, -1), 0.5, self._get_hex_color(self.GRAY_200)),
            ('LINEAFTER', (-1, 0), (-1, -1), 0.5, self._get_hex_color(self.GRAY_200)),
        ]

        # Alternating row colors
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                style_commands.append(
                    ('BACKGROUND', (0, i), (-1, i), self._get_hex_color(self.GRAY_50))
                )

        table.setStyle(TableStyle(style_commands))

        return table

    def _create_recommendations_section(self, styles):
        """Create recommendations/action plan section."""
        action_plan = self.report_data.get('action_plan', [])
        recommendations = self.report_data.get('recommendations', [])
        items = action_plan or recommendations

        if not items:
            return None

        elements = []
        elements.append(Paragraph("Recommendations & Action Plan", styles['SectionHeader']))

        # Create a visually appealing recommendations list
        for i, item in enumerate(items[:10], 1):
            if isinstance(item, dict):
                action = item.get('action', item.get('recommendation', item.get('title', '')))
                description = item.get('description', item.get('details', ''))
                priority = item.get('priority', '')
                savings = item.get('potential_savings', item.get('savings', ''))

                # Priority badge color
                priority_colors = {
                    'high': self.RED,
                    'medium': self.AMBER,
                    'low': self.GREEN
                }
                priority_color = priority_colors.get(str(priority).lower(), self.BLUE)

                # Build recommendation text
                rec_text = f"<b>{i}. {action}</b>"
                if priority:
                    rec_text += f' <font color="{priority_color}">[{priority.upper()}]</font>'

                elements.append(Paragraph(rec_text, styles['ReportBody']))

                if description:
                    elements.append(Paragraph(
                        f"&nbsp;&nbsp;&nbsp;&nbsp;{description}",
                        styles['ReportBody']
                    ))

                if savings:
                    savings_text = self.format_currency(savings) if isinstance(savings, (int, float)) else str(savings)
                    elements.append(Paragraph(
                        f"&nbsp;&nbsp;&nbsp;&nbsp;<font color=\"{self.GREEN}\">Potential Savings: {savings_text}</font>",
                        styles['Highlight']
                    ))

                elements.append(Spacer(1, 8))
            else:
                elements.append(Paragraph(f"<b>{i}.</b> {item}", styles['ReportBody']))
                elements.append(Spacer(1, 4))

        return elements
