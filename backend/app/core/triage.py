"""Raksha AI Triage — core logic. Pure functions, no I/O, no engine imports.

Two hard gates around the LLM:
- Front: `validate_vitals()` rejects impossible vitals before the model runs.
- Back: `validate_triage_output()` re-checks the model's JSON against the same
  schema; on failure the endpoint retries once, then falls back to
  `rule_based_triage()`, the deterministic ESI flowchart below (thresholds from
  PRD §7/§10 — see the Clinical Review Log before changing any number).

This module is the safety-critical core: every branch is covered by
`backend/tests/test_triage.py`.
"""
from __future__ import annotations

import json
import re
from typing import Any

# ── Vitals validator (front gate) ────────────────────────────────────────────
# Possible-value bounds: values outside these are impossible for a living human
# (or a data-entry error) and reject the call BEFORE the LLM is ever invoked.
VITAL_BOUNDS: dict[str, tuple[float, float, str]] = {
    "heart_rate": (20, 250, "Heart rate"),
    "systolic_bp": (40, 300, "Systolic BP"),
    "spo2": (50, 100, "SpO2"),
    "temperature_c": (30.0, 45.0, "Temperature"),
    "respiratory_rate": (4, 80, "Respiratory rate"),
}

# Carried demographic, not a rule input: ESI is gender-neutral, but the value
# flows into the LLM prompt and the audit trail so a clinician sees it.
GENDER_VALUES = ("male", "female", "other")


def validate_vitals(inp: dict) -> list[str]:
    """Return a list of impossible-vital errors; empty list means 'pass'."""
    errors: list[str] = []
    vitals = inp.get("vitals") or {}
    for key, (lo, hi, label) in VITAL_BOUNDS.items():
        value = vitals.get(key)
        if value is not None:
            if not isinstance(value, (int, float)):
                errors.append(f"{label} must be a number")
            elif not (lo <= value <= hi):
                errors.append(f"{label} {value} is outside the possible range {lo}-{hi}")

    age = inp.get("age_years")
    if age is not None and not (0 <= age <= 120):
        errors.append(f"Age {age} is outside the possible range 0-120")
    gender = vitals.get("gender")
    if gender is not None and gender not in GENDER_VALUES:
        errors.append(f"Gender must be one of {', '.join(GENDER_VALUES)}")
    pain = inp.get("pain_score")
    if pain is not None and not (0 <= pain <= 10):
        errors.append(f"Pain score {pain} must be 0-10")
    duration = inp.get("symptom_duration_hours")
    if duration is not None and duration < 0:
        errors.append("Symptom duration cannot be negative")
    return errors


# ── Age-aware vital bands ────────────────────────────────────────────────────
# The critical/borderline HR & RR checks below are adult defaults, but a
# toddler's normal heart rate (120-160) is *critical* by adult rules — that
# over-triages healthy children to ESI 1. Only heart rate and respiratory rate
# get age bands; BP/SpO2/temperature bands are stable enough for triage.
# Band format: (min_age, max_age_exclusive, hr_crit, hr_normal, rr_crit, rr_normal)
#   critical   = x < crit_lo or x > crit_hi                      → ESI 1
#   borderline = crit_lo < x < normal_lo or normal_hi < x <= crit_hi → ESI 2
# The adult default tuple reproduces the pre-band behavior exactly.
# ponytail: 4 bands; finer per-year tables add nothing to a triage gate.
AGE_VITAL_BANDS = [
    (0, 2, (70, 200), (95, 180), (16, 60), (24, 50)),    # infant
    (2, 12, (50, 170), (65, 155), (12, 50), (16, 40)),   # child
    (12, 18, (40, 160), (50, 150), (10, 40), (12, 30)),  # adolescent
    (75, 150, (35, 140), (45, 130), (8, 30), (10, 26)),  # elderly
]

_ADULT_VITAL_BANDS = ((40, 150), (50, 120), (8, 30), (11, 25))


def _hr_rr_bands(age_years):
    """Age-appropriate (hr_crit, hr_normal, rr_crit, rr_normal); adult default."""
    if age_years is not None:
        for lo, hi, hr_c, hr_n, rr_c, rr_n in AGE_VITAL_BANDS:
            if lo <= age_years < hi:
                return hr_c, hr_n, rr_c, rr_n
    return _ADULT_VITAL_BANDS


# ── Rule-based ESI flowchart (the deterministic fallback) ────────────────────
# Thresholds and reason wording follow PRD §7 and the Clinical Review Log §10.

RED_FLAGS: list[tuple[str, str]] = [
    ("unresponsive", "Unresponsive / unconscious"),
    ("not_breathing", "Not breathing or gasping"),
    ("stroke_signs", "Stroke signs (facial droop, arm weakness, slurred speech)"),
    ("chest_pain_severe", "Severe chest pain or pressure"),
    ("uncontrolled_bleeding", "Uncontrolled bleeding"),
    ("anaphylaxis_signs", "Signs of anaphylaxis (swelling, hives, trouble breathing)"),
    ("seizure_active", "Active seizure"),
]

HIGH_RISK_SYMPTOMS = {
    "chest_pain", "shortness_of_breath", "sudden_severe_headache", "confusion",
    "fainting", "coughing_blood", "severe_abdominal_pain", "one_sided_weakness",
}
GI_SYMPTOMS = {"vomiting", "diarrhea", "dehydration_signs", "unable_to_keep_fluids"}
FRACTURE_SYMPTOM = "suspected_fracture"

LABELS = {
    1: "Immediate — life-threatening",
    2: "Emergency — seek care now",
    3: "Urgent — seek care today",
    4: "Less urgent — seek care soon",
    5: "Non-urgent — self-care",
}

ACTIONS = {
    1: "Call emergency services now (112 / your local number). Do not wait.",
    2: "Seek emergency care immediately. Call ahead if you can.",
    3: "Seek care today — urgent care or a clinic. Monitor closely.",
    4: "Seek care soon — see a provider within a few days if it persists.",
    5: "Self-care and monitor. Seek care if symptoms worsen or persist.",
}


def _critical_vital_reasons(v: dict, age_years=None) -> list[str]:
    """Critical vitals → ESI 1. Exactly-on-boundary values are NOT critical
    (e.g. HR 40 or RR 8) — they fall into the borderline band instead."""
    reasons: list[str] = []
    hr_c, hr_n, rr_c, rr_n = _hr_rr_bands(age_years)
    checks = [
        (v.get("spo2"), lambda x: x < 90, "SpO2 below 90%"),
        (v.get("systolic_bp"), lambda x: x < 90 or x > 200, "Systolic BP under 90 or over 200"),
        (v.get("heart_rate"), lambda x: x < hr_c[0] or x > hr_c[1], f"Heart rate under {hr_c[0]} or over {hr_c[1]}"),
        (v.get("respiratory_rate"), lambda x: x < rr_c[0] or x > rr_c[1], f"Respiratory rate under {rr_c[0]} or over {rr_c[1]}"),
    ]
    for value, bad, label in checks:
        if value is not None and bad(value):
            reasons.append(f"Critical vital: {label} ({value})")
    return reasons


def _emergent_reasons(inp: dict) -> list[str]:
    """Emergent signals → ESI 2 (borderline vitals, temperature, high-risk
    symptoms, pain >= 9)."""
    reasons: list[str] = []
    v = inp.get("vitals") or {}
    hr_c, hr_n, rr_c, rr_n = _hr_rr_bands(inp.get("age_years"))
    checks = [
        (v.get("spo2"), lambda x: 90 <= x <= 94, "SpO2 90-94% (borderline)"),
        (v.get("systolic_bp"), lambda x: 90 <= x <= 99 or 181 <= x <= 200, "Systolic BP borderline"),
        (v.get("heart_rate"), lambda x: hr_c[0] < x < hr_n[0] or hr_n[1] < x <= hr_c[1], f"Heart rate borderline for age (normal {hr_n[0]}-{hr_n[1]})"),
        (v.get("respiratory_rate"), lambda x: rr_c[0] < x < rr_n[0] or rr_n[1] < x <= rr_c[1], f"Respiratory rate borderline for age (normal {rr_n[0]}-{rr_n[1]})"),
    ]
    for value, bad, label in checks:
        if value is not None and bad(value):
            reasons.append(f"Borderline vital: {label} ({value})")
    temp = v.get("temperature_c")
    if temp is not None:
        if temp >= 39.5:
            reasons.append(f"High fever: {temp} °C (>= 39.5)")
        elif temp <= 35.0:
            reasons.append(f"Hypothermia: {temp} °C (<= 35.0)")
    symptoms = set(inp.get("symptoms") or [])
    if symptoms & HIGH_RISK_SYMPTOMS:
        reasons.append("High-risk symptom: " + ", ".join(sorted(symptoms & HIGH_RISK_SYMPTOMS)))
    if (inp.get("pain_score") or 0) >= 9:
        reasons.append("Pain score 9 or higher")
    return reasons


def _urgent_reasons(inp: dict) -> list[str]:
    """Urgent signals → ESI 3 (GI/dehydration, fracture, pain >= 6, >= 48h)."""
    reasons: list[str] = []
    symptoms = set(inp.get("symptoms") or [])
    if symptoms & GI_SYMPTOMS:
        reasons.append("GI / dehydration symptom: " + ", ".join(sorted(symptoms & GI_SYMPTOMS)))
    if FRACTURE_SYMPTOM in symptoms:
        reasons.append("Suspected fracture")
    if (inp.get("pain_score") or 0) >= 6:
        reasons.append("Pain score 6 or higher")
    if (inp.get("symptom_duration_hours") or 0) >= 48:
        reasons.append("Symptoms present 48 hours or longer")
    return reasons


def rule_based_triage(inp: dict) -> dict:
    """Deterministic ESI severity. Strict priority order, ties to the more
    severe level, never silently downgrades. Pure — safe to unit test."""
    reasons = [
        f"Red flag: {label}"
        for key, label in RED_FLAGS
        if (inp.get("red_flags") or {}).get(key)
    ]
    reasons += _critical_vital_reasons(inp.get("vitals") or {}, inp.get("age_years"))
    if reasons:
        return _result(1, reasons)

    reasons = _emergent_reasons(inp)
    if reasons:
        return _result(2, reasons)

    reasons = _urgent_reasons(inp)
    if reasons:
        return _result(3, reasons)

    reasons = []
    if (inp.get("pain_score") or 0) >= 3:
        reasons.append("Pain score 3 or higher")
    if inp.get("symptoms"):
        reasons.append("Symptom selected: " + ", ".join(sorted(inp.get("symptoms"))))
    if reasons:
        return _result(4, reasons)

    return _result(5, ["No significant triggers"])


def _result(severity: int, reasons: list[str]) -> dict:
    return {
        "severity": severity,
        "label": LABELS[severity],
        "is_emergency": severity <= 2,
        "recommended_action": ACTIONS[severity],
        "reasons": reasons,
    }


# ── LLM output schema + re-check (back gate) ─────────────────────────────────

TRIAGE_SCHEMA_HINT = (
    '{"severity": <int 1-5>, "red_flags": [<str>...], '
    '"next_action": "<str>", "reasons": [<str>...]}'
)

SYSTEM_PROMPT = (
    "You are a triage agent implementing the Emergency Severity Index (ESI) protocol. "
    "You are a decision-support healthcare helper, not a doctor — you never diagnose. "
    "Assess the patient's urgency from the structured input. "
    "Return ONLY one JSON object, no prose, with EXACTLY these keys: "
    + TRIAGE_SCHEMA_HINT + ". "
    "severity: 1=life-threatening act now; 2=emergency seek care immediately; "
    "3=urgent seek care today; 4=less urgent seek care soon; 5=non-urgent self-care. "
    "red_flags: one string per triggered red flag (empty list if none). "
    "next_action: one short instruction string. "
    "reasons: one short string per reason for the chosen severity. "
    "Never invent values. Any red flag or critical vital (SpO2<90, systolic BP<90 "
    "or >200, HR<40 or >150, RR<8 or >30) means severity MUST be 1."
)


def build_triage_prompt(inp: dict, feedback: list[str] | None = None) -> str:
    """Strict-JSON prompt for the Triage Agent. `feedback` carries the previous
    attempt's schema errors on retry."""
    user = "Patient input:\n" + json.dumps(inp, default=str, indent=2)
    if feedback:
        user += (
            "\n\nYour previous output failed validation:\n- "
            + "\n- ".join(feedback)
            + "\nReturn valid JSON matching the schema exactly. Do not add anything outside the JSON."
        )
    return f"{SYSTEM_PROMPT}\n\n{user}"


def extract_json(text: str) -> dict:
    """Parse the model's reply as JSON, tolerating markdown fences and stray
    prose around the object. Raises ValueError when no JSON object is found."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("JSON is not an object")
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            parsed = json.loads(match.group())
            if isinstance(parsed, dict):
                return parsed
        raise ValueError("No JSON object found in model output")


def validate_triage_output(obj: Any) -> tuple[bool, list[str]]:
    """Back gate: re-check the model's output against the same schema used to
    prompt it. Returns (ok, errors). A 'fail' here triggers one retry, then the
    rule-based fallback — a malformed model reply can never block a decision."""
    if not isinstance(obj, dict):
        return False, ["Output was not a JSON object"]
    errors: list[str] = []
    severity = obj.get("severity")
    if not isinstance(severity, int) or isinstance(severity, bool) or not 1 <= severity <= 5:
        errors.append("severity must be an integer 1-5")
    for field in ("red_flags", "reasons"):
        value = obj.get(field)
        if value is None:
            errors.append(f"missing key: {field}")
        elif not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            errors.append(f"{field} must be a list of strings")
    action = obj.get("next_action")
    if not isinstance(action, str) or not action.strip():
        errors.append("next_action must be a non-empty string")
    return (not errors), errors


# ── Healthcare helper persona — medical chat routing ────────────────────────
# Any medical/healthcare query answered by ANY loaded model is routed through
# the triage agents: the model is told it is a healthcare helper and
# instructor (never a doctor), and a triage hint from the deterministic ESI
# flowchart is attached to the reply as a visible guardrail.

HEALTHCARE_HELPER_SYSTEM_PROMPT = (
    "You are Raksha AI, a healthcare helper and instructor — a decision-support "
    "aid, NOT a doctor. You never give a diagnosis, never prescribe, and never "
    "replace professional medical care. Follow the Emergency Severity Index "
    "(ESI): if any red flag or emergency sign appears (unconsciousness, not "
    "breathing, severe chest pain, stroke signs, uncontrolled bleeding, "
    "anaphylaxis, active seizure, critically abnormal vitals), instruct the "
    "person to call emergency services now (112 / their local number). Use the "
    "ESI levels (1-5) to explain how urgently to seek care, and always encourage "
    "following up with a real clinician for anything concerning. Keep answers "
    "calm, practical, and clearly non-medical in authority."
)

# Full words are matched on word boundaries so "pain" does not fire inside
# "painting" nor "cold" inside "scolding" (the safe direction stays: any real
# mention still matches, over-triggering just adds a harmless guardrail).
MEDICAL_WORD_KEYWORDS = [
    "pain", "ache", "aches", "headache", "fever", "temperature", "heart",
    "chest", "breath", "breathe", "breathing", "cough", "vomit", "nausea",
    "diarrhea", "rash", "swelling", "swollen", "blood", "bleed", "seizure",
    "stroke", "dizzy", "dizziness", "faint", "fatigue", "weakness", "numb",
    "sore throat", "cold", "flu", "anaphylaxis", "injury", "wound",
    "fracture", "broken bone", "urine", "poison", "overdose", "doctor",
    "hospital", "emergency", "ambulance", "blood pressure", "heart rate",
    "spo2", "oxygen", "sugar", "diabetes", "asthma", "hurts",
    "my head", "my back", "my leg", "my arm", "my stomach", "my knee",
    "my ankle", "my wrist", "my shoulder", "my neck", "my hand", "my foot",
]

# Distinctive prefix stems matched as substrings: they catch the inflected
# forms (diagnos->diagnose/diagnosis, medicat->medicate/medication) while
# being specific enough to avoid the word-boundary false positives above.
MEDICAL_STEM_KEYWORDS = ["diagnos", "medicat", "prescrib", "allerg", "dehydrat", "symptom", "infect"]

_MEDICAL_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in MEDICAL_WORD_KEYWORDS) + r")\b"
)


def is_medical_query(text: str) -> bool:
    """Heuristic medical-intent detector for free-text chat messages."""
    t = text.lower()
    if _MEDICAL_RE.search(t):
        return True
    return any(s in t for s in MEDICAL_STEM_KEYWORDS)


_RED_FLAG_KW: dict[str, tuple[str, ...]] = {
    "unresponsive": ("unresponsive", "unconscious", "won't wake", "cannot wake", "no response", "doesn't respond"),
    "not_breathing": ("not breathing", "stopped breathing", "gasping", "no pulse"),
    "stroke_signs": ("stroke", "facial droop", "face droop", "arm weakness", "slurred speech", "slurring"),
    "chest_pain_severe": ("severe chest pain", "crushing chest", "squeezing chest pain"),
    "uncontrolled_bleeding": ("uncontrolled bleeding", "bleeding heavily", "won't stop bleeding", "hemorrhage"),
    "anaphylaxis_signs": ("anaphylaxis", "anaphylactic"),
    "seizure_active": ("seizure", "fitting", "convulsion", "convulsing"),
}

_SYMPTOM_KW: dict[str, tuple[str, ...]] = {
    "chest_pain": ("chest pain", "chest tightness", "chest pressure"),
    "shortness_of_breath": ("shortness of breath", "can't breathe", "cannot breathe", "trouble breathing", "difficulty breathing", "out of breath"),
    "sudden_severe_headache": ("sudden severe headache", "worst headache", "exploding headache"),
    "confusion": ("confused", "confusion", "disoriented"),
    "fainting": ("fainted", "fainting", "passed out", "blacked out", "lost consciousness"),
    "coughing_blood": ("coughing blood", "cough up blood", "blood in sputum"),
    "severe_abdominal_pain": ("severe abdominal", "severe stomach", "abdominal pain"),
    "one_sided_weakness": ("one-sided weakness", "one side weakness", "weak on one side", "numbness on one side"),
    "vomiting": ("vomiting", "vomit", "throwing up"),
    "diarrhea": ("diarrhea", "diarrhoea"),
    "dehydration_signs": ("dehydrat", "not urinating", "not peeing"),
    "unable_to_keep_fluids": ("can't keep fluids", "cannot keep fluids", "can't keep water"),
    "suspected_fracture": ("fracture", "broken bone", "broken arm", "broken leg", "broken wrist"),
}


def triage_hint_from_text(text: str) -> dict:
    """Map detectable signals in free text onto the deterministic ESI flowchart
    (the same rule engine behind the structured triage endpoint), so any
    medical chat reply carries a triage-agent verdict."""
    t = text.lower()

    flags = {key: any(kw in t for kw in kws) for key, kws in _RED_FLAG_KW.items()}
    symptoms = {sid for sid, kws in _SYMPTOM_KW.items() if any(kw in t for kw in kws)}

    pain = 0
    if "severe pain" in t or "worst pain" in t:
        pain = 9
    elif "moderate pain" in t or "bad pain" in t:
        pain = 6
    elif "mild pain" in t:
        pain = 3
    elif "pain" in t or "hurts" in t:
        pain = 4

    duration_hours = 72 if any(w in t for w in ("for days", "for a week", "for weeks", "for 3 days")) else 0

    result = rule_based_triage(
        {
            "age_years": 30,
            "pain_score": pain,
            "symptom_duration_hours": duration_hours,
            "vitals": {},
            "red_flags": flags,
            "symptoms": sorted(symptoms),
        }
    )
    return {
        "severity": result["severity"],
        "label": result["label"],
        "is_emergency": result["is_emergency"],
        "recommended_action": result["recommended_action"],
        "reasons": result["reasons"],
    }
