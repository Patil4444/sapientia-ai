try:
    import streamlit as st
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        "Missing dependency `streamlit`. Install it with `pip install -r requirements.txt` "
        "inside your virtual environment, then run the app using `streamlit run app.py`."
    ) from e
import sys
import os

# If someone runs `python app.py` directly, Streamlit's ScriptRunContext will be missing.
# Detect that case early and show a clear actionable message.
try:
    import logging
    from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx

    # When running under plain `python`, Streamlit will emit a noisy warning.
    # Reduce it so users only see the actionable message below.
    logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)

    _RUNNING_WITH_STREAMLIT = get_script_run_ctx() is not None
except Exception:
    # If Streamlit internals change, don't block app startup.
    _RUNNING_WITH_STREAMLIT = True

if not _RUNNING_WITH_STREAMLIT:
    raise SystemExit("Run this app with `streamlit run app.py` (not `python app.py`).")

# Project root must be absolute so imports work from any CWD (e.g. Streamlit server)
_PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

st.set_page_config(
    page_title="Sapientia",
    page_icon="🦺",
    layout="wide",
    initial_sidebar_state="expanded"
)

from utils.agent import resolve_anthropic_api_key
from utils.http_api import normalize_api_base, sync_backend_url_env_from_streamlit

if "sapientia_api_url_field" not in st.session_state:
    st.session_state["sapientia_api_url_field"] = normalize_api_base(
        os.environ.get("SAPIENTIA_API_URL", "")
    )
sync_backend_url_env_from_streamlit(st.session_state)

# Global CSS — dark theme + shared sap-* design tokens
st.markdown("""
<style>
:root {
  --sap-bg: #0A0E1A;
  --sap-bg-elevated: #0F1520;
  --sap-border: #1A2540;
  --sap-text: #E8EDF5;
  --sap-text-strong: #F1F5F9;
  --sap-muted: #8899AA;
  --sap-dim: #3D5068;
  --sap-accent: #00E5FF;
  --sap-radius: 10px;
  --sap-radius-sm: 6px;
}
html, body { background-color: var(--sap-bg) !important; }
[data-testid="stApp"] { background-color: var(--sap-bg) !important; color: var(--sap-text) !important; }
[data-testid="stAppViewContainer"] > .main { background-color: var(--sap-bg) !important; }
.main .block-container { background-color: var(--sap-bg) !important; color: var(--sap-text) !important; }
input, textarea, [data-baseweb="input"] input, [data-baseweb="textarea"] textarea {
  background-color: var(--sap-bg-elevated) !important; color: var(--sap-text) !important; border-color: var(--sap-border) !important;
}
[data-baseweb="select"] > div:first-child { background-color: var(--sap-bg-elevated) !important; color: var(--sap-text) !important; }
[data-baseweb="popover"] [role="listbox"] { background-color: var(--sap-bg-elevated) !important; border: 1px solid var(--sap-border) !important; }
header[data-testid="stHeader"] { background-color: var(--sap-bg) !important; }
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebar"] { background-color: var(--sap-bg-elevated) !important; }
p, span, label, div, h1, h2, h3, h4, h5, h6 { color: var(--sap-text) !important; }
.stButton > button { border: 1px solid var(--sap-border) !important; color: var(--sap-text) !important; }
.stButton > button[kind="primary"] { background-color: var(--sap-accent) !important; color: var(--sap-bg) !important; border: none !important; }

/* Shared component classes */
.sap-muted { color: var(--sap-muted) !important; }
.sap-strong { color: var(--sap-text-strong) !important; font-weight: 600; }
.sap-label-upper {
  font-size: 11px; color: var(--sap-dim) !important; letter-spacing: 0.8px;
  text-transform: uppercase; font-weight: 600; margin-bottom: 8px;
}
.sap-section-title {
  font-size: 11px; color: var(--sap-dim) !important; letter-spacing: 1px;
  text-transform: uppercase; font-weight: 700; margin: 18px 0 10px;
}
.info-box {
  background: rgba(0, 229, 255, 0.06); border: 1px solid rgba(0, 229, 255, 0.18);
  border-radius: var(--sap-radius); padding: 14px 16px; font-size: 13px;
  color: var(--sap-muted) !important; line-height: 1.6; margin-bottom: 12px;
}
.sap-glass-panel {
  background: rgba(15, 21, 32, 0.85); border: 1px solid var(--sap-border);
  border-radius: var(--sap-radius); padding: 16px 18px; margin-bottom: 12px;
}
.sap-glass-panel--stack { display: flex; flex-direction: column; gap: 4px; }
.sap-glass-panel--compact { padding: 12px 14px; }
.sap-glass-panel--center { text-align: center; }
.sap-glass-panel--spacious { padding: 28px 24px; }
.sap-glass-panel--metric { text-align: center; padding: 18px 12px; }
.sap-glass-panel--pulse-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; border-left: 3px solid var(--sap-accent);
}
.sap-grid-2 {
  display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin: 14px 0;
}
@media (max-width: 768px) { .sap-grid-2 { grid-template-columns: 1fr; } }
.sap-result-hero-wrap { margin-bottom: 14px; }
.sap-result-hero { padding: 20px 22px; }
.sap-result-meta-row {
  display: flex; flex-wrap: wrap; gap: 24px; margin: 14px 0 18px;
}
.sap-result-meta-item { min-width: 120px; }
.sap-detail-row {
  display: flex; justify-content: space-between; gap: 12px;
  padding: 8px 0; border-bottom: 1px solid var(--sap-border); font-size: 14px;
}
.sap-detail-row:last-child { border-bottom: none; }
.sap-meta-chip {
  display: inline-block; background: rgba(0, 229, 255, 0.08); border: 1px solid rgba(0, 229, 255, 0.25);
  color: var(--sap-accent) !important; border-radius: 20px; padding: 3px 10px;
  font-size: 11px; font-weight: 600; margin-right: 6px; margin-bottom: 4px;
}
.sap-kpi-num { font-size: 28px; font-weight: 800; line-height: 1.1; }
.sap-kpi-label { font-size: 11px; color: var(--sap-muted) !important; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.6px; }
.sap-feed-card { margin-bottom: 10px; }
.sap-card-left-accent { border-left: 3px solid var(--sap-accent, var(--sap-accent)); }
.sap-live-dot, .sap-loading-dot {
  display: inline-block; width: 7px; height: 7px; border-radius: 50%;
  background: #00D68F; box-shadow: 0 0 6px rgba(0, 214, 143, 0.6);
  animation: pulse-dot-open 2s ease-in-out infinite;
}
.sap-loading-dot { background: var(--sap-accent); box-shadow: 0 0 6px rgba(0, 229, 255, 0.5); }
@keyframes pulse-dot-open {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}
@keyframes pulse-critical {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 68, 68, 0.4); }
  50% { box-shadow: 0 0 0 4px rgba(255, 68, 68, 0); }
}
.sap-sev-critical { animation: pulse-critical 2s infinite; }
</style>
""", unsafe_allow_html=True)

_NAV_PAGES = [
    "⬡ Report Incident",
    "◐ Toolbox Talk",
    "◇ Project Hub",
    "◉ Dashboard",
    "≡ Incident Log",
    "◈ Investor Demo",
    "⚙ Settings",
]

_LEGACY_NAV_MAP = {
    "📋 Report Incident": "⬡ Report Incident",
    "🏗️ Project Hub": "◇ Project Hub",
    "📊 Dashboard": "◉ Dashboard",
    "📁 Incident Log": "≡ Incident Log",
    "🚀 Investor Demo": "◈ Investor Demo",
    "⚙️ Settings": "⚙ Settings",
}

if "sapientia_nav_page" not in st.session_state:
    st.session_state.sapientia_nav_page = _NAV_PAGES[0]

_prev_nav = st.session_state.sapientia_nav_page
if _prev_nav in _LEGACY_NAV_MAP:
    st.session_state.sapientia_nav_page = _LEGACY_NAV_MAP[_prev_nav]

if st.session_state.sapientia_nav_page not in _NAV_PAGES:
    st.session_state.sapientia_nav_page = _NAV_PAGES[0]

# Sidebar navigation
with st.sidebar:
    st.markdown(
        '<div style="padding:8px 4px 10px;">'
        '<div style="font-size:19px;font-weight:800;letter-spacing:-0.4px;background:linear-gradient(100deg,#F8FAFC 0%,#A5F3FC 75%,#22D3EE 100%);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;font-family:Outfit,Inter,sans-serif;">⬡ Sapientia</div>'
        '<div style="font-size:11px;color:#3D5068;margin-top:4px;">Safety Intelligence</div>'
        '<div style="display:flex;align-items:center;gap:8px;margin-top:12px;">'
        '<span class="sap-live-dot"></span>'
        '<span style="font-size:10px;color:#3D5068;">Live</span>'
        "</div>"
        '</div>'
        '<div style="height:1px;background:#1A2540;margin:8px 0 14px;"></div>',
        unsafe_allow_html=True,
    )

    sel = st.session_state.sapientia_nav_page
    for i, label in enumerate(_NAV_PAGES):
        if st.button(
            label,
            key=f"sap_nav_{i}",
            use_container_width=True,
            type="primary" if label == sel else "secondary",
        ):
            st.session_state.sapientia_nav_page = label

    page = st.session_state.sapientia_nav_page

    st.markdown(
        '<div style="height:1px;background:#1A2540;margin:18px 0 12px;"></div>'
        '<div style="font-size:11px;color:#3D5068;letter-spacing:0.8px;text-transform:uppercase;margin-bottom:8px;">Quick Stats</div>',
        unsafe_allow_html=True,
    )

    from utils.data_store import load_incidents

    incidents = load_incidents()
    focus = st.session_state.get("sapientia_focus_project") or ""
    if focus:
        incidents = [i for i in incidents if (i.get("project") or "") == focus]
        st.caption(f"Focus: **{focus}**")
    total = len(incidents)
    critical = sum(1 for i in incidents if i.get("analysis", {}).get("severity") == "CRITICAL")

    _demo_mode = not resolve_anthropic_api_key(st.session_state.get("anthropic_api_key", ""))
    _demo_badge = (
        '<span class="sap-meta-chip" style="font-size:9px;margin-top:6px;margin-right:0;">Demo mode</span>'
        if _demo_mode
        else ""
    )
    st.markdown(
        f'<div style="font-size:13px;color:#8899AA;line-height:1.6;">'
        f"<strong style=\"color:#F1F5F9;\">{total}</strong> incidents · "
        f"<strong style=\"color:#FF4444;\">{critical}</strong> critical"
        f"</div>"
        f'<div style="margin-top:14px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;">'
        f'<span style="font-size:10px;color:#3D5068;">v2.0 · Phase 1</span>{_demo_badge}</div>',
        unsafe_allow_html=True,
    )

# Route pages (with error handling so failed pages show a clear message)
try:
    # `pages/*.py` are Streamlit multipage modules too. Since we import them here
    # and call `render()` manually, we set an env flag temporarily so they don't
    # auto-render during import (avoids duplicate widget IDs).
    _prev_skip_render = os.environ.get("SAPIENTIA_SKIP_RENDER")
    os.environ["SAPIENTIA_SKIP_RENDER"] = "1"
    try:
        if page == "⬡ Report Incident":
            from pages import report_page
            report_page.render()
        elif page == "◐ Toolbox Talk":
            from pages import toolbox_talk_page
            toolbox_talk_page.render()
        elif page == "◇ Project Hub":
            from pages import project_hub_page
            project_hub_page.render()
        elif page == "◉ Dashboard":
            from pages import dashboard_page
            dashboard_page.render()
        elif page == "≡ Incident Log":
            from pages import log_page
            log_page.render()
        elif page == "◈ Investor Demo":
            from pages import demo_page
            demo_page.render()
        elif page == "⚙ Settings":
            from pages import settings_page
            settings_page.render()
    finally:
        if _prev_skip_render is None:
            os.environ.pop("SAPIENTIA_SKIP_RENDER", None)
        else:
            os.environ["SAPIENTIA_SKIP_RENDER"] = _prev_skip_render
except Exception as e:
    st.error(f"**Error loading page**")
    st.exception(e)
