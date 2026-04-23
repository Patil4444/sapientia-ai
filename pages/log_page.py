import streamlit as st
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.data_store import load_incidents, update_incident
from utils.report_generator import generate_incident_report


def render():
    st.markdown("## 📁 Incident Log")
    st.caption("Search and manage all construction site incident reports")

    incidents = load_incidents()
    focus = st.session_state.get("sapientia_focus_project") or ""
    if focus:
        incidents = [i for i in incidents if (i.get("project") or "") == focus]
        st.caption(f"Filtered by Project Hub focus: **{focus}**")

    if not incidents:
        st.info("No incidents recorded yet. Submit one from **Report Incident**.")
        return

    # Filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        severity_filter = st.selectbox("Filter by Severity", ["All", "CRITICAL", "MEDIUM", "LOW"])
    with col2:
        status_filter = st.selectbox("Filter by Status", ["All", "Open", "Closed"])
    with col3:
        projects = ["All"] + sorted(set(i.get("project", "") for i in incidents))
        project_filter = st.selectbox("Filter by Project", projects)
    with col4:
        roles = ["All"] + sorted(
            set((i.get("stakeholder_role") or "Not specified") for i in incidents)
        )
        role_filter = st.selectbox("Filter by stakeholder role", roles)

    # Apply filters
    filtered = incidents
    if severity_filter != "All":
        filtered = [i for i in filtered if i.get("analysis",{}).get("severity") == severity_filter]
    if status_filter != "All":
        filtered = [i for i in filtered if i.get("status") == status_filter]
    if project_filter != "All":
        filtered = [i for i in filtered if i.get("project") == project_filter]
    if role_filter != "All":
        filtered = [
            i
            for i in filtered
            if (i.get("stakeholder_role") or "Not specified") == role_filter
        ]

    # Sort by date descending
    filtered = sorted(filtered, key=lambda x: x.get("timestamp",""), reverse=True)

    st.markdown(f"**{len(filtered)} incident(s)** found")
    st.markdown("---")

    for inc in filtered:
        a = inc.get("analysis", {})
        sev = a.get("severity", "LOW")
        badge_class = f"badge-{sev.lower()}"

        try:
            dt  = datetime.fromisoformat(inc["timestamp"])
            date_str = dt.strftime("%b %d, %Y  %H:%M")
        except Exception:
            date_str = inc.get("timestamp","—")

        # Expandable card
        expander_title = f"{sev} | {a.get('incident_type','—')} | {inc.get('project','—')} | {date_str}"
        with st.expander(expander_title):
            c1, c2 = st.columns([2,1])

            with c1:
                st.markdown(f'<span class="{badge_class}">{sev}</span>', unsafe_allow_html=True)
                st.markdown(f"**{a.get('incident_type','—')}** — {inc.get('project','—')}")
                role = inc.get("stakeholder_role") or "Not specified"
                org = inc.get("organization") or ""
                org_bit = f" · {org}" if org else ""
                st.markdown(
                    f"*Reported by {inc.get('reported_by','—')} ({role}{org_bit}) on {date_str}*"
                )
                st.markdown("---")
                st.markdown("**AI Summary**")
                st.markdown(a.get("summary","—"))
                st.markdown("**Original Report**")
                st.markdown(f'<div class="incident-card"><p style="font-style:italic;">{inc.get("raw_description","—")}</p></div>', unsafe_allow_html=True)

                # Actions
                if a.get("immediate_actions_required"):
                    st.markdown("**Immediate Actions**")
                    for action in a["immediate_actions_required"]:
                        st.markdown(f"• {action}")

            with c2:
                st.markdown("**Details**")
                details = {
                    "Location":       a.get("location_on_site","—"),
                    "Person":         a.get("injured_person","—"),
                    "Body Part":      a.get("body_part_affected","—"),
                    "Equipment":      a.get("equipment_involved","—"),
                    "OSHA Recordable": "Yes ⚠️" if a.get("osha_recordable") else "No ✅",
                    "Risk Score":     f'{a.get("risk_score","—")}/100' if a.get("risk_score") is not None else "—",
                    "Environmental Hazard": f'{a.get("environmental_hazard_score","—")}/100' if a.get("environmental_hazard_score") is not None else "—",
                    "Efficiency Score": f'{a.get("efficiency_score","—")}/100' if a.get("efficiency_score") is not None else "—",
                    "Status":         inc.get("status","—"),
                    "ID":             inc.get("id","—")[:8].upper(),
                }
                for k, v in details.items():
                    st.markdown(f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #e0d9d0;font-size:12px;"><span style="color:#888;">{k}</span><span>{v}</span></div>', unsafe_allow_html=True)

                if a.get("osha_forms_required"):
                    st.markdown("<br/>**OSHA Forms**", unsafe_allow_html=True)
                    for form in a["osha_forms_required"]:
                        st.markdown(f'`{form}`')

                st.markdown("<br/>", unsafe_allow_html=True)

                if a.get("evidence_snippets"):
                    with st.expander("Evidence snippets (why the risk score)"):
                        for sn in a.get("evidence_snippets", []):
                            st.markdown(f"- {sn}")

                # ---- Corrective actions lifecycle (stored in incident JSON) ----
                st.markdown("**Corrective Actions**")
                existing_actions = inc.get("corrective_actions", [])
                if existing_actions:
                    today = datetime.now().date()
                    for idx0, act in enumerate(existing_actions):
                        idx = idx0 + 1
                        desc = act.get("description", "—")
                        owner = act.get("owner", "—") or "—"
                        due = act.get("due_date", "") or ""
                        status = act.get("status", "Planned") or "Planned"

                        due_dt = None
                        try:
                            if due:
                                due_dt = datetime.fromisoformat(due).date()
                        except Exception:
                            due_dt = None

                        with st.expander(f"Action {idx} · {status} · Due {due or '—'}"):
                            if due_dt and status not in ("Closed", "Verified") and due_dt < today:
                                st.warning(f"Overdue! Due {due_dt.isoformat()}.")
                            st.markdown(f"**Owner:** {owner}")
                            st.markdown(f"**Description:** {desc}")
                            existing_notes = act.get("completion_notes", "") or ""
                            if existing_notes:
                                st.markdown(f"**Completion notes:** {existing_notes}")

                            ca_upd_status = st.selectbox(
                                "Update status",
                                ["Planned", "In Progress", "Verified", "Closed"],
                                index=["Planned", "In Progress", "Verified", "Closed"].index(status)
                                if status in ["Planned", "In Progress", "Verified", "Closed"]
                                else 0,
                                key=f"ca_upd_status_{inc['id']}_{idx0}",
                            )
                            ca_upd_notes = st.text_area(
                                "Completion notes (store when Verified/Closed)",
                                value=existing_notes,
                                key=f"ca_upd_notes_{inc['id']}_{idx0}",
                                height=90,
                            )

                            if st.button("Save update", key=f"ca_upd_btn_{inc['id']}_{idx0}"):
                                updated = list(existing_actions)
                                updated_action = dict(updated[idx0])
                                updated_action["status"] = ca_upd_status
                                updated_action["completion_notes"] = ca_upd_notes.strip() if ca_upd_status in ("Verified", "Closed") else ""
                                if ca_upd_status in ("Verified", "Closed"):
                                    updated_action["completed_at"] = datetime.now().isoformat()
                                else:
                                    updated_action.pop("completed_at", None)
                                    updated_action["completion_notes"] = ""
                                updated[idx0] = updated_action
                                update_incident(inc["id"], {"corrective_actions": updated})
                                st.rerun()
                else:
                    st.caption("No corrective actions added yet.")

                # Sustainability + efficiency
                with st.expander("Sustainability & Efficiency (Investor View)"):
                    st.markdown("**Sustainability concerns**")
                    for c in a.get("sustainability_concerns", []):
                        st.markdown(f"- {c}")
                    st.markdown("**Sustainability actions required**")
                    for x in a.get("sustainability_actions_required", []):
                        st.markdown(f"- {x}")

                    st.markdown("---")
                    st.markdown(f"**Efficiency score:** {a.get('efficiency_score','—')}/100")
                    if a.get("efficiency_score_reason"):
                        st.caption(a.get("efficiency_score_reason"))
                    st.markdown("**Efficiency actions required**")
                    for x in a.get("efficiency_actions_required", []):
                        st.markdown(f"- {x}")

                ca_desc = st.text_area(
                    "Add corrective action",
                    key=f"ca_desc_{inc['id']}",
                    placeholder="e.g. Install rebar end caps and enforce PPE compliance in rebar zone",
                    height=90
                )
                ca_owner = st.text_input(
                    "Owner (role/name)",
                    key=f"ca_owner_{inc['id']}",
                    placeholder="e.g. Safety Manager"
                )
                ca_due = st.date_input(
                    "Due date",
                    value=datetime.now().date(),
                    key=f"ca_due_{inc['id']}"
                )
                ca_status = st.selectbox(
                    "Action status",
                    ["Planned", "In Progress", "Verified", "Closed"],
                    key=f"ca_status_{inc['id']}"
                )
                ca_completion_notes = st.text_area(
                    "Completion notes (optional; used for Verified/Closed)",
                    key=f"ca_notes_{inc['id']}",
                    height=90,
                )
                if st.button("➕ Add action", key=f"ca_add_{inc['id']}"):
                    if not ca_desc.strip():
                        st.error("Corrective action description cannot be empty.")
                    else:
                        new_action = {
                            "description": ca_desc.strip(),
                            "owner": ca_owner.strip() if ca_owner else "",
                            "due_date": ca_due.isoformat() if ca_due else "",
                            "status": ca_status,
                            "completion_notes": ca_completion_notes.strip() if ca_status in ("Verified", "Closed") else "",
                            "created_at": datetime.now().isoformat()
                        }
                        if ca_status in ("Verified", "Closed"):
                            new_action["completed_at"] = datetime.now().isoformat()
                        updated = existing_actions + [new_action]
                        update_incident(inc["id"], {"corrective_actions": updated})
                        st.rerun()

                # Status toggle
                current_status = inc.get("status","Open")
                new_status = "Closed" if current_status == "Open" else "Open"
                if st.button(f"Mark as {new_status}", key=f"status_{inc['id']}"):
                    update_incident(inc["id"], {"status": new_status})
                    st.rerun()

                # PDF export — persist bytes in session_state so download survives reruns.
                st.markdown("")
                iid = inc["id"]
                pdf_bkey = f"_log_pdf_bytes_{iid}"
                pdf_fkey = f"_log_pdf_fname_{iid}"
                if st.button("📄 Generate PDF", key=f"pdf_{iid}"):
                    try:
                        pdf = generate_incident_report(inc)
                        update_incident(inc["id"], {"report_generated": True})
                        fname = f"incident_{iid[:8]}_{datetime.now().strftime('%Y%m%d')}.pdf"
                        st.session_state[pdf_bkey] = pdf
                        st.session_state[pdf_fkey] = fname
                        st.success("PDF ready — use Download below.")
                    except ImportError:
                        st.error("pip install reportlab")
                    except Exception as e:
                        st.error(str(e))

                if st.session_state.get(pdf_bkey):
                    st.download_button(
                        "⬇️ Download",
                        data=st.session_state[pdf_bkey],
                        file_name=st.session_state.get(pdf_fkey) or "incident.pdf",
                        mime="application/pdf",
                        key=f"dl_{iid}",
                        use_container_width=True,
                    )

                if a.get("_api_error"):
                    st.caption(f"Demo mode analysis")


# NOTE:
# `app.py` imports these page modules for navigation. To avoid duplicate widget
# IDs, `app.py` sets `SAPIENTIA_SKIP_RENDER=1` before importing.
# When you open a page directly via Streamlit's `pages/` multipage sidebar,
# that env var is not set, so the page should render normally.

if os.environ.get("SAPIENTIA_SKIP_RENDER") != "1":
    render()
