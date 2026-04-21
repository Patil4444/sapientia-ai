import streamlit as st
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.data_store import load_incidents
from utils.project_store import load_projects, add_project, update_project, get_active_project_names
from utils.verification import compute_signals, stakeholder_rollup


def render():
    st.markdown("## 🏗️ Project Hub")
    st.markdown(
        '<div class="info-box">'
        "<strong>Lifecycle command center</strong> — Pick the job site you are tracking, register projects from mobilization "
        "through closeout, and let <strong>automatic verification</strong> surface open critical items, stalled cases, "
        "OSHA documentation gaps, and repeat hazard patterns so teams spend less time manually rechecking spreadsheets."
        "</div>",
        unsafe_allow_html=True,
    )

    if "sapientia_focus_project" not in st.session_state:
        st.session_state["sapientia_focus_project"] = ""

    incidents = load_incidents()
    active_names = get_active_project_names()

    st.markdown("### 🎯 Active job site (filters Dashboard, Log & sidebar stats)")
    opts = ["— All projects —"] + active_names
    current = st.session_state["sapientia_focus_project"]
    try:
        idx = opts.index(current) if current in opts else 0
    except ValueError:
        idx = 0
    choice = st.selectbox(
        "Focus project",
        opts,
        index=idx,
        help="When set, analytics and quick stats emphasize this site only. Reporting still allows any project.",
    )
    st.session_state["sapientia_focus_project"] = "" if choice.startswith("—") else choice
    if st.session_state["sapientia_focus_project"]:
        st.caption(f"Focused on: **{st.session_state['sapientia_focus_project']}**")

    st.markdown("---")
    st.markdown("### 📋 Register & manage projects")
    c1, c2, c3 = st.columns(3)
    with c1:
        new_name = st.text_input("New project / site name", placeholder="e.g. North Campus Phase 1")
    with c2:
        start_d = st.text_input("Start date (optional)", placeholder="YYYY-MM-DD")
    with c3:
        end_d = st.text_input("Target end date (optional)", placeholder="YYYY-MM-DD")
    if st.button("➕ Add project to registry"):
        if not new_name or not new_name.strip():
            st.error("Enter a project name.")
        else:
            add_project(new_name.strip(), start_date=start_d.strip(), end_date=end_d.strip(), status="active")
            st.success(f"Added **{new_name.strip()}** — it will appear in incident reporting.")
            st.rerun()

    projects = load_projects()
    if projects:
        st.markdown("#### Registered sites")
        rows = []
        for p in projects:
            rows.append(
                {
                    "Name": p.get("name", ""),
                    "Start": p.get("start_date", "") or "—",
                    "End": p.get("end_date", "") or "—",
                    "Status": p.get("status", "active"),
                    "id": p.get("id", ""),
                }
            )
        df = pd.DataFrame(rows)
        st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)

        st.markdown("#### Archive or reactivate")
        labels = [f"{r['Name']} ({str(r['id'])[:8]}…)" for r in rows]
        picked = st.selectbox("Select project", labels, label_visibility="collapsed")
        sel_id = rows[labels.index(picked)]["id"]
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Mark archived (complete)"):
                update_project(sel_id, status="archived")
                st.success("Project archived.")
                st.rerun()
        with b2:
            if st.button("Mark active"):
                update_project(sel_id, status="active")
                st.success("Project active again.")
                st.rerun()

    st.markdown("---")
    focus = st.session_state["sapientia_focus_project"] or None
    sig = compute_signals(incidents, project_name=focus)

    st.markdown("### 🤖 Automatic verification (rule engine)")
    st.caption(
        "These checks run whenever you open this page — no manual tick-list. "
        "Use them for stand-ups, owner updates, and subcontractor reviews."
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Critical + open", sig["counts"]["critical_open"])
    m2.metric("Open > 14 days", sig["counts"]["stalled_open"])
    m3.metric("OSHA recordable, no PDF", sig["counts"]["osha_pdf_gap"])
    m4.metric("Repeat hazard groups", sig["counts"]["repeat_pattern_groups"])

    with st.expander("🔴 Critical incidents still open", expanded=sig["counts"]["critical_open"] > 0):
        if not sig["critical_open"]:
            st.success("None — all critical items are closed or no critical open cases.")
        else:
            for inc in sig["critical_open"]:
                a = inc.get("analysis") or {}
                st.markdown(f"- **{a.get('incident_type','—')}** · {inc.get('project','—')} · _{inc.get('reported_by','—')}_ · `{inc.get('id','')[:8]}…`")

    with st.expander("⏱️ Open cases older than 14 days (follow-up risk)", expanded=sig["counts"]["stalled_open"] > 0):
        if not sig["stalled_open"]:
            st.info("No stalled open cases in this scope.")
        else:
            for inc in sig["stalled_open"]:
                a = inc.get("analysis") or {}
                st.markdown(
                    f"- **{a.get('severity','—')}** {a.get('incident_type','—')} · {inc.get('project','—')} · `{inc.get('id','')[:8]}…`"
                )

    with st.expander("📄 OSHA recordable without generated PDF", expanded=sig["counts"]["osha_pdf_gap"] > 0):
        if not sig["osha_pdf_gap"]:
            st.success("No documentation gaps flagged.")
        else:
            for inc in sig["osha_pdf_gap"]:
                a = inc.get("analysis") or {}
                st.markdown(f"- {inc.get('project','—')} · {a.get('incident_type','—')} · `{inc.get('id','')[:8]}…`")

    with st.expander("🔁 Repeat patterns (same type, same project, 14 days)", expanded=bool(sig["repeat_patterns"])):
        if not sig["repeat_patterns"]:
            st.caption("No repeated incident types in the rolling window for this scope.")
        else:
            for rp in sig["repeat_patterns"]:
                st.markdown(
                    f"- **{rp['incident_type']}** on **{rp['project'] or '—'}** — **{rp['count']}** reports in window"
                )

    st.markdown("---")
    st.markdown("### 👷 Reports by stakeholder (subcontractors & partners)")
    roll = stakeholder_rollup(incidents, project_name=focus)
    if not roll:
        st.info("No incidents in this scope yet.")
    else:
        st.dataframe(pd.DataFrame(roll), use_container_width=True, hide_index=True)


if os.environ.get("SAPIENTIA_SKIP_RENDER") != "1":
    render()
