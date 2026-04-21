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

st.set_page_config(
    page_title="Sapientia",
    page_icon="🦺",
    layout="wide",
    initial_sidebar_state="expanded"
)

from utils.http_api import sync_backend_url_env_from_streamlit

sync_backend_url_env_from_streamlit(st.session_state)

# Custom CSS — modern construction & safety theme
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');

:root {
    --safety-orange: #E85D04;
    --safety-orange-dark: #DC2F02;
    --high-vis: #F4A261;
    --caution-yellow: #E9C46A;
    --charcoal: #1B1B1B;
    --slate: #2D2D2D;
    --concrete: #6B6B6B;
    --off-white: #FAFAF8;
    --card-bg: #FFFFFF;
    --border-light: #E8E6E1;
    --success: #2A9D8F;
    --danger: #E63946;
}

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* Main app — construction site feel */
.stApp {
    background: linear-gradient(165deg, #F8F7F5 0%, #EDEBE8 50%, #E8E6E1 100%);
    background-attachment: fixed;
}

/* Top status bar — hazard stripe inspired */
.status-bar {
    background: linear-gradient(90deg, var(--charcoal) 0%, var(--slate) 50%, var(--charcoal) 100%);
    color: var(--high-vis);
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 600;
    padding: 10px 24px;
    letter-spacing: 2px;
    text-transform: uppercase;
    border-bottom: 3px solid var(--safety-orange);
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.status-bar::before {
    content: "⚠ ";
    opacity: 0.9;
}

/* Sidebar — modern dark construction panel */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1B1B1B 0%, #252525 100%) !important;
    border-right: 4px solid var(--safety-orange) !important;
    box-shadow: 4px 0 20px rgba(0,0,0,0.2);
}
[data-testid="stSidebar"] * {
    color: #E8E8E8 !important;
}
[data-testid="stSidebar"] .stRadio label {
    font-weight: 500 !important;
    padding: 8px 12px !important;
    border-radius: 8px !important;
    transition: all 0.2s ease;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(232, 93, 4, 0.15) !important;
}
[data-testid="stSidebar"] .stRadio label[data-checked="true"] {
    background: linear-gradient(135deg, var(--safety-orange) 0%, var(--safety-orange-dark) 100%) !important;
    color: white !important;
}

/* Page headers */
h1, h2, h3 {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    color: var(--charcoal) !important;
    letter-spacing: -0.02em;
}
h2 { font-size: 1.6rem !important; border-left: 4px solid var(--safety-orange); padding-left: 14px; margin-top: 0.5rem !important; }
h3 { font-size: 1.2rem !important; color: var(--slate) !important; }

/* Metric / KPI cards — construction dashboard style */
[data-testid="metric-container"] {
    background: var(--card-bg) !important;
    border: 1px solid var(--border-light) !important;
    border-left: 4px solid var(--safety-orange) !important;
    padding: 16px 18px !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}
[data-testid="metric-container"] label {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    color: var(--concrete) !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Buttons — safety CTA style */
.stButton > button {
    background: linear-gradient(135deg, var(--safety-orange) 0%, var(--safety-orange-dark) 100%) !important;
    color: white !important;
    border: none !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.3px !important;
    border-radius: 8px !important;
    padding: 0.5rem 1.25rem !important;
    box-shadow: 0 4px 14px rgba(232, 93, 4, 0.35);
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(232, 93, 4, 0.45) !important;
    background: linear-gradient(135deg, #F0690A 0%, #E85D04 100%) !important;
}

/* Severity badges — high-visibility */
.badge-critical { background: linear-gradient(135deg, #E63946 0%, #C1121F 100%); color: white; padding: 5px 12px; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 2px 6px rgba(230,57,70,0.4); }
.badge-medium   { background: linear-gradient(135deg, var(--safety-orange) 0%, var(--safety-orange-dark) 100%); color: white; padding: 5px 12px; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 2px 6px rgba(232,93,4,0.4); }
.badge-low      { background: linear-gradient(135deg, #2A9D8F 0%, #238276 100%); color: white; padding: 5px 12px; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 2px 6px rgba(42,157,143,0.4); }

/* Incident / content cards */
.incident-card {
    background: var(--card-bg);
    border: 1px solid var(--border-light);
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 14px;
    font-family: 'Plus Jakarta Sans', sans-serif;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s ease;
}
.incident-card:hover {
    box-shadow: 0 4px 18px rgba(0,0,0,0.08);
}
.incident-card h4 { margin: 0 0 8px 0; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 15px; font-weight: 700; color: var(--charcoal); }
.incident-card p  { margin: 4px 0; font-size: 13px; color: var(--concrete); line-height: 1.5; }

/* Info / notice boxes */
.info-box {
    background: linear-gradient(90deg, #FFF8F0 0%, #FFFBF5 100%);
    border-left: 4px solid var(--safety-orange);
    padding: 14px 18px;
    margin: 10px 0;
    font-size: 13px;
    border-radius: 0 8px 8px 0;
    box-shadow: 0 2px 8px rgba(232,93,4,0.08);
    font-weight: 500;
}

/* Section divider */
hr {
    border: none;
    height: 2px;
    background: linear-gradient(90deg, var(--safety-orange) 0%, transparent 100%);
    opacity: 0.4;
    margin: 1.5rem 0 !important;
}

/* Inputs */
.stSelectbox > div, .stTextInput > div, [data-testid="stTextArea"] {
    border-radius: 8px !important;
    border-color: var(--border-light) !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 14px !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background: linear-gradient(135deg, var(--safety-orange) 0%, var(--safety-orange-dark) 100%) !important;
    border-radius: 6px;
}

/* Sidebar branding block */
.sidebar-brand {
    background: linear-gradient(135deg, var(--safety-orange) 0%, var(--safety-orange-dark) 100%);
    color: white !important;
    padding: 14px 16px;
    border-radius: 10px;
    font-weight: 800;
    font-size: 1.1rem;
    letter-spacing: -0.02em;
    margin-bottom: 12px;
    box-shadow: 0 4px 14px rgba(232,93,4,0.3);
}
.stats-label {
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--concrete) !important;
    margin-bottom: 4px;
}
</style>
""", unsafe_allow_html=True)

# Status bar — construction safety header
st.markdown(
    '<div class="status-bar">Sapientia — Safety Incident Management · OSHA 300/301 Ready · v1.1</div>',
    unsafe_allow_html=True
)

# Sidebar navigation
with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">🦺 Sapientia</div>',
        unsafe_allow_html=True
    )
    st.markdown("**Navigate**")
    page = st.radio(
        "Navigation",
        [
            "📋 Report Incident",
            "🏗️ Project Hub",
            "📊 Dashboard",
            "📁 Incident Log",
            "🚀 Investor Demo",
            "⚙️ Settings",
        ],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown("**Quick Stats**")

    from utils.data_store import load_incidents
    incidents = load_incidents()
    focus = st.session_state.get("sapientia_focus_project") or ""
    if focus:
        incidents = [i for i in incidents if (i.get("project") or "") == focus]
        st.caption(f"Stats: **{focus}**")
    total = len(incidents)
    critical = sum(1 for i in incidents if i.get("analysis", {}).get("severity") == "CRITICAL")
    open_cases = sum(1 for i in incidents if i.get("status") == "Open")

    st.metric("Total Incidents", total)
    st.metric("Critical", critical)
    st.metric("Open Cases", open_cases)
    st.markdown("---")
    st.markdown(
        '<p style="font-size:11px;color:#888;">Powered by Claude AI · OSHA 300/301 Compliant</p>',
        unsafe_allow_html=True
    )

# Route pages (with error handling so failed pages show a clear message)
try:
    # `pages/*.py` are Streamlit multipage modules too. Since we import them here
    # and call `render()` manually, we set an env flag temporarily so they don't
    # auto-render during import (avoids duplicate widget IDs).
    _prev_skip_render = os.environ.get("SAPIENTIA_SKIP_RENDER")
    os.environ["SAPIENTIA_SKIP_RENDER"] = "1"
    try:
        if page == "📋 Report Incident":
            from pages import report_page
            report_page.render()
        elif page == "🏗️ Project Hub":
            from pages import project_hub_page
            project_hub_page.render()
        elif page == "📊 Dashboard":
            from pages import dashboard_page
            dashboard_page.render()
        elif page == "📁 Incident Log":
            from pages import log_page
            log_page.render()
        elif page == "🚀 Investor Demo":
            from pages import demo_page
            demo_page.render()
        elif page == "⚙️ Settings":
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
