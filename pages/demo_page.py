import streamlit as st
from datetime import datetime, timedelta
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.agent import analyze_incident, get_severity_color, get_severity_emoji
from utils.data_store import save_incident, update_incident, load_incidents
from utils.report_generator import generate_incident_report, generate_pitch_pack_pdf
from utils.alerts import send_alert, should_alert
from utils.project_store import get_active_project_names


def _demo_project_pool():
    names = get_active_project_names()
    if names:
        return names
    return [
        "Harbor View Tower - Phase 2",
        "Riverside Bridge Rehab",
        "Downtown Mixed-Use Development",
        "Highway 128 Expansion",
        "Waterfront Parking Structure",
    ]

# Keep demo scenarios short and high-signal for investors.
DEMO_SCENARIOS = [
    "Worker fell from scaffolding on level 8 approximately 14 feet. John Smith, carpenter. He is conscious but cannot move his legs. Ambulance called immediately. Scaffolding board gave way.",
    "Close call with the tower crane today. Load swung over workers on the east side who hadn't been cleared from the zone. Nobody was hit but it was very close. Crew wasn't notified of the lift schedule.",
    "Sub-contractor got shocked while connecting to the panel on floor 3. Didn't follow lockout tagout procedure. His hand went numb. We sent him to urgent care right away.",
    "Form release agent spilled on worker forearm. Skin is red and irritated. Washed with water for 20 minutes. No blisters. Worker needs to see occupational health.",
    "Worker cut his right hand on exposed rebar end. Small laceration, treated with first aid kit on site. Applied bandage. Worker returned to work.",
]


def render():
    st.markdown("## 🚀 Investor Demo (End-to-End)")
    st.markdown(
        "Run a one-click demo that creates incidents, runs AI analysis (Claude if API key is set), generates PDFs, and triggers alerts for CRITICAL/MEDIUM. "
        "Use it to demonstrate real business value quickly."
    )

    api_key = st.session_state.get("anthropic_api_key", "")
    sendgrid_key = st.session_state.get("sendgrid_key", "")
    recipient = st.session_state.get("alert_email", "")

    colA, colB = st.columns(2)
    with colA:
        run_count = st.slider("How many demo incidents?", min_value=1, max_value=5, value=3)
    with colB:
        generate_pdfs = st.toggle("Generate PDFs (slower, but impressive)", value=True)

    reporter = st.text_input("Demo reporter name", value="Investor Demo User")

    if st.button("⚡ Run end-to-end demo", type="primary", use_container_width=True):
        if not reporter.strip():
            st.error("Please enter a reporter name.")
            return

        st.session_state.pop("_pitch_pdf_bytes", None)
        st.session_state.pop("_pitch_pdf_fname", None)

        run_count = int(run_count)
        chosen = DEMO_SCENARIOS[:run_count]
        results = []

        pool = _demo_project_pool()
        with st.spinner("Running demo pipeline..."):
            for idx, desc in enumerate(chosen):
                project = pool[idx % len(pool)]

                analysis = analyze_incident(desc, api_key=api_key or None)
                sev = analysis.get("severity", "LOW")
                emoji = get_severity_emoji(sev)

                incident = {
                    "reported_by": reporter.strip(),
                    "project": project,
                    "stakeholder_role": "General contractor (GC)",
                    "organization": "Investor demo",
                    "raw_description": desc,
                    "analysis": analysis,
                    "status": "Open",
                    "report_generated": False,
                }

                incident_id = save_incident(incident)
                incident["id"] = incident_id

                pdf_generated = False
                if generate_pdfs:
                    try:
                        _pdf_bytes = generate_incident_report(incident)
                        update_incident(incident_id, {"report_generated": True})
                        pdf_generated = True
                    except ImportError:
                        pdf_generated = False
                    except Exception:
                        pdf_generated = False

                alert_sent = False
                if should_alert(sev):
                    try:
                        _res = send_alert(
                            incident=incident,
                            analysis=analysis,
                            recipient_email=recipient or None,
                            sendgrid_key=sendgrid_key or None,
                        )
                        alert_sent = bool(_res.get("success", False))
                    except Exception:
                        alert_sent = False

                llm = analysis.get("_llm", {})
                results.append(
                    {
                        "incident_id": incident_id[:8].upper(),
                        "severity": sev,
                        "incident_type": analysis.get("incident_type", "—"),
                        "osha_recordable": analysis.get("osha_recordable"),
                        "risk_score": analysis.get("risk_score", "—"),
                        "environmental_hazard_score": analysis.get("environmental_hazard_score", "—"),
                        "efficiency_score": analysis.get("efficiency_score", "—"),
                        "sustainability_top_concern": (analysis.get("sustainability_concerns") or ["—"])[0],
                        "efficiency_top_action": (analysis.get("efficiency_actions_required") or ["—"])[0],
                        "pdf_generated": pdf_generated,
                        "alert_sent": alert_sent,
                        "llm_mode": llm.get("mode", "fallback"),
                        "latency_s": llm.get("latency_seconds"),
                    }
                )

        # ---- Show results ----
        st.success("Demo completed. Check Dashboard + Incident Log for the created records.")

        st.markdown("---")
        st.markdown("### Run Summary")
        c1, c2, c3, c4 = st.columns(4)
        total = len(results)
        critical = sum(1 for r in results if r["severity"] == "CRITICAL")
        medium = sum(1 for r in results if r["severity"] == "MEDIUM")
        recordable = sum(1 for r in results if r["osha_recordable"])
        c1.metric("Total created", total)
        c2.metric("CRITICAL", critical)
        c3.metric("MEDIUM", medium)
        c4.metric("OSHA Recordable", recordable)

        st.markdown("---")
        st.markdown("### Per-incident Output")
        # Streamlit can render a list of dicts as a table.
        st.dataframe(results, use_container_width=True)

        st.markdown("---")
        st.markdown("### Investor Pitch Pack Export")
        st.caption("Exports a single PDF summarizing risk distribution, OSHA recordability, avg efficiency/ESG hazard, and top actions.")
        if st.button("📄 Generate Investor Pitch Pack PDF", use_container_width=True, key="pitch_pack_btn"):
            try:
                all_incidents = load_incidents()
                pdf_bytes = generate_pitch_pack_pdf(all_incidents)
                filename = f"constructsafe_investor_pitch_pack_{datetime.now().strftime('%Y%m%d')}.pdf"
                st.session_state["_pitch_pdf_bytes"] = pdf_bytes
                st.session_state["_pitch_pdf_fname"] = filename
                st.success("Pitch pack generated — use **Download** below.")
            except ImportError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Error generating Pitch Pack: {e}")

        if st.session_state.get("_pitch_pdf_bytes"):
            st.download_button(
                label="⬇️ Download Pitch Pack PDF",
                data=st.session_state["_pitch_pdf_bytes"],
                file_name=st.session_state.get("_pitch_pdf_fname") or "pitch_pack.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="dl_pitch_pack_pdf",
            )


# NOTE:
# This file is a Streamlit multipage module too. When `app.py` imports it for
# navigation, we want to avoid auto-render. Use the same env flag pattern.
if os.environ.get("SAPIENTIA_SKIP_RENDER") != "1":
    render()

