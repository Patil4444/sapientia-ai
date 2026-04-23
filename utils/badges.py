"""HTML badge helpers for severity and status (used with st.markdown(..., unsafe_allow_html=True))."""


def get_severity_badge(severity: str) -> str:
    sev = (severity or "LOW").strip().upper()
    base = (
        "display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;"
        "letter-spacing:1px;text-transform:uppercase;font-family:Inter,system-ui,sans-serif;"
    )
    if sev == "CRITICAL":
        return (
            f'<span class="sap-sev-critical" style="{base}'
            f"background:#1A0A0A;border:1px solid #FF4444;color:#FF4444;"
            f'animation:pulse-critical 2s infinite;">{sev}</span>'
        )
    if sev == "MEDIUM":
        return (
            f'<span style="{base}'
            f"background:#1A1200;border:1px solid #FFB020;color:#FFB020;"
            '">' + sev + "</span>"
        )
    if sev == "LOW":
        return (
            f'<span style="{base}'
            f"background:#0A1A0A;border:1px solid #00D68F;color:#00D68F;"
            '">' + sev + "</span>"
        )
    return (
        f'<span style="{base}'
        f"background:#0F1520;border:1px solid #1A2540;color:#8899AA;"
        f'">{sev}</span>'
    )


def get_status_dot(status: str) -> str:
    st = (status or "Open").strip()
    dot_base = (
        "display:inline-block;width:6px;height:6px;border-radius:50%;"
        "vertical-align:middle;margin-right:6px;"
    )
    if st == "Open":
        return (
            f'<span style="{dot_base}background:#00D68F;'
            f'animation:pulse-dot-open 2s ease-in-out infinite;"></span>'
            f'<span style="font-size:12px;color:#8899AA;">{st}</span>'
        )
    if st == "In Progress":
        return (
            f'<span style="{dot_base}background:#FFB020;"></span>'
            f'<span style="font-size:12px;color:#8899AA;">{st}</span>'
        )
    if st == "Closed":
        return (
            f'<span style="{dot_base}background:#3D5068;"></span>'
            f'<span style="font-size:12px;color:#8899AA;">{st}</span>'
        )
    return (
        f'<span style="{dot_base}background:#3D5068;"></span>'
        f'<span style="font-size:12px;color:#8899AA;">{st}</span>'
    )
