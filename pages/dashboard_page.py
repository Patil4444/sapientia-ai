import html
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.badges import get_severity_badge, get_status_dot
from utils.data_store import load_incidents
from utils.empty_states import (
    no_critical_empty_state,
    no_incidents_empty_state,
)


def _parse_iso_ts(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


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
        Dashboard
    </h1>
</div>
""", unsafe_allow_html=True)
    focus = st.session_state.get("sapientia_focus_project") or ""
    incidents = load_incidents()
    if focus:
        incidents = [i for i in incidents if (i.get("project") or "") == focus]

    updated_slot = st.empty()
    now_utc = datetime.now(timezone.utc)
    updated_slot.markdown(
        f'<p class="sap-muted" style="margin:0;text-align:right;font-size:13px;">Updated {now_utc.strftime("%H:%M")} UTC</p>',
        unsafe_allow_html=True,
    )

    week_start = now_utc - timedelta(days=7)

    def _in_week(inc: dict) -> bool:
        dt = _parse_iso_ts(inc.get("timestamp") or "")
        if not dt:
            return False
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt >= week_start

    week_incidents = [i for i in incidents if _in_week(i)]
    crit_week = sum(
        1
        for i in week_incidents
        if (i.get("analysis") or {}).get("severity") == "CRITICAL"
    )
    type_ctr = Counter(
        (i.get("analysis") or {}).get("incident_type") or "Unknown" for i in incidents
    )
    top_type, top_n = type_ctr.most_common(1)[0] if type_ctr else ("—", 0)

    trend = (
        f"{top_type} trending up"
        if top_n > 1 and top_type != "—"
        else "No recurring pattern detected"
        if incidents
        else "Awaiting first report"
    )
    pulse_line = (
        f"{len(week_incidents)} incidents this week · {crit_week} critical · {trend}"
        if incidents
        else "No incidents yet — reporting pipeline ready"
    )

    st.markdown(
        f'<div class="sap-glass-panel--pulse-bar">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#00D68F;'
        f'animation:pulse-dot-open 2s ease-in-out infinite;"></span>'
        f'<span class="sap-muted" style="font-size:11px;letter-spacing:0.8px;text-transform:uppercase;">Monitoring</span></div>'
        f'<div style="flex:1;text-align:center;font-size:14px;color:#F1F5F9;font-weight:500;">{html.escape(pulse_line)}</div>'
        f'<div style="min-width:140px;"></div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    if not incidents:
        st.markdown(no_incidents_empty_state(), unsafe_allow_html=True)
        return

    critical_list = [
        i
        for i in incidents
        if (i.get("analysis") or {}).get("severity") == "CRITICAL"
    ]

    crit_count = len(critical_list)
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">'
        f'<span style="font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#FF4444;font-weight:700;">CRITICAL NOW</span>'
        f'<span style="background:#1A0A0A;border:1px solid #FF4444;color:#FF4444;font-size:11px;font-weight:700;'
        f'padding:2px 10px;border-radius:20px;">{crit_count}</span></div>',
        unsafe_allow_html=True,
    )

    checked_display = datetime.now(timezone.utc).strftime("%b %d, %Y %H:%M UTC")
    if not critical_list:
        st.markdown(no_critical_empty_state(checked_display), unsafe_allow_html=True)
    else:
        for inc in sorted(
            critical_list, key=lambda x: x.get("timestamp") or "", reverse=True
        ):
            _render_critical_card(inc)

    total = len(incidents)
    critical = sum(
        1 for i in incidents if (i.get("analysis") or {}).get("severity") == "CRITICAL"
    )
    open_cases = sum(1 for i in incidents if i.get("status") == "Open")
    week_n = len(week_incidents)

    mcols = st.columns(4)
    metric_specs = [
        ("Total incidents", total, "#F1F5F9"),
        ("Critical", critical, "#FF4444"),
        ("Open cases", open_cases, "#FFB020"),
        ("This week", week_n, "#00E5FF"),
    ]
    for col, (label, val, colr) in zip(mcols, metric_specs):
        with col:
            st.markdown(
                f'<div class="sap-glass-panel sap-glass-panel--metric">'
                f'<div class="sap-kpi-num" style="color:{colr};">{val}</div>'
                f'<div class="sap-kpi-label">{html.escape(label)}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown('<div class="sap-section-title">RECENT ACTIVITY</div>', unsafe_allow_html=True)

    sorted_feed = sorted(
        incidents, key=lambda x: x.get("timestamp") or "", reverse=True
    )[:10]

    border_for = {
        "CRITICAL": "#FF4444",
        "MEDIUM": "#FFB020",
        "LOW": "#00D68F",
    }

    for inc in sorted_feed:
        a = inc.get("analysis") or {}
        sev = (a.get("severity") or "LOW").upper()
        left_b = border_for.get(sev, "#1A2540")
        dt = _parse_iso_ts(inc.get("timestamp") or "")
        ts_disp = dt.strftime("%b %d %H:%M") if dt else html.escape(
            inc.get("timestamp") or "—"
        )
        itype = html.escape(a.get("incident_type") or "—")
        raw_desc = inc.get("raw_description") or a.get("summary") or "—"
        desc_short = html.escape(raw_desc[:220]) + (
            "…" if len(raw_desc) > 220 else ""
        )
        proj = html.escape(inc.get("project") or "—")
        rep = html.escape(inc.get("reported_by") or "—")
        status = inc.get("status") or "Open"

        st.markdown(
            f'<div class="sap-feed-card sap-glass-panel sap-glass-panel--compact sap-card-left-accent" '
            f'style="--sap-accent:{left_b};">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:8px;">'
            f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
            f"{get_severity_badge(sev)}"
            f'<span style="font-size:14px;font-weight:600;color:#F1F5F9;">{itype}</span></div>'
            f'<span class="sap-muted" style="font-size:11px;white-space:nowrap;">{html.escape(ts_disp)}</span></div>'
            f'<p style="margin:0 0 10px 0;font-size:14px;color:#8899AA;line-height:1.55;display:-webkit-box;'
            f'-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">{desc_short}</p>'
            f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">'
            f'<span class="sap-muted" style="font-size:12px;">{proj} · {rep}</span>'
            f'<span style="display:inline-flex;align-items:center;">{get_status_dot(status)}</span></div>'
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_critical_card(inc: dict) -> None:
    a = inc.get("analysis") or {}
    sev = (a.get("severity") or "CRITICAL").upper()
    dt = _parse_iso_ts(inc.get("timestamp") or "")
    ts_disp = dt.strftime("%b %d %H:%M") if dt else html.escape(
        inc.get("timestamp") or "—"
    )
    itype = html.escape(a.get("incident_type") or "—")
    raw_desc = inc.get("raw_description") or a.get("summary") or "—"
    desc_short = html.escape(raw_desc[:220]) + ("…" if len(raw_desc) > 220 else "")
    proj = html.escape(inc.get("project") or "—")
    rep = html.escape(inc.get("reported_by") or "—")
    status = inc.get("status") or "Open"

    st.markdown(
        f'<div class="sap-glass-panel sap-glass-panel--compact sap-card-left-accent" '
        f'style="--sap-accent:#FF4444;margin-bottom:12px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:8px;">'
        f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
        f"{get_severity_badge(sev)}"
        f'<span style="font-size:14px;font-weight:600;color:#F1F5F9;">{itype}</span></div>'
        f'<span class="sap-muted" style="font-size:11px;">{html.escape(ts_disp)}</span></div>'
        f'<p style="margin:0 0 10px 0;font-size:14px;color:#8899AA;line-height:1.55;display:-webkit-box;'
        f'-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">{desc_short}</p>'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span class="sap-muted" style="font-size:12px;">{proj} · {rep}</span>'
        f'<span style="display:inline-flex;align-items:center;">{get_status_dot(status)}</span></div>'
        f"</div>",
        unsafe_allow_html=True,
    )


# When opened via Streamlit multipage sidebar, env var is unset → render here.
if os.environ.get("SAPIENTIA_SKIP_RENDER") != "1":
    render()
