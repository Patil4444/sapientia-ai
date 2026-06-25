"""Module 2 — Toolbox Talk Generator (Claude + rule-based fallback)."""
import json
import re
import time

from utils.agent import ANTHROPIC_MODEL, resolve_anthropic_api_key
from utils.prompts.toolbox_talk import TOOLBOX_TALK_SYSTEM_PROMPT, TOOLBOX_TALK_USER_TEMPLATE

TRADES = ["Concrete", "MEP", "Steel", "Excavation", "Roofing", "General"]
INCIDENT_TYPES = ["Fall", "Struck-by", "Caught-in/between", "Electrical", "Heat", "Chemical"]
SEVERITY_LEVELS = ["Near-miss", "First Aid", "Recordable", "Lost Time"]

_TRADE_CONTEXT = {
    "Concrete": "formwork, rebar, pump trucks, and slab edges",
    "MEP": "mechanical, electrical, and plumbing rough-in with energized systems and overhead work",
    "Steel": "ironwork, connectors, rigging, and elevated steel erection",
    "Excavation": "trenching, shoring, utilities, and heavy equipment in open cut",
    "Roofing": "low-slope and steep-slope work, fall protection anchors, and hot materials",
    "General": "multi-trade coordination, mixed hazards, and daily site logistics",
}

_INCIDENT_STATS = {
    "Fall": "Falls remain the leading cause of death in construction, accounting for roughly one in three fatalities industry-wide (OSHA/BLS).",
    "Struck-by": "Struck-by incidents — including falling objects and vehicle contact — are among OSHA's Focus Four hazards and cause hundreds of serious injuries each year.",
    "Caught-in/between": "Caught-in/between events — trench collapse, rotating equipment, and pinch points — often result in severe or fatal injuries when controls fail.",
    "Electrical": "Electrical hazards contribute to a significant share of construction fatalities; even low-voltage contact can cause cardiac arrhythmia or secondary falls.",
    "Heat": "Heat illness sends thousands of workers to clinics annually; exertional heat stroke can be fatal within minutes without rapid cooling.",
    "Chemical": "Chemical exposures and dermatitis drive many recordable cases; SDS-driven controls and proper PPE prevent most preventable contact injuries.",
}

_SEVERITY_SCENARIO = {
    "Near-miss": (
        "A close call occurred — no injury requiring treatment, but the outcome could have been serious "
        "if timing or position had been slightly different."
    ),
    "First Aid": (
        "A worker received minor on-site first aid — bandage, ice, or eyewash — and returned to work the same shift."
    ),
    "Recordable": (
        "A worker needed medical treatment beyond first aid — clinic visit, prescription, or sutures — "
        "making the event OSHA recordable."
    ),
    "Lost Time": (
        "A worker sustained an injury requiring days away from work or restricted duty, stopping production on that crew."
    ),
}

_CORRECTIVE_BY_INCIDENT = {
    "Fall": [
        "Inspect fall protection and anchor points before every shift; tag out damaged lanyards or harnesses.",
        "Establish 100% tie-off zones at leading edges; no unprotected work above 6 feet.",
        "Keep floors and decks clear of trip hazards; secure tools and materials from falling.",
        "Use guardrails, covers, or safety nets where feasible before relying on PFAS alone.",
        "Conduct a pre-task briefing on access routes, rescue plan, and weather impacts.",
    ],
    "Struck-by": [
        "Define and barricade swing zones and lift paths; never work under suspended loads.",
        "Require hard hats and high-visibility vests in mixed-equipment areas at all times.",
        "Secure materials and tools at height; use toe boards and debris netting.",
        "Use spotters and two-way communication for backing equipment and crane picks.",
        "Stage deliveries away from pedestrian paths; coordinate lift schedules with all trades.",
    ],
    "Caught-in/between": [
        "Never enter a trench deeper than 5 feet without protective systems inspected by a competent person.",
        "Lock out and tag out equipment before clearing jams or performing maintenance.",
        "Keep hands and body clear of pinch points; use push tools instead of hands where possible.",
        "Verify machine guards and interlocks are in place before start-up.",
        "Maintain exclusion zones around rotating, crushing, or compacting equipment.",
    ],
    "Electrical": [
        "Verify zero energy with a meter before touching conductors; follow LOTO every time.",
        "Use GFCI protection on temporary power and inspect cords for damage daily.",
        "Maintain approach boundaries around energized parts; only qualified workers inside.",
        "Label panels and circuits; coordinate outages with all affected crews.",
        "Wear appropriate arc-rated PPE for the incident energy level when required.",
    ],
    "Heat": [
        "Schedule heavy work during cooler hours; rotate workers through shade breaks.",
        "Provide cool water within reach and encourage a cup every 15–20 minutes.",
        "Train everyone to recognize heat exhaustion vs. heat stroke and call 911 for stroke symptoms.",
        "Acclimatize new workers over 7–14 days; reduce workload the first week.",
        "Use buddy checks; no one works alone in extreme heat conditions.",
    ],
    "Chemical": [
        "Read the SDS before first use; know first aid, PPE, and spill steps.",
        "Wear chemical-resistant gloves and eye protection matched to the product.",
        "Store containers sealed, labeled, and segregated by compatibility.",
        "Keep spill kits stocked at point of use; contain runoff away from drains.",
        "Wash hands and face before eating; never mix products unless directed by SDS.",
    ],
}


def _get_anthropic_llm(api_key: str):
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=ANTHROPIC_MODEL,
        api_key=api_key,
        temperature=0.4,
        max_tokens=2048,
    )


def _parse_llm_json(content: str) -> dict:
    raw = (content or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def _word_count(*parts) -> int:
    text = " ".join(str(p) for p in parts if p)
    return len(re.findall(r"\b\w+\b", text))


def _assemble_full_text(data: dict) -> str:
    behaviors = data.get("corrective_behaviors") or []
    behavior_block = "\n".join(f"{i}. {b}" for i, b in enumerate(behaviors, 1))
    sections = [
        "OPENING",
        data.get("opening_statistic", ""),
        "",
        "SCENARIO",
        data.get("scenario_narrative", ""),
        "",
        "CORRECTIVE BEHAVIORS",
        behavior_block,
        "",
        "SIGN-OFF / ATTENDANCE",
        data.get("sign_off", ""),
    ]
    return "\n".join(s for s in sections if s is not None).strip()


def _normalize_talk(data: dict, trade: str, incident_type: str, severity: str) -> dict:
    behaviors = list(data.get("corrective_behaviors") or [])
    while len(behaviors) < 5:
        behaviors.append("Review job hazard analysis and stop work if conditions change.")
    data["corrective_behaviors"] = behaviors[:5]
    data["trade"] = trade
    data["incident_type"] = incident_type
    data["severity"] = severity
    data.setdefault("opening_statistic", _INCIDENT_STATS.get(incident_type, ""))
    data.setdefault("scenario_narrative", "")
    data.setdefault("sign_off", _default_sign_off())
    data["full_text"] = _assemble_full_text(data)
    data["word_count"] = _word_count(
        data["opening_statistic"],
        data["scenario_narrative"],
        " ".join(data["corrective_behaviors"]),
        data["sign_off"],
    )
    return data


def _default_sign_off() -> str:
    return (
        "Facilitator: _________________________  Date: _______________\n\n"
        "I acknowledge participation in today's toolbox talk:\n\n"
        "1. _________________________  2. _________________________\n"
        "3. _________________________  4. _________________________\n"
        "5. _________________________  6. _________________________\n"
        "7. _________________________  8. _________________________"
    )


def _mock_toolbox_talk(trade: str, incident_type: str, severity: str, error: str | None = None) -> dict:
    """Rule-based fallback when no API key or Claude fails."""
    ctx = _TRADE_CONTEXT.get(trade, _TRADE_CONTEXT["General"])
    stat = _INCIDENT_STATS.get(incident_type, "Construction injuries are largely preventable with planning and consistent field discipline.")
    sev_note = _SEVERITY_SCENARIO.get(severity, _SEVERITY_SCENARIO["Near-miss"])
    behaviors = list(_CORRECTIVE_BY_INCIDENT.get(incident_type, _CORRECTIVE_BY_INCIDENT["Fall"]))

    narrative = (
        f"On a recent {trade.lower()} project, the crew was working with {ctx}. "
        f"During a routine task, conditions aligned for a {incident_type.lower()} event. {sev_note} "
        f"The foreman stopped work immediately, secured the area, and walked the crew through what went wrong.\n\n"
        f"Before the event, the team had skipped a full pre-task briefing because the scope looked small. "
        f"Materials were staged in a travel path, communication between trades was informal, and at least one worker "
        f"assumed existing controls would be enough. That combination — hurry, assumptions, and unclear roles — "
        f"is how serious events start on jobs that otherwise have good safety paperwork.\n\n"
        f"In this scenario, the trigger was familiar: production pressure, a last-minute schedule change, and "
        f"nobody willing to call a timeout. After the event, the crew documented lessons learned, updated the JHA, "
        f"and agreed on five field behaviors we will practice starting today. Nobody should need luck to go home safe. "
        f"Your signature at the end of this talk confirms you understand the scenario and will apply these controls "
        f"before the next pour, pick, tie-in, or excavation."
    )

    # Pad narrative toward charter 400–600 word target when rule-based.
    extra = (
        f"\n\nFor {trade} work specifically, focus on the interfaces: where your task meets equipment, "
        f"weather, adjacent trades, and changing site layout. When those interfaces shift, stop and re-brief. "
        f"A {severity.lower()} outcome is a signal — either we got lucky or our controls partially worked. "
        f"Either way, we tighten the plan before repeating the same task tomorrow.\n\n"
        f"Discuss with your crew: What would you do differently in the first 30 seconds? Who has authority to stop work? "
        f"Where are the nearest phones, eyewash stations, and muster points? Take two minutes now to point them out."
    )
    narrative = narrative + extra

    result = _normalize_talk(
        {
            "opening_statistic": stat,
            "scenario_narrative": narrative,
            "corrective_behaviors": behaviors,
            "sign_off": _default_sign_off(),
            "_llm": {"mode": "rule_based"},
        },
        trade,
        incident_type,
        severity,
    )
    if error:
        result["_api_error"] = error
    return result


def _call_claude(trade: str, incident_type: str, severity: str, api_key: str) -> dict:
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = _get_anthropic_llm(api_key)
    user_content = TOOLBOX_TALK_USER_TEMPLATE.format(
        trade=trade,
        incident_type=incident_type,
        severity=severity,
    )
    messages = [
        SystemMessage(content=TOOLBOX_TALK_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    max_attempts = 3
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            t0 = time.perf_counter()
            response = llm.invoke(messages)
            t1 = time.perf_counter()
            content = response.content
            if not isinstance(content, str):
                content = str(content or "")
            data = _parse_llm_json(content)
            data["_llm"] = {
                "model": ANTHROPIC_MODEL,
                "latency_seconds": round(t1 - t0, 3),
                "mode": "claude",
                "attempt": attempt,
            }
            return _normalize_talk(data, trade, incident_type, severity)
        except Exception as e:
            last_error = e
            if attempt < max_attempts:
                time.sleep(2 ** (attempt - 1))
                continue
            break

    raise RuntimeError(f"Claude toolbox talk failed after retries: {last_error}")


def generate_toolbox_talk(
    trade: str,
    incident_type: str,
    severity: str,
    api_key: str | None = None,
) -> dict:
    """
    Generate a structured ~10-minute toolbox talk.
    Delegates to FastAPI when SAPIENTIA_API_URL is set; otherwise calls Claude or rule-based fallback.
    """
    from utils.http_api import client_api_base

    trade = trade if trade in TRADES else "General"
    incident_type = incident_type if incident_type in INCIDENT_TYPES else "Fall"
    severity = severity if severity in SEVERITY_LEVELS else "Near-miss"

    base = client_api_base()
    if base:
        import httpx

        try:
            r = httpx.post(
                f"{base}/api/toolbox-talk/generate",
                json={
                    "trade": trade,
                    "incident_type": incident_type,
                    "severity": severity,
                    "api_key": api_key or "",
                },
                timeout=120.0,
            )
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            from utils.http_api import format_backend_http_error

            raise RuntimeError(
                format_backend_http_error(e, base, context="toolbox-talk API")
            ) from e

    resolved_key = resolve_anthropic_api_key(api_key)
    if resolved_key:
        try:
            return _call_claude(trade, incident_type, severity, resolved_key)
        except Exception as e:
            return _mock_toolbox_talk(trade, incident_type, severity, error=str(e))

    return _mock_toolbox_talk(trade, incident_type, severity)
