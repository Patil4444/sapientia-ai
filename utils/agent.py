import json
import re
from datetime import datetime
import time
import anthropic
import hashlib
import copy

# ---------------------------------------------------------------------------
# Core agent — uses Claude to parse, classify, and structure raw incident text.
# Trained with real open-source construction incidents (2020–present) so
# classification aligns with OSHA/BLS patterns and incidents this platform would have helped prevent.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_BASE = """You are a construction safety specialist AI agent embedded in an incident reporting system.
Your job is to analyze raw incident reports submitted by construction workers and extract structured data.
Your classifications are informed by real construction incidents (2020–present) from OSHA, BLS CFOI, and public reports—incidents that early reporting and correct classification could have helped prevent or mitigate.

Always respond with ONLY valid JSON, no preamble, no markdown fences.

Extract and return this exact JSON structure:
{
  "analysis_schema_version": 3,
  "incident_type": "<one of: Fall, Struck-By, Caught-In/Between, Electrical, Fire/Explosion, Chemical Exposure, Equipment Failure, Near Miss, Other>",
  "severity": "<one of: LOW, MEDIUM, CRITICAL>",
  "severity_reason": "<1 sentence explaining severity classification>",
  "injured_person": "<name or 'Unknown' if not mentioned>",
  "body_part_affected": "<body part or 'None' if no injury>",
  "location_on_site": "<specific location mentioned or 'General site'>",
  "equipment_involved": "<equipment/tools involved or 'None'>",
  "immediate_cause": "<brief root cause in 1 sentence>",
  "osha_recordable": <true or false>,
  "osha_reason": "<why this is or is not OSHA recordable>",
  "osha_forms_required": ["<list of required forms: OSHA 300, OSHA 301, 300A as applicable>"],
  "immediate_actions_required": ["<list of 2-4 immediate actions that should be taken>"],
  "risk_score": <int 0-100>,
  "risk_score_reason": "<1 sentence explaining the risk score>",
  "evidence_snippets": ["<short verbatim snippets from the incident report that justify severity/risk>"],
  "environmental_hazard_score": <int 0-100>,
  "environmental_hazard_reason": "<1 sentence explaining environmental hazard scoring>",
  "sustainability_concerns": ["<list of sustainability/environment concerns (e.g., spill to soil/water)>"],
  "sustainability_actions_required": ["<list of 2-4 sustainability actions to reduce impact>"],
  "efficiency_score": <int 0-100>,
  "efficiency_score_reason": "<1 sentence explaining efficiency opportunity scoring>",
  "efficiency_actions_required": ["<list of 2-4 efficiency actions (reduce rework, downtime, waste)>"],
  "summary": "<clean 2-3 sentence summary of the incident suitable for official report>"
}

Severity guidelines (aligned with real incident data 2020+):
- CRITICAL: fatality, hospitalization, lost consciousness, fractures, severe lacerations, amputations, chemical burns, falls > 6 feet, trench collapse, electrocution, fire/explosion with injury
- MEDIUM: medical treatment beyond first aid, restricted work, near miss with high fatality potential, equipment failure with near hit
- LOW: first aid only, minor near miss, property damage only

OSHA recordability: Recordable if days away from work, restricted work, transfer, medical treatment beyond first aid, loss of consciousness, or significant injury/illness diagnosis."""


def _build_system_prompt_with_training() -> str:
    """Append few-shot examples from real construction incidents (2020–present) to improve classification."""
    try:
        from utils.training_data import load_real_incidents
        incidents = load_real_incidents()
        if not incidents:
            return SYSTEM_PROMPT_BASE
        # Add 3 short examples: report excerpt -> correct type + severity
        examples = []
        for inc in incidents[:3]:
            raw = inc.get("raw_description", "")[:200]
            if raw:
                raw = raw + "..." if len(inc.get("raw_description", "")) > 200 else raw
            itype = inc.get("incident_type", "Other")
            sev = inc.get("severity", "MEDIUM")
            examples.append(f'Report: "{raw}" → incident_type: "{itype}", severity: "{sev}" (real incident, {inc.get("year", "N/A")})')
        if examples:
            return SYSTEM_PROMPT_BASE + "\n\nExamples from real construction incidents (classify similarly):\n" + "\n".join(examples)
    except Exception:
        pass
    return SYSTEM_PROMPT_BASE


def analyze_incident(raw_text: str, api_key: str = None) -> dict:
    """
    Send incident text to Claude and get structured analysis back.
    Falls back to rule-based mock analysis if no API key provided.
    """
    from utils.http_api import client_api_base

    base = client_api_base()
    if base:
        import httpx

        r = httpx.post(
            f"{base}/api/analyze",
            json={"raw_text": raw_text, "api_key": api_key or ""},
            timeout=120.0,
        )
        r.raise_for_status()
        return r.json()

    if api_key:
        try:
            system_prompt = _build_system_prompt_with_training()
            client = anthropic.Anthropic(api_key=api_key)

            model = "claude-opus-4-6"
            cache_key = _build_analysis_cache_key(api_key=api_key, model=model, raw_text=raw_text)
            cached = _analysis_cache_get(cache_key)
            if cached is not None:
                analysis = copy.deepcopy(cached)
                analysis.setdefault("_llm", {})
                analysis["_llm"]["cache_hit"] = True
                analysis["_llm"]["mode"] = "claude"
                return analysis

            max_attempts = 3
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    t0 = time.perf_counter()
                    message = client.messages.create(
                        model=model,
                        max_tokens=1024,
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": f"Analyze this incident report:\n\n{raw_text}"}
                        ],
                    )
                    t1 = time.perf_counter()
                    raw = message.content[0].text.strip()
                    # Strip any accidental markdown fences
                    raw = re.sub(r"^```(?:json)?\s*", "", raw)
                    raw = re.sub(r"\s*```$", "", raw)
                    analysis = json.loads(raw)
                    analysis = _normalize_analysis(analysis, raw_text=raw_text)

                    # Attach LLM metadata for demo/traceability (not part of the model contract)
                    usage = getattr(message, "usage", None) or {}
                    analysis["_llm"] = {
                        "model": getattr(message, "model", model),
                        "input_tokens": usage.get("input_tokens"),
                        "output_tokens": usage.get("output_tokens"),
                        "total_tokens": usage.get("total_tokens"),
                        "latency_seconds": round(t1 - t0, 3),
                        "mode": "claude",
                        "attempt": attempt,
                        "cache_hit": False,
                    }

                    _analysis_cache_set(cache_key, analysis)
                    return analysis
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts:
                        backoff_s = 2 ** (attempt - 1)
                        time.sleep(backoff_s)
                        continue
                    break
        except Exception as e:
            return _mock_analysis(raw_text, error=str(e))
    else:
        return _mock_analysis(raw_text)

    # If we reached here, Claude calls failed after retries.
    return _mock_analysis(raw_text, error=f"Claude analysis failed after retries: {last_error}")


_ANALYSIS_CACHE: dict[str, tuple[float, dict]] = {}
_ANALYSIS_CACHE_TTL_SECONDS = 600  # 10 minutes (session-level in-memory cache)


def _build_analysis_cache_key(api_key: str, model: str, raw_text: str) -> str:
    api_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
    text_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16]
    return f"{api_hash}:{model}:{text_hash}"


def _analysis_cache_get(cache_key: str) -> dict | None:
    item = _ANALYSIS_CACHE.get(cache_key)
    if not item:
        return None
    ts, analysis = item
    if (time.time() - ts) > _ANALYSIS_CACHE_TTL_SECONDS:
        _ANALYSIS_CACHE.pop(cache_key, None)
        return None
    return analysis


def _analysis_cache_set(cache_key: str, analysis: dict) -> None:
    _ANALYSIS_CACHE[cache_key] = (time.time(), copy.deepcopy(analysis))


def _mock_analysis(text: str, error: str = None) -> dict:
    """
    Rule-based fallback so the demo works without an API key.
    Uses real incident training data (2020–present) when the report matches a known scenario.
    """
    text_stripped = text.strip()
    text_lower = text_stripped.lower()
    # Try to match against real training incidents first (so real 2020+ scenarios classify correctly)
    try:
        from utils.training_data import load_real_incidents
        for inc in load_real_incidents():
            raw = (inc.get("raw_description") or "").strip()
            if raw and (raw.lower() in text_lower or text_lower in raw.lower() or _text_similar(text_stripped, raw)):
                return _mock_from_training_incident(inc, text_stripped, error)
    except Exception:
        pass

    # Classify severity (aligned with real incident patterns 2020+)
    critical_keywords = ["fall", "fell", "fracture", "broken", "unconscious", "hospitali",
                         "blood", "severe", "electrocuted", "crushed", "trapped", "fatality", "fatal",
                         "trench", "collapse", "amputation", "lockout", "loto", "confined space", "hot work",
                         "pronounced dead", "sustained fatal"]
    medium_keywords   = ["medical", "treatment", "doctor", "cut", "laceration", "sprain",
                         "strain", "near miss", "almost", "equipment failure", "urgent care", "beyond first aid"]

    if any(k in text_lower for k in critical_keywords):
        severity = "CRITICAL"
    elif any(k in text_lower for k in medium_keywords):
        severity = "MEDIUM"
    else:
        severity = "LOW"

    # Incident type
    if any(k in text_lower for k in ["fall", "fell", "roof", "scaffold", "ladder", "height"]):
        itype = "Fall"
    elif any(k in text_lower for k in ["electric", "shock", "wire", "current"]):
        itype = "Electrical"
    elif any(k in text_lower for k in ["chemical", "spill", "fume", "gas", "vapor"]):
        itype = "Chemical Exposure"
    elif any(k in text_lower for k in ["fire", "explosion", "burn", "flame"]):
        itype = "Fire/Explosion"
    elif any(k in text_lower for k in ["caught", "pinch", "crush", "caught in"]):
        itype = "Caught-In/Between"
    elif any(k in text_lower for k in ["struck", "hit by", "flying", "debris"]):
        itype = "Struck-By"
    elif "near miss" in text_lower or "close call" in text_lower:
        itype = "Near Miss"
    else:
        itype = "Other"

    osha_recordable = severity in ("CRITICAL", "MEDIUM")

    risk_score = _compute_risk_score(severity=severity, itype=itype, osha_recordable=osha_recordable, text=text_lower)
    evidence_snippets = _extract_evidence_snippets(text_stripped, text_lower=text_lower, max_snippets=3)
    environmental_hazard_score = _compute_environmental_hazard_score(itype=itype, text_lower=text_lower)
    sustainability_concerns = _get_sustainability_concerns(itype=itype, text_lower=text_lower, max_items=4)
    sustainability_actions_required = _get_sustainability_actions_required(
        itype=itype, text_lower=text_lower, max_items=4
    )
    efficiency_score = _compute_efficiency_score(severity=severity, itype=itype, text_lower=text_lower)
    efficiency_score_reason = _efficiency_score_reason_from_inputs(severity, itype, text_lower=text_lower)
    efficiency_actions_required = _get_efficiency_actions_required(
        severity=severity, itype=itype, text_lower=text_lower, max_items=4
    )

    result = {
        "analysis_schema_version": 3,
        "incident_type": itype,
        "severity": severity,
        "severity_reason": f"Classified as {severity} based on keywords detected in report.",
        "injured_person": "Unknown",
        "body_part_affected": "Unknown",
        "location_on_site": "General site",
        "equipment_involved": "None",
        "immediate_cause": "Under investigation — see full incident description.",
        "osha_recordable": osha_recordable,
        "osha_reason": "Likely requires medical treatment beyond first aid." if osha_recordable else "First aid only — not recordable.",
        "osha_forms_required": ["OSHA 300", "OSHA 301"] if osha_recordable else [],
        "risk_score": risk_score,
        "risk_score_reason": _risk_score_reason_from_inputs(severity, osha_recordable, itype),
        "evidence_snippets": evidence_snippets,
        "environmental_hazard_score": environmental_hazard_score,
        "environmental_hazard_reason": _environmental_hazard_reason_from_inputs(
            itype=itype, score=environmental_hazard_score
        ),
        "sustainability_concerns": sustainability_concerns,
        "sustainability_actions_required": sustainability_actions_required,
        "efficiency_score": efficiency_score,
        "efficiency_score_reason": efficiency_score_reason,
        "efficiency_actions_required": efficiency_actions_required,
        "immediate_actions_required": [
            "Secure the area and prevent further hazards",
            "Provide first aid or call 911 if needed",
            "Notify safety manager immediately",
            "Preserve evidence for investigation"
        ],
        "summary": f"Incident report submitted. AI analysis completed using rule-based fallback (no API key configured). Incident classified as {itype} with {severity} severity. Please review and verify all fields."
    }

    if error:
        result["_api_error"] = error

    return result


def _text_similar(a: str, b: str, min_len: int = 50) -> bool:
    """True if a and b share a substantial overlap (e.g. same incident description)."""
    if len(a) < min_len or len(b) < min_len:
        return False
    a_l, b_l = a.lower(), b.lower()
    return a_l[:80] == b_l[:80] or a_l in b_l or b_l in a_l


def _mock_from_training_incident(inc: dict, raw_text: str, error: str = None) -> dict:
    """Build mock analysis from a real training incident (2020–present) so classification is correct."""
    itype = inc.get("incident_type", "Other")
    sev = inc.get("severity", "MEDIUM")
    osha_recordable = sev in ("CRITICAL", "MEDIUM")

    risk_score = _compute_risk_score(severity=sev, itype=itype, osha_recordable=osha_recordable, text=raw_text.lower())
    evidence_snippets = _extract_evidence_snippets(raw_text, text_lower=raw_text.lower(), max_snippets=2)
    text_lower = raw_text.lower()
    environmental_hazard_score = _compute_environmental_hazard_score(itype=itype, text_lower=text_lower)
    sustainability_concerns = _get_sustainability_concerns(itype=itype, text_lower=text_lower, max_items=4)
    sustainability_actions_required = _get_sustainability_actions_required(
        itype=itype, text_lower=text_lower, max_items=4
    )
    efficiency_score = _compute_efficiency_score(severity=sev, itype=itype, text_lower=text_lower)
    efficiency_score_reason = _efficiency_score_reason_from_inputs(sev, itype, text_lower=text_lower)
    efficiency_actions_required = _get_efficiency_actions_required(
        severity=sev, itype=itype, text_lower=text_lower, max_items=4
    )

    result = {
        "analysis_schema_version": 3,
        "incident_type": itype,
        "severity": sev,
        "severity_reason": f"Classified from real construction incident pattern ({inc.get('year', '2020+')}). Early reporting and this platform would have triggered correct OSHA handling.",
        "injured_person": "Unknown",
        "body_part_affected": "Unknown",
        "location_on_site": "Construction site",
        "equipment_involved": "See report",
        "immediate_cause": "See incident description and investigation.",
        "osha_recordable": osha_recordable,
        "osha_reason": "Medical treatment beyond first aid or fatality — OSHA recordable." if osha_recordable else "First aid only — not recordable.",
        "osha_forms_required": ["OSHA 300", "OSHA 301"] if osha_recordable else [],
        "risk_score": risk_score,
        "risk_score_reason": _risk_score_reason_from_inputs(sev, osha_recordable, itype),
        "evidence_snippets": evidence_snippets,
        "environmental_hazard_score": environmental_hazard_score,
        "environmental_hazard_reason": _environmental_hazard_reason_from_inputs(
            itype=itype, score=environmental_hazard_score
        ),
        "sustainability_concerns": sustainability_concerns,
        "sustainability_actions_required": sustainability_actions_required,
        "efficiency_score": efficiency_score,
        "efficiency_score_reason": efficiency_score_reason,
        "efficiency_actions_required": efficiency_actions_required,
        "immediate_actions_required": [
            "Secure area and prevent further exposure",
            "Provide first aid / call 911 as needed",
            "Notify safety manager and document per OSHA",
            "Preserve evidence and complete investigation"
        ],
        "summary": f"Incident aligned with real construction incident data ({inc.get('year', 'N/A')}): {itype}, {sev}. {inc.get('how_constructsafe_helps', 'Sapientia would have enabled early reporting and correct classification.')}"
    }
    if error:
        result["_api_error"] = error
    return result


def _compute_risk_score(severity: str, itype: str, osha_recordable: bool, text: str) -> int:
    """
    Lightweight risk scoring for demo/investor clarity.
    (0-100) where severity + OSHA recordability dominate.
    """
    base = {"CRITICAL": 90, "MEDIUM": 60, "LOW": 25}.get(severity, 30)
    # Small boosts for incident types that tend to have higher consequence volatility.
    type_boost = 0
    if itype in ("Electrical", "Fire/Explosion", "Chemical Exposure"):
        type_boost += 8
    if itype == "Fall":
        type_boost += 5
    if itype == "Near Miss":
        type_boost -= 10

    recordable_boost = 6 if osha_recordable else 0
    # Keyword-based escalation for demo.
    escalation = 0
    for k in ["fracture", "amputation", "trapped", "electrocuted", "fatal", "hospital", "unconscious", "collapse"]:
        if k in text:
            escalation += 4

    score = base + type_boost + recordable_boost + escalation
    return max(0, min(100, int(score)))


def _risk_score_reason_from_inputs(severity: str, osha_recordable: bool, itype: str) -> str:
    recordable_text = "OSHA recordable" if osha_recordable else "not OSHA recordable"
    return f"Risk scored mainly from {severity} severity plus incident category ({itype}) and {recordable_text}."


def _extract_evidence_snippets(raw_text: str, text_lower: str = None, max_snippets: int = 3) -> list[str]:
    """
    Extract short snippets that justify severity/risk.
    Used by demo/mocks and as a fallback when Claude output is missing.
    """
    if text_lower is None:
        text_lower = raw_text.lower()
    # Split into short sentence-ish chunks.
    parts = [p.strip() for p in re.split(r"[.\n]", raw_text) if p.strip()]
    keywords = [
        "fell", "fracture", "unconscious", "hospital", "electrocut", "shock", "amput", "trench",
        "collapse", "chemical", "spill", "burn", "fire", "explosion", "trapped", "numb"
    ]
    picked = []
    for p in parts:
        pl = p.lower()
        if any(k in pl for k in keywords):
            picked.append(p[:140])
        if len(picked) >= max_snippets:
            break
    if not picked:
        # Fallback: take first sentences.
        picked = [parts[0][:140], parts[1][:140]] if len(parts) > 1 else [parts[0][:140]] if parts else ["No evidence snippets extracted."]
    return picked[:max_snippets]


def _normalize_analysis(analysis: dict, raw_text: str) -> dict:
    """
    Make the model output robust to missing keys and older stored incidents.
    Ensures the UI always has the fields it needs for a clean demo.
    """
    if not isinstance(analysis, dict):
        return _mock_analysis(raw_text, error="Invalid model output type (expected JSON object).")

    # Versioning / defaults
    analysis.setdefault("analysis_schema_version", 3)
    analysis.setdefault("incident_type", "Other")
    analysis.setdefault("severity", "LOW")
    analysis.setdefault("injured_person", "Unknown")
    analysis.setdefault("body_part_affected", "None")
    analysis.setdefault("location_on_site", "General site")
    analysis.setdefault("equipment_involved", "None")
    analysis.setdefault("immediate_cause", "Under investigation — see full incident description.")
    analysis.setdefault("osha_recordable", False)
    analysis.setdefault("osha_reason", "First aid only — not recordable.")
    analysis.setdefault("osha_forms_required", [])
    analysis.setdefault("immediate_actions_required", [])
    analysis.setdefault("summary", "Incident report submitted. Please review and verify fields.")

    # Risk/explainability: compute if missing.
    sev = analysis.get("severity", "LOW")
    itype = analysis.get("incident_type", "Other")
    rec = bool(analysis.get("osha_recordable", False))
    analysis.setdefault("risk_score", _compute_risk_score(severity=sev, itype=itype, osha_recordable=rec, text=raw_text.lower()))
    analysis.setdefault("risk_score_reason", _risk_score_reason_from_inputs(sev, rec, itype))
    if not analysis.get("evidence_snippets"):
        analysis["evidence_snippets"] = _extract_evidence_snippets(raw_text, text_lower=raw_text.lower(), max_snippets=3)

    # Efficiency + sustainability: compute if missing.
    text_lower = raw_text.lower()
    analysis.setdefault(
        "environmental_hazard_score",
        _compute_environmental_hazard_score(itype=itype, text_lower=text_lower),
    )
    analysis.setdefault(
        "environmental_hazard_reason",
        _environmental_hazard_reason_from_inputs(itype=itype, score=int(analysis.get("environmental_hazard_score", 0) or 0)),
    )
    analysis.setdefault(
        "sustainability_concerns",
        _get_sustainability_concerns(itype=itype, text_lower=text_lower, max_items=4),
    )
    analysis.setdefault(
        "sustainability_actions_required",
        _get_sustainability_actions_required(itype=itype, text_lower=text_lower, max_items=4),
    )
    analysis.setdefault(
        "efficiency_score",
        _compute_efficiency_score(severity=sev, itype=itype, text_lower=text_lower),
    )
    analysis.setdefault(
        "efficiency_score_reason",
        _efficiency_score_reason_from_inputs(sev, itype, text_lower=text_lower),
    )
    analysis.setdefault(
        "efficiency_actions_required",
        _get_efficiency_actions_required(severity=sev, itype=itype, text_lower=text_lower, max_items=4),
    )

    # Ensure booleans / types are sensible for the UI.
    analysis["osha_recordable"] = bool(analysis.get("osha_recordable", False))
    try:
        analysis["risk_score"] = int(analysis.get("risk_score", 0))
    except Exception:
        analysis["risk_score"] = _compute_risk_score(severity=sev, itype=itype, osha_recordable=rec, text=raw_text.lower())

    # Coerce new numeric scores.
    try:
        analysis["environmental_hazard_score"] = int(analysis.get("environmental_hazard_score", 0))
    except Exception:
        analysis["environmental_hazard_score"] = _compute_environmental_hazard_score(itype=itype, text_lower=raw_text.lower())
    try:
        analysis["efficiency_score"] = int(analysis.get("efficiency_score", 0))
    except Exception:
        analysis["efficiency_score"] = _compute_efficiency_score(severity=sev, itype=itype, text_lower=raw_text.lower())

    return analysis


def _compute_environmental_hazard_score(itype: str, text_lower: str) -> int:
    """
    Lightweight (demo) environmental hazard score (0-100).
    Higher means a higher chance of environmental impact (spill, combustion, contamination).
    """
    base = {
        "Chemical Exposure": 75,
        "Fire/Explosion": 60,
        "Electrical": 35,
        "Equipment Failure": 45,
        "Fall": 20,
        "Struck-By": 20,
        "Caught-In/Between": 25,
        "Near Miss": 15,
        "Other": 25,
    }.get(itype, 25)

    boost = 0
    for k in [
        "spill",
        "release",
        "chemical",
        "solvent",
        "fume",
        "vapor",
        "burn",
        "fire",
        "explosion",
        "washed with water",
        "hot work",
        "soot",
        "smoke",
        "extinguis",
        "foam",
        "runoff",
        "hose",
    ]:
        if k in text_lower:
            boost += 5
    return max(0, min(100, int(base + boost)))


def _environmental_hazard_reason_from_inputs(itype: str, score: int) -> str:
    label = "high" if score >= 70 else "moderate" if score >= 40 else "low"
    return f"Environmental hazard assessed as {label} based on incident category and environmental-release indicators."


def _get_sustainability_concerns(itype: str, text_lower: str, max_items: int = 4) -> list[str]:
    concerns = []

    # OPS/ESG angle for the categories most likely to appear in investor demos.
    if itype == "Fall":
        concerns.append("Dropped/fragmented materials create waste and disposal load")
        concerns.append("Cleanup may release debris to soil or storm drains if not contained")
        if "dust" in text_lower or "debris" in text_lower:
            concerns.append("Cleanup dust/particulates may require additional controls")

    if itype == "Electrical":
        concerns.append("Incorrect energizing/repair triggers avoidable component replacement (e-waste + materials waste)")
        if "fire" in text_lower or "burn" in text_lower or "smoke" in text_lower:
            concerns.append("Electrical fault risk implies additional air/emissions impacts")

    if itype == "Fire/Explosion":
        concerns.append("Combustion emissions and air-quality impact (smoke/particulates)")
        concerns.append("Handling and disposal of contaminated debris/soot")
        if "runoff" in text_lower or "washed" in text_lower or "foam" in text_lower or "hose" in text_lower:
            concerns.append("Firefighting runoff/wash-down contamination risk for soil/water")

    # Keep existing chemical indicators (often strongly ESG-relevant too).
    if itype == "Chemical Exposure" or "spill" in text_lower or "chemical" in text_lower:
        concerns.append("Potential chemical release to soil/water")
        concerns.append("Contaminated PPE/waste handling risk")
        concerns.append("Need SDS-driven spill response")

    if itype in ("Equipment Failure", "Electrical") and ("repair" in text_lower or "rework" in text_lower):
        concerns.append("Avoidable downtime and rework leading to wasted materials")

    if itype == "Near Miss":
        concerns.append("Waste and carbon impacts from repeated incidents can be avoided with stronger controls")

    # De-duplicate while preserving order.
    seen = set()
    unique = []
    for c in concerns:
        if c not in seen:
            unique.append(c)
            seen.add(c)
    if not unique:
        unique = ["Limited direct environmental indicators in the report"]
    return unique[:max_items]


def _get_sustainability_actions_required(itype: str, text_lower: str, max_items: int = 4) -> list[str]:
    actions = []

    if itype == "Fall":
        actions += [
            "Contain fallen/debris materials during cleanup (no loose debris near drains; use lined collection bins)",
            "Segregate damaged scaffold/ladder components into waste streams (recycle/landfill per site SOP)",
            "Use dust suppression or controlled clean-up methods if particulates are generated during removal",
            "Update scaffold/ladder inspection checklist and require documented sign-off before work starts",
        ]

    elif itype == "Electrical":
        actions += [
            "Strengthen LOTO compliance (pre-task checklist + sign-off + verification point at the panel/work location)",
            "Reduce reactive repairs by adding failure-pattern checks to preventive maintenance schedules",
            "Stop unnecessary replacements: repair/replace decisions require documented fault verification",
            "Ensure any removed components are handled as e-waste/material waste per approved vendor stream",
        ]

    elif itype == "Fire/Explosion":
        actions += [
            "Implement hot-work controls (permit, gas monitoring, fire watch, and smoke/dust mitigation plan)",
            "Contain soot/contaminated debris during cleanup; bag, label, and dispose via compliant route",
            "Manage firefighting runoff/wash-down water: block drains, collect water, and document handling",
            "Capture root cause + inspection findings to prevent repeat hot-work downtime and rework",
        ]

    # Chemical remains first-class ESG.
    if not actions and (itype == "Chemical Exposure" or "spill" in text_lower or "chemical" in text_lower):
        actions += [
            "Contain and isolate the spill area; use spill kit and follow SDS",
            "Flush/neutralize per SDS and prevent entry to drains/waterways",
            "Segregate contaminated waste/PPE for compliant disposal",
            "Document environmental controls and corrective prevention steps",
        ]

    # Generic but still ops-friendly fallback if none of the above matched.
    if not actions:
        actions += [
            "Review environmental risks in the task plan (JHA) and set measurable control checks before start",
            "Ensure cleanup and waste disposal follow site sustainability procedures (waste stream + documentation)",
            "Update controls to prevent recurrence and unnecessary rework",
            "Log lessons learned and schedule follow-up verification",
        ]

    return actions[:max_items]


def _compute_efficiency_score(severity: str, itype: str, text_lower: str) -> int:
    """
    Demo efficiency opportunity score (0-100).
    Higher means the incident suggests stronger opportunity to reduce downtime, rework, and waste via better process controls.
    """
    base = {"CRITICAL": 85, "MEDIUM": 65, "LOW": 45}.get(severity, 50)

    boost = 0
    for k in [
        "didn't follow",
        "notified",
        "wasn't",
        "lockout",
        "loto",
        "schedule",
        "no entry",
        "gave way",
        "broke",
        "failure to communicate",
        "urgent care",
        "equipment failure",
    ]:
        if k in text_lower:
            boost += 4

    type_boost = 0
    if itype in ("Electrical", "Chemical Exposure", "Fire/Explosion"):
        type_boost += 6
    if itype == "Near Miss":
        type_boost += 3
    if itype == "Fall":
        type_boost += 5
    return max(0, min(100, int(base + boost + type_boost)))


def _efficiency_score_reason_from_inputs(severity: str, itype: str, text_lower: str) -> str:
    sev_label = "high-impact" if severity == "CRITICAL" else "moderate-impact" if severity == "MEDIUM" else "lower-impact"
    return f"Efficiency opportunity driven by {sev_label} incident impact ({itype}) and process-control gaps detected in the report."


def _get_efficiency_actions_required(severity: str, itype: str, text_lower: str, max_items: int = 4) -> list[str]:
    actions = []
    if itype == "Electrical":
        actions += [
            "Use a LOTO verification checklist at the point of work (checkboxes + supervisor sign-off before energizing)",
            "Add photo evidence/verification steps for completed lockout/tagout where feasible",
            "Track repeat issues and trigger targeted re-training within 7 days of the incident",
            "Ensure spare parts are kitted to reduce downtime from follow-on repairs",
        ]
    elif itype == "Chemical Exposure":
        actions += [
            "Pre-stage chemical PPE and spill kits to reduce response time",
            "Implement SDS-based handling SOPs for every task requiring chemicals",
            "Introduce double-checks for PPE and container labeling before use",
            "Review chemical handling workflow to reduce spills and rework",
        ]
    elif itype == "Fire/Explosion":
        actions += [
            "Tighten hot-work permits and gas monitoring to prevent repeat events (no permit, no work)",
            "Prepare designated equipment/materials for hot-work in advance to reduce start-stop downtime",
            "Use post-event inspection findings to eliminate rework/cleanup loops (documented corrective plan)",
            "Improve housekeeping and waste segregation so cleanup is faster and less resource-intensive",
        ]
    elif itype == "Fall":
        actions += [
            "Introduce a standardized scaffold/ladder inspection schedule with documented sign-off per shift",
            "Implement dropped-object/fall prevention checks (guards, planks, access) as a pre-start gate",
            "Reduce downtime by ensuring replacement components are staged on-site for rapid corrections",
            "Run short interval toolbox talks focused on the specific failure mode detected",
        ]
    else:
        actions += [
            "Improve communication and pre-task planning to prevent repeat near misses",
            "Use job hazard analysis (JHA) with measurable control checks before start",
            "Capture root cause and update SOPs to reduce waste from rework",
            "Set a lightweight corrective action cadence (weekly follow-up) for closure",
        ]

    # Small additions based on generic signals.
    if "schedule" in text_lower or "lift schedule" in text_lower:
        actions.insert(0, "Fix lift/entry scheduling communication so crews work only inside cleared zones")

    return actions[:max_items]


def get_severity_color(severity: str) -> str:
    return {"CRITICAL": "#FF1744", "MEDIUM": "#FF6B00", "LOW": "#2E7D32"}.get(severity, "#666")


def get_severity_emoji(severity: str) -> str:
    return {"CRITICAL": "🔴", "MEDIUM": "🟠", "LOW": "🟢"}.get(severity, "⚪")
