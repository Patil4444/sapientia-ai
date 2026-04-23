"""
Sapientia REST API — same persistence and logic as the Streamlit app.
Run from project root: uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
"""
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# This process generates PDFs in-process. Prevents utils.report_generator from
# delegating via HTTP to the same host when SAPIENTIA_API_URL is set globally.
os.environ["SAPIENTIA_IS_PDF_WORKER"] = "1"

from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from utils import data_store, project_store
from utils.agent import analyze_incident
from utils.alerts import send_alert
from utils.report_generator import (
    REPORTLAB_AVAILABLE,
    generate_incident_report,
    generate_pitch_pack_pdf,
)

app = FastAPI(title="Sapientia API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https://.*\.streamlit\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    raw_text: str
    api_key: str = ""


class ProjectCreate(BaseModel):
    name: str
    start_date: str = ""
    end_date: str = ""
    status: str = "active"


class AlertRequest(BaseModel):
    incident: dict
    analysis: dict
    recipient_email: str | None = None
    sendgrid_key: str | None = None


class PitchPackRequest(BaseModel):
    incidents: list[dict] = Field(default_factory=list)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "sapientia-api",
        "reportlab": REPORTLAB_AVAILABLE,
        "pdf_routes": ["/api/reports/incident-pdf", "/api/reports/pitch-pack-pdf"],
    }


@app.get("/api/incidents")
def list_incidents():
    return data_store.load_incidents()


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):
    inc = data_store.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc


@app.post("/api/incidents")
def create_incident(body: dict[str, Any] = Body(...)):
    incident_id = data_store.save_incident(dict(body))
    return {"id": incident_id}


@app.patch("/api/incidents/{incident_id}")
def patch_incident(incident_id: str, body: dict[str, Any] = Body(...)):
    if not data_store.get_incident(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    data_store.update_incident(incident_id, body)
    return {"ok": True}


@app.get("/api/projects")
def list_projects():
    return project_store.load_projects()


@app.post("/api/projects")
def create_project(body: ProjectCreate):
    row = project_store.add_project(
        name=body.name,
        start_date=body.start_date,
        end_date=body.end_date,
        status=body.status,
    )
    return row


@app.patch("/api/projects/{project_id}")
def patch_project(project_id: str, body: dict[str, Any] = Body(...)):
    updated = project_store.update_project(project_id, **body)
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return updated


@app.post("/api/analyze")
def post_analyze(req: AnalyzeRequest):
    key = (req.api_key or "").strip() or None
    return analyze_incident(req.raw_text, api_key=key)


@app.post("/api/reports/incident-pdf")
def post_incident_pdf(incident: dict[str, Any] = Body(...)):
    try:
        pdf = generate_incident_report(incident)
    except ImportError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}") from e
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="incident_report.pdf"'},
    )


@app.post("/api/reports/pitch-pack-pdf")
def post_pitch_pack_pdf(req: PitchPackRequest):
    try:
        pdf = generate_pitch_pack_pdf(req.incidents)
    except ImportError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}") from e
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="pitch_pack.pdf"'},
    )


@app.post("/api/alerts/send")
def post_alert(req: AlertRequest):
    return send_alert(
        req.incident,
        req.analysis,
        recipient_email=req.recipient_email,
        sendgrid_key=req.sendgrid_key,
    )
