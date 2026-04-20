"""
Generate professionally formatted PDF from Management Introduction
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from datetime import datetime

NAVY = colors.HexColor("#1e3a5f")
TEAL = colors.HexColor("#0d9488")
LIGHT_GRAY = colors.HexColor("#f8fafc")
DARK_GRAY = colors.HexColor("#334155")


def create_header_footer(canvas, doc):
    canvas.saveState()

    canvas.setFillColor(NAVY)
    canvas.rect(0, letter[1] - 50, letter[0], 50, fill=True, stroke=False)

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(40, letter[1] - 32, "Versatex Analytics")

    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(letter[0] - 40, letter[1] - 32, "Enterprise Procurement Analytics")

    canvas.setFillColor(DARK_GRAY)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(40, 30, f"Versatex / Defoxx Analytics")
    canvas.drawCentredString(letter[0]/2, 30, f"Page {doc.page}")
    canvas.drawRightString(letter[0] - 40, 30, datetime.now().strftime("%B %Y"))

    canvas.setStrokeColor(TEAL)
    canvas.setLineWidth(2)
    canvas.line(40, 45, letter[0] - 40, 45)

    canvas.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        "Versatex_Analytics_Management_Introduction.pdf",
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=70,
        bottomMargin=60
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='CoverTitle',
        parent=styles['Title'],
        fontSize=32,
        textColor=NAVY,
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='CoverSubtitle',
        parent=styles['Normal'],
        fontSize=18,
        textColor=TEAL,
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica'
    ))

    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=NAVY,
        spaceBefore=20,
        spaceAfter=12,
        fontName='Helvetica-Bold',
        borderPadding=(0, 0, 5, 0),
    ))

    styles.add(ParagraphStyle(
        name='ModuleTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=TEAL,
        spaceBefore=15,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='SubHeading',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=DARK_GRAY,
        spaceBefore=8,
        spaceAfter=4,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='Body',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK_GRAY,
        spaceBefore=4,
        spaceAfter=4,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    ))

    styles.add(ParagraphStyle(
        name='BulletText',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK_GRAY,
        leftIndent=20,
        spaceBefore=2,
        spaceAfter=2,
        fontName='Helvetica'
    ))

    styles.add(ParagraphStyle(
        name='ValueProp',
        parent=styles['Normal'],
        fontSize=10,
        textColor=NAVY,
        spaceBefore=6,
        spaceAfter=8,
        fontName='Helvetica-Oblique',
        leftIndent=10,
        borderColor=TEAL,
        borderWidth=2,
        borderPadding=8,
    ))

    story = []

    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("Versatex Analytics", styles['CoverTitle']))
    story.append(Paragraph("Enterprise Procurement Analytics Platform", styles['CoverSubtitle']))
    story.append(Spacer(1, 0.5*inch))
    story.append(HRFlowable(width="60%", thickness=3, color=TEAL, spaceBefore=20, spaceAfter=20))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Senior Management Introduction", styles['CoverSubtitle']))
    story.append(Spacer(1, 2*inch))

    cover_data = [
        ["Prepared by:", "Versatex / Defoxx Analytics"],
        ["Date:", datetime.now().strftime("%B %Y")],
        ["Version:", "1.0"],
    ]
    cover_table = Table(cover_data, colWidths=[1.5*inch, 3*inch])
    cover_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), DARK_GRAY),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(cover_table)

    story.append(PageBreak())

    story.append(Paragraph("Executive Summary", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceBefore=0, spaceAfter=15))

    story.append(Paragraph(
        "<b>Versatex Analytics</b> is an enterprise-grade procurement analytics platform designed to "
        "transform raw procurement data into actionable insights. The platform provides comprehensive "
        "visibility into organizational spending, supplier relationships, and procure-to-pay processes.",
        styles['Body']
    ))

    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Key Value Propositions:", styles['SubHeading']))

    value_props = [
        "Centralized spend visibility across all categories and suppliers",
        "AI-powered recommendations with measurable ROI tracking",
        "End-to-end procure-to-pay process analytics",
        "Automated reporting with customizable scheduling"
    ]
    for prop in value_props:
        story.append(Paragraph(f"• {prop}", styles['BulletText']))

    story.append(PageBreak())

    story.append(Paragraph("1. Core Procurement Dashboard", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceBefore=0, spaceAfter=15))

    modules_core = [
        {
            "name": "Overview Dashboard",
            "purpose": "Executive-level snapshot of procurement health",
            "features": [
                "Real-time KPI cards (Total Spend, Supplier Count, Transaction Volume)",
                "Interactive charts: Spend by Category, Spend by Supplier, Monthly Trends",
                "Drill-down capability - click any chart segment for detailed breakdowns",
                "Date range filtering with quick presets (Last 30/90 days, YTD)"
            ],
            "value": "Single-pane view for executives to monitor procurement performance at a glance"
        },
        {
            "name": "Categories Module",
            "purpose": "Analyze spending by procurement category",
            "features": [
                "Category hierarchy visualization",
                "Subcategory breakdown analysis",
                "Supplier distribution per category",
                "Risk scoring and concentration analysis"
            ],
            "value": "Identify category-level savings opportunities and consolidation targets"
        },
        {
            "name": "Suppliers Module",
            "purpose": "Supplier portfolio management and risk assessment",
            "features": [
                "HHI (Herfindahl-Hirschman Index) concentration risk indicators",
                "Supplier ranking by spend volume",
                "Performance metrics and scorecards",
                "Search and filtering capabilities"
            ],
            "value": "Mitigate supplier risk, identify strategic vs. tactical suppliers"
        }
    ]

    for module in modules_core:
        story.append(Paragraph(module["name"], styles['ModuleTitle']))
        story.append(Paragraph(f"<b>Purpose:</b> {module['purpose']}", styles['Body']))
        story.append(Paragraph("<b>Key Features:</b>", styles['SubHeading']))
        for feature in module["features"]:
            story.append(Paragraph(f"• {feature}", styles['BulletText']))
        story.append(Paragraph(f"<i>Business Value: {module['value']}</i>", styles['ValueProp']))
        story.append(Spacer(1, 0.1*inch))

    story.append(PageBreak())

    story.append(Paragraph("2. Advanced Spend Analytics", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceBefore=0, spaceAfter=15))

    modules_analytics = [
        {
            "name": "Pareto Analysis",
            "purpose": "Apply 80/20 rule to supplier base",
            "features": [
                "Cumulative spend visualization",
                "Supplier classification: Critical (80%), Important (15%), Tail (5%)",
                "Drill-down to individual supplier details"
            ],
            "value": "Focus negotiation efforts on high-impact suppliers"
        },
        {
            "name": "Spend Stratification",
            "purpose": "Kraljic matrix-style spend segmentation",
            "features": [
                "Four segments: Strategic, Leverage, Routine, Tactical",
                "Spend band analysis ($0-10K, $10K-50K, $50K-100K, $100K+)",
                "Category and supplier drill-downs"
            ],
            "value": "Develop category-specific procurement strategies"
        },
        {
            "name": "Seasonality Analysis",
            "purpose": "Identify spending patterns across time",
            "features": [
                "Monthly spending heatmap",
                "Seasonal index calculations",
                "Peak/trough identification",
                "Fiscal vs. calendar year toggle"
            ],
            "value": "Optimize procurement timing and budget planning"
        },
        {
            "name": "Year-over-Year Comparison",
            "purpose": "Compare spending trends across years",
            "features": [
                "Dual-year variance analysis",
                "Top gainers and decliners identification",
                "Category and supplier drill-downs"
            ],
            "value": "Track procurement efficiency improvements over time"
        },
        {
            "name": "Tail Spend Analysis",
            "purpose": "Identify fragmented, low-value spending",
            "features": [
                "Adjustable threshold slider for tail classification",
                "Vendor fragmentation metrics",
                "Consolidation opportunity identification"
            ],
            "value": "Reduce administrative overhead, consolidate vendor base"
        }
    ]

    for module in modules_analytics:
        story.append(Paragraph(module["name"], styles['ModuleTitle']))
        story.append(Paragraph(f"<b>Purpose:</b> {module['purpose']}", styles['Body']))
        story.append(Paragraph("<b>Key Features:</b>", styles['SubHeading']))
        for feature in module["features"]:
            story.append(Paragraph(f"• {feature}", styles['BulletText']))
        story.append(Paragraph(f"<i>Business Value: {module['value']}</i>", styles['ValueProp']))
        story.append(Spacer(1, 0.1*inch))

    story.append(PageBreak())

    story.append(Paragraph("3. AI & Predictive Analytics", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceBefore=0, spaceAfter=15))

    story.append(Paragraph("AI Insights", styles['ModuleTitle']))
    story.append(Paragraph("<b>Purpose:</b> AI-powered recommendations and ROI tracking", styles['Body']))
    story.append(Paragraph("<b>Key Features:</b>", styles['SubHeading']))
    story.append(Paragraph("• <b>Insights Tab:</b> Cost optimization, supplier risk alerts, anomaly detection, consolidation opportunities", styles['BulletText']))
    story.append(Paragraph("• <b>ROI Tracking Tab:</b> Track actions taken, measure actual vs. projected savings, action history", styles['BulletText']))
    story.append(Paragraph("<i>Business Value: Data-driven decision support with measurable outcomes</i>", styles['ValueProp']))
    story.append(Spacer(1, 0.15*inch))

    story.append(Paragraph("Predictive Analytics", styles['ModuleTitle']))
    story.append(Paragraph("<b>Purpose:</b> Forecast future spending patterns", styles['Body']))
    story.append(Paragraph("<b>Key Features:</b>", styles['SubHeading']))
    story.append(Paragraph("• Spend prediction models with confidence intervals", styles['BulletText']))
    story.append(Paragraph("• Demand forecasting and model accuracy metrics", styles['BulletText']))
    story.append(Paragraph("<i>Business Value: Improve budgeting accuracy and cash flow planning</i>", styles['ValueProp']))

    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph("4. Risk & Compliance", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceBefore=0, spaceAfter=15))

    story.append(Paragraph("Contract Optimization", styles['ModuleTitle']))
    story.append(Paragraph("<b>Purpose:</b> Maximize contract value and coverage", styles['Body']))
    story.append(Paragraph("• Contract portfolio overview with utilization tracking", styles['BulletText']))
    story.append(Paragraph("• Expiration alerts and category breakdown per contract", styles['BulletText']))
    story.append(Paragraph("<i>Business Value: Reduce off-contract spending, improve contract leverage</i>", styles['ValueProp']))
    story.append(Spacer(1, 0.15*inch))

    story.append(Paragraph("Maverick Spend", styles['ModuleTitle']))
    story.append(Paragraph("<b>Purpose:</b> Identify and resolve policy violations", styles['Body']))
    story.append(Paragraph("• Policy violation listing with batch resolution capability", styles['BulletText']))
    story.append(Paragraph("• Notes/documentation tracking and trend analysis", styles['BulletText']))
    story.append(Paragraph("<i>Business Value: Enforce procurement policies, reduce compliance risk</i>", styles['ValueProp']))

    story.append(PageBreak())

    story.append(Paragraph("5. Procure-to-Pay (P2P) Analytics", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceBefore=0, spaceAfter=15))

    p2p_modules = [
        ("P2P Cycle Analysis", "End-to-end process visibility",
         "Full cycle timing (PR→PO→GR→Invoice→Payment), bottleneck identification, process funnel",
         "Reduce cycle times, improve operational efficiency"),
        ("3-Way Matching", "Invoice accuracy and exception management",
         "PO vs. GR vs. Invoice matching, exception dashboard, variance analysis",
         "Prevent overpayments, reduce invoice disputes"),
        ("Invoice Aging", "Accounts payable management",
         "Aging buckets (Current, 31-60, 61-90, 90+ days), DPO trends, cash flow forecasting",
         "Optimize working capital, maintain supplier relationships"),
        ("Requisitions", "Purchase requisition workflow analysis",
         "PR volume/trends, approval rate tracking, rejection analysis by department",
         "Streamline approval processes, reduce cycle times"),
        ("Purchase Orders", "PO compliance and efficiency",
         "Contract coverage metrics, maverick spend identification, amendment patterns",
         "Improve PO compliance, reduce amendments"),
        ("Supplier Payments", "Payment performance management",
         "Supplier payment scorecards, on-time tracking, risk level indicators",
         "Maintain supplier relationships, capture early payment discounts")
    ]

    for name, purpose, features, value in p2p_modules:
        story.append(Paragraph(name, styles['ModuleTitle']))
        story.append(Paragraph(f"<b>Purpose:</b> {purpose}", styles['Body']))
        story.append(Paragraph(f"• {features}", styles['BulletText']))
        story.append(Paragraph(f"<i>Business Value: {value}</i>", styles['ValueProp']))
        story.append(Spacer(1, 0.08*inch))

    story.append(PageBreak())

    story.append(Paragraph("6. Reporting & Administration", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceBefore=0, spaceAfter=15))

    story.append(Paragraph("Reports Module", styles['ModuleTitle']))
    story.append(Paragraph("<b>Purpose:</b> Automated report generation and scheduling", styles['Body']))
    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph("<b>14+ Report Types Available:</b>", styles['SubHeading']))

    report_data = [
        ["Executive Summary", "Spend Analysis", "Supplier Performance"],
        ["Pareto Analysis", "Contract Compliance", "Savings Opportunities"],
        ["Spend Stratification", "Seasonality & Trends", "Year-over-Year"],
        ["Tail Spend", "PR Status (P2P)", "PO Compliance (P2P)"],
        ["AP Aging (P2P)", "", ""]
    ]

    report_table = Table(report_data, colWidths=[2*inch, 2*inch, 2*inch])
    report_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), DARK_GRAY),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
    ]))
    story.append(report_table)
    story.append(Spacer(1, 0.15*inch))

    story.append(Paragraph("• <b>Output Formats:</b> PDF, Excel, CSV", styles['BulletText']))
    story.append(Paragraph("• <b>Scheduling:</b> Daily, Weekly, Monthly, Quarterly", styles['BulletText']))
    story.append(Paragraph("• <b>Branding:</b> Organization logo, colors, custom footer", styles['BulletText']))
    story.append(Paragraph("<i>Business Value: Standardized reporting, reduced manual effort</i>", styles['ValueProp']))

    story.append(PageBreak())

    story.append(Paragraph("Platform Capabilities", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceBefore=0, spaceAfter=15))

    story.append(Paragraph("Security & Access Control", styles['ModuleTitle']))
    story.append(Paragraph("• <b>Role-Based Access:</b> Admin, Manager, Viewer roles with appropriate permissions", styles['BulletText']))
    story.append(Paragraph("• <b>Multi-Organization Support:</b> Users can belong to multiple organizations", styles['BulletText']))
    story.append(Paragraph("• <b>Audit Logging:</b> Track all user actions for compliance", styles['BulletText']))

    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph("User Experience", styles['ModuleTitle']))
    story.append(Paragraph("• <b>Responsive Design:</b> Works on desktop, tablet, and mobile", styles['BulletText']))
    story.append(Paragraph("• <b>Dark/Light Mode:</b> Customizable visual theme", styles['BulletText']))
    story.append(Paragraph("• <b>Real-Time Updates:</b> Automatic data refresh", styles['BulletText']))
    story.append(Paragraph("• <b>Saved Filters:</b> Save and reuse common filter combinations", styles['BulletText']))

    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph("Summary by User Role", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceBefore=0, spaceAfter=15))

    role_data = [
        ["Role", "Primary Modules"],
        ["Executive", "Overview, AI Insights, Reports"],
        ["Procurement Manager", "Pareto, Stratification, Contracts, Maverick"],
        ["Category Manager", "Categories, Suppliers, Tail Spend"],
        ["AP/Finance", "Invoice Aging, 3-Way Matching, Supplier Payments"],
        ["Operations", "P2P Cycle, Requisitions, Purchase Orders"]
    ]

    role_table = Table(role_data, colWidths=[2*inch, 4*inch])
    role_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), DARK_GRAY),
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_GRAY),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_GRAY, colors.white]),
    ]))
    story.append(role_table)

    story.append(Spacer(1, 0.4*inch))

    story.append(Paragraph("Next Steps", styles['SectionTitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceBefore=0, spaceAfter=15))

    next_steps = [
        ("<b>1. Demo Session</b> — Schedule hands-on walkthrough of key modules"),
        ("<b>2. Data Requirements</b> — Identify data sources for initial load"),
        ("<b>3. User Provisioning</b> — Define roles and access levels"),
        ("<b>4. Report Templates</b> — Customize report branding and schedules")
    ]

    for step in next_steps:
        story.append(Paragraph(step, styles['Body']))
        story.append(Spacer(1, 0.08*inch))

    doc.build(story, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
    print("PDF generated: Versatex_Analytics_Management_Introduction.pdf")


if __name__ == "__main__":
    build_pdf()
