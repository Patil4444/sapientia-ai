"""
Generates OSHA-style PDF incident reports using ReportLab.
Produces a professional, field-ready document.
"""
import os
import io
from datetime import datetime
from collections import Counter
import math

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, HRFlowable)
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# Brand colors
ORANGE = colors.HexColor("#FF6B00")
DARK   = colors.HexColor("#0f0f0f")
LIGHT  = colors.HexColor("#f5f2ed")
RED    = colors.HexColor("#FF1744")
GREEN  = colors.HexColor("#2E7D32")
GRAY   = colors.HexColor("#888888")
WHITE  = colors.white
BLACK  = colors.black


def generate_incident_report(incident: dict) -> bytes:
    """Generate a PDF report and return bytes."""
    from utils.http_api import client_api_base

    base = client_api_base()
    # When the FastAPI server runs with SAPIENTIA_API_URL set, skip HTTP (avoid calling self).
    if base and os.environ.get("SAPIENTIA_IS_PDF_WORKER") != "1":
        import httpx

        try:
            r = httpx.post(f"{base}/api/reports/incident-pdf", json=incident, timeout=120.0)
            r.raise_for_status()
            return r.content
        except httpx.RequestError as e:
            raise RuntimeError(
                f"Backend PDF API unreachable at {base!r}. Clear **Backend base URL** in Settings "
                "to generate PDFs locally with ReportLab, or start the FastAPI server."
            ) from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Backend PDF API returned {e.response.status_code} for {base!r}. "
                "Check the server or clear the backend URL in Settings to use local ReportLab."
            ) from e

    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab not installed. Run: pip install reportlab")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    story  = []

    # ---- Custom styles ----
    mono_bold = ParagraphStyle("mono_bold", fontName="Courier-Bold",   fontSize=9,  textColor=BLACK)
    mono_reg  = ParagraphStyle("mono_reg",  fontName="Courier",        fontSize=9,  textColor=BLACK)
    label_s   = ParagraphStyle("label",     fontName="Helvetica-Bold", fontSize=8,  textColor=GRAY,  spaceAfter=1)
    value_s   = ParagraphStyle("value",     fontName="Helvetica",      fontSize=10, textColor=BLACK)
    section_s = ParagraphStyle("section",   fontName="Helvetica-Bold", fontSize=11, textColor=WHITE, spaceAfter=4)
    sub_s     = ParagraphStyle("sub",       fontName="Helvetica",      fontSize=9,  textColor=GRAY)
    body_s    = ParagraphStyle("body",      fontName="Helvetica",      fontSize=9,  textColor=BLACK, leading=14)
    action_s  = ParagraphStyle("action",    fontName="Helvetica",      fontSize=9,  textColor=BLACK, leftIndent=10, leading=14)

    analysis = incident.get("analysis", {})
    severity = analysis.get("severity", "LOW")
    sev_color = {"CRITICAL": RED, "MEDIUM": ORANGE, "LOW": GREEN}.get(severity, GRAY)

    # ======================================================
    # HEADER BLOCK
    # ======================================================
    header_data = [[
        Paragraph("<b>CONSTRUCTSAFE AI</b>", ParagraphStyle("hd", fontName="Courier-Bold", fontSize=16, textColor=ORANGE)),
        Paragraph(
            f"<b>CONSTRUCTION SAFETY INCIDENT REPORT</b><br/>"
            f"<font size=8 color='#888888'>OSHA 300/301 Recordkeeping Format</font>",
            ParagraphStyle("hd2", fontName="Helvetica-Bold", fontSize=13, textColor=BLACK, alignment=TA_RIGHT)
        )
    ]]
    header_table = Table(header_data, colWidths=[3.5*inch, 3.5*inch])
    header_table.setStyle(TableStyle([
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("LINEBELOW",   (0,0), (-1,-1), 2,        ORANGE),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.2*inch))

    # ======================================================
    # SEVERITY BANNER
    # ======================================================
    banner_text = f"  ■  SEVERITY: {severity}  |  {analysis.get('incident_type','Unknown')}  |  {'⚠ OSHA RECORDABLE' if analysis.get('osha_recordable') else 'NOT OSHA RECORDABLE'}  "
    banner = Table([[Paragraph(banner_text, ParagraphStyle("bn", fontName="Courier-Bold", fontSize=10, textColor=WHITE))]],
                   colWidths=[7*inch])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), sev_color),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    story.append(banner)
    story.append(Spacer(1, 0.2*inch))

    # ======================================================
    # SECTION HELPER
    # ======================================================
    def section_header(title: str):
        t = Table([[Paragraph(f"  {title}", section_s)]], colWidths=[7*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), DARK),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.1*inch))

    def field_row(label: str, value: str, label2: str = None, value2: str = None):
        if label2:
            row = [[
                Paragraph(label.upper(), label_s),
                Paragraph(str(value), value_s),
                Paragraph(label2.upper(), label_s),
                Paragraph(str(value2), value_s),
            ]]
            t = Table(row, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
        else:
            row = [[Paragraph(label.upper(), label_s), Paragraph(str(value), value_s)]]
            t = Table(row, colWidths=[1.4*inch, 5.6*inch])
        t.setStyle(TableStyle([
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("LINEBELOW",     (0,0), (-1,-1), 0.5, colors.HexColor("#e0d9d0")),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.04*inch))

    # ======================================================
    # SECTION 1 — REPORT INFORMATION
    # ======================================================
    section_header("01  ·  REPORT INFORMATION")
    ts = incident.get("timestamp", datetime.now().isoformat())
    try:
        dt = datetime.fromisoformat(ts)
        date_str = dt.strftime("%B %d, %Y")
        time_str = dt.strftime("%H:%M")
    except Exception:
        date_str = ts
        time_str = "—"

    field_row("Report ID",      incident.get("id", "—")[:8].upper(),
              "Date of Incident", date_str)
    field_row("Time",           time_str,
              "Report Status",   incident.get("status", "Open"))
    field_row("Reported By",    incident.get("reported_by", "—"),
              "Project",         incident.get("project", "—"))
    story.append(Spacer(1, 0.15*inch))

    # ======================================================
    # SECTION 2 — INCIDENT DETAILS
    # ======================================================
    section_header("02  ·  INCIDENT DETAILS")
    field_row("Incident Type",    analysis.get("incident_type", "—"),
              "Severity",         severity)
    field_row("Location on Site", analysis.get("location_on_site", "—"),
              "Equipment/Tools",  analysis.get("equipment_involved", "None"))
    field_row("Person Affected",  analysis.get("injured_person", "Unknown"),
              "Body Part",        analysis.get("body_part_affected", "None"))
    story.append(Spacer(1, 0.1*inch))

    # Severity reason
    story.append(Paragraph("SEVERITY CLASSIFICATION RATIONALE", label_s))
    story.append(Paragraph(analysis.get("severity_reason", "—"), body_s))
    story.append(Spacer(1, 0.1*inch))

    # Immediate cause
    story.append(Paragraph("IMMEDIATE CAUSE", label_s))
    story.append(Paragraph(analysis.get("immediate_cause", "—"), body_s))
    story.append(Spacer(1, 0.15*inch))

    # ======================================================
    # SECTION 3 — ORIGINAL REPORT (VERBATIM)
    # ======================================================
    section_header("03  ·  ORIGINAL INCIDENT DESCRIPTION (VERBATIM)")
    desc_box = Table(
        [[Paragraph(incident.get("raw_description", "—"), body_s)]],
        colWidths=[7*inch]
    )
    desc_box.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#fff8f0")),
        ("BOX",           (0,0), (-1,-1), 0.5, ORANGE),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    story.append(desc_box)
    story.append(Spacer(1, 0.1*inch))

    # AI summary
    story.append(Paragraph("AI-GENERATED SUMMARY", label_s))
    story.append(Paragraph(analysis.get("summary", "—"), body_s))
    story.append(Spacer(1, 0.15*inch))

    # ======================================================
    # SECTION 4 — OSHA COMPLIANCE
    # ======================================================
    section_header("04  ·  OSHA COMPLIANCE")
    recordable = analysis.get("osha_recordable", False)
    rec_text = "YES — THIS INCIDENT IS OSHA RECORDABLE" if recordable else "NO — NOT OSHA RECORDABLE"
    rec_color = RED if recordable else GREEN

    rec_banner = Table(
        [[Paragraph(f"  {rec_text}", ParagraphStyle("rb", fontName="Courier-Bold", fontSize=10, textColor=WHITE))]],
        colWidths=[7*inch]
    )
    rec_banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), rec_color),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    story.append(rec_banner)
    story.append(Spacer(1, 0.08*inch))

    story.append(Paragraph("OSHA RATIONALE", label_s))
    story.append(Paragraph(analysis.get("osha_reason", "—"), body_s))
    story.append(Spacer(1, 0.08*inch))

    forms = analysis.get("osha_forms_required", [])
    if forms:
        story.append(Paragraph("FORMS REQUIRED", label_s))
        for f in forms:
            story.append(Paragraph(f"■  {f}", action_s))
    story.append(Spacer(1, 0.15*inch))

    # ======================================================
    # SECTION 5 — IMMEDIATE ACTIONS REQUIRED
    # ======================================================
    section_header("05  ·  IMMEDIATE ACTIONS REQUIRED")
    actions = analysis.get("immediate_actions_required", [])
    for idx, action in enumerate(actions, 1):
        row = [[
            Paragraph(str(idx), ParagraphStyle("num", fontName="Courier-Bold", fontSize=12,
                                               textColor=WHITE, alignment=TA_CENTER)),
            Paragraph(action, body_s)
        ]]
        t = Table(row, colWidths=[0.35*inch, 6.65*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (0,-1), ORANGE),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (1,0), (1,-1), 10),
            ("LINEBELOW",     (0,0), (-1,-1), 0.5, colors.HexColor("#e0d9d0")),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.04*inch))
    story.append(Spacer(1, 0.15*inch))

    # ======================================================
    # SECTION 6 — SIGNATURES
    # ======================================================
    section_header("06  ·  SIGNATURES & REVIEW")
    sig_data = [
        ["Safety Manager Signature", "Date", "Superintendent Signature", "Date"],
        ["", "", "", ""],
        ["_" * 28, "_" * 12, "_" * 28, "_" * 12],
        ["Print Name", "Title", "Print Name", "Title"],
        ["", "", "", ""],
        ["_" * 28, "_" * 12, "_" * 28, "_" * 12],
    ]
    sig_table = Table(sig_data, colWidths=[2.2*inch, 1.3*inch, 2.2*inch, 1.3*inch])
    sig_table.setStyle(TableStyle([
        ("FONTNAME",      (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("TEXTCOLOR",     (0,0), (-1,-1), GRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("LEFTPADDING",   (0,0), (-1,-1), 4),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 0.2*inch))

    # ======================================================
    # FOOTER
    # ======================================================
    footer = Table([[
        Paragraph("CONSTRUCTSAFE AI  ·  Automated Safety Reporting  ·  Powered by Claude AI",
                  ParagraphStyle("ft", fontName="Courier", fontSize=8, textColor=GRAY)),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                  ParagraphStyle("ft2", fontName="Courier", fontSize=8, textColor=GRAY, alignment=TA_RIGHT))
    ]], colWidths=[4.5*inch, 2.5*inch])
    footer.setStyle(TableStyle([
        ("LINEABOVE", (0,0), (-1,-1), 1, ORANGE),
        ("TOPPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(footer)

    doc.build(story)
    return buf.getvalue()


def generate_pitch_pack_pdf(incidents: list[dict]) -> bytes:
    """
    Generate an investor-ready "Pitch Pack" PDF summarizing:
    - risk distribution
    - OSHA recordability stats
    - avg efficiency + avg environmental hazard
    - top actions needed
    """
    from utils.http_api import client_api_base

    base = client_api_base()
    if base and os.environ.get("SAPIENTIA_IS_PDF_WORKER") != "1":
        import httpx

        try:
            r = httpx.post(
                f"{base}/api/reports/pitch-pack-pdf",
                json={"incidents": incidents},
                timeout=120.0,
            )
            r.raise_for_status()
            return r.content
        except httpx.RequestError as e:
            raise RuntimeError(
                f"Backend pitch-pack API unreachable at {base!r}. Clear **Backend base URL** in Settings "
                "to generate PDFs locally, or start the FastAPI server."
            ) from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Backend pitch-pack API returned {e.response.status_code} for {base!r}."
            ) from e

    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab not installed. Run: pip install reportlab")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    story = []

    mono_bold = ParagraphStyle("mono_bold", fontName="Courier-Bold", fontSize=9, textColor=BLACK)
    label_s = ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=8, textColor=GRAY, spaceAfter=1)
    body_s = ParagraphStyle("body", fontName="Helvetica", fontSize=10, textColor=BLACK, leading=14)
    section_s = ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=11, textColor=WHITE, spaceAfter=4)

    total = len(incidents)
    by_severity = Counter((i.get("analysis", {}) or {}).get("severity", "LOW") for i in incidents)
    recordable_cnt = sum(1 for i in incidents if (i.get("analysis", {}) or {}).get("osha_recordable"))
    risk_scores = []
    eff_scores = []
    env_scores = []
    for i in incidents:
        a = i.get("analysis", {}) or {}
        rs = a.get("risk_score")
        es = a.get("efficiency_score")
        hs = a.get("environmental_hazard_score")
        if isinstance(rs, (int, float)):
            risk_scores.append(int(rs))
        if isinstance(es, (int, float)):
            eff_scores.append(int(es))
        if isinstance(hs, (int, float)):
            env_scores.append(int(hs))

    def _avg(vals: list[int]) -> int:
        return int(sum(vals) / len(vals)) if vals else 0

    avg_eff = _avg(eff_scores)
    avg_env = _avg(env_scores)

    # Risk distribution buckets
    risk_bins = {"0-30": 0, "31-60": 0, "61-100": 0}
    for r in risk_scores:
        if r <= 30:
            risk_bins["0-30"] += 1
        elif r <= 60:
            risk_bins["31-60"] += 1
        else:
            risk_bins["61-100"] += 1

    # Top actions needed: frequency count across analysis action libraries
    action_counts = Counter()
    for i in incidents:
        a = i.get("analysis", {}) or {}
        for act in a.get("efficiency_actions_required", []) or []:
            action_counts[act] += 1
        for act in a.get("sustainability_actions_required", []) or []:
            action_counts[act] += 1

    top_actions = [f"{idx+1}. {act}" for idx, (act, _c) in enumerate(action_counts.most_common(7))]

    # ---- Header ----
    header_data = [[
        Paragraph("<b>CONSTRUCTSAFE AI</b>", ParagraphStyle("hd", fontName="Courier-Bold", fontSize=18, textColor=ORANGE)),
        Paragraph(
            "<b>INVESTOR PITCH PACK</b><br/>"
            "<font size=8 color='#888888'>Risk · OSHA · Efficiency · ESG</font>",
            ParagraphStyle("hd2", fontName="Helvetica-Bold", fontSize=13, textColor=BLACK, alignment=TA_RIGHT),
        ),
    ]]
    header_table = Table(header_data, colWidths=[3.8 * inch, 3.2 * inch])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 2, ORANGE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.2 * inch))

    # ---- KPI summary table ----
    recordable_pct = int((recordable_cnt / total) * 100) if total else 0
    kpi_rows = [
        ["Total incidents analyzed", str(total)],
        ["OSHA recordable incidents", f"{recordable_cnt} ({recordable_pct}%)"],
        ["Avg Risk Score", f"{_avg(risk_scores) if risk_scores else 0}/100"],
        ["Avg Efficiency Score", f"{avg_eff}/100"],
        ["Avg Environmental Hazard", f"{avg_env}/100"],
        ["Severity distribution", " · ".join([f"{k}:{by_severity.get(k,0)}" for k in ["CRITICAL", "MEDIUM", "LOW"]])],
    ]

    kpi_table = Table([[Paragraph("Metric", label_s), Paragraph("Value", label_s)]] + [[Paragraph(k, body_s), Paragraph(v, body_s)] for k, v in kpi_rows], colWidths=[3.5 * inch, 2.5 * inch])
    kpi_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0d9d0")),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.25 * inch))

    # ---- Risk distribution ----
    story.append(Paragraph("1 · Risk Distribution", section_s))
    risk_text = " · ".join([f"{k}: {v}" for k, v in risk_bins.items()])
    story.append(Paragraph(risk_text, body_s))
    story.append(Spacer(1, 0.15 * inch))

    # ---- Top actions needed ----
    story.append(Paragraph("2 · Top Actions Needed (Ops-ready)", section_s))
    if top_actions:
        for a in top_actions:
            story.append(Paragraph(a, body_s))
    else:
        story.append(Paragraph("No actions found in incident analyses.", body_s))

    story.append(Spacer(1, 0.2 * inch))

    # ---- Methodology ----
    story.append(Paragraph("3 · Methodology (what this pitch pack is)", section_s))
    story.append(
        Paragraph(
            "ConstructSAFE automatically classifies incidents, checks OSHA 300/301 recordability, "
            "and provides ESG-aware efficiency + sustainability recommendations. Scores and top actions "
            "are derived from incident text analysis and stored as structured fields for consistent reporting.",
            body_s,
        )
    )

    footer = Table([[
        Paragraph("CONSTRUCTSAFE AI · Investor Pitch Pack", ParagraphStyle("ft", fontName="Courier", fontSize=8, textColor=GRAY)),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                  ParagraphStyle("ft2", fontName="Courier", fontSize=8, textColor=GRAY, alignment=TA_RIGHT)),
    ]], colWidths=[4.5 * inch, 2.5 * inch])
    footer.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, -1), 1, ORANGE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(Spacer(1, 0.25 * inch))
    story.append(footer)

    doc.build(story)
    return buf.getvalue()
