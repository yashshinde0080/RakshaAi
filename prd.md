# Product Requirements Document (PRD) — HealthAI Triage

---
## 1. Overview
**HealthAI Triage** is an **offline-first symptom triage mobile app** that helps a user (or a caregiver) assess the *urgency* of a medical situation before deciding whether to call emergency services, seek urgent care, or wait. The core of the product is a **deterministic, rule-based triage engine** that runs entirely on the device: no internet, no accounts, no cloud, no model inference.

The product deliberately separates **decision** (the auditable rule engine) from any future **explanation** layer. See §3.2 for why triage decisions are rule-based rather than LLM-based.

## 2. Problem
- People and caregivers are often unsure **how urgent** a symptom is: "Do I call emergency now, or can I wait until morning?"
- Online symptom checkers require internet and typically send personal health data to third parties.
- Triage advice must be **consistent, auditable, and safe** — a black-box model guess is not acceptable for a safety-relevant decision.
- In an emergency, time and connectivity are scarce: a triage answer must be instant and available with zero network.

## 3. Goals & Design Principles

### 3.1 Product goals
1. Give a clear **severity level (1–5)** plus a recommended action within seconds, fully offline.
2. Unambiguously flag **emergencies (Level 1–2)** and offer a one-tap call to a region-configurable emergency number.
3. Explain *why* a level was chosen — every triggered reason maps to a concrete condition checked in code.
4. Work on low-end devices with no network, and stay usable by a stressed user (large touch targets, high contrast, minimal typing).
5. Respect privacy: no health data ever leaves the device.

### 3.2 Why rule-based over LLM (decision rationale)
The triage **decision** is made by hand-written rules, and this is a deliberate, non-negotiable product decision:

- **Auditability & determinism.** Same input → same output, every time, on every device. Each severity level is the product of explicit, reviewable conditions; a clinician or regulator can read the exact rule that produced a result. An LLM cannot offer this property.
- **Safety.** Rule engines cannot hallucinate a symptom relationship, cannot silently downgrade an emergency, and never "invent" a reason. Every triggered reason maps 1:1 to a coded condition. LLM outputs are non-deterministic and unverifiable in the safety-critical path.
- **Testability.** Because `calculateTriage()` is a pure function with a closed set of branches, every branch can be unit-tested (TRD §9) before release — a guarantee that cannot be made for probabilistic inference.
- **Performance & resources.** A rule pass runs in constant time (< 1 ms) on low-end hardware with no battery or memory cost from model inference — important in emergencies and offline settings.
- **Privacy & regulatory posture.** No inference means no model telemetry and no data-processing pipeline to audit; the liability story for a decision-support aid is far stronger with explicit, reviewable rules.

An LLM layer is *not* banned forever — it may return later strictly as an **explanation add-on** (a plain-language "why" and follow-up guidance), and it must **never** override or influence the rule engine's level. It remains explicitly out of scope for the MVP (§11).

## 4. Target Users
Primary:
- **Individuals & family caregivers** doing a quick self-check when someone feels unwell — "is this fever a wait-and-see or a 3 a.m. ER visit?"
- **Non-clinical staff in low-connectivity settings** — clinic front desks, field camps, remote/rural stations, disaster response, where reliable internet does not exist.
- **Stressed or time-pressured users** — parents of young children, travellers who don't know the local emergency number, anyone who needs a structured answer fast.

Non-goals: HealthAI Triage is **not** a diagnostic tool and is not aimed at clinicians making treatment decisions. It is a decision-support aid backed by a persistent non-diagnostic disclaimer.

## 5. Key Features (MVP)
| Feature | Detail | Rationale |
|---|---|---|
| Symptom intake form | Red flags first (unresponsive, not breathing/gasping, stroke signs, severe chest pain, uncontrolled bleeding, anaphylaxis signs, active seizure), then vitals (HR, BP, SpO2, temp, RR), pain 0–10, duration, symptom chips | Structured input feeds the deterministic engine; red flags are asked first because any red flag short-circuits to Level 1 |
| Rule-based triage | `calculateTriage()` pure function → Level 1–5, constant-time, offline | The safety-critical core (see §3.2) |
| Result screen | Color-coded severity badge, recommended action, triggered reasons | "Explain why" is a core goal — builds trust and auditability |
| Emergency call | Level 1–2 only → one-tap call to region-configurable `EMERGENCY_NUMBER` | One decisive action when it matters most; hidden for non-emergencies to avoid false alarms |
| Persistent disclaimer | "Not a medical diagnosis" banner on every screen | Legal/compliance baseline + sets user expectations |
| On-device history | Past assessments stored locally (AsyncStorage), viewable list with details, delete / clear all | Offline-first continuity without accounts; reinforces the privacy promise |

## 6. How It Works
1. User opens the app and sees the intake form beneath the persistent disclaimer.
2. Completing red flags / vitals / pain / duration / symptoms runs `calculateTriage(input)` on-device, synchronously.
3. The result screen shows the severity badge, recommended action, and triggered reasons.
4. Level 1–2 → "Call Emergency Services" button (region-configurable number) with guidance to seek care now.
5. Level 3–5 → care-timeline guidance (urgent today / soon / self-care and monitor).
6. Every completed assessment is saved to on-device history; the user can view, delete, or clear all — no account, no cloud.

**Safety rule:** severity is always decided by the rule engine, never by a model; ties resolve to the more severe level; the engine never silently downgrades; missing vitals skip their check rather than erroring.

## 7. Severity Levels
| Level | Meaning | Example trigger |
|---|---|---|
| 1 | Immediate, life-threatening — act now | Any red flag; critical vitals (SpO2 < 90, systolic BP < 90 or > 200, HR < 40 or > 150, RR < 8 or > 30) |
| 2 | Emergency — seek care immediately | Borderline vitals, high-risk symptom (e.g. high fever ≥ 39.5 °C), pain ≥ 9 |
| 3 | Urgent — seek care today | GI/dehydration symptoms, suspected fracture, pain ≥ 6, duration ≥ 48 h |
| 4 | Less urgent — seek care soon | Pain ≥ 3, or any other symptom selected |
| 5 | Non-urgent — self-care / monitor | No significant triggers |

## 8. Non-Functional Requirements
- **Offline-first:** zero network calls in the core flow; the app is fully functional in airplane mode.
- **Deterministic & auditable:** same input → same result on every device; every reason maps to a coded condition.
- **Performance:** triage in < 1 ms; no async operations in the critical path.
- **Safety:** never silently downgrade severity; ties resolve to the more severe level.
- **Privacy:** no user health data leaves the device (no accounts, no telemetry).
- **Accessibility:** touch targets ≥ 40×40 px (44 recommended), readable contrast, screen-reader labels — users may be stressed or in pain.
- **Localization-ready:** every user-facing string lives in one typed catalog (`healthai-triage/src/i18n/en.ts`, ~120 strings) and renders through `t()` — including engine labels and `triggeredReasons`. `t()` params are type-checked per key: `ParamsOf` derives the required placeholders from each template, so a missing or undeclared param fails `tsc --noEmit`, and a translation module typed as `StringCatalog` gets compile-time key parity. Units, placeholders, and the list separator are catalog entries; the emergency number stays region-configurable in `config.ts`, not hardcoded.

## 9. Success Metrics
- 100% of `calculateTriage` branches unit-tested before release (55 tests in `healthai-triage/tests/triageEngine.test.ts`).
- Sub-second result on a low-end device, fully offline.
- Zero cases where an emergency condition (red flag / critical vital) is downgraded.
- Emergency-call button present for 100% of Level 1–2 results and absent for 100% of Level 4–5 results.

## 10. Clinical Review Log
Every severity-determining threshold in the safety-critical engine (`healthai-triage/src/logic/triageEngine.ts`) requires sign-off by a licensed clinician (or clinical review board) for the target jurisdiction before production release — TRD §9 makes clinical sign-off a release gate. This log is the single source of truth for that sign-off.

**Process:**
- A row moves from **Pending → Approved** only with a named reviewer and date (recorded in the tables below).
- If a threshold is changed after approval, the row is set to **Revised** and the change must be re-approved; the affected tests in `tests/triageEngine.test.ts` must be updated in the same change.
- Adding a new red flag, vital rule, or symptom to the catalog requires a new row here.

**Status legend:** Pending — awaiting clinical review · In review — submitted · Approved — signed off (reviewer + date) · Revised — changed after approval, re-review required.

### 10.1 Decision thresholds (all currently Pending)
| # | Rule (engine step) | Threshold(s) in `triageEngine.ts` | Level | Status | Reviewer / date | Notes |
|---|---|---|---|---|---|---|
| 1 | Any red flag (`RED_FLAGS`) | Unresponsive; not breathing/gasping; stroke signs; severe chest pain/pressure; uncontrolled bleeding; anaphylaxis signs; active seizure | 1 | Pending | — | Rule-level sign-off per flag; all seven are discrete conditions |
| 2 | Critical vitals | SpO2 < 90%; systolic BP < 90 or > 200 mmHg; HR < 40 or > 150 bpm; RR < 8 or > 30 | 1 | Pending | — | Boundaries per TRD §5 |
| 3 | Borderline vitals | SpO2 90–94%; systolic BP 90–99 or 181–200; HR 41–49 or 121–150; RR 9–10 or 26–30 | 2 | Pending | — | Band values are engine extensions of TRD's "borderline" wording — confirm ranges |
| 4 | Temperature | ≥ 39.5 °C (high fever) or ≤ 35.0 °C (hypothermia) | 2 | Pending | — | Engine extension beyond TRD's named vitals; needs explicit approval |
| 5 | High-risk symptoms (8 tags) | Chest pain/tightness, shortness of breath, sudden severe headache, confusion, fainting, coughing blood, severe abdominal pain, one-sided weakness | 2 | Pending | — | Catalog curation — which symptoms count as "high-risk" |
| 6 | Pain score | ≥ 9 | 2 | Pending | — | — |
| 7 | GI/dehydration symptoms (4 tags) | Vomiting, diarrhea, signs of dehydration, unable to keep fluids down | 3 | Pending | — | Catalog curation |
| 8 | Suspected fracture | Fracture-tagged symptom | 3 | Pending | — | — |
| 9 | Pain score | ≥ 6 | 3 | Pending | — | — |
| 10 | Symptom duration | ≥ 48 h | 3 | Pending | — | — |
| 11 | Pain score | ≥ 3 | 4 | Pending | — | — |
| 12 | Any other symptom | Any untagged symptom selected | 4 | Pending | — | — |
| 13 | Default | No triggers above | 5 | Pending | — | — |

### 10.2 Open decisions (need a clinical ruling, not just sign-off)
| # | Question | Location | Current behavior | Decision needed |
|---|---|---|---|---|
| A | HR = 40 bpm and RR = 8/min exactly are not flagged | `criticalVitalReasons` (ponytail comment) | Fall between the critical (<40/<8) and borderline (41–49 / 9–10) bands | Rule in: keep as-is, or narrow a boundary (with test updates) |
| B | Borderline vital band values (row 3) | `emergentReasons` | Author-chosen bands | Confirm clinically appropriate ranges |
| C | Temperature thresholds (row 4) | `emergentReasons` | ≥ 39.5 °C / ≤ 35.0 °C | Confirm high-fever and hypothermia cut-offs |

## 11. Out of Scope (MVP)
- Diagnosis or treatment recommendation.
- Remote data storage, user accounts, cloud sync.
- Any ML/LLM-based triage decision (explicitly rejected — see §3.2).
- Multi-language UI (localization-ready only).
- EHR/EMR integration.
- Pediatric-specific rules (age is collected now to enable them later).

## 12. Future Iterations (post-MVP, unprioritized)
- Pediatric rule set using the already-collected age field.
- Locale resolution: select an active catalog (e.g. `fr.ts` typed as `StringCatalog` — key *and* placeholder parity enforced by typecheck) with a language toggle. The strings infrastructure is shipped; switching locales is not.
- History schema v2: store triggered-reason **keys** rather than rendered strings, so stored assessments re-render in the active locale; bump the AsyncStorage key from `@healthai-triage/history/v1`.
- Unit localization: temperature is stored as °C, so a °F locale needs input conversion plus per-locale copy for `vital.temperatureUnit` and the fever/hypothermia reason strings.
- List formatting: replace the catalog `common.listSeparator` with device-locale formatting (`Intl.ListFormat`) when a second locale lands.
- Optional local LLM *explanation* layer — never overrides the engine (§3.2).
- Export/print a triage summary for clinic handoff.
- Voice input for hands-free use.

## See Also
- [[TRD]] — technical implementation, data model, and decision logic (kept in sync with `src/logic/triageEngine.ts`)
