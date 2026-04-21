import streamlit as st
from datetime import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.agent import analyze_incident, get_severity_color, get_severity_emoji
from utils.data_store import save_incident, update_incident
from utils.alerts import send_alert, should_alert
from utils.report_generator import generate_incident_report
from utils.training_data import get_sample_scenario_options
from utils.project_store import get_active_project_names


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
# Add real open-source incidents (2020–present)
for label, desc in get_sample_scenario_options():
    SAMPLE_SCENARIOS[label] = desc


def render():
    st.markdown("## 📋 Report New Incident")
    st.markdown(
        '<div class="info-box">'
        '<strong>Construction site incident reporting</strong> — Enter details below. '
        'Reports are attributed to <strong>role + organization</strong> for multi-stakeholder job sites. '
        'The AI classifies severity, OSHA recordability, and supports continuous tracking from mobilization to closeout.'
        '</div>',
        unsafe_allow_html=True
    )

    # Load API key from settings
    api_key = st.session_state.get("anthropic_api_key", "")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### 📋 Incident Details")

        reported_by = st.text_input("Your Name / Reporter", placeholder="e.g. Mike Torres")
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
            custom_site = st.text_input("Custom site name", placeholder="Type the official job name")
        project = custom_site.strip() if proj_sel == "Other (custom site name)" else proj_sel

        # Sample scenario loader (includes real incidents 2020–present)
        sample = st.selectbox(
            "Quick-fill with sample scenario (demos + real incidents 2020–present)",
            list(SAMPLE_SCENARIOS.keys())
        )
        if sample != "Select a sample scenario...":
            default_desc = SAMPLE_SCENARIOS[sample]
        else:
            default_desc = ""

        description = st.text_area(
            "Describe what happened",
            value=default_desc,
            height=160,
            placeholder="Be specific: who was involved, what happened, where on site, what equipment was involved, any injuries..."
        )

    with col2:
        st.markdown("#### 📌 Tips for a good report")
        st.markdown("""
<div style="background:#FFFFFF;border:1px solid #E8E6E1;padding:18px;border-radius:10px;font-size:13px;line-height:1.8;box-shadow:0 2px 12px rgba(0,0,0,0.06);">
<div style="font-weight:700;color:#1B1B1B;margin-bottom:8px;">Include:</div>
✓ What happened & where on site<br/>
✓ Who was involved & equipment/materials<br/>
✓ Any injuries & immediate response<br/>
<br/>
<div style="font-weight:700;color:#1B1B1B;margin-bottom:8px;">AI will extract:</div>
→ Incident type & severity<br/>
→ OSHA recordability & forms (300/301)<br/>
→ Immediate actions & PDF report
</div>
""", unsafe_allow_html=True)

        if not api_key:
            st.markdown("""
<div style="background:linear-gradient(90deg,#FFF8F0,#FFFBF5);border-left:4px solid #E85D04;padding:12px 14px;margin-top:12px;font-size:12px;border-radius:0 8px 8px 0;box-shadow:0 2px 8px rgba(232,93,4,0.08);">
⚙️ <b>No API key set.</b> Running in demo mode with rule-based analysis. Add your Anthropic key in <b>Settings</b> for full AI analysis.
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

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
        _ = get_severity_color(severity)

        # Save to data store (idempotent guard via session key)
        submission_key = _submission_key_for(description_text, reporter, proj, role, org)
        if st.session_state.get("last_saved_submission_key") == submission_key and st.session_state.get("last_saved_incident_id"):
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

        # Send alert if needed
        recipient = st.session_state.get("alert_email", "")
        sendgrid_key = st.session_state.get("sendgrid_key", "")
        if should_alert(severity):
            alert_result = send_alert(incident, analysis, recipient or None, sendgrid_key or None)
            alert_sent = alert_result.get("success", False)
        else:
            alert_sent = False

        # ---- Show Results ----
        st.markdown(f"---")
        st.markdown(f"### {emoji} Analysis Complete")

        # Severity card
        sev_col, type_col, osha_col = st.columns(3)
        with sev_col:
            st.markdown(f'<span class="badge-{severity.lower()}">{severity}</span><br/><small style="color:#888;">Severity Level</small>', unsafe_allow_html=True)
        with type_col:
            st.markdown(f'<b style="font-size:15px;">{analysis.get("incident_type","—")}</b><br/><small style="color:#888;">Incident Type</small>', unsafe_allow_html=True)
        with osha_col:
            osha_text = "⚠️ OSHA RECORDABLE" if analysis.get("osha_recordable") else "✅ Not Recordable"
            st.markdown(f'<b style="font-size:14px;">{osha_text}</b><br/><small style="color:#888;">OSHA Status</small>', unsafe_allow_html=True)

        st.markdown("---")

        r1, r2 = st.columns(2)
        with r1:
            st.markdown("**AI Summary**")
            st.markdown(f'<div class="incident-card"><p>{analysis.get("summary","—")}</p></div>', unsafe_allow_html=True)

            st.markdown("**Immediate Actions Required**")
            for i, action in enumerate(analysis.get("immediate_actions_required", []), 1):
                st.markdown(
                    f'<div style="display:flex;gap:10px;margin-bottom:6px;">'
                    f'<span style="background:#FF6B00;color:white;padding:2px 8px;border-radius:3px;font-family:monospace;font-size:12px;font-weight:bold;min-width:24px;text-align:center;">{i}</span>'
                    f'<span style="font-size:13px;">{action}</span></div>',
                    unsafe_allow_html=True,
                )

        with r2:
            st.markdown("**Incident Details**")
            details = {
                "Location": analysis.get("location_on_site", "—"),
                "Person Affected": analysis.get("injured_person", "—"),
                "Body Part": analysis.get("body_part_affected", "—"),
                "Equipment": analysis.get("equipment_involved", "—"),
                "Immediate Cause": analysis.get("immediate_cause", "—"),
                "Risk Score": f'{analysis.get("risk_score","—")}/100' if analysis.get("risk_score") is not None else "—",
                "Environmental Hazard": f'{analysis.get("environmental_hazard_score","—")}/100' if analysis.get("environmental_hazard_score") is not None else "—",
                "Efficiency Score": f'{analysis.get("efficiency_score","—")}/100' if analysis.get("efficiency_score") is not None else "—",
            }
            for k, v in details.items():
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #e0d9d0;font-size:13px;">'
                    f'<span style="color:#888;">{k}</span><span style="font-weight:500;">{v}</span></div>',
                    unsafe_allow_html=True,
                )

            if analysis.get("osha_forms_required"):
                st.markdown("<br/>**OSHA Forms Required**", unsafe_allow_html=True)
                for form in analysis["osha_forms_required"]:
                    st.markdown(
                        f'<span style="background:#fff8f0;border:1px solid #FF6B00;padding:3px 10px;border-radius:3px;font-family:monospace;font-size:12px;margin-right:6px;">{form}</span>',
                        unsafe_allow_html=True,
                    )

            if analysis.get("evidence_snippets"):
                with st.expander("Why this severity/risk (evidence)"):
                    for sn in analysis.get("evidence_snippets", []):
                        st.markdown(f"- {sn}")

            if alert_sent:
                st.success("✉️ Alert dispatched to safety manager")

            # Sustainability + efficiency
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

        # OSHA reason
        st.markdown(f'<div class="info-box"><b>OSHA Rationale:</b> {analysis.get("osha_reason","—")}</div>', unsafe_allow_html=True)

        st.markdown("---")

        # Generate PDF
        st.markdown("**Generate Official Report**")
        if st.button("📄 Generate OSHA-Formatted PDF Report"):
            try:
                pdf_bytes = generate_incident_report(incident)
                update_incident(incident_id, {"report_generated": True})
                fname = f"incident_report_{incident_id[:8]}_{datetime.now().strftime('%Y%m%d')}.pdf"
                st.download_button(
                    label="⬇️ Download PDF Report",
                    data=pdf_bytes,
                    file_name=fname,
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.success("PDF report generated successfully!")
            except ImportError:
                st.error("ReportLab not installed. Run: pip install reportlab")
            except Exception as e:
                st.error(f"Error generating PDF: {e}")

        if analysis.get("_api_error"):
            st.caption(f"ℹ️ Demo mode (rule-based): {analysis['_api_error'][:100]}")

    # If a background Claude analysis job is running, show a check button instead of blocking.
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

    if st.button("🤖 Analyze & Submit Incident", use_container_width=True):
        if not description.strip():
            st.error("Please describe the incident before submitting.")
            return
        if not reported_by.strip():
            st.error("Please enter your name.")
            return
        if proj_sel == "Other (custom site name)" and not (custom_site or "").strip():
            st.error("Enter a custom site name, or pick a registered project.")
            return

        submission_key = _submission_key_for(
            description, reported_by, project, stakeholder_role, organization
        )
        if api_key:
            # Start Claude analysis in a background thread to keep the UI responsive.
            future = _ANALYSIS_EXECUTOR.submit(analyze_incident, description, api_key=api_key or None)
            st.session_state["analysis_job"] = {
                "status": "running",
                "future": future,
                "submission_key": submission_key,
                "description": description,
                "reported_by": reported_by,
                "project": project,
                "stakeholder_role": stakeholder_role,
                "organization": organization,
            }
            st.info("AI analysis started in background. Click 'Check analysis status' when ready.")
        else:
            with st.spinner("AI agent analyzing incident..."):
                analysis = analyze_incident(description, api_key=None)
            _render_results(
                description_text=description,
                reporter=reported_by,
                proj=project,
                role=stakeholder_role,
                org=organization,
                analysis=analysis,
            )


# NOTE:
# `app.py` imports these page modules for navigation. To avoid duplicate widget
# IDs, `app.py` sets `SAPIENTIA_SKIP_RENDER=1` before importing.
# When you open a page directly via Streamlit's `pages/` multipage sidebar,
# that env var is not set, so the page should render normally.

if os.environ.get("SAPIENTIA_SKIP_RENDER") != "1":
    render()
