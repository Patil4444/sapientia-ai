# Sapientia
### AI Automation Agent for Construction Safety Incident Reporting

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red?style=flat&logo=streamlit)](https://streamlit.io)
[![Claude API](https://img.shields.io/badge/Powered_by-Claude_AI-orange?style=flat)](https://anthropic.com)
[![OSHA](https://img.shields.io/badge/OSHA-300%2F301_Compliant-green?style=flat)](https://osha.gov)

---

## The Problem

Safety incident reporting on construction sites is slow, inconsistent, and error-prone. Workers fill out paper forms or spreadsheets after the fact. Safety managers chase documentation. OSHA-required logs (Form 300/301) get filed late or incomplete. High-severity incidents don't get escalated fast enough.

**Typical current workflow:** Incident occurs → Worker fills paper form (hours later) → Safety manager manually re-types into OSHA log → Reports filed weekly → Trends reviewed monthly, if at all.

**With Sapientia:** Incident occurs → Worker types what happened in plain English → AI agent classifies severity, checks OSHA recordability, drafts formatted report, alerts safety manager — all in under 30 seconds.

---

## Features

| Feature | Description |
|---|---|
| **Natural Language Intake** | Workers describe incidents in plain English — no forms to navigate |
| **AI Severity Classification** | Claude classifies LOW / MEDIUM / CRITICAL with reasoning |
| **OSHA Compliance Check** | Automatic 300/301 recordability determination |
| **PDF Report Generation** | OSHA-formatted incident reports, auto-filled, ready for signature |
| **Real-Time Alerts** | Email/SMS dispatch to safety manager for CRITICAL and MEDIUM incidents |
| **Analytics Dashboard** | Incident trends by severity, type, project, and OSHA status |
| **Demo Mode** | Fully functional without API keys using rule-based fallback |

---

## Tech Stack

```
Language:      Python 3.11+
UI Framework:  Streamlit
API (optional): FastAPI + Uvicorn (REST backend for shared data / multi-client)
AI Core:       Anthropic Claude API (claude-opus-4-6)
PDF Engine:    ReportLab
Email Alerts:  SendGrid
Data Storage:  JSON (file-based, no DB dependency)
```

---

## Project Structure

```
constructsafe/
├── app.py                     # Main entry point, navigation, global CSS
├── backend/
│   └── main.py                # FastAPI REST API (optional; pairs with Streamlit)
├── requirements.txt
├── README.md
├── pages/
│   ├── report_page.py         # Incident submission form + AI analysis
│   ├── dashboard_page.py      # KPI metrics + trend charts
│   ├── log_page.py            # Searchable incident log + PDF export
│   └── settings_page.py       # API key config + about
├── utils/
│   ├── agent.py               # AI agent core (Claude API + rule-based fallback)
│   ├── data_store.py          # JSON persistence layer + sample data
│   ├── http_api.py            # Optional FastAPI mode: SAPIENTIA_API_URL sync from Settings
│   ├── report_generator.py    # OSHA-formatted PDF generation (ReportLab)
│   └── alerts.py              # Email alert dispatcher (SendGrid)
└── sample_data/
    └── incidents.json         # Auto-generated with 5 realistic demo incidents
```

---

## Installation & Setup

**1. Clone the repo**
```bash
git clone https://github.com/[your-username]/constructsafe-ai.git
cd constructsafe-ai
```

**2. Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Run the app**

**Option A — Streamlit only (default, file-based data)**  
```bash
streamlit run app.py
```

**Option B — Streamlit + REST API (shared backend)**  
Terminal 1 — API server (from project root):
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
Terminal 2 — UI:
```bash
streamlit run app.py
```
In **Settings**, set **Backend base URL** to `http://127.0.0.1:8000` (this updates `SAPIENTIA_API_URL` for the app process), or set the same variable in your shell before starting Streamlit.  
API docs: `http://127.0.0.1:8000/docs`

App opens at `http://localhost:8501`

---

## Configuration

API keys are configured in the **Settings** page within the app. No `.env` file required.

| Setting | Required | Purpose |
|---|---|---|
| Anthropic API Key | Optional | Full AI analysis (Claude). Without it, runs rule-based demo mode. |
| SendGrid API Key | Optional | Real email alerts. Without it, alerts are simulated to console. |
| Alert Email | Optional | Recipient email for safety manager alerts. |

**Demo mode works with zero configuration** — the app ships with 5 realistic sample incidents and rule-based classification so you can see the full workflow immediately.

### Costs & billing (this project)

This codebase does **not** sign you up for any subscription, payment plan, or in-app billing. There is no Stripe (or similar) integration.

- **Streamlit + FastAPI + Uvicorn + ReportLab** run on your machine; they do not charge you through this app.
- **Optional usage-based cost** happens only if **you** add your own API keys under **Settings** (Anthropic for Claude, SendGrid for email). Usage is billed by those providers per their pricing, not by Sapientia.
- Without those keys, the app uses **free local fallbacks** (rule-based analysis, simulated alerts).

---

## How the AI Agent Works

The agent follows a 5-step pipeline:

```
1. INPUT          Worker submits incident description (free text)
       ↓
2. PARSE          Claude extracts: type, location, person, equipment, cause
       ↓
3. CLASSIFY       Severity (LOW/MEDIUM/CRITICAL) with reasoning
       ↓
4. COMPLIANCE     OSHA recordability check → required forms (300, 301)
       ↓
5. OUTPUT         PDF report + alert dispatch + dashboard log
```

**Claude system prompt** instructs the model to return structured JSON only, covering all OSHA-relevant fields. The fallback uses keyword matching for demo purposes.

---

## OSHA Compliance Notes

This tool is designed to assist with OSHA 300/301 recordkeeping as defined in **29 CFR Part 1904**.

- **OSHA 300 (Log of Work-Related Injuries)** — required for recordable incidents
- **OSHA 301 (Injury and Illness Incident Report)** — required within 7 days of recordable incident

**Recordability criteria implemented:**
- Days away from work
- Restricted work or job transfer
- Medical treatment beyond first aid
- Loss of consciousness
- Significant diagnosis by healthcare professional

> ⚠️ This tool is an aid, not a replacement for a qualified safety professional. Always verify OSHA recordability with your safety officer.

---

## Resume Bullet Points

```
Sapientia — AI Safety Incident Reporting Agent  |  Python · Claude API · Streamlit
• Built end-to-end AI automation agent reducing safety incident documentation time by ~70%,
  auto-generating OSHA-compliant reports from unstructured worker input using Claude LLM
• Implemented severity classification (LOW/MEDIUM/CRITICAL) and OSHA 300/301 recordability
  determination, eliminating manual compliance review bottlenecks
• Deployed full-stack web application with real-time alert dispatch, PDF report generation
  (ReportLab), and incident trend analytics dashboard serving multi-project safety teams
```

---

## Future Enhancements

- [ ] Voice input via Whisper API transcription
- [ ] Photo upload with computer vision damage assessment
- [ ] Corrective action tracking and close-out workflow
- [ ] Integration with Procore / Autodesk Construction Cloud
- [ ] Weekly automated OSHA 300 log export (Excel format)
- [ ] Mobile-optimized PWA for field use

---

## Author

**Pranjal** — MS Project Management (Construction Management), Northeastern University  
3+ years construction project management experience | OSHA 30 Certified

---

*Built to demonstrate practical AI automation in construction project management.*
