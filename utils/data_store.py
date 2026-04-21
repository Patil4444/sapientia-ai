import json
import os
import uuid
from datetime import datetime

# Use absolute path so it works regardless of CWD (e.g. when run from pages/)
_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_FILE = os.path.join(_DATA_DIR, "sample_data", "incidents.json")


def _ensure_file():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        # Seed with realistic sample data for demo
        samples = [
            {
                "id": str(uuid.uuid4()),
                "timestamp": "2025-03-01T08:32:00",
                "reported_by": "Mike Torres",
                "project": "Harbor View Tower - Phase 2",
                "raw_description": "Worker fell from scaffolding on level 8 approximately 12 feet. Worker is conscious but complaining of back pain. Called ambulance.",
                "analysis": {
                    "incident_type": "Fall",
                    "severity": "CRITICAL",
                    "severity_reason": "Fall from height >6 feet with potential spinal injury.",
                    "injured_person": "Unknown",
                    "body_part_affected": "Back/Spine",
                    "location_on_site": "Level 8 scaffolding",
                    "equipment_involved": "Scaffolding",
                    "immediate_cause": "Scaffolding plank gave way under worker weight.",
                    "osha_recordable": True,
                    "osha_reason": "Fall from height resulting in likely hospitalization.",
                    "osha_forms_required": ["OSHA 300", "OSHA 301"],
                    "immediate_actions_required": [
                        "911 called — ambulance en route",
                        "Secure scaffolding level 8 — no entry",
                        "Notify project superintendent",
                        "Preserve scaffolding plank for investigation"
                    ],
                    "summary": "Worker fell approximately 12 feet from Level 8 scaffolding. Worker remained conscious but reported back pain. Emergency services contacted immediately. Scaffolding area secured pending investigation."
                },
                "status": "Closed",
                "report_generated": True
            },
            {
                "id": str(uuid.uuid4()),
                "timestamp": "2025-03-05T14:15:00",
                "reported_by": "Sarah Kim",
                "project": "Harbor View Tower - Phase 2",
                "raw_description": "Near miss — crane swung load over workers who were not in designated safe zone. No injuries. Workers did not receive proper communication of lift schedule.",
                "analysis": {
                    "incident_type": "Near Miss",
                    "severity": "MEDIUM",
                    "severity_reason": "High potential for struck-by fatality if swing had contacted workers.",
                    "injured_person": "None",
                    "body_part_affected": "None",
                    "location_on_site": "Crane lift zone — east side",
                    "equipment_involved": "Tower crane",
                    "immediate_cause": "Failure to communicate lift schedule to ground crew.",
                    "osha_recordable": False,
                    "osha_reason": "No injury occurred — near miss only.",
                    "osha_forms_required": [],
                    "immediate_actions_required": [
                        "Review lift communication protocol",
                        "Mandatory toolbox talk with crane operator and ground crew",
                        "Re-mark exclusion zones with high-vis barriers"
                    ],
                    "summary": "Tower crane load swung over workers not cleared from the lift zone. No injuries sustained. Root cause identified as breakdown in pre-lift communication protocol. Corrective action initiated immediately."
                },
                "status": "Open",
                "report_generated": True
            },
            {
                "id": str(uuid.uuid4()),
                "timestamp": "2025-03-08T09:45:00",
                "reported_by": "James Okafor",
                "project": "Riverside Bridge Rehab",
                "raw_description": "Minor cut on right hand from rebar. Treated on site with first aid kit. No stitches needed. Worker returned to work.",
                "analysis": {
                    "incident_type": "Struck-By",
                    "severity": "LOW",
                    "severity_reason": "Minor laceration treated with first aid only.",
                    "injured_person": "James Okafor",
                    "body_part_affected": "Right hand",
                    "location_on_site": "Rebar placement area",
                    "equipment_involved": "Rebar",
                    "immediate_cause": "Unprotected rebar ends — no caps installed.",
                    "osha_recordable": False,
                    "osha_reason": "First aid only, worker returned to full duty.",
                    "osha_forms_required": [],
                    "immediate_actions_required": [
                        "Install rebar end caps on all exposed rebar",
                        "Check PPE (gloves) compliance in rebar zone"
                    ],
                    "summary": "Worker sustained minor cut to right hand from exposed rebar end. Treated on-site with first aid. Worker returned to full duty. Rebar end caps to be installed to prevent recurrence."
                },
                "status": "Closed",
                "report_generated": False
            },
            {
                "id": str(uuid.uuid4()),
                "timestamp": "2025-03-10T11:20:00",
                "reported_by": "Luis Mendez",
                "project": "Downtown Mixed-Use",
                "raw_description": "Electrical panel sparked when subcontractor attempted connection without lockout/tagout. Worker got minor shock, hand is numb. Sent to urgent care.",
                "analysis": {
                    "incident_type": "Electrical",
                    "severity": "CRITICAL",
                    "severity_reason": "Electrical shock with numbness indicates nerve involvement — hospitalization possible.",
                    "injured_person": "Unknown subcontractor",
                    "body_part_affected": "Hand/Arm",
                    "location_on_site": "Electrical room — floor 3",
                    "equipment_involved": "Electrical panel",
                    "immediate_cause": "Lockout/tagout procedure not followed before energized work.",
                    "osha_recordable": True,
                    "osha_reason": "Medical treatment beyond first aid — sent to urgent care.",
                    "osha_forms_required": ["OSHA 300", "OSHA 301"],
                    "immediate_actions_required": [
                        "Confirm worker received medical evaluation",
                        "Lock out electrical panel — do not energize",
                        "Notify electrical subcontractor supervisor",
                        "Conduct LOTO re-training for all electrical subs"
                    ],
                    "summary": "Subcontractor received electrical shock from panel while performing connection without lockout/tagout. Worker experienced hand numbness and was transported to urgent care. LOTO violation to be investigated and corrective training scheduled."
                },
                "status": "Open",
                "report_generated": True
            },
            {
                "id": str(uuid.uuid4()),
                "timestamp": "2025-03-12T16:05:00",
                "reported_by": "Dana Patel",
                "project": "Riverside Bridge Rehab",
                "raw_description": "Chemical spill — concrete form release agent spilled on worker's forearm. Skin is red and irritated. Washed with water for 15 min. No blistering.",
                "analysis": {
                    "incident_type": "Chemical Exposure",
                    "severity": "MEDIUM",
                    "severity_reason": "Chemical burn with skin irritation requires medical evaluation.",
                    "injured_person": "Unknown",
                    "body_part_affected": "Forearm",
                    "location_on_site": "Formwork area",
                    "equipment_involved": "Form release agent",
                    "immediate_cause": "No PPE (chemical-resistant gloves) worn during product application.",
                    "osha_recordable": True,
                    "osha_reason": "Chemical burn requiring medical evaluation beyond first aid.",
                    "osha_forms_required": ["OSHA 300", "OSHA 301"],
                    "immediate_actions_required": [
                        "Continue flushing with water — 20 minutes minimum",
                        "Consult SDS for release agent — check medical section",
                        "Send worker to occupational health clinic",
                        "Enforce chemical PPE compliance in formwork area"
                    ],
                    "summary": "Worker sustained chemical burn to forearm from form release agent spill. Immediate decontamination performed on site. Medical evaluation recommended due to persistent skin irritation. PPE compliance failure identified as root cause."
                },
                "status": "Open",
                "report_generated": False
            }
        ]
        with open(DATA_FILE, "w") as f:
            json.dump(samples, f, indent=2)


def load_incidents() -> list:
    from utils.http_api import client_api_base

    base = client_api_base()
    if base:
        import httpx

        try:
            r = httpx.get(f"{base}/api/incidents", timeout=60.0)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, json.JSONDecodeError):
            # If backend URL is unreachable or responds with non-JSON (e.g. HTML),
            # gracefully fall back to local demo/file storage.
            pass

    _ensure_file()
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_incident(incident: dict) -> str:
    from utils.http_api import client_api_base

    base = client_api_base()
    if base:
        import httpx

        try:
            payload = {k: v for k, v in incident.items() if k not in ("id", "timestamp")}
            r = httpx.post(f"{base}/api/incidents", json=payload, timeout=60.0)
            r.raise_for_status()
            return r.json()["id"]
        except (httpx.HTTPError, json.JSONDecodeError, KeyError):
            pass

    _ensure_file()
    incidents = load_incidents()
    incident_id = str(uuid.uuid4())
    incident["id"] = incident_id
    incident["timestamp"] = datetime.now().isoformat()
    incidents.append(incident)
    with open(DATA_FILE, "w") as f:
        json.dump(incidents, f, indent=2)
    return incident_id


def update_incident(incident_id: str, updates: dict):
    from utils.http_api import client_api_base

    base = client_api_base()
    if base:
        import httpx

        try:
            r = httpx.patch(f"{base}/api/incidents/{incident_id}", json=updates, timeout=60.0)
            r.raise_for_status()
            return
        except httpx.HTTPError:
            pass

    _ensure_file()
    incidents = load_incidents()
    for i, inc in enumerate(incidents):
        if inc["id"] == incident_id:
            incidents[i].update(updates)
            break
    with open(DATA_FILE, "w") as f:
        json.dump(incidents, f, indent=2)


def get_incident(incident_id: str) -> dict | None:
    from utils.http_api import client_api_base

    base = client_api_base()
    if base:
        import httpx

        try:
            r = httpx.get(f"{base}/api/incidents/{incident_id}", timeout=60.0)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, json.JSONDecodeError):
            pass

    incidents = load_incidents()
    for inc in incidents:
        if inc["id"] == incident_id:
            return inc
    return None
