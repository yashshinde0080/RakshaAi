"""Tests for the Raksha AI triage safety core: front gate, rule flowchart,
and back gate. Every severity branch of rule_based_triage is covered.

Run: cd backend && uv run pytest tests/test_triage.py -q
"""
import pytest

from app.core.triage import (
    build_triage_prompt,
    extract_json,
    is_medical_query,
    rule_based_triage,
    triage_hint_from_text,
    validate_triage_output,
    validate_vitals,
)


def base_input(**over):
    inp = {
        "age_years": 30,
        "pain_score": 0,
        "symptom_duration_hours": 2,
        "vitals": {},
        "red_flags": {},
        "symptoms": [],
    }
    inp.update(over)
    return inp


# ── Front gate: impossible vitals are rejected ──────────────────────────────
@pytest.mark.parametrize(
    "vitals,key",
    [
        ({"heart_rate": 300}, "Heart rate"),
        ({"heart_rate": 5}, "Heart rate"),
        ({"systolic_bp": 400}, "Systolic BP"),
        ({"spo2": 105}, "SpO2"),
        ({"spo2": 10}, "SpO2"),
        ({"temperature_c": 50}, "Temperature"),
        ({"temperature_c": 20}, "Temperature"),
        ({"respiratory_rate": 100}, "Respiratory rate"),
    ],
)
def test_validate_vitals_rejects_impossible(vitals, key):
    errors = validate_vitals(base_input(vitals=vitals))
    assert any(key in e for e in errors), errors


def test_validate_vitals_rejects_bad_age_pain_duration():
    assert validate_vitals(base_input(age_years=150))
    assert validate_vitals(base_input(pain_score=11))
    assert validate_vitals(base_input(symptom_duration_hours=-3))


def test_validate_gender():
    # Carried demographic: valid values pass, junk rejects, missing is fine.
    assert validate_vitals(base_input(vitals={"gender": "male"})) == []
    assert validate_vitals(base_input(vitals={"gender": "female"})) == []
    assert validate_vitals(base_input(vitals={"gender": "other"})) == []
    assert "Gender" in validate_vitals(base_input(vitals={"gender": "attack helicopter"}))[0]
    assert validate_vitals(base_input()) == []


def test_validate_vitals_passes_normal_values():
    inp = base_input(
        age_years=45,
        pain_score=4,
        symptom_duration_hours=24,
        vitals={"heart_rate": 80, "systolic_bp": 120, "spo2": 98, "temperature_c": 37.0, "respiratory_rate": 16},
    )
    assert validate_vitals(inp) == []


# ── Rule flowchart: ESI levels per PRD §7 ───────────────────────────────────
def test_any_red_flag_is_level_1():
    for flag in (
        "unresponsive", "not_breathing", "stroke_signs", "chest_pain_severe",
        "uncontrolled_bleeding", "anaphylaxis_signs", "seizure_active",
    ):
        result = rule_based_triage(base_input(red_flags={flag: True}))
        assert result["severity"] == 1 and result["is_emergency"], flag


@pytest.mark.parametrize(
    "vitals",
    [
        {"spo2": 85},
        {"systolic_bp": 70},
        {"systolic_bp": 220},
        {"heart_rate": 30},
        {"heart_rate": 180},
        {"respiratory_rate": 5},
        {"respiratory_rate": 40},
    ],
)
def test_critical_vitals_are_level_1(vitals):
    assert rule_based_triage(base_input(vitals=vitals))["severity"] == 1


@pytest.mark.parametrize(
    "vitals",
    [
        {"spo2": 92},
        {"systolic_bp": 95},
        {"systolic_bp": 190},
        {"heart_rate": 45},
        {"heart_rate": 130},
        {"respiratory_rate": 9},
        {"respiratory_rate": 28},
        {"temperature_c": 40.0},
        {"temperature_c": 34.0},
    ],
)
def test_borderline_vitals_are_level_2(vitals):
    assert rule_based_triage(base_input(vitals=vitals))["severity"] == 2


def test_high_risk_symptom_is_level_2():
    assert rule_based_triage(base_input(symptoms=["chest_pain"]))["severity"] == 2


def test_pain_9_is_level_2():
    assert rule_based_triage(base_input(pain_score=9))["severity"] == 2


def test_gi_symptoms_are_level_3():
    assert rule_based_triage(base_input(symptoms=["vomiting"]))["severity"] == 3


def test_fracture_is_level_3():
    assert rule_based_triage(base_input(symptoms=["suspected_fracture"]))["severity"] == 3


def test_pain_6_is_level_3():
    assert rule_based_triage(base_input(pain_score=6))["severity"] == 3


def test_duration_48h_is_level_3():
    assert rule_based_triage(base_input(symptom_duration_hours=48))["severity"] == 3


def test_pain_3_is_level_4():
    assert rule_based_triage(base_input(pain_score=3))["severity"] == 4


def test_any_other_symptom_is_level_4():
    assert rule_based_triage(base_input(symptoms=["cough"]))["severity"] == 4


def test_no_triggers_is_level_5():
    result = rule_based_triage(base_input())
    assert result["severity"] == 5 and not result["is_emergency"]
    assert result["recommended_action"]


def test_ties_resolve_to_more_severe():
    # pain 9 (L2) + vomiting (L3): must stay L2, never downgrade to L3+.
    result = rule_based_triage(base_input(pain_score=9, symptoms=["vomiting"]))
    assert result["severity"] == 2


# ── Age-band vitals: children must not be over-triaged to ESI 1/2 ───────────
def test_infant_hr_normal_is_not_over_triaged():
    # HR 160 is a normal infant heart rate; adult rules would call it critical.
    assert rule_based_triage(base_input(age_years=0, vitals={"heart_rate": 160}))["severity"] == 5


def test_infant_hr_bradycardia_is_critical():
    assert rule_based_triage(base_input(age_years=0, vitals={"heart_rate": 60}))["severity"] == 1


def test_child_hr_borderline_is_level_2():
    # 8-year-old, HR 160: borderline for age → ESI 2 (adult rule → ESI 1).
    assert rule_based_triage(base_input(age_years=8, vitals={"heart_rate": 160}))["severity"] == 2


def test_elderly_hr_145_is_critical():
    assert rule_based_triage(base_input(age_years=80, vitals={"heart_rate": 145}))["severity"] == 1


def test_adult_vital_bands_unchanged():
    # Byte-for-byte pre-band behavior: 160 critical, 150/45 borderline, 120 clear.
    assert rule_based_triage(base_input(vitals={"heart_rate": 160}))["severity"] == 1
    assert rule_based_triage(base_input(vitals={"heart_rate": 150}))["severity"] == 2
    assert rule_based_triage(base_input(vitals={"heart_rate": 45}))["severity"] == 2
    assert rule_based_triage(base_input(vitals={"heart_rate": 120}))["severity"] == 5
    assert rule_based_triage(base_input(vitals={"respiratory_rate": 28}))["severity"] == 2
    assert rule_based_triage(base_input(vitals={"respiratory_rate": 10}))["severity"] == 2


# ── Back gate: schema re-check ──────────────────────────────────────────────
def test_valid_output_passes():
    ok, errors = validate_triage_output(
        {"severity": 3, "red_flags": [], "next_action": "Seek care today", "reasons": ["Pain 6"]}
    )
    assert ok and errors == []


@pytest.mark.parametrize(
    "obj",
    [
        {"severity": 0, "red_flags": [], "next_action": "x", "reasons": []},
        {"severity": 6, "red_flags": [], "next_action": "x", "reasons": []},
        {"severity": "3", "red_flags": [], "next_action": "x", "reasons": []},
        {"severity": 3, "red_flags": "urgent", "next_action": "x", "reasons": []},
        {"severity": 3, "red_flags": [], "next_action": "", "reasons": []},
        {"severity": 3, "red_flags": [], "reasons": []},  # missing next_action
        "not an object",
    ],
)
def test_invalid_output_fails(obj):
    ok, errors = validate_triage_output(obj)
    assert not ok and errors


def test_extract_json_tolerates_fences_and_prose():
    assert extract_json('```json\n{"severity": 2}\n```')["severity"] == 2
    assert extract_json('Sure, here is the result: {"severity": 1, "red_flags": [], "next_action": "call", "reasons": []}')["severity"] == 1


def test_extract_json_rejects_garbage():
    with pytest.raises(ValueError):
        extract_json("I cannot do that.")


def test_build_prompt_mentions_schema_and_feedback():
    prompt = build_triage_prompt(base_input())
    assert "severity" in prompt and "next_action" in prompt
    retry = build_triage_prompt(base_input(), feedback=["severity must be an integer 1-5"])
    assert "failed validation" in retry and "severity must be an integer" in retry


# ── Healthcare helper routing (chat medical intent + free-text hint) ────────
def test_is_medical_query():
    assert is_medical_query("I have chest pain and can't breathe")
    assert is_medical_query("My son has a fever of 39")
    assert is_medical_query("should I see a doctor for this headache?")
    assert is_medical_query("the doctor prescribed medication")
    assert not is_medical_query("What is the capital of France?")
    assert not is_medical_query("Explain how transformers work")


def test_is_medical_query_word_boundaries():
    # Substring matches must not fire inside unrelated words (regression guard).
    assert not is_medical_query("I am painting my house")
    assert not is_medical_query("She is scolding the dog")
    assert not is_medical_query("I was scolded yesterday")
    assert not is_medical_query("the cake has a sugary glaze")
    assert not is_medical_query("What is the capital of France?")
    # ...while real mentions still match.
    assert is_medical_query("I have a cold")
    assert is_medical_query("Add sugar to my coffee")
    assert is_medical_query("My head aches")
    assert is_medical_query("my head hurts")
    assert is_medical_query("he is not breathing")


def test_hint_red_flag_is_level_1():
    hint = triage_hint_from_text("my father is unresponsive and not breathing")
    assert hint["severity"] == 1 and hint["is_emergency"]


def test_hint_gi_symptoms_are_level_3():
    hint = triage_hint_from_text("I have been vomiting and have diarrhea for days")
    assert hint["severity"] == 3


def test_llm_triage_timeout_falls_back_to_rules(monkeypatch):
    """A hung model must fall back to rules instead of blocking triage."""
    import asyncio
    from types import SimpleNamespace
    import app.api.triage as triage_api

    class _HangingEngine:
        task_metadata = {"task_type": "causal_lm", "is_generative": True}
        tokenizer = None

        async def generate(self, **kwargs):
            await asyncio.sleep(5)

    monkeypatch.setattr(triage_api, "TRIAGE_LLM_TIMEOUT_SECONDS", 0.05)
    app = SimpleNamespace(state=SimpleNamespace(active_engine=_HangingEngine()))
    result, source, retries, errors = asyncio.run(triage_api._llm_triage(app, base_input()))
    assert result is None
    assert source == "rules"
    assert retries == 1
    assert "llm timed out" in errors


def test_hint_shape_has_guardrail_fields():
    hint = triage_hint_from_text("I have a mild headache")
    assert set(hint) == {"severity", "label", "is_emergency", "recommended_action", "reasons"}
    assert isinstance(hint["reasons"], list)
