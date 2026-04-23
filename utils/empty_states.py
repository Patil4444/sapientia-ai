"""Reusable HTML empty-state blocks for Sapientia (use with st.markdown(..., unsafe_allow_html=True))."""

from __future__ import annotations

import html


def no_incidents_empty_state() -> str:
    return (
        '<div class="sap-glass-panel sap-glass-panel--center sap-glass-panel--spacious">'
        '<div style="font-size:28px;color:#00D68F;margin-bottom:10px;">✓</div>'
        '<div style="font-size:16px;color:#00D68F;font-weight:600;">All clear</div>'
        '<div style="font-size:13px;color:#8899AA;margin-top:8px;line-height:1.5;">No incidents reported yet</div>'
        "</div>"
    )


def no_critical_empty_state(timestamp_display: str) -> str:
    ts = html.escape(timestamp_display)
    return (
        '<div class="sap-glass-panel sap-glass-panel--center" style="padding:22px 20px;">'
        '<div style="font-size:22px;color:#8899AA;margin-bottom:8px;">🛡</div>'
        '<div style="font-size:16px;color:#00D68F;font-weight:600;">No critical incidents</div>'
        f'<div style="font-size:12px;color:#3D5068;margin-top:8px;">System nominal · last checked {ts}</div>'
        "</div>"
    )


def loading_state(message: str) -> str:
    msg = html.escape(message)
    return (
        '<div class="sap-glass-panel" style="display:flex;align-items:center;gap:12px;padding:14px 16px;">'
        '<span class="sap-loading-dot"></span>'
        f'<span style="font-size:13px;color:#8899AA;">{msg}</span>'
        "</div>"
    )


def error_state(message: str) -> str:
    msg = html.escape(message)
    return (
        '<div style="padding:16px;background:#1A0A0A;border:1px solid #FF4444;border-radius:12px;">'
        '<div style="font-size:13px;color:#FF4444;font-weight:700;margin-bottom:6px;">⚠ Something went wrong</div>'
        f'<div style="font-size:13px;color:#8899AA;line-height:1.5;">{msg}</div>'
        '<div style="font-size:12px;color:#3D5068;margin-top:10px;">Try again in a moment or refresh the page.</div>'
        "</div>"
    )
