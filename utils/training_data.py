"""
Load curated real construction incidents (2020–present) for training the AI agent
and for demo scenarios. Data is from open-source patterns (OSHA, BLS CFOI, public reports).
"""

import json
import os

_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TRAINING_FILE = os.path.join(_DATA_DIR, "sample_data", "real_incidents_training.json")


def load_real_incidents() -> list[dict]:
    """Load the list of real construction incidents (2020–present)."""
    if not os.path.exists(TRAINING_FILE):
        return []
    with open(TRAINING_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("incidents", [])


def get_few_shot_examples(max_examples: int = 4) -> list[tuple[str, dict]]:
    """
    Return (raw_description, expected_analysis) pairs for few-shot prompting.
    Picks a mix of severities and incident types.
    """
    incidents = load_real_incidents()
    if not incidents:
        return []

    # Prefer CRITICAL and MEDIUM, mix of types
    by_sev = {"CRITICAL": [], "MEDIUM": [], "LOW": []}
    for inc in incidents:
        sev = inc.get("severity", "MEDIUM")
        if sev in by_sev:
            by_sev[sev].append(inc)

    chosen = []
    for sev in ("CRITICAL", "MEDIUM", "LOW"):
        for inc in by_sev[sev][:2]:  # up to 2 per severity
            if len(chosen) >= max_examples:
                break
            raw = inc.get("raw_description", "")
            itype = inc.get("incident_type", "Other")
            expected = {
                "incident_type": itype,
                "severity": sev,
                "summary": f"Real incident ({inc.get('year', 'N/A')}): {itype}. {raw[:120]}...",
                "osha_recordable": sev in ("CRITICAL", "MEDIUM"),
            }
            chosen.append((raw, expected))
    return chosen[:max_examples]


def get_sample_scenario_options() -> list[tuple[str, str]]:
    """
    Return options for the Report page "Quick-fill with sample scenario" dropdown:
    list of (label, raw_description). Labels are unique (year + type + severity + index).
    """
    incidents = load_real_incidents()
    options = []
    for idx, inc in enumerate(incidents):
        year = inc.get("year", "")
        itype = inc.get("incident_type", "Incident")
        sev = inc.get("severity", "MEDIUM")
        label = f"[{year}] {itype} ({sev}) — real incident"
        if any(l == label for l, _ in options):
            label = f"[{year}] {itype} ({sev}) — real #{idx + 1}"
        options.append((label, inc.get("raw_description", "")))
    return options
