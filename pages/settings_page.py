import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.agent import ANTHROPIC_MODEL, resolve_anthropic_api_key
from utils.http_api import format_backend_http_error, normalize_api_base


def _format_anthropic_connection_error(exc: Exception) -> str:
    msg = str(exc).strip()
    lower = msg.lower()
    if "no module named 'langchain_anthropic'" in lower:
        return (
            "Missing dependency `langchain-anthropic`. "
            "From the project root run: `venv\\Scripts\\python.exe -m pip install -r requirements.txt`"
        )
    if "authentication" in lower or "invalid x-api-key" in lower or "401" in lower:
        return (
            "Anthropic rejected the API key (invalid or expired). "
            "Use a key from console.anthropic.com that starts with `sk-ant-`."
        )
    if "not_found" in lower or "model" in lower and "404" in lower:
        return f"Model `{ANTHROPIC_MODEL}` not available for this key. Error: {msg}"
    return msg


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
        Settings
    </h1>
</div>
""", unsafe_allow_html=True)
    has_api_key = bool(resolve_anthropic_api_key(st.session_state.get("anthropic_api_key", "")))
    if not has_api_key:
        st.markdown(
            '<div class="info-box"><strong>Free demo mode — no API key required.</strong> '
            'Incident reports, toolbox talks, and OSHA PDFs work right away using built-in rule-based analysis. '
            'Nothing below is required to try the app.</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div class="info-box">Configure optional API keys and alert preferences. Keys are stored in your session only — never saved to disk. '
        'This app does not bill you or enroll you in any plan — paid keys only call Anthropic Claude/SendGrid under <strong>your</strong> accounts if you add them.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ---- Backend API (FastAPI) ----
    st.markdown("### 🖧 Backend API (optional)")
    st.markdown(
        "Run the FastAPI server so the Streamlit UI talks to a **shared REST API** (incidents, projects, PDFs, analysis, alerts). "
        "Leave empty to use **local JSON files** only (default)."
    )
    st.text_input(
        "Backend base URL",
        key="sapientia_api_url_field",
        placeholder="http://127.0.0.1:8000",
        help=(
            "Server root only — not /api or /docs. "
            "Start: uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"
        ),
    )
    field_val = normalize_api_base(st.session_state.get("sapientia_api_url_field") or "")
    raw_field = st.session_state.get("sapientia_api_url_field") or ""
    if raw_field and field_val != raw_field:
        st.session_state["sapientia_api_url_field"] = field_val
    if field_val:
        st.caption(
            f"Using backend: `{field_val}` · health check: `{field_val}/api/health` "
            "(applied at start of each app run)"
        )
        if st.button("Test backend health"):
            try:
                import httpx

                r = httpx.get(f"{field_val}/api/health", timeout=10.0)
                r.raise_for_status()
                st.success(f"✅ {r.json()}")
            except Exception as e:
                st.error(f"❌ {format_backend_http_error(e, field_val)}")
    else:
        st.caption("In-process storage: `sample_data/*.json` on this machine.")

    st.markdown("---")

    # ---- Anthropic Claude API ----
    st.markdown("### 🤖 Anthropic Claude API · Optional (paid)")
    st.markdown(
        f"Optional — enables live Claude AI for incident parsing and classification ({ANTHROPIC_MODEL}). "
        "Skip this section to stay in free demo mode. "
        "[Get your API key →](https://console.anthropic.com/settings/keys)"
    )

    env_key = resolve_anthropic_api_key(None) or ""
    default_key = st.session_state.get("anthropic_api_key", "") or env_key

    if os.environ.get("GOOGLE_API_KEY", "").strip() and not env_key:
        st.warning(
            "`.env` still has **GOOGLE_API_KEY** (Gemini) but no **ANTHROPIC_API_KEY**. "
            "Add a separate Anthropic key below or in `.env` — Google keys cannot be used for Claude."
        )

    api_key = st.text_input(
        "Anthropic API Key (optional, paid)",
        value=default_key,
        type="password",
        placeholder="sk-ant-... (leave blank for free demo)",
        help="Session-only. Leave blank for free demo mode. You can also set ANTHROPIC_API_KEY in the environment.",
    )
    if api_key:
        st.session_state["anthropic_api_key"] = api_key
        st.success("✅ Anthropic API key saved for this session")
    else:
        st.caption("Free demo mode — rule-based analysis works without a key")

    st.markdown("---")

    # ---- Alert Settings ----
    st.markdown("### ✉️ Email Alerts (SendGrid)")
    st.markdown("Sends real-time alerts to the safety manager for CRITICAL and MEDIUM incidents. [Get SendGrid API key →](https://sendgrid.com)")

    sendgrid_key = st.text_input(
        "SendGrid API Key",
        value=st.session_state.get("sendgrid_key",""),
        type="password",
        placeholder="SG...."
    )
    if sendgrid_key:
        st.session_state["sendgrid_key"] = sendgrid_key

    alert_email = st.text_input(
        "Safety Manager Email (alert recipient)",
        value=st.session_state.get("alert_email",""),
        placeholder="safety.manager@yourcompany.com"
    )
    if alert_email:
        st.session_state["alert_email"] = alert_email

    if sendgrid_key and alert_email:
        st.success(f"✅ Alerts will be sent to {alert_email}")
    else:
        st.caption("Without SendGrid, alerts are simulated (logged to console)")

    st.markdown("---")

    # ---- About ----
    st.markdown("### 📋 About Sapientia")
    st.markdown("""
<div class="sap-glass-panel" style="font-size:13px;line-height:1.85;">
<div style="font-weight:800;font-size:1.1rem;color:#F1F5F9;margin-bottom:4px;">Sapientia</div>
<div class="sap-muted" style="margin-bottom:14px;">AI-powered construction safety incident reporting & OSHA compliance</div>

<div style="font-weight:700;color:#F1F5F9;margin:12px 0 6px 0;">Problem solved</div>
<div class="sap-muted">Manual safety reporting is slow and prone to compliance gaps. This system automates the workflow from incident description to OSHA-formatted documentation.</div>

<div style="font-weight:700;color:#F1F5F9;margin:12px 0 6px 0;">Tech stack</div>
<div class="sap-muted">Python 3.11+ · Streamlit · Anthropic Claude Sonnet · ReportLab (OSHA PDFs) · SendGrid (alerts)</div>

<div style="font-weight:700;color:#F1F5F9;margin:12px 0 6px 0;">Features</div>
<div class="sap-muted">
• Natural language incident intake · AI severity classification (LOW / MEDIUM / CRITICAL)<br/>
• OSHA 300/301 recordability · Auto-generated reports · Safety manager alerts · Analytics dashboard
</div>

<div class="sap-muted" style="margin-top:14px;font-size:12px;">Built for construction — OSHA 300/301 compliant · v2.0 Phase 1</div>
<div class="sap-muted" style="margin-top:10px;font-size:11px;">AI is informed by real open-source construction incidents (2020–present) from OSHA/BLS patterns so classification matches incidents this platform would have helped prevent.</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ---- Quick demo test ----
    st.markdown("### 🧪 Test API Connection")
    if st.button("Test Anthropic API Key"):
        key = resolve_anthropic_api_key(st.session_state.get("anthropic_api_key", ""))
        if not key:
            st.error(
                "No Anthropic API key set. Paste a key above or add "
                "`ANTHROPIC_API_KEY=sk-ant-...` to `.env` and restart the app."
            )
        elif not key.startswith("sk-ant-"):
            st.error(
                "This does not look like an Anthropic key (expected prefix `sk-ant-`). "
                "If you pasted GOOGLE_API_KEY from the Gemini setup, replace it with a key from "
                "[Anthropic Console](https://console.anthropic.com/settings/keys)."
            )
        else:
            try:
                from langchain_core.messages import HumanMessage
                from langchain_anthropic import ChatAnthropic

                llm = ChatAnthropic(
                    model=ANTHROPIC_MODEL,
                    api_key=key,
                    max_tokens=30,
                )
                response = llm.invoke(
                    [HumanMessage(content="Reply with exactly: API connection successful")]
                )
                content = response.content if isinstance(response.content, str) else str(response.content or "")
                st.success(f"✅ {content.strip()}")
            except Exception as e:
                st.error(f"❌ Connection failed: {_format_anthropic_connection_error(e)}")


if os.environ.get("SAPIENTIA_SKIP_RENDER") != "1":
    render()
