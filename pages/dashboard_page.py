import streamlit as st
from datetime import datetime
from collections import Counter
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.data_store import load_incidents


def render():
    st.markdown("## 📊 Safety Dashboard")

    incidents = load_incidents()

    if not incidents:
        st.info("No incidents logged yet. Submit your first incident report.")
        return

    # ---- KPI Row ----
    total      = len(incidents)
    critical   = sum(1 for i in incidents if i.get("analysis", {}).get("severity") == "CRITICAL")
    medium     = sum(1 for i in incidents if i.get("analysis", {}).get("severity") == "MEDIUM")
    low        = sum(1 for i in incidents if i.get("analysis", {}).get("severity") == "LOW")
    recordable = sum(1 for i in incidents if i.get("analysis", {}).get("osha_recordable"))
    open_cases = sum(1 for i in incidents if i.get("status") == "Open")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Incidents", total)
    c2.metric("🔴 Critical",     critical)
    c3.metric("🟠 Medium",       medium)
    c4.metric("🟢 Low",          low)
    c5.metric("⚠️ OSHA Recordable", recordable)
    c6.metric("📂 Open Cases",   open_cases)

    st.markdown("---")

    col_left, col_right = st.columns(2)

    # ---- Severity Breakdown ----
    with col_left:
        st.markdown("#### Incidents by Severity")
        sev_counts = Counter(i.get("analysis", {}).get("severity", "Unknown") for i in incidents)
        for sev, color, emoji in [("CRITICAL", "#FF1744", "🔴"), ("MEDIUM", "#FF6B00", "🟠"), ("LOW", "#2E7D32", "🟢")]:
            count = sev_counts.get(sev, 0)
            pct   = int(count / total * 100) if total else 0
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
                f'<span style="width:80px;font-size:12px;font-family:monospace;">{emoji} {sev}</span>'
                f'<div style="flex:1;background:#e0d9d0;border-radius:2px;height:18px;position:relative;">'
                f'<div style="background:{color};width:{pct}%;height:100%;border-radius:2px;"></div></div>'
                f'<span style="width:30px;text-align:right;font-size:13px;font-weight:bold;">{count}</span>'
                f'<span style="width:36px;font-size:11px;color:#888;">{pct}%</span></div>',
                unsafe_allow_html=True
            )

    # ---- Incident Types ----
    with col_right:
        st.markdown("#### Incidents by Type")
        type_counts = Counter(i.get("analysis", {}).get("incident_type", "Unknown") for i in incidents)
        for itype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            pct = int(count / total * 100) if total else 0
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
                f'<span style="width:130px;font-size:12px;font-family:monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{itype}</span>'
                f'<div style="flex:1;background:#e0d9d0;border-radius:2px;height:16px;">'
                f'<div style="background:#FF6B00;width:{pct}%;height:100%;border-radius:2px;"></div></div>'
                f'<span style="width:28px;text-align:right;font-size:13px;font-weight:bold;">{count}</span></div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    col3, col4 = st.columns(2)

    # ---- Projects Breakdown ----
    with col3:
        st.markdown("#### Incidents by Project")
        proj_counts = Counter(i.get("project", "Unknown") for i in incidents)
        for proj, count in proj_counts.most_common():
            pct   = int(count / total * 100) if total else 0
            short = proj[:28] + "…" if len(proj) > 28 else proj
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px;">'
                f'<span style="width:170px;font-size:11px;white-space:nowrap;">{short}</span>'
                f'<div style="flex:1;background:#e0d9d0;border-radius:2px;height:14px;">'
                f'<div style="background:#0f0f0f;width:{pct}%;height:100%;border-radius:2px;"></div></div>'
                f'<span style="font-size:13px;font-weight:bold;">{count}</span></div>',
                unsafe_allow_html=True
            )

    # ---- OSHA Status ----
    with col4:
        st.markdown("#### OSHA Recordkeeping Status")
        forms_needed = []
        for inc in incidents:
            forms_needed.extend(inc.get("analysis", {}).get("osha_forms_required", []))
        form_counts = Counter(forms_needed)

        forms_html = "".join(
            f'<span style="background:#fff8f0;border:1px solid #FF6B00;padding:3px 10px;'
            f'border-radius:3px;font-family:monospace;font-size:12px;margin-right:6px;">'
            f'{f}: {c}</span>'
            for f, c in form_counts.items()
        ) or '<span style="font-size:12px;color:#888;">None required</span>'

        st.markdown(
            f'<div style="background:white;border:1px solid #e0d9d0;border-radius:4px;padding:16px;">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:12px;">'
            f'<div style="text-align:center;">'
            f'<div style="font-size:28px;font-weight:bold;color:#FF1744;font-family:monospace;">{recordable}</div>'
            f'<div style="font-size:11px;color:#888;">Recordable</div></div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:28px;font-weight:bold;color:#2E7D32;font-family:monospace;">{total - recordable}</div>'
            f'<div style="font-size:11px;color:#888;">Not Recordable</div></div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:28px;font-weight:bold;color:#FF6B00;font-family:monospace;">{open_cases}</div>'
            f'<div style="font-size:11px;color:#888;">Open Cases</div></div></div>'
            f'<hr style="border:none;border-top:1px solid #e0d9d0;margin:10px 0;"/>'
            f'<div style="font-size:11px;color:#888;font-weight:bold;margin-bottom:6px;">FORMS REQUIRED</div>'
            f'{forms_html}</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ---- Recent Incidents ----
    st.markdown("#### Recent Incidents")
    sorted_incidents = sorted(incidents, key=lambda x: x.get("timestamp", ""), reverse=True)[:8]

    for inc in sorted_incidents:
        a   = inc.get("analysis", {})
        sev = a.get("severity", "LOW")
        sev_color = {"CRITICAL": "#FF1744", "MEDIUM": "#FF6B00", "LOW": "#2E7D32"}.get(sev, "#888")
        status_color = "#FF6B00" if inc.get("status") == "Open" else "#888"

        try:
            dt       = datetime.fromisoformat(inc["timestamp"])
            date_str = dt.strftime("%b %d, %Y  %H:%M")
        except Exception:
            date_str = inc.get("timestamp", "—")

        osha_tag = (
            '<span style="background:#fff8f0;border:1px solid #FF6B00;padding:1px 7px;'
            'border-radius:3px;font-size:11px;font-family:monospace;margin-left:6px;">OSHA</span>'
            if a.get("osha_recordable") else ""
        )

        summary = a.get("summary", "—")
        summary_short = summary[:180] + "…" if len(summary) > 180 else summary

        st.markdown(
            f'<div style="background:white;border:1px solid #e0d9d0;border-radius:4px;'
            f'padding:14px;margin-bottom:10px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">'
            f'<div>'
            f'<span style="background:{sev_color};color:white;padding:3px 10px;border-radius:3px;'
            f'font-family:monospace;font-size:12px;font-weight:600;">{sev}</span>'
            f'<span style="font-size:13px;font-weight:600;margin-left:8px;">{a.get("incident_type", "—")}</span>'
            f'{osha_tag}</div>'
            f'<span style="font-size:11px;color:{status_color};font-family:monospace;font-weight:bold;">'
            f'{inc.get("status", "Open")}</span></div>'
            f'<p style="margin:0;font-size:12px;color:#888;">'
            f'{inc.get("project", "—")} · {date_str} · Reported by {inc.get("reported_by", "—")}</p>'
            f'<p style="margin:4px 0 0 0;font-size:13px;">{summary_short}</p>'
            f'</div>',
            unsafe_allow_html=True
        )
