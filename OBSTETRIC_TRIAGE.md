# Obstetric Triage — MoHFW LaQshya SOP 2018 (decision record)

**Status:** encoded as a pure rule engine, tested, NOT yet wired to an API
endpoint or UI. Read "Decisions made" before changing anything; read "Open for
the next person" before wiring it up.

The ESI triage (`backend/app/core/triage.py`) is the general adult triage
protocol. This module is a **separate, parallel protocol** for labour-room /
maternal-fetal triage. They are not interchangeable: ESI outputs a 1–5
severity; LaQshya outputs an **escalation_level 0–3** (referral chain).

## What this is (faithful, from the actual doc)

The MoHFW LaQshya SOP 2018 is a **rule-based binary trigger system, NOT a
point-weighted score**. Any single trigger in a tier escalates to that tier;
the highest triggered tier wins. The "point score" idea was a prior
misinterpretation — it does not exist in the document.

Files:

| File | What it is |
|---|---|
| `backend/app/core/obstetric_triage.py` | Pure rule engine — `rule_based_obstetric_triage()`, `validate_obstetric_input()`, escalation labels/next-steps |
| `backend/app/schemas/obstetric_triage.py` | Pydantic JSON contract for request/response |
| `backend/tests/test_obstetric_triage.py` | One parametrized test per binary trigger |
| `OBSTETRIC_TRIAGE.md` | This decision record |

Run tests: `cd backend && uv run pytest tests/test_obstetric_triage.py -q`

## Escalation levels (0–3)

| Level | Meaning | Who is called | Triggered by (any one) |
|---|---|---|---|
| 0 | Routine | — | no triggers |
| 1 | MO review | Medical Officer | mother antibiotic trigger; partograph alert line crossed |
| 2 | Obstetrician | Obstetrician | retained placenta >1h; blood loss >350ml with continued bleeding; partograph action line crossed |
| 3 | Refer FRU | immediate referral | ANY danger sign; shock (all 3 criteria); PPH ≥500ml or pad <5min; severe pre-eclampsia/MgSO4 criteria; fetal distress; newborn danger signs; no progress 8h |

Referral chain (never skips a rung): **Staff Nurse → Medical Officer →
Obstetrician → FRU / higher centre**. `next_step` in the response names the
rung to call.

## The actual triggers (encoded verbatim)

**Danger signs → immediate referral (any ONE):** vaginal bleeding · severe
abdominal pain · high fever (temp ≥38°C) · history of heart disease/major
illness · severe headache or blurred vision · difficulty breathing ·
convulsions.

**Shock (exact definition — all three, not any one):** fast + feeble pulse AND
systolic BP <90 mmHg AND cold/moist skin.

**PPH thresholds:** blood loss ≥500ml OR 1 pad soaked in <5min → immediate PPH
protocol (level 3). Retained placenta >1h OR blood loss >350ml with continued
bleeding → obstetrician called (level 2).

**Antibiotic trigger (mother) — ANY:** temp ≥38°C · foul-smelling vaginal
discharge · ROM >12h without labour OR >18h with labour · labour >24h /
obstructed labour · ROM <37 weeks gestation.

**Severe pre-eclampsia / MgSO4 trigger:** systolic ≥160 OR diastolic ≥110 with
≥3+ proteinuria; OR systolic ≥140 OR diastolic ≥90 with trace–2+ proteinuria
AND any of: severe headache, blurred vision, difficulty breathing, epigastric
pain, oliguria (<400ml/24h), convulsions.

**Fetal distress:** FHR <120 or >160/min, or meconium-stained liquor.

**Newborn danger signs (antibiotic/referral trigger) — ANY:** RR >60 or
<30/min · chest indrawing · grunting · convulsions · lethargic/irritable ·
temp <36°C (not rising after warming) or >38°C · excessive crying.

**Partograph:** start at cervix ≥4cm (context only, not a trigger) · alert line
crossed → MO · action line crossed → obstetrician · no progress 8h → refer.

## Decisions made (with reasons)

1. **Binary triggers, highest tier wins.** This is literally how the SOP
   works. Ties resolve to the more severe level, same policy as `rule_based_triage`.
2. **Shock requires all three criteria.** The doc defines shock as the
   conjunction. Encoding it as "any one" would over-refer.
3. **Temp ≥38°C appears in two places** (danger signs AND antibiotic trigger).
   By the highest-wins rule it lands at level 3 (danger) when present. The
   antibiotic-trigger branch still lists it so the schema documents the full
   trigger set.
4. **Blood loss 350–499ml with continued bleeding = level 2**, not 3. The 500ml
   line is the immediate-protocol/refer threshold; 350ml+ continued bleeding
   escalates to the obstetrician. Loss without continued bleeding is not a trigger.
5. **Mild pre-eclampsia (trace–2+ proteinuria, BP ≥140/90) requires a
   symptom** to reach level 3. BP+proteinuria alone, without symptoms, is not
   severe by the SOP. A missing symptom field therefore under-triggers, not
   over-triggers — safe direction for a binary system.
6. **`is_urgent = level >= 2`.** MO review (1) is action but not the "drop
   everything" threshold; obstetrician/referral are.
7. **All input fields optional in the schema.** The engine treats missing as
   "no trigger". This is the safe direction (never fabricates an escalation);
   facility policy should decide which fields are mandatory at the UI layer.

## Mapping ambiguity the next person MUST confirm with a clinician

The doc never assigns escalation levels explicitly — it names actions. Two
readings exist for PPH ≥500ml and severe pre-eclampsia/MgSO4:

- **Chosen (current): level 3 (refer FRU).** Danger signs say "immediate
  referral", and these are the most life-threatening triggers.
- **Alternative: level 2 (obstetrician + protocol).** "Immediate PPH protocol"
  and "MgSO4 administration" are in-facility actions; the referral chain only
  says "refer FRU if beyond facility capacity".

Either is defensible. The chosen mapping is coded and tested; before facility
deployment, a clinician should sign which one this module follows (see
Clinical Review Log convention in PRD §10).
8. **No LLM in this path.** LaQshya is fully deterministic — every trigger is a
   boolean/number. Putting a model in the loop adds failure modes to a protocol
   whose whole point is binary certainty. `OBSTETRIC_SCHEMA_HINT` is kept as
   the documented contract in case that changes.

## Open for the next person (decisions to make)

- **Wire an endpoint?** Add `POST /v1/obstetric/triage` mirroring
  `backend/app/api/triage.py` (front gate → rules → audit_log). The engine is
  ready; the endpoint is ~40 lines.
- **Mandatory fields at the UI?** Which readings can a labour room actually
  capture? Decide the required set per facility (e.g. BP + temp + FHR + blood
  loss are cheap; oliguria needs a 24h collection).
- **Route in chat?** The medical chat detector (`is_medical_query` in
  `core/triage.py`) currently routes to ESI. Decide whether
  pregnancy/labour-keyword messages should route to obstetric triage instead,
  or run both and take the higher urgency.
- **Newborn vs mother split?** Currently one payload. A real labour room
  assesses mother and newborn separately — decide if the API should accept
  them as two calls.
- **Clinical sign-off.** Thresholds are encoded from the SOP; before any
  facility deploys this, a clinician should sign the Clinical Review Log for
  this module (same convention as ESI thresholds in PRD §7/§10).
