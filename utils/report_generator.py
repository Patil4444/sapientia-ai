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


# Brand colors (only defined when ReportLab is available).
if REPORTLAB_AVAILABLE:
    ORANGE = colors.HexColor("#FF6B00")
    DARK = colors.HexColor("#0f0f0f")
    LIGHT = colors.HexColor("#f5f2ed")
    RED = colors.HexColor("#FF1744")
    GREEN = colors.HexColor("#2E7D32")
    GRAY = colors.HexColor("#888888")
    WHITE = colors.white
    BLACK = colors.black


def generate_pdf(incident: dict) -> bytes:
    """Generate OSHA incident PDF and return bytes."""
    from utils.http_api import client_api_base

    base = client_api_base()
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
            from utils.http_api import format_backend_http_error

            raise RuntimeError(
                format_backend_http_error(e, base, context="incident PDF API")
            ) from e

    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab not installed. Run: pip install reportlab")

    analysis = incident.get("analysis", {}) or {}
    details = incident.get("details", {}) or {}
    severity = (incident.get("severity") or analysis.get("severity") or "LOW").upper()
    severity_color = {"CRITICAL": colors.HexColor("#FF4444"), "MEDIUM": colors.HexColor("#FFB020"), "LOW": colors.HexColor("#00D68F")}.get(severity, colors.HexColor("#00D68F"))
    recordable = bool(incident.get("osha_recordable", analysis.get("osha_recordable", False)))
    forms_required = incident.get("osha_forms_required") or analysis.get("osha_forms_required") or ["OSHA 300", "OSHA 301"]
    actions = incident.get("immediate_actions") or analysis.get("immediate_actions_required") or []
    description = incident.get("description") or incident.get("raw_description") or "—"
    ai_summary = incident.get("ai_summary") or analysis.get("summary") or "—"

    timestamp = incident.get("timestamp", datetime.now().isoformat())
    try:
        incident_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        date_text = incident_dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        date_text = timestamp

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Heading1"], alignment=TA_CENTER, textColor=colors.white, fontSize=13, fontName="Helvetica-Bold", leading=16)
    label_style = ParagraphStyle("label", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#5B6475"), fontName="Helvetica-Bold")
    value_style = ParagraphStyle("value", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#0F172A"), fontName="Helvetica")
    body_style = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, leading=14, textColor=colors.HexColor("#0F172A"), alignment=TA_LEFT)
    footer_style = ParagraphStyle("footer", parent=styles["Normal"], alignment=TA_CENTER, fontSize=8, textColor=colors.HexColor("#5B6475"))

    story = []

    header = Table([[Paragraph("SAPIENTIA AI — OSHA INCIDENT REPORT", title_style)]], colWidths=[6.9 * inch])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0F1520")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.extend([header, Spacer(1, 10)])

    meta_rows = [
        [Paragraph("INCIDENT ID", label_style), Paragraph(str(incident.get("id", "unknown")), value_style),
         Paragraph("DATE", label_style), Paragraph(date_text, value_style)],
        [Paragraph("PROJECT", label_style), Paragraph(str(incident.get("project", "—")), value_style),
         Paragraph("REPORTER", label_style), Paragraph(str(incident.get("reporter") or incident.get("reported_by", "—")), value_style)],
    ]
    meta = Table(meta_rows, colWidths=[1.1 * inch, 2.35 * inch, 1.1 * inch, 2.35 * inch])
    meta.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5DEEA")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([meta, Spacer(1, 10)])

    sev_badge = Table([[Paragraph(f"SEVERITY: {severity}", ParagraphStyle("sev", alignment=TA_CENTER, textColor=colors.white, fontName="Helvetica-Bold", fontSize=10))]], colWidths=[6.9 * inch])
    sev_badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), severity_color),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([sev_badge, Spacer(1, 8)])

    story.append(Paragraph(f"<b>OSHA Recordable:</b> {'Yes' if recordable else 'No'}", body_style))
    story.append(Paragraph(f"<b>OSHA Forms Required:</b> {', '.join(str(f) for f in forms_required)}", body_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Incident Description</b>", value_style))
    story.append(Paragraph(str(description), body_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>AI Summary</b>", value_style))
    story.append(Paragraph(str(ai_summary), body_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Immediate Actions</b>", value_style))
    if actions:
        for action in actions:
            story.append(Paragraph(f"• {str(action)}", body_style))
    else:
        story.append(Paragraph("• None listed", body_style))
    story.append(Spacer(1, 8))

    details_table = Table(
        [
            ["Location", "Person Involved", "Body Part", "Equipment", "Risk Score"],
            [
                str(details.get("location") or analysis.get("location_on_site") or "—"),
                str(details.get("person_involved") or analysis.get("injured_person") or "—"),
                str(details.get("body_part") or analysis.get("body_part_affected") or "—"),
                str(details.get("equipment") or analysis.get("equipment_involved") or "—"),
                str(incident.get("risk_score") if incident.get("risk_score") is not None else analysis.get("risk_score", "—")),
            ],
        ],
        colWidths=[1.35 * inch, 1.45 * inch, 1.2 * inch, 1.45 * inch, 1.45 * inch],
    )
    details_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#141D2B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#E8EDF5")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5DEEA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([details_table, Spacer(1, 10), HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#D5DEEA"))])
    story.append(Spacer(1, 6))
    story.append(Paragraph("Generated by Sapientia AI · OSHA 300/301 Compliant · Confidential", footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_incident_report(incident: dict) -> bytes:
    """Backward-compatible wrapper for existing callers."""
    return generate_pdf(incident)


def generate_toolbox_talk_pdf(talk: dict) -> bytes:
    """
    Generate an OSHA-style toolbox talk / safety briefing PDF.

    Accepts the structured dict returned by ``generate_toolbox_talk()``:
    trade, incident_type, severity, opening_statistic, scenario_narrative,
    corrective_behaviors, sign_off, plus optional date, facilitator, duration, project.
    """
    from utils.http_api import client_api_base

    base = client_api_base()
    if base and os.environ.get("SAPIENTIA_IS_PDF_WORKER") != "1":
        import httpx

        try:
            r = httpx.post(
                f"{base}/api/reports/toolbox-talk-pdf",
                json=talk,
                timeout=120.0,
            )
            r.raise_for_status()
            return r.content
        except httpx.RequestError as e:
            raise RuntimeError(
                f"Backend toolbox-talk PDF API unreachable at {base!r}. Clear **Backend base URL** in Settings "
                "to generate PDFs locally, or start the FastAPI server."
            ) from e
        except httpx.HTTPStatusError as e:
            from utils.http_api import format_backend_http_error

            raise RuntimeError(
                format_backend_http_error(e, base, context="toolbox-talk PDF API")
            ) from e

    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab not installed. Run: pip install reportlab")

    def _esc(text) -> str:
        return str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    trade = talk.get("trade", "—")
    incident_type = talk.get("incident_type", "—")
    severity = talk.get("severity", "—")
    word_count = talk.get("word_count", "—")
    date_text = talk.get("date") or datetime.now().strftime("%Y-%m-%d")
    facilitator = talk.get("facilitator") or "_________________________"
    duration = talk.get("duration") or "~10 min"
    project = talk.get("project") or "—"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "tt_title",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        textColor=colors.white,
        fontSize=13,
        fontName="Helvetica-Bold",
        leading=16,
    )
    subtitle_style = ParagraphStyle(
        "tt_subtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#C5D0E0"),
        fontSize=8,
        fontName="Helvetica",
        leading=10,
    )
    label_style = ParagraphStyle(
        "tt_label",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#5B6475"),
        fontName="Helvetica-Bold",
    )
    value_style = ParagraphStyle(
        "tt_value",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#0F172A"),
        fontName="Helvetica",
    )
    body_style = ParagraphStyle(
        "tt_body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0F172A"),
        alignment=TA_LEFT,
    )
    section_style = ParagraphStyle(
        "tt_section",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#E8EDF5"),
        leading=12,
    )
    footer_style = ParagraphStyle(
        "tt_footer",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=8,
        textColor=colors.HexColor("#5B6475"),
        leading=11,
    )
    grid_color = colors.HexColor("#D5DEEA")
    header_bg = colors.HexColor("#0F1520")
    section_bg = colors.HexColor("#141D2B")

    story = []

    header_rows = [
        [Paragraph("SAPIENTIA AI — TOOLBOX TALK / SAFETY BRIEFING", title_style)],
        [Paragraph("Construction Site Safety Briefing · Field Distribution Copy", subtitle_style)],
    ]
    header = Table(header_rows, colWidths=[6.9 * inch])
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), header_bg),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (0, 0), 10),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
                ("TOPPADDING", (0, 1), (0, 1), 0),
                ("BOTTOMPADDING", (0, 0), (0, 0), 2),
            ]
        )
    )
    story.extend([header, Spacer(1, 10)])

    meta_rows = [
        [
            Paragraph("DATE", label_style),
            Paragraph(_esc(date_text), value_style),
            Paragraph("TRADE", label_style),
            Paragraph(_esc(trade), value_style),
        ],
        [
            Paragraph("INCIDENT TYPE", label_style),
            Paragraph(_esc(incident_type), value_style),
            Paragraph("SEVERITY", label_style),
            Paragraph(_esc(severity), value_style),
        ],
        [
            Paragraph("FACILITATOR", label_style),
            Paragraph(_esc(facilitator), value_style),
            Paragraph("DURATION", label_style),
            Paragraph(_esc(duration), value_style),
        ],
        [
            Paragraph("PROJECT", label_style),
            Paragraph(_esc(project), value_style),
            Paragraph("WORD COUNT", label_style),
            Paragraph(_esc(word_count), value_style),
        ],
    ]
    meta = Table(meta_rows, colWidths=[1.15 * inch, 2.3 * inch, 1.15 * inch, 2.3 * inch])
    meta.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, grid_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([meta, Spacer(1, 12)])

    def _section_heading(title: str):
        bar = Table([[Paragraph(title.upper(), section_style)]], colWidths=[6.9 * inch])
        bar.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), section_bg),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(bar)
        story.append(Spacer(1, 6))

    def _section_body(text: str):
        for para in (text or "").split("\n\n"):
            para = para.strip()
            if para:
                story.append(Paragraph(_esc(para).replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 10))

    _section_heading("1 · Opening Safety Statistic")
    _section_body(talk.get("opening_statistic", ""))

    _section_heading("2 · Incident Scenario")
    _section_body(talk.get("scenario_narrative", ""))

    _section_heading("3 · Corrective Behaviors")
    story.append(
        Paragraph(
            "Apply these five field behaviors before repeating similar work:",
            body_style,
        )
    )
    story.append(Spacer(1, 4))
    behaviors = talk.get("corrective_behaviors") or []
    if behaviors:
        beh_rows = [[Paragraph("#", label_style), Paragraph("Behavior / Control", label_style)]]
        for i, behavior in enumerate(behaviors, 1):
            beh_rows.append(
                [
                    Paragraph(str(i), value_style),
                    Paragraph(_esc(behavior), body_style),
                ]
            )
        beh_table = Table(beh_rows, colWidths=[0.45 * inch, 6.45 * inch])
        beh_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), section_bg),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#E8EDF5")),
                    ("GRID", (0, 0), (-1, -1), 0.5, grid_color),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.extend([beh_table, Spacer(1, 10)])
    else:
        story.append(Paragraph("No corrective behaviors listed.", body_style))
        story.append(Spacer(1, 10))

    _section_heading("4 · Attendance Sign-off")
    sign_off_note = (talk.get("sign_off") or "").strip()
    if sign_off_note and "acknowledge participation" in sign_off_note.lower():
        story.append(
            Paragraph(
                "I acknowledge participation in today's toolbox talk and understand the hazards discussed.",
                body_style,
            )
        )
    elif sign_off_note:
        _section_body(sign_off_note)
    else:
        story.append(
            Paragraph(
                "I acknowledge participation in today's toolbox talk and understand the hazards discussed.",
                body_style,
            )
        )
    story.append(Spacer(1, 6))

    attendance_header = [
        Paragraph("Printed Name", label_style),
        Paragraph("Signature", label_style),
        Paragraph("Date", label_style),
    ]
    attendance_rows = [attendance_header]
    for _ in range(8):
        attendance_rows.append(
            [
                Paragraph("_______________________________", value_style),
                Paragraph("_______________________________", value_style),
                Paragraph("_______________", value_style),
            ]
        )
    attendance_table = Table(
        attendance_rows,
        colWidths=[2.5 * inch, 2.9 * inch, 1.5 * inch],
    )
    attendance_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4F7FB")),
                ("GRID", (0, 0), (-1, -1), 0.5, grid_color),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([attendance_table, Spacer(1, 12)])

    facilitator_row = Table(
        [
            [
                Paragraph("Facilitator Signature", label_style),
                Paragraph("_______________________________", value_style),
                Paragraph("Date", label_style),
                Paragraph("_______________", value_style),
            ]
        ],
        colWidths=[1.35 * inch, 2.8 * inch, 0.55 * inch, 2.2 * inch],
    )
    facilitator_row.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, grid_color),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([facilitator_row, Spacer(1, 12), HRFlowable(width="100%", thickness=0.8, color=grid_color)])
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "OSHA Reference: 29 CFR 1926 (Safety and Health Regulations for Construction) · "
            "Employers must instruct each employee in recognizing and avoiding unsafe conditions "
            "and the regulations applicable to the work environment (1926.21(b)(2)).",
            footer_style,
        )
    )
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"Generated by Sapientia AI · {datetime.now().strftime('%Y-%m-%d %H:%M')} · Confidential",
            footer_style,
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


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
            from utils.http_api import format_backend_http_error

            raise RuntimeError(
                format_backend_http_error(e, base, context="pitch-pack PDF API")
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
