# Plan — Ship Offline Triage Feature + Frontend Rework (RakshaAi)

## 1. Overview

Complete and ship the uncommitted triage feature and the frontend navigation
rework currently sitting in the working tree. Backend triage engine + API +
tests are written and passing (48/48). Frontend triage screen, SQLite history
storage, tabbed navigation, and a large `api.ts` expansion are written but the
work is uncommitted and partially unverified. This plan takes it to a shippable,
tested, committed state.

**Status:** work-in-progress on `main`, ~6.5k insertions across 20+ files.

## 2. Premises

1. Triage decision must stay **deterministic and auditable** — rule engine is the
   safety floor; LLM output is re-validated and can be escalated, never trusted alone.
2. **Privacy first** — triage history stays on-device (SQLite), never leaves device.
3. App must work **offline-first** — UI degrades gracefully when backend is unreachable.
4. Safety-critical vitals bounds must match **exactly** between frontend validator,
   backend validator, and rule engine (single source of truth, no drift).
5. The rework targets both **native (Expo) and web** — both entry points must keep working.

## 3. Scope

### In scope
- Triage feature end-to-end: form → frontend validate → POST `/triage/` → result card → SQLite history.
- Backend triage endpoint hardening + audit logging.
- Frontend rework: `(tabs)` layout, new screens (benchmark, console, documents, plugins, workspace), triage screen wiring, `api.ts` expansion, theme consolidation.
- Tests: backend triage (exists, passing); add missing backend + frontend coverage.
- CORS: `allow_origin_regex` change in `main.py` (verify it doesn't over-open).

### Not in scope
- Multi-language / i18n of triage.
- Cloud sync of triage history (explicitly contrary to premise 2).
- New triage medical content beyond the PRD's ESI thresholds.
- Backend layerstream/manualstream engine internals (unchanged by this work).

## 4. What already exists

| Sub-problem | Existing code | State |
|---|---|---|
| Triage rule engine (ESI flowchart) | `backend/app/core/triage.py` | Written, 267 lines, tested |
| Vitals front gate | `validate_vitals()` in `core/triage.py` + mirror in `triage.tsx` | Written |
| LLM back gate + retry + escalation | `api/triage.py` | Written |
| Triage API schema | `backend/app/schemas/triage.py` | Written |
| Triage API tests | `backend/tests/test_triage.py` | Passing (48/48) |
| Frontend triage screen | `raksha_app/src/app/triage.tsx` | Written, 647 lines |
| On-device history | `raksha_app/src/storage/triageDb.ts` | Written |
| Triage API client | `runTriage()` in `api.ts` | Written |
| Tab navigation | `src/app/(tabs)/` + `app-tabs.tsx` (+ `.web.tsx`) | Written |
| Theme consolidation | `constants/theme.ts` | Rewritten (dark-only) |

## 5. Architecture

```
┌─ triage.tsx (form UI) ─────────────┐
│  frontend validateForm()           │
└──────────────┬─────────────────────┘
               │ POST /triage/ (runTriage)
               ▼
┌─ api/triage.py ────────────────────┐
│  1. validate_vitals() → 422        │
│  2. LLM (if generative engine)     │
│     strict-JSON prompt → parse     │
│     → validate_triage_output()     │
│     → retry once w/ feedback       │
│  3. fallback rule_based_triage()   │
│  4. safety floor: escalate to      │
│     rule level if higher           │
│  5. audit.log → SQLite             │
└──────────────┬─────────────────────┘
               │ result
               ▼
┌─ triageDb.ts (SQLite history) ─────┐
   saveTriage / listTriage / delete / clear
```

- `core/triage.py` = pure functions, no I/O, unit-testable.
- `api/triage.py` = orchestration + audit + HTTP.
- Frontend validator mirrors backend bounds (drift risk — see risks).

## 6. Implementation Tasks

### 6.1 Backend hardening
- [ ] **T1** Verify single source of truth for vitals bounds: `VITAL_BOUNDS` in
      `core/triage.py` is the canonical set; ensure frontend `validateForm` bounds
      match exactly (currently hand-duplicated).
- [ ] **T2** Confirm audit logging path (`app.state.db.audit.log`) exists and works
      with the current DB manager; add a test that a triage call writes an audit row.
- [ ] **T3** Review CORS `allow_origin_regex=r"https?://.*"` in `main.py` — this is
      broader than the previous explicit allowlist. Confirm intent; tighten to
      `localhost:3000`, `127.0.0.1:3000`, `app://`, `exp://` if possible. Security risk.
- [ ] **T4** Add endpoint test via FastAPI TestClient: valid input → 200 + correct
      ESI level; impossible vitals → 422; malformed LLM output → rule fallback
      (mock engine).

### 6.2 Frontend
- [ ] **T5** Verify triage screen reachable from Home (`router.push('/triage')`) and
      `_layout.tsx` Stack route registered. Confirm back navigation works.
- [ ] **T6** TypeScript check passes across `raksha_app` (`tsc --noEmit`); fix any
      errors in new screens + `api.ts`.
- [ ] **T7** Web entry point (`app-tabs.web.tsx`) parity — ensure all new tabs render
      on web; the triage screen is native+web capable.
- [ ] **T8** Offline behavior: `runTriage` failure → `ErrorBanner` shown, no crash;
      history still renders from SQLite. Verify empty-state text.

### 6.3 Tests & verification
- [ ] **T9** Backend: run full `pytest` suite (not just triage) — confirm no regressions.
- [ ] **T10** Frontend: run `tsc --noEmit` + lint. Add unit test for `validateForm`
      bounds parity vs backend `VITAL_BOUNDS` if a test runner is configured.
- [ ] **T11** Manual smoke: start backend + `expo start` (native + web), run one
      triage, confirm result card + history row persists after reload.

### 6.4 Ship
- [ ] **T12** Commit the work in logical chunks (triage feature, then rework).
- [ ] **T13** Update `README.md` + `trd.md` with triage feature + new nav structure.

## 7. Test Plan

| Codepath | Test | Type |
|---|---|---|
| Vitals validator rejects impossible values | `test_validate_vitals_rejects_impossible` (parametrized) | backend unit |
| Rule flowchart — red flag → ESI 1 | `test_*` in `test_triage.py` | backend unit |
| Rule flowchart — critical vital → ESI 1 | `test_*` | backend unit |
| Rule flowchart — emergent → ESI 2 | `test_*` | backend unit |
| Rule flowchart — urgent → ESI 3 | `test_*` | backend unit |
| Rule flowchart — mild → ESI 4/5 | `test_*` | backend unit |
| JSON extraction (fenced/prose) | `extract_json` tests | backend unit |
| LLM back gate validation | `validate_triage_output` tests | backend unit |
| Endpoint: valid / 422 / LLM-fallback | **T4 (new)** | backend integration |
| Audit row written | **T2 (new)** | backend integration |
| Frontend validator parity | **T10 (new, if runner)** | frontend unit |
| UI smoke (native + web) | **T11** | manual |

## 8. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Vitals bounds drift between frontend/backend | High | T1 canonicalization; test parity (T10) |
| CORS overly permissive | Med | T3 tighten regex |
| Frontend screens broken on web | Med | T7 parity pass + T11 smoke |
| LLM path untested end-to-end (no real engine loaded) | Med | T4 mocks engine; rule fallback always safe |
| Large uncommitted diff → messy commit history | Low | T12 logical commit chunks |

## 9. Completion Criteria

- [ ] 100% triage rule branches covered by passing tests (incl. new T2/T4).
- [ ] `pytest` full suite green; `tsc --noEmit` clean; lint clean.
- [ ] Manual smoke passes on native + web (one full triage cycle, history persists).
- [ ] CORS tightened to intended origins.
- [ ] Work committed in logical chunks; README/TRD updated.

---
---

# /autoplan Review — CEO Phase (SELECTIVE EXPANSION)

## Premise gate
Premises 1-5 reviewed against code. P1 (rule floor), P2 (privacy), P3 (offline-first), P4 (parity), P5 (dual entry) all traceable to real code. **P3 is the weakest** — the triage decision lives in FastAPI, so "offline-first" really means "backend must be running." Flagged in alternatives; the plan ships the backend-first architecture while the PRD specifies on-device rule engine. This is a User Challenge (CEO voice agrees) surfaced at the final gate.

## CEO dual voices — consensus table
Codex unavailable → `[subagent-only]`.

| Dimension | Claude subagent | Codex | Consensus |
|---|---|---|---|
| 1. Premises valid? | P3 challenged (offline-first ≠ delivered) | N/A | DISAGREE-vs-PRD |
| 2. Right problem? | Partially — wrong architecture for triage | N/A | CHALLENGE |
| 3. Scope calibrated? | No — rework bundled with medical feature | N/A | CHALLENGE |
| 4. Alternatives explored? | No — on-device TS engine dismissed | N/A | CHALLENGE |
| 5. Competitive risk? | Yes — medical/regulatory exposure | N/A | FLAGGED |
| 6. 6-month trajectory? | Risky — inverted safety floor (F1) | N/A | FLAGGED |

## CEO findings (subagent)
- **F1 CRITICAL** — `api/triage.py:124` `if rule["severity"] > result["severity"]` is inverted. ESI severity: 1=most urgent, 5=least. When rule is MORE urgent (lower number) than LLM, no escalation fires; when rule is LESS urgent (higher number), it actively downgrades the LLM. Net: less-urgent level wins on every disagreement. Opposite of PRD "never silently downgrade." **Verified against code.** Fix: `if rule["severity"] < result["severity"]`.
- **F2 HIGH** — LLM severity used directly when schema-valid; contradicts PRD §3.2 "LLM must never influence triage level."
- **F3 HIGH** — no clinical sign-off gate; PRD §10 thresholds all "Pending"; `EMERGENCY_NUMBER='112'` hardcoded (`triage.tsx:23`), PRD requires region-configurable.
- **F4 HIGH** — CORS widened to `allow_origin_regex=r"https?://.*"` + `allow_credentials=True` (`main.py:136`) → every http/https origin credentialed. Verified.
- **F5 HIGH** — offline-first not delivered; full raw health input persisted to server audit_log; web `resolveApiUrl` hostname probe would send data off-device.
- **F6 HIGH** — 6.5k insertions direct-to-main, no branch/PR; `frontend/` (Next.js) dirty parallel stack.
- **F7 MEDIUM** — 91 passed not 48; zero endpoint/integration tests; no frontend test runner.
- **F8 MEDIUM** — PRD/TRD describe `healthai-triage/` project that doesn't exist; code contradicts governing docs.
- **F9 MEDIUM** — Home screen (`index.tsx:26,34,179,213`) fabricates hardware/model/AVX telemetry. **Verified.**
- **F10 MEDIUM** — vitals bounds hand-duplicated `triage.tsx:120-141` vs `core/triage.py:22-28`.

## NOT in scope (CEO)
- On-device TS triage engine (deferred — requires architecture change; User Challenge at gate).
- Reconcile `frontend/` vs `raksha_app/` (two web stacks) — deferred, strategic debt.
- i18n, multi-language triage.
- Cloud sync of triage history (contrary to premise 2).
- Clinical sign-off process itself (cannot be coded; must be gated).

## What already exists (CEO)
Mapping produced in §4. Note: audit table exists (`manager.py:68`), wired (`main.py:68`). `chat.py` `{"text"}`/`{"output"}` fallback pattern reused by `_engine_text`. Frontend validator duplicates backend bounds (no shared artifact).

## Dream state delta
```
CURRENT: LLM server + basic app THIS PLAN: triage w/ rule floor + tabs rework 12-MONTH IDEAL: on-device rule engine, clinician-reviewed thresholds, region config
screens, no triage, inconsistent theme tests green, audit trail, dark theme
```

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|-----------|-----------|----------|
| 1 | CEO | Mode = SELECTIVE EXPANSION | Mechanical | autoplan override | Hold scope, surface expansions individually | — |
| 2 | CEO | F1 escalation comparison inverted → must fix | Mechanical | P1 completeness | Release-blocking safety bug, verified in code | Fix is `<`, no downside |
| 3 | CEO | CORS regex = release blocker, tighten | Mechanical | P3 pragmatic / P5 explicit | Security; `https?://.*` + credentials is over-permissive | Keep `app://`/`exp://` |
| 4 | CEO | Emergency number → config | Mechanical | P1 completeness | PRD §3.1 requires region-configurable | Hardcode is non-compliant |
| 5 | CEO | On-device TS rule engine | Taste | P2/P4 | CEO subagent recommends; contradicts shipped architecture | Deferred to gate |
| 6 | CEO | Split triage from rework into separate commits | Taste | P2 | Isolate safety-critical revert boundary | Deferred to gate |
| 7 | CEO | Clinical sign-off gate | User Challenge | P1 | PRD §10 blocks release without it | Surface at gate |
| 8 | CEO | Fabricated telemetry → unavailable states | Mechanical | P1 | F9 verified; health product trust | — |

# /autoplan Review — Eng Phase

## Eng dual voices — consensus table
Codex unavailable → `[subagent-only]`.

| Dimension | Claude subagent | Codex | Consensus |
|---|---|---|---|
| 1. Architecture sound? | No — C1 inverted safety floor, H5 dup routes | N/A | FAIL |
| 2. Test coverage sufficient? | No — zero endpoint tests, no frontend runner | N/A | FAIL |
| 3. Performance risks addressed? | No — 15s timeout vs 600-token LLM (H1) | N/A | FAIL |
| 4. Security threats covered? | No — CORS open (H3), rate limit unapplied (H4) | N/A | FAIL |
| 5. Error paths handled? | Partial — retry-once + fallback good, exceptions swallowed (M5) | N/A | PARTIAL |
| 6. Deployment risk manageable? | No — direct-to-main, dup routes block build | N/A | FAIL |

## Eng findings (subagent)
- **C1 CRITICAL (conf 9)** — escalation inverted `api/triage.py:124`. Independent confirmation of CEO F1. Fix `<`; add 4 endpoint tests.
- **H1 HIGH (8)** — 15s axios timeout vs 600-token LLM gen → primary flow silently times out; server finishes, client never saves history.
- **H2 HIGH (9)** — audit_log persists full raw health input; `AuditTable.cleanup()` exists but never called.
- **H3 HIGH (8)** — CORS regex open + credentials (confirms CEO F4).
- **H4 HIGH (8)** — rate limiter declared (`60/minute`) but zero `@limiter.limit` decorators; unthrottled LLM endpoint.
- **H5 HIGH (7)** — duplicate expo-router routes: root `app/benchmark.tsx` etc. AND `app/(tabs)/<same>.tsx` both map to `/benchmark` — build/ambiguity risk.
- **M1 MED (8)** — vitals bounds hand-duplicated, no test runner → no parity enforcement (confirms F10).
- **M2 MED (9)** — safety floor itself untested end-to-end.
- **M3 MED-HIGH (8)** — prompt injection via symptom strings; no payload cap on `symptoms`.
- **M4 MED (9)** — no offline triage despite premise 3 (confirms F5).
- **M5 MED (7)** — synchronous audit writes; `_llm_triage` swallows exceptions silently.
- **M6 MED (7)** — blank age → `age_years: 0` (neonate); rule engine ignores age entirely.

## Architecture diagram (eng)
```
triage.tsx ──POST /triage/──▶ api/triage.py ──▶ core/triage.py (pure rules)
  │ validateForm()              │ front gate 422       ▲ rule fallback
  │ (mirrors VITAL_BOUNDS)      │ _llm_triage() (LLM)  │
  │                             │ retry ×1 → fallback │
  │                             │ escalation (C1 BUG) │
  ▼                             ▼                      │
triageDb.ts ◀──saveTriage──    audit_log (SQLite, raw PHI)
  (device SQLite history)       (server, unbounded H2)
```

## NOT in scope (eng)
- On-device TS engine port (M4) — deferred, architecture change.
- Audit retention job (H2) — defer to TODOS.
- Pediatric triage calibration (M6) — needs clinical input.
- Frontend test runner setup — pending decision at gate.

## What already exists (eng)
`manager.py:68` `self.audit = AuditTable(...)`; wired `main.py:68`. `chat.py` text/output fallback pattern. `rule_based_triage` pure + 48 tests. Frontend `validateForm` = client gate but no rule engine.

## Failure modes registry (eng)
| Codepath | Failure mode | Rescued? | Test? | User sees? | Logged? |
|---|---|---|---|---|---|
| escalation | LLM under-triage missed | N (inverted) | N | L4 no call btn | N ← CRITICAL |
| escalation | LLM over-triage downgraded | N (inverted) | N | L5 self-care | N ← CRITICAL |
| LLM generate | 600-token timeout | N (15s) | N | "Network Error" | server yes, client no |
| audit write | SQLite lock | Y (busy_timeout) | N | nothing | N |
| _llm_triage except | engine crash | Y (silent) | N | rules fallback | N ← GAP |
| dup routes | bundle ambiguity | N | N | build error | N |

# /autoplan Review — Design Phase

## Design litmus scorecard
Codex unavailable → `[subagent-only]`. UI scope: YES (triage + tabs).

| Dimension | Score | Notes |
|---|---|---|
| Info hierarchy | 5/10 | Call button buried at end of gated flow |
| Interaction states | 4/10 | Offline = cryptic "Network Error", no call path |
| User journey | 4/10 | Arc collapses offline; red-flag tap gives zero feedback |
| Specificity | 5/10 | Plan generic on UI; no screen-by-screen spec |
| Design system | 5/10 | Dark-only claimed but light palette + system switching remain |

## Design findings (subagent)
- **A1 CRITICAL** — emergency call affordance only in ResultCard after full form + network call (`triage.tsx:504-516`); disclaimer non-tappable.
- **B1 CRITICAL** — offline = no decision, raw axios "Network Error", no emergency guidance.
- **E1 CRITICAL** — duplicate routes (root + `(tabs)`) → expo-router ambiguity (confirms eng H5).
- **A3 HIGH** — triage not a tab; absent from web sidebar (`app-tabs.web.tsx`).
- **E2 HIGH** — native (7 tabs, no Workspace/Plugins/Chat) vs web (8 + orphaned chat) nav sets diverge.
- **E3 HIGH** — `EMERGENCY_NUMBER='112'` hardcoded; PRD requires configurable (confirms CEO F3).
- **E4 HIGH** — "dark-only" contradicted: light palette + OS scheme switching + web pre-hydration light flash.
- **E5 HIGH** — severity badge white-on-amber/green fails WCAG contrast (2.0-2.7:1 on levels 2-4).
- **E6 HIGH** — chips ~20px, stepper ~28px, bare-text delete; no switch/selected a11y roles.
- **B5 HIGH** — stale result persists after form edits; user can't tell card reflects current form.
- **B2-B4, A2, C4, E7-E8 MED** — error wall-of-text, web history "unavailable" vs "empty", no auto-scroll, vitals optionality unstated, no keyboard handling, nested pressables + no clear-all confirm.

## User flow diagram (design)
```
HOME (server dashboard) ──quick cmd──▶ TRIAGE (stack screen)
  └ triage missing from tabs          │ red flags (7 toggles)
                                       │ vitals (5, optional unstated)
                                       │ pain/duration
                                       │ 19 symptom chips
                                       │ [Run Triage] ──15s spinner──▶
  ONLINE: ResultCard (badge + call btn at bottom)
  OFFLINE: "Network Error" ✗ no call path ← B1 CRITICAL
```

## NOT in scope (design)
- Full screen-by-screen UI acceptance spec — deferred, flagged at gate.
- WCAG full audit — minimal badge/contrast fixes in scope.
- i18n of triage UI.

## What already exists (design)
Dark-teal `Colors` in `theme.ts`. `ThemedView`/`ThemedText`/`ErrorBanner`/`StatRow` components. `app-tabs` native + web variants.

# /autoplan Review — DX Phase

DX subagent failed (API stream timeout) → phase run inline. Product = developer tool (local LLM platform + API). DX scope: YES.

## DX findings (inline)
- **DX1 HIGH** — README is 10 bytes (`# RakshaAi`). No run instructions for backend (`uv run uvicorn`? never documented) or app (`expo start`). Zero-to-running TTHW is guesswork; a new dev must reverse-engineer.
- **DX2 HIGH** — two web stacks: `raksha_app` (Expo web) + `frontend/` (Next.js 16, "sovereign-ai-frontend"). Confusing; plan doesn't reconcile. Confirms CEO F6.
- **DX3 MED** — API surface is 38 exported functions across 8+ resource families (models, system, chat, rag, documents, plugins, benchmark, workspace, triage, settings, agents). Naming is consistent (`listX`, `getX`, `runX`). No API docs.
- **DX4 MED** — error messages: `errMsg(e)` returns raw `e.message`; axios network errors → "Network Error" with no cause/fix. Violates problem+cause+fix.
- **DX5 MED** — prd.md/trd.md describe `healthai-triage/` project that doesn't exist; README describes nothing. Doc stack is 3 disconnected narratives.
- **DX6 LOW** — no CI. No lint-on-commit, no test gate.

## DX scorecard
| Dimension | Score |
|---|---|
| Getting started | 2/10 |
| API/CLI design | 6/10 |
| Error messages | 3/10 |
| Documentation | 2/10 |
| Upgrade path | 4/10 |
| Dev environment | 4/10 |
| Community/ecosystem | 2/10 |
| DX measurement | 2/10 |

## Decision Audit Trail (continued)

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|-----------|-----------|----------|
| 9 | Eng | C1 escalation inversion — release blocker, fix `<` | Mechanical | P1 | Confirmed by CEO F1 + eng subagent, conf 9 | — |
| 10 | Eng | Add endpoint tests: escalate/never-downgrade/fallback | Mechanical | P1 | Safety floor untested (M2) | — |
| 11 | Eng | Raise triage timeout + cut max_tokens | Mechanical | P3 | H1: primary flow times out at 15s | Streaming deferred |
| 12 | Eng | Cap symptoms payload + prompt-injection guard | Mechanical | P3 | M3 | — |
| 13 | Eng | Fix duplicate routes (H5/E1) | Mechanical | P5 | Build blocker | Keep `(tabs)` as canonical |
| 14 | Eng | Rate limiter actually applied | Mechanical | P3 | H4: declared, zero decorators | — |
| 15 | Design | Emergency call affordance promoted | Taste | P1 | A1 critical | Surface at gate |
| 16 | Design | Offline message + call path | Taste | P1 | B1 critical | Surface at gate |
| 17 | Design | Dark-only enforced / theme setting wired | Taste | P3 | E4 | Surface at gate |
| 18 | Design | Badge contrast fix (WCAG) | Taste | P1 | E5 | Surface at gate |
| 19 | DX | Write README with run instructions | Mechanical | P1 | DX1: 10-byte README | — |
| 20 | DX | Reconcile frontend/ vs raksha_app/ | Taste | P2 | DX2/F6 | Defer to TODOS |

## Cross-phase themes
- **Escalation inversion (C1/F1)** — flagged in CEO + Eng independently. Highest-confidence signal.
- **CORS open (F4/H3)** — flagged CEO + Eng. Release blocker.
- **Duplicate routes (E1/H5)** — flagged Design + Eng independently. Build blocker.
- **Hardcoded emergency number (F3/E3)** — flagged CEO + Design. PRD non-compliant.
- **Offline-first not delivered (F5/M4)** — flagged CEO + Eng + Design (B1). Product doctrine conflict.
- **No test coverage of safety floor (F7/M2)** — flagged CEO + Eng.
- **Two web stacks (F6/DX2)** — flagged CEO + DX.

## Deferred to TODOS.md
- Audit retention job (`AuditTable.cleanup` scheduler) — H2.
- On-device TS triage engine — M4/F5 (User Challenge).
- `frontend/` vs `raksha_app/` reconciliation — DX2/F6.
- Frontend test runner (vitest) setup — M1/T10.
- Pediatric triage calibration — M6.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/autoplan` | Scope & strategy | 1 | ISSUES_OPEN | 10 findings (1 critical), 2 critical gaps |
| Codex Review | `/autoplan` | Independent 2nd opinion | 0 | N/A (codex not installed) | — |
| Eng Review | `/autoplan` | Architecture & tests (required) | 1 | ISSUES_OPEN | 12 findings (1 critical), 3 critical gaps |
| Design Review | `/autoplan` | UI/UX gaps | 1 | ISSUES_OPEN | 15 findings (3 critical) |
| DX Review | `/autoplan` | Developer experience gaps | 1 | ISSUES_OPEN | 6 findings |

- **VERDICT:** NOT CLEARED — eng review required gate failed. Release-blocking: escalation inversion (C1/F1), open CORS (H3/F4), duplicate routes (H5/E1), zero endpoint tests (M2/F7).
- **CODEX:** not run — codex CLI not installed; dual voices degraded to Claude subagent only.
- **CROSS-MODEL:** escalation inversion confirmed independently by CEO + Eng subagents (confidence 9/9). CORS, dup routes, offline-first gap, hardcoded emergency number confirmed across 2+ phases.

**UNRESOLVED DECISIONS:**
- User Challenge: triage architecture (LLM-as-scorer backend vs PRD's on-device rules-authoritative) — pending user call at final gate.
- User Challenge: direct-to-main vs branch+PR for the 6.5k-line changeset.
- Taste: split triage vs rework commits; emergency-call prominence; offline message; dark-only enforcement; badge contrast; frontend/ reconciliation — pending at final gate.
