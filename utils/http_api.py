"""Resolve backend API base URL for Streamlit when using split frontend + API server."""
import json
import os

# Suffixes users often paste into Settings by mistake (docs link, health path, etc.).
_STRIP_SUFFIXES = ("/api/health", "/api", "/docs", "/redoc", "/openapi.json")


def normalize_api_base(url: str) -> str:
    """
    Return the server root only (no trailing slash, no /api or /docs suffix).
    All client calls append paths like /api/health and /api/incidents themselves.
    """
    s = str(url or "").strip()
    if not s:
        return ""
    while s.endswith("/"):
        s = s[:-1]
    lowered = s.lower()
    for suffix in _STRIP_SUFFIXES:
        if lowered.endswith(suffix):
            s = s[: -len(suffix)]
            while s.endswith("/"):
                s = s[:-1]
            lowered = s.lower()
    return s


def format_backend_http_error(exc: Exception, base: str, *, context: str = "backend") -> str:
    """Turn httpx/FastAPI failures into actionable Settings guidance."""
    msg = str(exc).strip()
    detail = ""
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            body = response.json()
            if isinstance(body, dict) and body.get("detail"):
                detail = str(body["detail"])
        except (json.JSONDecodeError, ValueError, AttributeError):
            pass
        status = getattr(response, "status_code", None)
        if status == 404 or (detail and detail.lower() == "not found"):
            return (
                f"Cannot reach {context} at {base!r} — got 404 Not Found"
                f"{f' ({detail})' if detail else ''}. "
                "Set **Backend base URL** to the server root only, e.g. `http://127.0.0.1:8000` "
                "(not `/api`, `/api/health`, or `/docs`). "
                "Start the API with: `uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000`"
            )
    if "connection" in msg.lower() or "connect" in msg.lower() or "refused" in msg.lower():
        return (
            f"Cannot connect to {context} at {base!r}. "
            "Start the FastAPI server from the project root, then use "
            "`http://127.0.0.1:8000` as the Backend base URL."
        )
    if detail:
        return f"Cannot reach {context} at {base!r}: {detail}"
    return f"Cannot reach {context} at {base!r}: {msg}"


def sync_backend_url_env_from_streamlit(session_state) -> None:
    """
    Copy Settings widget value into SAPIENTIA_API_URL for this process.
    Called from app.py each run so utils never import Streamlit.
    """
    if "sapientia_api_url_field" not in session_state:
        env_url = normalize_api_base(os.environ.get("SAPIENTIA_API_URL", ""))
        if env_url:
            os.environ["SAPIENTIA_API_URL"] = env_url
        return
    stripped = normalize_api_base(session_state.get("sapientia_api_url_field") or "")
    if stripped:
        os.environ["SAPIENTIA_API_URL"] = stripped
    else:
        os.environ.pop("SAPIENTIA_API_URL", None)


def client_api_base() -> str:
    return normalize_api_base(os.environ.get("SAPIENTIA_API_URL", ""))
