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

# Global CSS — Sapientia dark UI (palette + typography + components)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap');

@keyframes pulse-critical {
  0% { box-shadow: 0 0 0 0 rgba(255, 68, 68, 0.4); }
  70% { box-shadow: 0 0 0 8px rgba(255, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(255, 68, 68, 0); }
}

@keyframes pulse-dot-open {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(0, 214, 143, 0.5); }
  50% { opacity: 0.85; box-shadow: 0 0 0 6px rgba(0, 214, 143, 0); }
}

@keyframes sap-live-fade {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

@keyframes sap-load-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

@keyframes sap-top-load {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.sap-live-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #00D68F;
  animation: sap-live-fade 2s ease-in-out infinite;
}

.sap-loading-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #00E5FF;
  animation: sap-load-blink 1.2s ease-in-out infinite;
}

.sap-top-load-track {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: #0A0E1A;
  overflow: hidden;
  z-index: 999999;
  pointer-events: none;
}

.sap-top-load-bar {
  height: 100%;
  width: 40%;
  background: linear-gradient(90deg, transparent, #00E5FF, #A78BFA, transparent);
  animation: sap-top-load 0.8s ease-out forwards;
}

/* —— Affinity / Canva-inspired ambient art layer —— */
.sap-art-layer {
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  overflow: hidden;
}

.sap-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(76px);
  opacity: 0.52;
  mix-blend-mode: screen;
  will-change: transform;
}

.sap-orb-1 {
  width: min(560px, 58vw);
  height: min(560px, 58vw);
  background: radial-gradient(circle at 32% 30%, rgba(0, 229, 255, 0.95), rgba(0, 229, 255, 0) 62%);
  top: -14%;
  left: -12%;
  animation: sap-orb-float-a 24s ease-in-out infinite;
}

.sap-orb-2 {
  width: min(480px, 48vw);
  height: min(480px, 48vw);
  background: radial-gradient(circle at 55% 42%, rgba(167, 139, 250, 0.75), rgba(167, 139, 250, 0) 65%);
  top: 18%;
  right: -16%;
  animation: sap-orb-float-b 28s ease-in-out infinite;
}

.sap-orb-3 {
  width: min(520px, 52vw);
  height: min(520px, 52vw);
  background: radial-gradient(circle at 45% 55%, rgba(0, 214, 143, 0.55), rgba(0, 214, 143, 0) 62%);
  bottom: -18%;
  left: 8%;
  animation: sap-orb-float-c 22s ease-in-out infinite;
}

@keyframes sap-orb-float-a {
  0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
  35% { transform: translate3d(6vw, 8vh, 0) scale(1.07); }
  70% { transform: translate3d(-4vw, 5vh, 0) scale(0.96); }
}

@keyframes sap-orb-float-b {
  0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
  40% { transform: translate3d(-7vw, 10vh, 0) scale(1.09); }
  75% { transform: translate3d(5vw, -4vh, 0) scale(0.93); }
}

@keyframes sap-orb-float-c {
  0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
  45% { transform: translate3d(8vw, -6vh, 0) scale(1.05); }
  80% { transform: translate3d(-5vw, -8vh, 0) scale(0.94); }
}

.sap-mesh-sheen {
  position: absolute;
  inset: -35% -25%;
  background: linear-gradient(
    118deg,
    transparent 0%,
    rgba(0, 229, 255, 0.09) 22%,
    transparent 46%,
    rgba(167, 139, 250, 0.1) 68%,
    transparent 88%
  );
  background-size: 240% 240%;
  animation: sap-mesh-drift 32s linear infinite;
  opacity: 0.75;
}

@keyframes sap-mesh-drift {
  0% { transform: translate(-6%, -4%) rotate(0deg); background-position: 0% 40%; }
  50% { transform: translate(5%, 6%) rotate(2deg); background-position: 60% 55%; }
  100% { transform: translate(-6%, -4%) rotate(0deg); background-position: 100% 40%; }
}

.sap-grain {
  position: absolute;
  inset: 0;
  opacity: 0.055;
  mix-blend-mode: overlay;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.55'/%3E%3C/svg%3E");
}

.sap-vignette {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse 85% 75% at 50% 45%, transparent 35%, rgba(5, 8, 18, 0.85) 100%);
  opacity: 0.55;
}

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

:root {
  --bg: #0A0E1A;
  --surface: #0F1520;
  --surface2: #141D2B;
  --accent: #00E5FF;
  --accent-hover: #00CFEA;
  --critical: #FF4444;
  --warning: #FFB020;
  --success: #00D68F;
  --border: #1A2540;
  --text-primary: #F1F5F9;
  --text-secondary: #8899AA;
  --text-muted: #3D5068;
}

html, body {
  background-color: #050810 !important;
}

.stApp {
  background: transparent !important;
  color: var(--text-secondary) !important;
  font-family: 'Inter', sans-serif !important;
  position: relative;
  isolation: isolate;
}

[data-testid="stAppViewContainer"] {
  background: linear-gradient(
      180deg,
      rgba(7, 11, 20, 0.55) 0%,
      rgba(10, 14, 26, 0.42) 55%,
      rgba(5, 8, 16, 0.62) 100%
    ),
    transparent !important;
}

[data-testid="stHeader"] {
  background: rgba(5, 8, 16, 0.35) !important;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid rgba(0, 229, 255, 0.06);
}

main[data-testid="stMain"] {
  background: transparent !important;
}

.block-container {
  padding-top: 1.25rem !important;
  padding-bottom: 2rem !important;
  padding-left: 1.5rem !important;
  padding-right: 1.5rem !important;
  max-width: 100% !important;
  position: relative;
  z-index: 1;
  animation: sap-content-rise 0.85s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes sap-content-rise {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Type scale — Canva-like display + editorial hierarchy */
h1 {
  font-family: 'Outfit', 'Inter', sans-serif !important;
  font-size: 32px !important;
  font-weight: 700 !important;
  letter-spacing: -0.6px !important;
  line-height: 1.15 !important;
  background: linear-gradient(92deg, #f8fafc 0%, #e2e8f0 38%, #5eead4 72%, #22d3ee 108%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 10px 38px rgba(0, 229, 255, 0.12));
}

h2 {
  font-family: 'Outfit', 'Inter', sans-serif !important;
  font-size: 22px !important;
  font-weight: 600 !important;
  color: var(--text-primary) !important;
  letter-spacing: -0.35px !important;
}
h3 {
  font-family: 'Inter', sans-serif !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  color: #CBD5E1 !important;
}
p, .stMarkdown p, [data-testid="stMarkdownContainer"] p {
  font-family: 'Inter', sans-serif !important;
  font-size: 14px !important;
  color: var(--text-secondary) !important;
  line-height: 1.6 !important;
}

/* Labels / captions */
label, .stCheckbox label, .stRadio label, [data-testid="stWidgetLabel"] {
  font-family: 'Inter', sans-serif !important;
  font-size: 11px !important;
  color: var(--text-muted) !important;
  letter-spacing: 0.8px !important;
  text-transform: uppercase !important;
  font-weight: 600 !important;
}

[data-testid="stCaption"] {
  font-size: 11px !important;
  color: var(--text-muted) !important;
  letter-spacing: 0.5px !important;
}

/* Sidebar — frosted panel (Affinity-style depth) */
section[data-testid="stSidebar"] {
  background: linear-gradient(165deg, rgba(15, 21, 32, 0.88) 0%, rgba(8, 12, 22, 0.78) 100%) !important;
  backdrop-filter: blur(22px) saturate(165%);
  -webkit-backdrop-filter: blur(22px) saturate(165%);
  border-right: 1px solid rgba(0, 229, 255, 0.14) !important;
  box-shadow: 12px 0 48px rgba(0, 0, 0, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.04);
  min-width: 260px !important;
  position: relative;
  z-index: 2;
}
section[data-testid="stSidebar"] > div {
  background-color: transparent !important;
}

section[data-testid="stSidebar"] .stRadio > div {
  gap: 4px !important;
}

section[data-testid="stSidebar"] .stRadio label {
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important;
  padding: 8px 16px !important;
  border-radius: 6px !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  color: var(--text-secondary) !important;
  border-left: 2px solid transparent !important;
}

section[data-testid="stSidebar"] .stRadio label:hover {
  background: #1A2540 !important;
  color: #00E5FF !important;
  text-decoration: none !important;
}

section[data-testid="stSidebar"] .stRadio label[data-checked="true"] {
  background: #1A2540 !important;
  border-left: 2px solid #00E5FF !important;
  color: #00E5FF !important;
}

/* Buttons — base then primary */
.stButton > button {
  background: transparent !important;
  color: var(--text-secondary) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 600 !important;
}
.stButton > button:hover {
  background: var(--surface2) !important;
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}

.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #00f0ff 0%, #00e5ff 45%, #38bdf8 100%) !important;
  color: var(--bg) !important;
  border: none !important;
  padding: 14px 20px !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  box-shadow: 0 6px 28px rgba(0, 229, 255, 0.28), 0 0 0 1px rgba(255, 255, 255, 0.12) inset !important;
  transition: transform 0.4s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.35s ease, filter 0.35s ease !important;
}
.stButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #5ef4ff 0%, #00e5ff 50%, #60a5fa 100%) !important;
  color: var(--bg) !important;
  transform: translateY(-2px);
  box-shadow: 0 14px 42px rgba(0, 229, 255, 0.38), 0 0 0 1px rgba(255, 255, 255, 0.15) inset !important;
  filter: saturate(1.08);
}

/* Metrics — glass tiles */
[data-testid="metric-container"] {
  background: rgba(15, 21, 32, 0.72) !important;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(26, 37, 64, 0.95) !important;
  border-radius: 12px !important;
  padding: 16px !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  transition: transform 0.45s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.45s ease, border-color 0.35s ease !important;
}
[data-testid="metric-container"]:hover {
  transform: translateY(-3px);
  box-shadow: 0 16px 44px rgba(0, 229, 255, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.07);
  border-color: rgba(0, 229, 255, 0.35) !important;
}
[data-testid="metric-container"] label {
  font-family: 'Inter', sans-serif !important;
  font-size: 11px !important;
  color: var(--text-muted) !important;
  letter-spacing: 0.8px !important;
  text-transform: uppercase !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
  color: var(--text-primary) !important;
}

/* Inputs — dark surfaces */
.stTextInput input, .stTextArea textarea, [data-baseweb="textarea"] textarea {
  background-color: var(--surface) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
}

.stSelectbox > div > div {
  background-color: var(--surface) !important;
  border-color: var(--border) !important;
  color: var(--text-primary) !important;
}

/* Expanders */
.streamlit-expanderHeader {
  font-family: 'Inter', sans-serif !important;
  color: var(--text-primary) !important;
}

/* Alerts — tint for dark bg */
.stAlert {
  background-color: var(--surface) !important;
  border: 1px solid var(--border) !important;
}

/* Legacy helper classes used in pages */
.incident-card {
  background: rgba(15, 21, 32, 0.82);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(26, 37, 64, 0.9);
  border-radius: 12px;
  padding: 18px 20px;
  margin-bottom: 14px;
  font-family: 'Inter', sans-serif;
  box-shadow: 0 10px 36px rgba(0, 0, 0, 0.22);
  transition: transform 0.45s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.45s ease, border-color 0.35s ease;
}
.incident-card:hover {
  transform: translateY(-2px);
  border-color: rgba(0, 229, 255, 0.28);
  box-shadow: 0 18px 48px rgba(0, 229, 255, 0.1);
}
.incident-card p {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.6;
}

.info-box {
  background: linear-gradient(90deg, rgba(15, 21, 32, 0.92) 0%, rgba(12, 18, 30, 0.72) 100%);
  border-left: 3px solid var(--accent);
  padding: 14px 18px;
  margin: 10px 0;
  font-size: 14px;
  border-radius: 0 12px 12px 0;
  color: var(--text-secondary);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.18);
}

hr {
  border: none;
  height: 1px;
  background: var(--border);
  margin: 1.5rem 0 !important;
}

.badge-critical, .badge-medium, .badge-low {
  font-family: 'Inter', sans-serif !important;
}

/* Incident report — message composer (matches primary text areas app-wide) */
.stTextArea textarea {
  min-height: 120px !important;
  font-size: 15px !important;
  line-height: 1.55 !important;
  color: #F1F5F9 !important;
  background: #0F1520 !important;
  border: 1px solid #1A2540 !important;
  border-radius: 10px !important;
  padding: 15px !important;
}
.stTextArea textarea:focus {
  border-color: #00E5FF !important;
  box-shadow: 0 0 0 1px rgba(0, 229, 255, 0.25) !important;
}

[data-testid="stDownloadButton"] button {
  background: transparent !important;
  color: #00E5FF !important;
  border: 1px solid #00E5FF !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
}
[data-testid="stDownloadButton"] button:hover {
  background: rgba(0, 229, 255, 0.08) !important;
}

.sap-result-hero {
  text-align: center;
  margin: 0;
}
.sap-result-hero-wrap {
  margin: 12px 0 20px;
  padding: 20px 18px;
  text-align: center;
}
.sap-result-hero .sap-sev-critical span,
.sap-result-hero span[style*="pulse-critical"] {
  font-size: 15px !important;
  padding: 8px 16px !important;
}

/* —— Shared layout utilities (dashboard, report, empty states) —— */
.sap-glass-panel {
  background: rgba(15, 21, 32, 0.82);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(26, 37, 64, 0.95);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 10px 36px rgba(0, 0, 0, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.sap-glass-panel--compact {
  padding: 14px 16px;
}

.sap-glass-panel--metric {
  text-align: center;
}

.sap-glass-panel--pulse-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  margin: -0.25rem -1rem 18px -1rem;
  padding: 14px 18px;
  border-radius: 0;
  border: none;
  border-bottom: 1px solid rgba(26, 37, 64, 0.95);
  background: rgba(15, 21, 32, 0.78);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}

.sap-glass-panel--stack {
  margin-top: 16px;
}

.sap-card-left-accent {
  border-left: 3px solid var(--sap-accent, #1a2540) !important;
}

.sap-kpi-num {
  font-size: 32px;
  font-weight: 700;
  line-height: 1.1;
}

.sap-kpi-label {
  margin-top: 8px;
  font-size: 11px;
  color: #3d5068;
  letter-spacing: 0.8px;
  text-transform: uppercase;
}

.sap-section-title {
  margin: 24px 0 12px;
  font-size: 11px;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: #8899aa;
  font-weight: 700;
}

.sap-detail-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid #1a2540;
  font-size: 13px;
}

.sap-meta-chip {
  display: inline-block;
  margin: 4px 8px 0 0;
  padding: 4px 10px;
  border: 1px solid #1a2540;
  border-radius: 6px;
  font-size: 12px;
  color: #00e5ff;
  font-family: ui-monospace, monospace;
}

.sap-result-meta-row {
  display: flex;
  justify-content: center;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

.sap-result-meta-item {
  text-align: center;
}

.sap-label-upper {
  font-size: 11px;
  color: #3d5068;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.sap-label-upper--tight {
  margin-bottom: 4px;
}

.sap-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.sap-muted {
  color: #3d5068;
}

.sap-strong {
  color: #f1f5f9;
  font-weight: 500;
}

.sap-glass-panel--center {
  text-align: center;
}

.sap-glass-panel--spacious {
  padding: 26px 24px;
}

/* Sidebar nav buttons — selected vs idle */
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: #1A2540 !important;
  color: #00E5FF !important;
  border: 1px solid #1A2540 !important;
  border-left: 2px solid #00E5FF !important;
  justify-content: flex-start !important;
  text-align: left !important;
  padding: 10px 16px !important;
  border-radius: 6px !important;
  font-size: 13px !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
  background: transparent !important;
  color: #8899AA !important;
  border: none !important;
  justify-content: flex-start !important;
  text-align: left !important;
  padding: 10px 16px !important;
  border-radius: 6px !important;
  font-size: 13px !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
  background: #1A2540 !important;
  color: #00E5FF !important;
}

/* Dashboard feed — glass + accent border via --sap-accent */
.sap-feed-card {
  margin-bottom: 8px;
  transition: transform 0.5s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.5s ease, background 0.4s ease, border-color 0.4s ease !important;
}
.sap-feed-card:hover {
  background: rgba(20, 29, 43, 0.92) !important;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(0, 229, 255, 0.12) !important;
}

@media (prefers-reduced-motion: reduce) {
  .sap-orb,
  .sap-mesh-sheen,
  .sap-top-load-bar,
  .sap-live-dot,
  .sap-loading-dot,
  .block-container {
    animation: none !important;
    transition: none !important;
  }
  .sap-art-layer .sap-orb {
    animation: none !important;
  }
  .sap-feed-card {
    transition: none !important;
  }
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    """
<div class="sap-art-layer" aria-hidden="true">
  <div class="sap-orb sap-orb-1"></div>
  <div class="sap-orb sap-orb-2"></div>
  <div class="sap-orb sap-orb-3"></div>
  <div class="sap-mesh-sheen"></div>
  <div class="sap-grain"></div>
  <div class="sap-vignette"></div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="sap-top-load-track"><div class="sap-top-load-bar"></div></div>',
    unsafe_allow_html=True,
)

_NAV_PAGES = [
    "⬡ Report Incident",
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

    st.markdown(
        f'<div style="font-size:13px;color:#8899AA;line-height:1.6;">'
        f"<strong style=\"color:#F1F5F9;\">{total}</strong> incidents · "
        f"<strong style=\"color:#FF4444;\">{critical}</strong> critical"
        f"</div>"
        '<div style="margin-top:14px;font-size:10px;color:#3D5068;">v1.1 · OSHA Ready</div>',
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
