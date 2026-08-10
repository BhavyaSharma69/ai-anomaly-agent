"""report_pdf.py - assembles the anomaly_agent output + charts into a polished PDF report."""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
)

from anomaly_agent import build_report
from make_charts import render_charts


def generate_pdf(data_path="business_metrics.xlsx", output_path="anomaly_report.pdf"):
    report = build_report(data_path)
    chart_paths = render_charts(data_path)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontSize=20,
                                  textColor=colors.HexColor("#111827"))
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=10,
                                     textColor=colors.HexColor("#6b7280"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, spaceBefore=14,
                         spaceAfter=6, textColor=colors.HexColor("#111827"))
    body = ParagraphStyle("BodyCustom", parent=styles["Normal"], fontSize=10, leading=15)
    note_style = ParagraphStyle("Note", parent=styles["Normal"], fontSize=10, leading=15,
                                 textColor=colors.HexColor("#1e3a8a"),
                                 backColor=colors.HexColor("#eff6ff"),
                                 borderPadding=8, spaceBefore=4, spaceAfter=4)

    severity_color = {"high": colors.HexColor("#dc2626"), "moderate": colors.HexColor("#d97706")}

    doc = SimpleDocTemplate(output_path, pagesize=letter,
                             topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                             leftMargin=0.7 * inch, rightMargin=0.7 * inch)
    story = []

    # --- Header ---
    story.append(Paragraph("Business KPI Anomaly Report", title_style))
    story.append(Paragraph(
        f"Generated {report['generated_at'].strftime('%B %d, %Y at %I:%M %p')} &nbsp;|&nbsp; "
        f"Data through {report['report_date'].strftime('%B %d, %Y')} &nbsp;|&nbsp; "
        f"{report['rows_analyzed']} days analyzed &nbsp;|&nbsp; "
        f"Source: business_metrics.xlsx",
        subtitle_style
    ))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#e5e7eb"), thickness=1))
    story.append(Spacer(1, 10))

    # --- Status banner ---
    status_color = colors.HexColor("#dc2626") if report["anomalies"] else colors.HexColor("#16a34a")
    status_text = f"STATUS: {report['status']} — {len(report['anomalies'])} flagged in the last {report['lookback_days']} days"
    story.append(Paragraph(f'<font color="{status_color}"><b>{status_text}</b></font>',
                            ParagraphStyle("Status", parent=body, fontSize=12)))
    story.append(Spacer(1, 8))

    # --- Summary table ---
    story.append(Paragraph("Summary of Flagged Anomalies", h2))
    table_data = [["Date", "Metric", "Value", "vs. Baseline", "Severity"]]
    for a in report["anomalies"]:
        pct = (a.value - a.baseline_mean) / a.baseline_mean * 100
        table_data.append([
            a.date.strftime("%b %d"),
            a.metric.replace("_", " ").title(),
            f"{a.value:,.2f}",
            f"{pct:+.1f}%",
            a.severity.upper(),
        ])

    t = Table(table_data, colWidths=[0.8 * inch, 1.5 * inch, 1.2 * inch, 1.1 * inch, 1 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
    ]))
    for i, a in enumerate(report["anomalies"], start=1):
        t.setStyle(TableStyle([("TEXTCOLOR", (4, i), (4, i), severity_color.get(a.severity, colors.black))]))
    story.append(t)
    story.append(Spacer(1, 12))

    # --- Explanations ---
    story.append(Paragraph("What Changed (Plain-English Summary)", h2))
    for a in report["anomalies"]:
        bullet = f"<b>{a.date.strftime('%b %d')} — {a.metric.replace('_',' ').title()}:</b> {a.explanation}"
        story.append(Paragraph(bullet, body))
        story.append(Spacer(1, 4))

    if report["cross_reference_notes"]:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Analyst Notes", h2))
        for d, note in report["cross_reference_notes"].items():
            story.append(Paragraph(f"<b>{d.strftime('%b %d')}:</b> {note}", note_style))
            story.append(Spacer(1, 6))

    # --- Charts ---
    story.append(Spacer(1, 10))
    story.append(Paragraph("Trend Charts (last 60 days, anomalies marked in red)", h2))
    for path in chart_paths:
        story.append(Image(path, width=6.2 * inch, height=2.6 * inch))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#e5e7eb"), thickness=1))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Generated automatically by the AI Anomaly Agent · Detection method: rolling 14-day "
        "z-score baseline · This report was also sent via automated email alert.",
        subtitle_style
    ))

    doc.build(story)
    print(f"PDF report saved to {output_path}")


if __name__ == "__main__":
    generate_pdf()
