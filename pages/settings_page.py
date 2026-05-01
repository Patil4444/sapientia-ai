import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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
    st.markdown(
        '<div class="info-box">Configure API keys and alert preferences. Keys are stored in your session only — never saved to disk. '
        'This app does not bill you or enroll you in any plan — optional keys only call Anthropic/SendGrid under <strong>your</strong> accounts if you add them.</div>',
        unsafe_allow_html=True
    )

    st.markdown("---")

    # ---- Backend API (FastAPI) ----
    st.markdown("### 🖧 Backend API (optional)")
    st.markdown(
        "Run the FastAPI server so the Streamlit UI talks to a **shared REST API** (incidents, projects, PDFs, analysis, alerts). "
        "Leave empty to use **local JSON files** only (default)."
    )
    if "sapientia_api_url_field" not in st.session_state:
        st.session_state["sapientia_api_url_field"] = os.environ.get("SAPIENTIA_API_URL", "").strip().rstrip("/")

    st.text_input(
        "Backend base URL",
        key="sapientia_api_url_field",
        placeholder="http://127.0.0.1:8000",
        help="Start server from project root: uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000",
    )
    field_val = (st.session_state.get("sapientia_api_url_field") or "").strip().rstrip("/")
    if field_val:
        st.caption(f"Using backend: `{field_val}` (applied at start of each app run)")
        if st.button("Test backend health"):
            try:
                import httpx

                r = httpx.get(f"{field_val}/api/health", timeout=10.0)
                r.raise_for_status()
                st.success(f"✅ {r.json()}")
            except Exception as e:
                st.error(f"❌ Cannot reach backend: {e}")
    else:
        st.caption("In-process storage: `sample_data/*.json` on this machine.")

    st.markdown("---")

    # ---- Anthropic API ----
    st.markdown("### 🤖 Anthropic API (Claude AI)")
    st.markdown("Used for intelligent incident parsing and classification. [Get your API key →](https://console.anthropic.com)")

    api_key = st.text_input(
        "Anthropic API Key",
        value=st.session_state.get("anthropic_api_key",""),
        type="password",
        placeholder="sk-ant-..."
    )
    if api_key:
        st.session_state["anthropic_api_key"] = api_key
        st.success("✅ Anthropic API key saved for this session")
    else:
        st.caption("Without a key, the app uses rule-based analysis (good for demos)")

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
<div style="background:#FFFFFF;border:1px solid #E8E6E1;border-radius:10px;padding:22px;font-size:13px;line-height:1.85;box-shadow:0 2px 12px rgba(0,0,0,0.06);">
<div style="font-weight:800;font-size:1.1rem;color:#1B1B1B;margin-bottom:4px;">Sapientia</div>
<div style="color:#6B6B6B;margin-bottom:14px;">AI-powered construction safety incident reporting & OSHA compliance</div>

<div style="font-weight:700;color:#1B1B1B;margin:12px 0 6px 0;">Problem solved</div>
Manual safety reporting is slow and prone to compliance gaps. This system automates the workflow from incident description to OSHA-formatted documentation.

<div style="font-weight:700;color:#1B1B1B;margin:12px 0 6px 0;">Tech stack</div>
Python 3.11+ · Streamlit · Anthropic Claude API · ReportLab (OSHA PDFs) · SendGrid (alerts)

<div style="font-weight:700;color:#1B1B1B;margin:12px 0 6px 0;">Features</div>
• Natural language incident intake · AI severity classification (LOW / MEDIUM / CRITICAL)<br/>
• OSHA 300/301 recordability · Auto-generated reports · Safety manager alerts · Analytics dashboard

<div style="margin-top:14px;font-size:12px;color:#6B6B6B;">Built for construction — OSHA 300/301 compliant</div>
<div style="margin-top:10px;font-size:11px;color:#6B6B6B;">AI is informed by real open-source construction incidents (2020–present) from OSHA/BLS patterns so classification matches incidents this platform would have helped prevent.</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ---- Quick demo test ----
    st.markdown("### 🧪 Test API Connection")
    if st.button("Test Anthropic API Key"):
        key = st.session_state.get("anthropic_api_key","")
        if not key:
            st.error("No API key set above.")
        else:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=key)
                msg = client.messages.create(
                    model="claude-opus-4-6",
                    max_tokens=30,
                    messages=[{"role":"user","content":"Reply with: API connection successful"}]
                )
                st.success(f"✅ {msg.content[0].text}")
            except Exception as e:
                st.error(f"❌ Connection failed: {e}")


# NOTE:
# `app.py` imports these page modules for navigation. To avoid duplicate widget
# IDs, `app.py` sets `SAPIENTIA_SKIP_RENDER=1` before importing.
# When you open a page directly via Streamlit's `pages/` multipage sidebar,
# that env var is not set, so the page should render normally.

if os.environ.get("SAPIENTIA_SKIP_RENDER") != "1":
    render()
