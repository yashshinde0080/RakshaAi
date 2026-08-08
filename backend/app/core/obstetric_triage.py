"""Raksha AI — Obstetric (LaQshya) triage. Pure functions, no I/O, no engine imports.

Faithful encoding of the MoHFW LaQshya SOP 2018 (Labour Room Quality
Improvement Initiative). This is a BINARY TRIGGER system, NOT a weighted or
point-scored scale: any single trigger in a tier escalates to that tier, and
the highest triggered tier wins.

Output is escalation_level:
    0 = routine            — continue routine intrapartum care
    1 = MO review          — Medical Officer called
    2 = obstetrician       — Obstetrician called
    3 = refer FRU          — immediate referral to FRU / higher centre

Referral chain (never skip a rung): Staff Nurse -> Medical Officer ->
Obstetrician -> FRU / higher centre.

Source fidelity notes (decisions, see OBSTETRIC_TRIAGE.md):
- Any trigger wins ("OR"), highest tier wins. No point weighting exists in the
  actual SOP — the "score" idea was a prior misinterpretation.
- Shock is the EXACT definition: fast+feeble pulse AND systolic BP <90 mmHg
  AND cold/moist skin — all three, not any one.
- Temp >= 38C is BOTH a danger sign (tier 3) and an antibiotic trigger
  (tier 1); the danger sign tier wins by the highest-wins rule.
- Partograph: alert line crossed -> MO; action line crossed -> obstetrician;
  no progress in 8h -> refer.
"""
from __future__ import annotations

from typing import Any

# ── Obstetric input validator (front gate) ───────────────────────────────────
# Possible-value bounds for the LaQshya fields. Rejects impossible data-entry
# values BEFORE any decision is made, mirroring validate_vitals() in triage.py.
OB_BOUNDS: dict[str, tuple[float, float, str]] = {
    "gestation_weeks": (0, 45, "Gestation"),
    "temp_c": (30.0, 45.0, "Temperature"),
    "systolic_bp": (40, 300, "Systolic BP"),
    "diastolic_bp": (20, 200, "Diastolic BP"),
    "fhr_bpm": (40, 240, "Fetal heart rate"),
    "rr_per_min": (4, 120, "Newborn respiratory rate"),
    "blood_loss_ml": (0, 5000, "Blood loss"),
    "pad_soaked_minutes": (0, 600, "Pad soak time"),
    "retained_placenta_hours": (0, 72, "Retained placenta duration"),
    "rom_hours": (0, 200, "Rupture of membranes duration"),
    "labour_hours": (0, 100, "Labour duration"),
    "oliguria_ml_24h": (0, 10000, "Urine output"),
    "cervix_dilation_cm": (0, 10, "Cervical dilation"),
    "no_progress_hours": (0, 72, "No-progress duration"),
}

PROTEINURIA_LEVELS = ("0", "trace", "1", "2", "3", "4")


def validate_obstetric_input(inp: dict) -> list[str]:
    """Return a list of impossible-value errors; empty list means 'pass'."""
    errors: list[str] = []

    def _check(holder: dict, key: str, label: str) -> None:
        value = holder.get(key)
        if value is None:
            return
        lo, hi, _ = OB_BOUNDS[key]
        if not isinstance(value, (int, float)):
            errors.append(f"{label} must be a number")
        elif not (lo <= value <= hi):
            errors.append(f"{label} {value} is outside the possible range {lo}-{hi}")

    mother = inp.get("mother") or {}
    for key in ("temp_c", "systolic_bp", "diastolic_bp"):
        _check(mother, key, OB_BOUNDS[key][2])
    labour = inp.get("labour") or {}
    for key in ("rom_hours", "labour_hours"):
        _check(labour, key, OB_BOUNDS[key][2])
    pph = inp.get("pph") or {}
    for key in ("blood_loss_ml", "pad_soaked_minutes", "retained_placenta_hours"):
        _check(pph, key, OB_BOUNDS[key][2])
    pre = inp.get("preeclampsia") or {}
    _check(pre, "oliguria_ml_24h", OB_BOUNDS["oliguria_ml_24h"][2])
    if pre.get("proteinuria") is not None and pre.get("proteinuria") not in PROTEINURIA_LEVELS:
        errors.append(f"proteinuria must be one of {PROTEINURIA_LEVELS}")
    fetal = inp.get("fetal") or {}
    _check(fetal, "fhr_bpm", OB_BOUNDS["fhr_bpm"][2])
    baby = inp.get("baby") or {}
    for key in ("rr_per_min", "temp_c"):
        _check(baby, key, OB_BOUNDS[key][2])
    pg = inp.get("partograph") or {}
    for key in ("cervix_dilation_cm", "no_progress_hours"):
        _check(pg, key, OB_BOUNDS[key][2])
    gestation = inp.get("gestation_weeks")
    if gestation is not None and not (0 <= gestation <= 45):
        errors.append(f"Gestation {gestation} is outside the possible range 0-45")
    return errors


# ── Escalation levels (0-3) ──────────────────────────────────────────────────
ESCALATION_LABELS = {
    0: "Routine",
    1: "Medical Officer review",
    2: "Obstetrician required",
    3: "Refer to FRU / higher centre",
}

NEXT_STEPS = {
    0: "Continue routine intrapartum care per partograph.",
    1: "Call the Medical Officer now.",
    2: "Call the Obstetrician now.",
    3: "Immediate referral to FRU / higher centre. Do not delay.",
}


def _result(level: int, reasons: list[str]) -> dict:
    return {
        "escalation_level": level,
        "label": ESCALATION_LABELS[level],
        "next_step": NEXT_STEPS[level],
        "is_urgent": level >= 2,
        "reasons": reasons,
    }


# ── Tier 3: danger signs -> immediate referral ───────────────────────────────
DANGER_SIGNS: list[tuple[str, str]] = [
    ("vaginal_bleeding", "Vaginal bleeding"),
    ("severe_abdominal_pain", "Severe abdominal pain"),
    ("severe_headache_or_blurred_vision", "Severe headache or blurred vision"),
    ("difficulty_breathing", "Difficulty breathing"),
    ("convulsions", "Convulsions"),
    ("hx_heart_disease_major_illness", "History of heart disease / major illness"),
]


def _tier3_reasons(inp: dict) -> list[str]:
    """ANY danger sign, shock, PPH >=500ml or pad <5min, severe pre-eclampsia,
    fetal distress, newborn danger sign, or 8h no progress -> refer FRU."""
    reasons: list[str] = []
    signs = inp.get("danger_signs") or {}
    for key, label in DANGER_SIGNS:
        if signs.get(key):
            reasons.append(f"Danger sign: {label}")

    mother = inp.get("mother") or {}
    # High fever (>=38C) is both a danger sign and an antibiotic trigger.
    if (mother.get("temp_c") or 0) >= 38:
        reasons.append("Danger sign: high fever (temp >= 38C)")

    # Shock is the EXACT LaQshya definition — all three, not any one.
    sbp = mother.get("systolic_bp")
    if (
        mother.get("fast_feeble_pulse")
        and sbp is not None and sbp < 90
        and mother.get("cold_moist_skin")
    ):
        reasons.append("Shock: fast+feeble pulse, systolic BP <90, cold/moist skin")

    pph = inp.get("pph") or {}
    if (pph.get("blood_loss_ml") or 0) >= 500:
        reasons.append("PPH: blood loss >= 500ml — immediate PPH protocol")
    pad = pph.get("pad_soaked_minutes")
    if pad is not None and pad < 5:
        reasons.append("PPH: one pad soaked in <5 minutes — immediate PPH protocol")

    pre = inp.get("preeclampsia") or {}
    prot = pre.get("proteinuria")
    if prot is not None:
        sbp, dbp = mother.get("systolic_bp"), mother.get("diastolic_bp")
        severe = prot in ("3", "4") and ((sbp or 0) >= 160 or (dbp or 0) >= 110)
        mild = prot in ("trace", "1", "2") and ((sbp or 0) >= 140 or (dbp or 0) >= 90)
        symptoms = (
            signs.get("severe_headache_or_blurred_vision")
            or signs.get("difficulty_breathing")
            or signs.get("convulsions")
            or pre.get("epigastric_pain")
            or (pre.get("oliguria_ml_24h") is not None and pre.get("oliguria_ml_24h") < 400)
        )
        if severe or (mild and symptoms):
            reasons.append(
                f"Severe pre-eclampsia/MgSO4 criteria: BP {sbp}/{dbp}, proteinuria {prot}"
            )

    fetal = inp.get("fetal") or {}
    fhr = fetal.get("fhr_bpm")
    if fhr is not None and (fhr < 120 or fhr > 160):
        reasons.append(f"Fetal distress: FHR {fhr} (<120 or >160)")
    if fetal.get("meconium_stained_liquor"):
        reasons.append("Fetal distress: meconium-stained liquor")

    baby = inp.get("baby") or {}
    rr = baby.get("rr_per_min")
    if rr is not None and (rr > 60 or rr < 30):
        reasons.append("Newborn danger: respiratory rate >60 or <30/min")
    for key, label in (
        ("chest_indrawing", "Newborn danger: chest indrawing"),
        ("grunting", "Newborn danger: grunting"),
        ("convulsions", "Newborn danger: convulsions"),
        ("lethargic_or_irritable", "Newborn danger: lethargic or irritable"),
        ("excessive_crying", "Newborn danger: excessive crying"),
    ):
        if baby.get(key):
            reasons.append(label)
    btemp = baby.get("temp_c")
    if btemp is not None and (btemp < 36 or btemp > 38):
        reasons.append(f"Newborn danger: temp {btemp}C (<36 or >38, not rising after warming)")

    pg = inp.get("partograph") or {}
    if (pg.get("no_progress_hours") or 0) >= 8:
        reasons.append("Partograph: no progress in 8 hours — refer")
    return reasons


# ── Tier 2: obstetrician required ────────────────────────────────────────────
def _tier2_reasons(inp: dict) -> list[str]:
    """Retained placenta >1h, blood loss >350ml with continued bleeding, or
    partograph action line crossed -> obstetrician called."""
    reasons: list[str] = []
    pph = inp.get("pph") or {}
    if (pph.get("retained_placenta_hours") or 0) > 1:
        reasons.append("Retained placenta >1 hour")
    if (pph.get("blood_loss_ml") or 0) > 350 and pph.get("continued_bleeding"):
        reasons.append("Blood loss >350ml with continued bleeding")
    pg = inp.get("partograph") or {}
    if pg.get("action_line_crossed"):
        reasons.append("Partograph: action line crossed")
    return reasons


# ── Tier 1: MO review (mother antibiotic trigger) ────────────────────────────
def _tier1_reasons(inp: dict) -> list[str]:
    """ANY mother antibiotic trigger -> Medical Officer review.

    Note: temp >= 38C is NOT listed here on purpose — it is a danger sign and
    always escalates to tier 3 first (highest-wins), so this branch would be
    dead code. The schema field documents the trigger."""
    reasons: list[str] = []
    mother = inp.get("mother") or {}
    if mother.get("foul_smelling_discharge"):
        reasons.append("Antibiotic trigger: foul-smelling vaginal discharge")

    labour = inp.get("labour") or {}
    rom = labour.get("rom_hours")
    with_labour = labour.get("rom_with_labour")
    if rom is not None and ((rom > 18 and with_labour) or (rom > 12 and not with_labour)):
        reasons.append(f"Antibiotic trigger: ROM >{'18h with' if with_labour else '12h without'} labour")
    if (labour.get("labour_hours") or 0) > 24 or labour.get("obstructed_labour"):
        reasons.append("Antibiotic trigger: labour >24h / obstructed labour")
    if labour.get("rom_before_37wks"):
        reasons.append("Antibiotic trigger: ROM <37 weeks gestation")

    pg = inp.get("partograph") or {}
    if pg.get("alert_line_crossed"):
        reasons.append("Partograph: alert line crossed")
    return reasons


# ── Entry point ──────────────────────────────────────────────────────────────
def rule_based_obstetric_triage(inp: dict) -> dict:
    """Deterministic LaQshya escalation. Strict priority: the highest triggered
    tier wins (ties to the more severe level, never downgrades). Pure — safe to
    unit test. Mirrors rule_based_triage() in triage.py."""
    reasons = _tier3_reasons(inp)
    if reasons:
        return _result(3, reasons)
    reasons = _tier2_reasons(inp)
    if reasons:
        return _result(2, reasons)
    reasons = _tier1_reasons(inp)
    if reasons:
        return _result(1, reasons)
    return _result(0, ["No LaQshya triggers — routine intrapartum care"])


# ── Output schema for the LLM/lower-tier validation (back gate) ──────────────
# If this ever gets a model in the loop, validate the model JSON against this
# same contract (mirror validate_triage_output in triage.py). Deterministic
# binary triggers need no LLM today — kept as the documented contract.
OBSTETRIC_SCHEMA_HINT = (
    '{"escalation_level": <int 0-3>, "reasons": [<str>...], "next_step": "<str>"}'
)
