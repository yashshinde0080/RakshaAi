"""Raksha AI Triage — one endpoint, two agents, hard validation gates.

Pipeline per request:
1. Front gate: plain-Python vitals validator — impossible vitals (e.g. HR 300)
   are rejected with 422 before the LLM is ever invoked.
2. Triage Agent (LLM, when a generative engine is loaded): forced into strict
   JSON via prompt; the reply is re-checked against the same schema.
3. Back gate: on a schema failure it retries once with the errors fed back,
   then falls back to the deterministic rule-based ESI flowchart — a bad model
   output can never block a triage decision. The rule engine also acts as a
   floor: if it scores MORE severe than the LLM, the result escalates (and an
   LLM that scores MORE severe than the floor is flagged over_triage). The LLM
   call is also time-boxed — a slow model falls back just like a bad one.
4. Every call + validation result is logged to local SQLite (audit_log).
"""
import asyncio

from fastapi import APIRouter, HTTPException, Request

from app.schemas.triage import TriageRequest, TriageResponse, TriageValidation
from app.core.triage import (
    LABELS,
    build_triage_prompt,
    extract_json,
    rule_based_triage,
    validate_triage_output,
    validate_vitals,
)

router = APIRouter()

# A hung or glacial model must never block a triage decision: cap the LLM call
# and let the existing retry → rule-fallback path take over.
TRIAGE_LLM_TIMEOUT_SECONDS = 180


def _is_generative_engine(engine) -> bool:
    """Can this engine produce free text? Mirrors the web console's heuristics."""
    meta = getattr(engine, "task_metadata", {}) or {}
    task = meta.get("task_type")
    if meta.get("is_generative"):
        return True
    if task in ("causal_lm", "seq2seq_lm", "unknown"):
        return True
    # Engine exposed no task_metadata (e.g. an older LayerStream load). Never
    # silently skip the LLM on that — resolve from the model path like the
    # /models/current endpoint does.
    try:
        from app.core.task_resolver import TaskResolver
        resolved = TaskResolver.resolve(getattr(engine, "model_path", ""))
        return bool(resolved.get("is_generative", False))
    except Exception:
        return False


def _engine_text(response: dict) -> str:
    # FullRAM/LayerStream chat engines return {"text": ...}; unified task
    # engines return {"output": ...}. Same fallback as chat.py.
    if "output" in response:
        return response.get("output", "") or ""
    return response.get("text", "") or ""


async def _llm_triage(app, inp: dict) -> tuple[dict | None, str, int, list[str]]:
    """Run the Triage Agent. Returns (result-or-None, source, retries, errors)."""
    engine = app.state.active_engine
    if not engine or not _is_generative_engine(engine):
        return None, "rules", 0, []

    tokenizer = getattr(engine, "tokenizer", None)
    raw_prompt = build_triage_prompt(inp)
    errors: list[str] = []
    timed_out = False

    for attempt in range(2):  # initial + one retry
        try:
            # Always template from the raw prompt — never re-template the
            # already-templated string from a previous attempt.
            prompt = raw_prompt
            if tokenizer and hasattr(tokenizer, "apply_chat_template"):
                prompt = tokenizer.apply_chat_template(
                    [{"role": "user", "content": raw_prompt}],
                    tokenize=False,
                    add_generation_prompt=True,
                )
            response = await asyncio.wait_for(
                engine.generate(
                    input_data=prompt, max_tokens=600, temperature=0.2, top_p=0.9
                ),
                timeout=TRIAGE_LLM_TIMEOUT_SECONDS,
            )
            text = _engine_text(response)
            parsed = extract_json(text)
            ok, errors = validate_triage_output(parsed)
            if ok:
                return _normalize(parsed), ("llm" if attempt == 0 else "llm_retry"), attempt, []
            raw_prompt = build_triage_prompt(inp, feedback=errors)  # retry with feedback
        except asyncio.TimeoutError:
            timed_out = True
            continue  # slow model — retry once, then rules
        except Exception:
            # model error / malformed JSON — retry, then fall back to rules
            continue
    if timed_out:
        errors.insert(0, "llm timed out")
    return None, "rules", 1, errors


def _normalize(parsed: dict) -> dict:
    severity = parsed["severity"]
    return {
        "severity": severity,
        "label": LABELS[severity],
        "is_emergency": severity <= 2,
        "recommended_action": parsed["next_action"].strip(),
        "reasons": parsed.get("reasons", []),
        "red_flags": parsed.get("red_flags", []),
    }


@router.post("/", response_model=TriageResponse)
async def run_triage(request: Request, triage: TriageRequest):
    app = request.app
    inp = triage.model_dump()

    # ── Front gate: impossible vitals are rejected before the LLM runs ──
    validator_errors = validate_vitals(inp)
    if validator_errors:
        app.state.db.audit.log(
            event_type="triage",
            severity="warning",
            source="triage.validator",
            message="Triage rejected: impossible vitals",
            metadata={"errors": validator_errors, "input": inp},
        )
        raise HTTPException(status_code=422, detail="; ".join(validator_errors))

    # ── Triage Agent (LLM) with schema re-check, retry, then rule fallback ──
    result, source, retries, schema_errors = await _llm_triage(app, inp)

    escalated = False
    over_triage = False
    if result is None:
        result = rule_based_triage(inp)
        source = "rules"
    else:
        rule = rule_based_triage(inp)
        # Asymmetry is the safe direction: the model may over-triage (flagged,
        # kept — the action still says seek care) but never under-triage. The
        # rule engine is the floor (PRD: ties resolve to the more severe level).
        over_triage = result["severity"] > rule["severity"]
        if rule["severity"] > result["severity"]:
            result["severity"] = rule["severity"]
            result["label"] = rule["label"]
            result["is_emergency"] = rule["is_emergency"]
            result["recommended_action"] = rule["recommended_action"]
            result["reasons"] = list(dict.fromkeys(rule["reasons"] + result["reasons"]))
            escalated = True

    schema_ok = source != "rules" or not schema_errors

    # ── Audit trail: every call + validation result → local SQLite ──
    app.state.db.audit.log(
        event_type="triage",
        source="triage",
        message=f"Triage complete: ESI level {result['severity']} via {source}"
        + (" (escalated)" if escalated else "")
        + (" (over-triaged by ai)" if over_triage else ""),
        metadata={
            "input": inp,
            "severity": result["severity"],
            "source": source,
            "escalated": escalated,
            "over_triage": over_triage,
            "retries": retries,
            "schema_ok": schema_ok,
            "schema_errors": schema_errors,
            "reasons": result["reasons"],
        },
    )

    return TriageResponse(
        severity=result["severity"],
        label=result["label"],
        is_emergency=result["is_emergency"],
        recommended_action=result["recommended_action"],
        reasons=result["reasons"],
        red_flags=result.get("red_flags", []),
        source=source,
        escalated=escalated,
        over_triage=over_triage,
        validation=TriageValidation(
            validator_errors=[],
            schema_ok=schema_ok,
            retries=retries,
        ),
    )
