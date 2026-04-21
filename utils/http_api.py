"""Resolve backend API base URL for Streamlit when using split frontend + API server."""
import os


def sync_backend_url_env_from_streamlit(session_state) -> None:
    """
    Copy Settings widget value into SAPIENTIA_API_URL for this process.
    Called from app.py each run so utils never import Streamlit.
    If the user never opened Settings, the key is absent and the OS env is left unchanged.
    """
    if "sapientia_api_url_field" not in session_state:
        return
    raw = session_state.get("sapientia_api_url_field") or ""
    stripped = str(raw).strip().rstrip("/")
    if stripped:
        os.environ["SAPIENTIA_API_URL"] = stripped
    else:
        os.environ.pop("SAPIENTIA_API_URL", None)


def client_api_base() -> str:
    return os.environ.get("SAPIENTIA_API_URL", "").strip().rstrip("/")
