"""Tests for the LaQshya obstetric triage engine (app/core/obstetric_triage.py).

Covers every binary trigger tier from the MoHFW LaQshya SOP 2018: any trigger
wins, highest tier wins, ties to the more severe level.

Run: cd backend && uv run pytest tests/test_obstetric_triage.py -q
"""
import pytest

from app.core.obstetric_triage import (
    ESCALATION_LABELS,
    rule_based_obstetric_triage,
    validate_obstetric_input,
)


def base_input(**over):
    inp = {
        "gestation_weeks": 38,
        "mother": {},
        "labour": {},
        "danger_signs": {},
        "preeclampsia": {},
        "pph": {},
        "fetal": {},
        "baby": {},
        "partograph": {},
    }
    for holder in ("mother", "labour", "danger_signs", "preeclampsia",
                   "pph", "fetal", "baby", "partograph"):
        if holder in over:
            base = inp[holder] or {}
            base.update(over.pop(holder))
            inp[holder] = base
    inp.update(over)
    return inp


# ── Tier 3: danger signs, shock, PPH, severe pre-eclampsia, fetal/newborn ───
@pytest.mark.parametrize(
    "sign",
    [
        {"vaginal_bleeding": True},
        {"severe_abdominal_pain": True},
        {"severe_headache_or_blurred_vision": True},
        {"difficulty_breathing": True},
        {"convulsions": True},
        {"hx_heart_disease_major_illness": True},
    ],
)
def test_any_danger_sign_refer(sign):
    r = rule_based_obstetric_triage(base_input(danger_signs=sign))
    assert r["escalation_level"] == 3, r["reasons"]


def test_high_fever_is_danger_sign():
    r = rule_based_obstetric_triage(base_input(mother={"temp_c": 38.5}))
    assert r["escalation_level"] == 3


def test_shock_requires_all_three_criteria():
    # All three -> refer. Missing any one -> NOT shock.
    full = rule_based_obstetric_triage(base_input(mother={
        "fast_feeble_pulse": True, "systolic_bp": 85, "cold_moist_skin": True}))
    assert full["escalation_level"] == 3
    partial = rule_based_obstetric_triage(base_input(mother={
        "fast_feeble_pulse": True, "cold_moist_skin": True}))  # no BP
    assert partial["escalation_level"] == 0


@pytest.mark.parametrize(
    "pph",
    [
        {"blood_loss_ml": 500},
        {"blood_loss_ml": 750},
        {"pad_soaked_minutes": 4},
    ],
)
def test_immediate_pph_protocol_refer(pph):
    r = rule_based_obstetric_triage(base_input(pph=pph))
    assert r["escalation_level"] == 3, r["reasons"]


def test_retained_placenta_is_obstetrician_not_refer():
    r = rule_based_obstetric_triage(base_input(pph={"retained_placenta_hours": 2}))
    assert r["escalation_level"] == 2


def test_blood_loss_350_with_continued_bleeding_is_obstetrician():
    r = rule_based_obstetric_triage(base_input(pph={"blood_loss_ml": 400, "continued_bleeding": True}))
    assert r["escalation_level"] == 2
    # Same loss without continued bleeding -> no trigger.
    r2 = rule_based_obstetric_triage(base_input(pph={"blood_loss_ml": 400}))
    assert r2["escalation_level"] == 0


@pytest.mark.parametrize(
    "pre,mother",
    [
        # severe: >=160/110 with 3+ proteinuria
        ({"proteinuria": "3"}, {"systolic_bp": 160, "diastolic_bp": 100}),
        ({"proteinuria": "4"}, {"systolic_bp": 150, "diastolic_bp": 110}),
        # mild: >=140/90 with trace-2+ AND a symptom
        ({"proteinuria": "1", "epigastric_pain": True}, {"systolic_bp": 145, "diastolic_bp": 95}),
        ({"proteinuria": "trace", "oliguria_ml_24h": 300}, {"systolic_bp": 140, "diastolic_bp": 90}),
    ],
)
def test_severe_preeclampsia_refer(pre, mother):
    inp = base_input(preeclampsia=pre, mother=mother)
    r = rule_based_obstetric_triage(inp)
    assert r["escalation_level"] == 3, r["reasons"]


def test_convulsions_as_preeclampsia_symptom_refer():
    # convulsions live in danger_signs; as a pre-eclampsia symptom they still
    # reach the severe threshold with mild BP + proteinuria.
    inp = base_input(
        preeclampsia={"proteinuria": "1"},
        mother={"systolic_bp": 142, "diastolic_bp": 92},
        danger_signs={"convulsions": True},
    )
    r = rule_based_obstetric_triage(inp)
    assert r["escalation_level"] == 3, r["reasons"]


def test_mild_preeclampsia_without_symptoms_not_refer():
    r = rule_based_obstetric_triage(base_input(
        preeclampsia={"proteinuria": "1"},
        mother={"systolic_bp": 145, "diastolic_bp": 95},
    ))
    assert r["escalation_level"] == 0  # no symptom -> not severe


@pytest.mark.parametrize(
    "fetal",
    [
        {"fhr_bpm": 110},
        {"fhr_bpm": 170},
        {"meconium_stained_liquor": True},
    ],
)
def test_fetal_distress_refer(fetal):
    r = rule_based_obstetric_triage(base_input(fetal=fetal))
    assert r["escalation_level"] == 3


@pytest.mark.parametrize(
    "baby",
    [
        {"rr_per_min": 65},
        {"rr_per_min": 25},
        {"chest_indrawing": True},
        {"grunting": True},
        {"convulsions": True},
        {"lethargic_or_irritable": True},
        {"temp_c": 35.5},
        {"temp_c": 38.5},
        {"excessive_crying": True},
    ],
)
def test_newborn_danger_signs_refer(baby):
    r = rule_based_obstetric_triage(base_input(baby=baby))
    assert r["escalation_level"] == 3, r["reasons"]


# ── Tier 1/2: partograph ─────────────────────────────────────────────────────
def test_partograph_alert_line_is_mo():
    r = rule_based_obstetric_triage(base_input(partograph={"alert_line_crossed": True}))
    assert r["escalation_level"] == 1


def test_partograph_action_line_is_obstetrician():
    r = rule_based_obstetric_triage(base_input(partograph={"action_line_crossed": True}))
    assert r["escalation_level"] == 2


def test_partograph_no_progress_8h_refer():
    r = rule_based_obstetric_triage(base_input(partograph={"no_progress_hours": 8}))
    assert r["escalation_level"] == 3
    r2 = rule_based_obstetric_triage(base_input(partograph={"no_progress_hours": 7}))
    assert r2["escalation_level"] == 0


# ── Tier 1: mother antibiotic triggers ───────────────────────────────────────
@pytest.mark.parametrize(
    "labour",
    [
        {"rom_hours": 13},                            # >12h without labour
        {"rom_hours": 19, "rom_with_labour": True},   # >18h with labour
        {"labour_hours": 25},
        {"obstructed_labour": True},
        {"rom_before_37wks": True},
    ],
)
def test_antibiotic_triggers_are_mo_review(labour):
    r = rule_based_obstetric_triage(base_input(labour=labour))
    assert r["escalation_level"] == 1, r["reasons"]


def test_foul_smelling_discharge_is_mo_review():
    r = rule_based_obstetric_triage(base_input(mother={"foul_smelling_discharge": True}))
    assert r["escalation_level"] == 1


def test_rom_12h_without_labour_not_trigger():
    r = rule_based_obstetric_triage(base_input(labour={"rom_hours": 12}))
    assert r["escalation_level"] == 0


def test_rom_boundaries_are_strict():
    # >18 with labour is the trigger; exactly 18 with labour is not.
    assert rule_based_obstetric_triage(
        base_input(labour={"rom_hours": 18, "rom_with_labour": True}))["escalation_level"] == 0
    # >12 without labour is the trigger; exactly 18 without labour IS a trigger.
    assert rule_based_obstetric_triage(
        base_input(labour={"rom_hours": 18}))["escalation_level"] == 1


def test_pph_boundaries_are_strict():
    # pad soaked exactly 5 min is NOT PPH (<5 only).
    assert rule_based_obstetric_triage(
        base_input(pph={"pad_soaked_minutes": 5}))["escalation_level"] == 0
    # blood loss exactly 350ml with continued bleeding is NOT the obstetrician
    # trigger (>350 only); >=500 is still the immediate-protocol refer.
    assert rule_based_obstetric_triage(
        base_input(pph={"blood_loss_ml": 350, "continued_bleeding": True}))["escalation_level"] == 0
    assert rule_based_obstetric_triage(
        base_input(pph={"blood_loss_ml": 500, "continued_bleeding": True}))["escalation_level"] == 3


def test_shock_bp_90_is_not_shock():
    # Shock needs systolic BP <90 (strict); exactly 90 is not shock.
    r = rule_based_obstetric_triage(base_input(mother={
        "fast_feeble_pulse": True, "systolic_bp": 90, "cold_moist_skin": True}))
    assert r["escalation_level"] == 0


def test_fhr_boundaries_are_strict():
    # Fetal distress is <120 or >160 (strict); exactly 120 and 160 are not.
    assert rule_based_obstetric_triage(base_input(fetal={"fhr_bpm": 120}))["escalation_level"] == 0
    assert rule_based_obstetric_triage(base_input(fetal={"fhr_bpm": 160}))["escalation_level"] == 0
    assert rule_based_obstetric_triage(base_input(fetal={"fhr_bpm": 119}))["escalation_level"] == 3
    assert rule_based_obstetric_triage(base_input(fetal={"fhr_bpm": 161}))["escalation_level"] == 3


# ── Tier resolution: highest wins ────────────────────────────────────────────
def test_highest_tier_wins():
    # MO trigger + obstetrician trigger + danger sign -> refer (3), never lower.
    r = rule_based_obstetric_triage(base_input(
        labour={"labour_hours": 25},
        pph={"retained_placenta_hours": 2},
        danger_signs={"vaginal_bleeding": True},
    ))
    assert r["escalation_level"] == 3
    # obstetrician beat MO
    r2 = rule_based_obstetric_triage(base_input(
        labour={"labour_hours": 25}, pph={"retained_placenta_hours": 2}))
    assert r2["escalation_level"] == 2


def test_routine_when_no_triggers():
    r = rule_based_obstetric_triage(base_input())
    assert r["escalation_level"] == 0 and not r["is_urgent"]
    assert r["label"] == ESCALATION_LABELS[0] and r["next_step"]


# ── Front gate ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "over",
    [
        {"gestation_weeks": 50},
        {"mother": {"temp_c": 50}},
        {"mother": {"systolic_bp": 400}},
        {"preeclampsia": {"proteinuria": "5"}},
        {"fetal": {"fhr_bpm": 300}},
        {"baby": {"rr_per_min": 200}},
        {"pph": {"blood_loss_ml": -10}},
        {"labour": {"labour_hours": -1}},
    ],
)
def test_validator_rejects_impossible(over):
    assert validate_obstetric_input(base_input(**over))


def test_validator_passes_normal():
    inp = base_input(
        gestation_weeks=38,
        mother={"temp_c": 37.0, "systolic_bp": 120, "diastolic_bp": 80},
        fetal={"fhr_bpm": 145},
        baby={"rr_per_min": 45, "temp_c": 37.0},
        partograph={"cervix_dilation_cm": 5},
        preeclampsia={"proteinuria": "0"},
    )
    assert validate_obstetric_input(inp) == []
