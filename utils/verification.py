"""
Rule-based automatic verification signals — no extra human re-review loops.
Recomputed whenever dashboards load; safe for full project lifecycle tracking.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def _parse_ts(inc: dict) -> datetime | None:
    raw = inc.get("timestamp") or ""
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def incidents_for_scope(incidents: list[dict], project_name: str | None) -> list[dict]:
    if not project_name:
        return list(incidents)
    return [i for i in incidents if (i.get("project") or "") == project_name]


def compute_signals(
    incidents: list[dict],
    *,
    project_name: str | None = None,
    stalled_days: int = 14,
    repeat_window_days: int = 14,
    repeat_min_count: int = 2,
) -> dict[str, Any]:
    """
    Returns aggregated lists management would otherwise hunt for manually.
    """
    incs = incidents_for_scope(incidents, project_name)
    now = datetime.now()
    cut_stall = now - timedelta(days=stalled_days)
    cut_repeat = now - timedelta(days=repeat_window_days)

    critical_open: list[dict] = []
    stalled_open: list[dict] = []
    osha_pdf_gap: list[dict] = []
    type_buckets: dict[tuple[str, str], list[dict]] = {}

    for inc in incs:
        a = inc.get("analysis") or {}
        sev = a.get("severity")
        st = inc.get("status")
        ts = _parse_ts(inc)
        proj = inc.get("project") or ""
        itype = a.get("incident_type") or "Other"

        if sev == "CRITICAL" and st == "Open":
            critical_open.append(inc)

        if st == "Open" and ts and ts < cut_stall:
            stalled_open.append(inc)

        if a.get("osha_recordable") and not inc.get("report_generated"):
            osha_pdf_gap.append(inc)

        if ts and ts >= cut_repeat:
            type_buckets.setdefault((proj, itype), []).append(inc)

    repeat_patterns: list[dict[str, Any]] = []
    for (proj, itype), lst in type_buckets.items():
        if len(lst) >= repeat_min_count:
            repeat_patterns.append(
                {
                    "project": proj,
                    "incident_type": itype,
                    "count": len(lst),
                    "incident_ids": [x.get("id") for x in lst if x.get("id")],
                }
            )
    repeat_patterns.sort(key=lambda x: x["count"], reverse=True)

    scope = project_name or "All projects"
    return {
        "scope_label": scope,
        "critical_open": critical_open,
        "stalled_open": stalled_open,
        "osha_pdf_gap": osha_pdf_gap,
        "repeat_patterns": repeat_patterns,
        "counts": {
            "critical_open": len(critical_open),
            "stalled_open": len(stalled_open),
            "osha_pdf_gap": len(osha_pdf_gap),
            "repeat_pattern_groups": len(repeat_patterns),
        },
    }


def stakeholder_rollup(incidents: list[dict], project_name: str | None = None) -> list[dict[str, Any]]:
    """Count reports by role + organization for subcontractor / GC visibility."""
    from collections import Counter

    incs = incidents_for_scope(incidents, project_name)
    key_counts: Counter[tuple[str, str]] = Counter()
    for inc in incs:
        role = (inc.get("stakeholder_role") or "Not specified").strip() or "Not specified"
        org = (inc.get("organization") or "—").strip() or "—"
        key_counts[(role, org)] += 1
    rows = []
    for (role, org), n in key_counts.most_common():
        rows.append({"stakeholder_role": role, "organization": org, "reports": n})
    return rows
