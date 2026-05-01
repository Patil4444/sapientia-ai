import hashlib
import html
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.agent import analyze_incident, get_severity_emoji
from utils.alerts import send_alert, should_alert
from utils.badges import get_severity_badge
from utils.data_store import save_incident, update_incident
from utils.project_store import get_active_project_names
from utils.report_generator import generate_pdf
from utils.training_data import get_sample_scenario_options


_ANALYSIS_EXECUTOR = ThreadPoolExecutor(max_workers=2)

LEGACY_PROJECTS = [
    "Harbor View Tower - Phase 2",
    "Riverside Bridge Rehab",
    "Downtown Mixed-Use Development",
    "Highway 128 Expansion",
    "Waterfront Parking Structure",
]

STAKEHOLDER_ROLES = [
    "General contractor (GC)",
    "Subcontractor",
    "Owner / client representative",
    "Safety officer / HSE",
    "Site superintendent",
    "Trade crew / worker",
    "Other stakeholder",
]


def _project_options() -> list[str]:
    names = get_active_project_names()
    if not names:
        names = list(LEGACY_PROJECTS)
    return names + ["Other (custom site name)"]


# Demo scenarios + real construction incidents (2020–present) the platform would have helped prevent
SAMPLE_SCENARIOS = {
    "Select a sample scenario...": "",
    "🔴 Scaffolding fall (CRITICAL)": "Worker fell from scaffolding on level 8, approximately 14 feet. John Smith, carpenter. He is conscious but cannot move his legs. Ambulance called immediately. Scaffolding board gave way.",
    "🟠 Near miss — crane swing (MEDIUM)": "Close call with the tower crane today. Load swung over workers on the east side who hadn't been cleared from the zone. Nobody was hit but it was very close. Crew wasn't notified of the lift schedule.",
    "🟢 Minor cut from rebar (LOW)": "Worker cut his right hand on exposed rebar end. Small laceration, treated with first aid kit on site. Applied bandage. Worker returned to work. Need to add end caps.",
    "🔴 Electrical shock (CRITICAL)": "Sub-contractor got shocked while connecting to the panel on floor 3. Didn't follow lockout tagout procedure. His hand went numb. We sent him to urgent care right away.",
    "🟠 Chemical spill (MEDIUM)": "Form release agent spilled on worker forearm. Skin is red and irritated. Washed with water for 20 minutes. No blisters. Worker needs to see occupational health.",
}
for label, desc in get_sample_scenario_options():
    SAMPLE_SCENARIOS[label] = desc


def _sync_sample_to_body() -> None:
    sel = st.session_state.get("sample_pick", "Select a sample scenario...")
    if sel in SAMPLE_SCENARIOS and sel != "Select a sample scenario...":
        st.session_state["report_body"] = SAMPLE_SCENARIOS[sel]


def render():
    st.markdown("""
<div style="margin-bottom:20px; padding-bottom:16px; 
            border-bottom:1px solid #1A2540;">
    <div style="font-size:11px; color:#3D5068; letter-spacing:1.5px; 
                text-transform:uppercase; margin-bottom:6px; font-weight:600;">
        SAPIENTIA AI · OSHA 300/301
    </div>
    <h1 style="font-size:26px; font-weight:700; color:#F1F5F9; 
               margin:0; letter-spacing:-0.3px;">
        Report Incident
    </h1>
</div>
""", unsafe_allow_html=True)

    api_key = st.session_state.get("anthropic_api_key", "")
    if not api_key:
        st.markdown(
            '<p style="font-size:12px;color:#3D5068;margin:0 0 12px 0;">'
            "Running in demo mode (rule-based) without an Anthropic API key — add one in Settings for full Claude analysis.</p>",
            unsafe_allow_html=True,
        )

    if "report_body" not in st.session_state:
        st.session_state.report_body = ""
    if "sample_pick" not in st.session_state:
        st.session_state.sample_pick = "Select a sample scenario..."

    st.markdown(
        '<p style="font-size:11px;color:#3D5068;letter-spacing:0.8px;text-transform:uppercase;margin:0 0 6px 0;">'
        "Incident description</p>",
        unsafe_allow_html=True,
    )

    description = st.text_area(
        "Incident description",
        key="report_body",
        height=180,
        placeholder=(
            "Describe what happened. Be specific: who, what, where, "
            "any injuries or equipment involved."
        ),
        label_visibility="collapsed",
    )

    with st.expander("Add details (optional)", expanded=False):
        reported_by = st.text_input(
            "Your name / reporter", placeholder="Leave blank for Anonymous"
        )
        stakeholder_role = st.selectbox("Your role (stakeholder)", STAKEHOLDER_ROLES)
        organization = st.text_input(
            "Company / subcontractor / crew (optional)",
            placeholder="e.g. Apex Concrete LLC",
        )

        proj_opts = _project_options()
        focus = st.session_state.get("sapientia_focus_project") or ""
        proj_index = 0
        if focus and focus in proj_opts:
            proj_index = proj_opts.index(focus)
        proj_sel = st.selectbox("Project / site", proj_opts, index=proj_index)

        custom_site = ""
        if proj_sel == "Other (custom site name)":
            custom_site = st.text_input(
                "Custom site name", placeholder="Type the official job name"
            )

        if proj_sel == "Other (custom site name)":
            project = (custom_site or "").strip() or "Unspecified site"
        else:
            project = proj_sel

        st.selectbox(
            "Quick-fill with sample scenario",
            list(SAMPLE_SCENARIOS.keys()),
            key="sample_pick",
            on_change=_sync_sample_to_body,
        )

    reporter = (reported_by or "").strip() or "Anonymous"
    role = stakeholder_role
    org = organization

    st.markdown("<br/>", unsafe_allow_html=True)

    def _submission_key_for(
        description_text: str, reporter: str, proj: str, role: str, org: str
    ) -> str:
        raw = f"{reporter}::{proj}::{role}::{org}::{description_text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _render_results(
        *,
        description_text: str,
        reporter: str,
        proj: str,
        role: str,
        org: str,
        analysis: dict,
    ):
        severity = analysis.get("severity", "LOW")
        emoji = get_severity_emoji(severity)

        submission_key = _submission_key_for(description_text, reporter, proj, role, org)
        if st.session_state.get("last_saved_submission_key") == submission_key and st.session_state.get(
            "last_saved_incident_id"
        ):
            incident_id = st.session_state["last_saved_incident_id"]
            incident = {
                "id": incident_id,
                "reported_by": reporter,
                "project": proj,
                "stakeholder_role": role,
                "organization": org.strip() or "",
                "raw_description": description_text,
                "analysis": analysis,
                "status": "Open",
                "report_generated": False,
            }
        else:
            incident = {
                "reported_by": reporter,
                "project": proj,
                "stakeholder_role": role,
                "organization": org.strip() or "",
                "raw_description": description_text,
                "analysis": analysis,
                "status": "Open",
                "report_generated": False,
            }
            incident_id = save_incident(incident)
            incident["id"] = incident_id
            st.session_state["last_saved_submission_key"] = submission_key
            st.session_state["last_saved_incident_id"] = incident_id

        # Drop cached PDF when results are for a different incident (Streamlit reruns).
        if st.session_state.get("_report_pdf_incident_id") != incident_id:
            st.session_state.pop("_report_pdf_bytes", None)
            st.session_state.pop("_report_pdf_fname", None)
        st.session_state["_report_pdf_incident_id"] = incident_id

        recipient = st.session_state.get("alert_email", "")
        sendgrid_key = st.session_state.get("sendgrid_key", "")
        if should_alert(severity):
            alert_result = send_alert(incident, analysis, recipient or None, sendgrid_key or None)
            alert_sent = alert_result.get("success", False)
        else:
            alert_sent = False

        st.markdown("---")

        st.markdown(
            f'<div class="sap-glass-panel sap-result-hero-wrap sap-result-hero">'
            f'<div style="margin-bottom:6px;font-size:14px;color:#8899AA;">'
            f"{emoji} Analysis complete</div>"
            f"{get_severity_badge(severity)}"
            f"</div>",
            unsafe_allow_html=True,
        )

        osha_text = (
            "OSHA RECORDABLE"
            if analysis.get("osha_recordable")
            else "NOT RECORDABLE"
        )
        itype = html.escape(analysis.get("incident_type", "—"))

        st.markdown(
            f'<div class="sap-result-meta-row">'
            f'<div class="sap-result-meta-item">'
            f'<div class="sap-muted" style="font-size:13px;margin-bottom:4px;">TYPE</div>'
            f'<div style="font-size:15px;font-weight:600;color:#F1F5F9;">{itype}</div></div>'
            f'<div class="sap-result-meta-item">'
            f'<div class="sap-muted" style="font-size:13px;margin-bottom:4px;">OSHA</div>'
            f'<div style="font-size:15px;font-weight:600;color:#F1F5F9;">{osha_text}</div></div>'
            f"</div>",
            unsafe_allow_html=True,
        )

        sum_col = (
            f'<div class="sap-glass-panel">'
            f'<div class="sap-label-upper">AI Summary</div>'
            f'<p style="margin:0;font-size:14px;color:#8899AA;line-height:1.6;">{html.escape(analysis.get("summary", "—"))}</p>'
            f"</div>"
        )

        actions = analysis.get("immediate_actions_required", []) or []
        actions_html = "".join(
            f'<div style="display:flex;gap:8px;margin-bottom:6px;"><span style="color:#00E5FF;font-weight:700;">{i}.</span>'
            f'<span style="font-size:14px;color:#8899AA;">{html.escape(str(a))}</span></div>'
            for i, a in enumerate(actions, 1)
        ) or '<p class="sap-muted" style="font-size:13px;">None listed.</p>'

        act_col = (
            f'<div class="sap-glass-panel">'
            f'<div class="sap-label-upper">Immediate actions</div>'
            f"{actions_html}</div>"
        )

        st.markdown(
            f'<div class="sap-grid-2">{sum_col}{act_col}</div>',
            unsafe_allow_html=True,
        )

        det_col1 = (
            f'<div class="sap-glass-panel sap-glass-panel--stack">'
            f'<div class="sap-label-upper" style="margin-bottom:10px;">Incident details</div>'
        )
        details = {
            "Location": analysis.get("location_on_site", "—"),
            "Person affected": analysis.get("injured_person", "—"),
            "Body part": analysis.get("body_part_affected", "—"),
            "Equipment": analysis.get("equipment_involved", "—"),
            "Immediate cause": analysis.get("immediate_cause", "—"),
            "Risk score": f'{analysis.get("risk_score", "—")}/100'
            if analysis.get("risk_score") is not None
            else "—",
            "Environmental hazard": f'{analysis.get("environmental_hazard_score", "—")}/100'
            if analysis.get("environmental_hazard_score") is not None
            else "—",
            "Efficiency score": f'{analysis.get("efficiency_score", "—")}/100'
            if analysis.get("efficiency_score") is not None
            else "—",
        }
        rows = "".join(
            f'<div class="sap-detail-row"><span class="sap-muted">{html.escape(k)}</span>'
            f'<span class="sap-strong">{html.escape(str(v))}</span></div>'
            for k, v in details.items()
        )
        st.markdown(det_col1 + rows + "</div>", unsafe_allow_html=True)

        det_col2 = (
            f'<div class="sap-glass-panel sap-glass-panel--stack">'
            f'<div class="sap-label-upper" style="margin-bottom:10px;">OSHA rationale</div>'
            f'<p style="margin:0;font-size:14px;color:#8899AA;line-height:1.6;">{html.escape(analysis.get("osha_reason", "—"))}</p>'
            f"</div>"
        )
        st.markdown(det_col2, unsafe_allow_html=True)

        if analysis.get("osha_forms_required"):
            forms_bits = "".join(
                f'<span class="sap-meta-chip">{html.escape(str(f))}</span>'
                for f in analysis["osha_forms_required"]
            )
            st.markdown(
                f'<div style="margin-top:14px;"><span class="sap-label-upper">Forms required</span>'
                f'<div style="margin-top:6px;">{forms_bits}</div></div>',
                unsafe_allow_html=True,
            )

        if analysis.get("evidence_snippets"):
            with st.expander("Why this severity/risk (evidence)"):
                for sn in analysis.get("evidence_snippets", []):
                    st.markdown(f"- {sn}")

        if alert_sent:
            st.success("Alert dispatched to safety manager")

        with st.expander("Sustainability & Efficiency (Investor View)"):
            st.markdown("**Sustainability concerns**")
            for c in analysis.get("sustainability_concerns", []):
                st.markdown(f"- {c}")
            st.markdown("**Sustainability actions required**")
            for a in analysis.get("sustainability_actions_required", []):
                st.markdown(f"- {a}")

            st.markdown("---")
            st.markdown(f"**Efficiency score:** {analysis.get('efficiency_score','—')}/100")
            st.markdown(f"_{analysis.get('efficiency_score_reason','')}_")
            st.markdown("**Efficiency actions required**")
            for a in analysis.get("efficiency_actions_required", []):
                st.markdown(f"- {a}")

        st.markdown("---")
        st.markdown(
            '<p class="sap-label-upper" style="margin-bottom:8px;">Official report</p>',
            unsafe_allow_html=True,
        )

        # Generate once → store in session_state. Download button must NOT live only
        # inside `if st.button(...)`, or it disappears on the next rerun (Streamlit).
        if st.button("📄 Generate OSHA-formatted PDF", key="gen_pdf_report"):
            try:
                pdf_bytes = generate_pdf(incident)
                update_incident(incident_id, {"report_generated": True})
                st.session_state["_report_pdf_bytes"] = pdf_bytes
                st.session_state["_report_pdf_fname"] = f"incident_report_{incident.get('id', 'unknown')[:8]}.pdf"
                st.success("PDF generated — use **Download PDF report** below.")
            except ImportError:
                st.error("ReportLab not installed. Run: pip install reportlab")
            except Exception as e:
                st.error(f"Error generating PDF: {e}")

        pdf_bytes = st.session_state.get("_report_pdf_bytes")
        pdf_fname = st.session_state.get("_report_pdf_fname") or "incident_report.pdf"
        if pdf_bytes and st.session_state.get("_report_pdf_incident_id") == incident_id:
            st.download_button(
                label="Download OSHA Report (PDF)",
                data=pdf_bytes,
                file_name=f"sapientia_report_{incident.get('id','')[:8]}.pdf",
                mime="application/pdf",
                key=f"pdf_{incident.get('id', 'unknown')}",
                use_container_width=True,
            )

        if analysis.get("_api_error"):
            st.caption(f"ℹ️ Demo mode (rule-based): {analysis['_api_error'][:100]}")

    job = st.session_state.get("analysis_job")
    if job and job.get("status") == "running" and job.get("future") is not None:
        if st.button("⏳ Check analysis status", use_container_width=True, key="check_analysis_status"):
            future = job["future"]
            if future.done():
                try:
                    analysis = future.result()
                    st.session_state["analysis_job"] = None
                    _render_results(
                        description_text=job["description"],
                        reporter=job["reported_by"],
                        proj=job["project"],
                        role=job.get("stakeholder_role", ""),
                        org=job.get("organization", ""),
                        analysis=analysis,
                    )
                except Exception as e:
                    st.error(f"Error getting analysis result: {e}")
                    st.session_state["analysis_job"] = None
            else:
                st.info("AI analysis still running. Click again in a moment.")

    if st.button("Analyze & Submit →", type="primary", use_container_width=True, key="report_submit_main"):
        if not (description or "").strip():
            st.error("Please describe what happened before submitting.")
        else:
            submission_key = _submission_key_for(
                description, reporter, project, role, org
            )
            if api_key:
                future = _ANALYSIS_EXECUTOR.submit(
                    analyze_incident, description, api_key=api_key or None
                )
                st.session_state["analysis_job"] = {
                    "status": "running",
                    "future": future,
                    "submission_key": submission_key,
                    "description": description,
                    "reported_by": reporter,
                    "project": project,
                    "stakeholder_role": role,
                    "organization": org,
                }
                st.info("AI analysis started in background. Click 'Check analysis status' when ready.")
            else:
                with st.spinner("Analyzing incident…"):
                    analysis = analyze_incident(description, api_key=None)
                _render_results(
                    description_text=description,
                    reporter=reporter,
                    proj=project,
                    role=role,
                    org=org,
                    analysis=analysis,
                )


if os.environ.get("SAPIENTIA_SKIP_RENDER") != "1":
    render()
