import json
import os
import uuid

_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECTS_FILE = os.path.join(_DATA_DIR, "sample_data", "projects.json")


def _default_rows():
    return [
        {"id": str(uuid.uuid4()), "name": "Harbor View Tower - Phase 2", "start_date": "", "end_date": "", "status": "active"},
        {"id": str(uuid.uuid4()), "name": "Riverside Bridge Rehab", "start_date": "", "end_date": "", "status": "active"},
        {"id": str(uuid.uuid4()), "name": "Downtown Mixed-Use Development", "start_date": "", "end_date": "", "status": "active"},
        {"id": str(uuid.uuid4()), "name": "Highway 128 Expansion", "start_date": "", "end_date": "", "status": "active"},
        {"id": str(uuid.uuid4()), "name": "Waterfront Parking Structure", "start_date": "", "end_date": "", "status": "active"},
    ]


def _ensure_file():
    os.makedirs(os.path.dirname(PROJECTS_FILE), exist_ok=True)
    if not os.path.exists(PROJECTS_FILE):
        with open(PROJECTS_FILE, "w") as f:
            json.dump({"projects": _default_rows()}, f, indent=2)


def load_projects() -> list:
    from utils.http_api import client_api_base

    base = client_api_base()
    if base:
        import httpx

        try:
            r = httpx.get(f"{base}/api/projects", timeout=60.0)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, json.JSONDecodeError):
            pass

    _ensure_file()
    with open(PROJECTS_FILE, "r") as f:
        data = json.load(f)
    return data.get("projects", [])


def save_all_projects(projects: list):
    _ensure_file()
    with open(PROJECTS_FILE, "w") as f:
        json.dump({"projects": projects}, f, indent=2)


def add_project(name: str, start_date: str = "", end_date: str = "", status: str = "active") -> dict:
    from utils.http_api import client_api_base

    base = client_api_base()
    if base:
        import httpx

        try:
            r = httpx.post(
                f"{base}/api/projects",
                json={
                    "name": name.strip(),
                    "start_date": start_date or "",
                    "end_date": end_date or "",
                    "status": status if status in ("active", "archived") else "active",
                },
                timeout=60.0,
            )
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, json.JSONDecodeError):
            pass

    projects = load_projects()
    row = {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "start_date": start_date or "",
        "end_date": end_date or "",
        "status": status if status in ("active", "archived") else "active",
    }
    projects.append(row)
    save_all_projects(projects)
    return row


def update_project(project_id: str, **fields):
    from utils.http_api import client_api_base

    base = client_api_base()
    if base:
        import httpx

        try:
            body = {k: v for k, v in fields.items() if k in ("name", "start_date", "end_date", "status") and v is not None}
            r = httpx.patch(f"{base}/api/projects/{project_id}", json=body, timeout=60.0)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, json.JSONDecodeError):
            pass

    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") == project_id:
            for k, v in fields.items():
                if k in ("name", "start_date", "end_date", "status") and v is not None:
                    projects[i][k] = v
            if projects[i].get("status") not in ("active", "archived"):
                projects[i]["status"] = "active"
            save_all_projects(projects)
            return projects[i]
    return None


def get_active_project_names() -> list[str]:
    return [p["name"] for p in load_projects() if p.get("status") == "active" and p.get("name")]
