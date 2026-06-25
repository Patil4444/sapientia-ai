"""Shared validation helpers for incident intake (frontend + backend)."""

MIN_DESCRIPTION_LENGTH = 50
MIN_CUSTOM_SITE_NAME_LENGTH = 2


def validate_description(text: str) -> list[str]:
    """Return warning messages for description text (non-blocking)."""
    warnings: list[str] = []
    stripped = (text or "").strip()
    if not stripped:
        return warnings
    if len(stripped) < MIN_DESCRIPTION_LENGTH:
        warnings.append(
            f"Description is short ({len(stripped)} chars). "
            f"Aim for at least {MIN_DESCRIPTION_LENGTH} characters for better AI analysis."
        )
    return warnings


def validate_custom_site_name(name: str, other_selected: bool) -> list[str]:
    """Return warnings when 'Other (custom site name)' is selected."""
    if not other_selected:
        return []
    warnings: list[str] = []
    stripped = (name or "").strip()
    if not stripped:
        warnings.append("Custom site name is empty — consider entering the official job name.")
    elif len(stripped) < MIN_CUSTOM_SITE_NAME_LENGTH:
        warnings.append(
            f"Custom site name is very short ({len(stripped)} chars). "
            f"Use at least {MIN_CUSTOM_SITE_NAME_LENGTH} characters."
        )
    return warnings


def validate_analyze_request(raw_text: str) -> tuple[list[str], str | None]:
    """
    Validate analyze API input.
    Returns (warnings, error). error is set only for blocking issues (empty text).
    """
    stripped = (raw_text or "").strip()
    if not stripped:
        return [], "Incident description is required."
    return validate_description(stripped), None
