# PLAN — Emami Distributor Experience Platform (POC)

Status: **Plan written, awaiting approval.** No code yet.
Source of truth: `PROJECT_CONTEXT.md` > renders. Numbers always come from the simulator.

---

## 0. Key design decisions (read these first)

1. **Two SQLite files.** `backend/data/emami_dx.sqlite` stays the untouched Day-0 world (the provided `test_counts` asserts
   it has exactly 12 tables). Run tables live in `backend/data/runs.sqlite` (git-ignored, created on first start). The app
   opens `runs.sqlite` and `ATTACH`es the Day-0 DB **read-only** as `world`, so joins still work in plain SQL.
2. **Compute ahead, reveal by clock.** The simulator is deterministic. It computes the timeline **segment by segment**
   and writes every row with its sim timestamp. `loop_runs.current_day` is the "reveal" pointer. Every page query is
   `WHERE sim_day <= :day`. That makes `?day=` trivial, makes past days viewable, and makes Play/SSE just "move the pointer
   and stream the events it passes".
   - **Segment A (Day 0 → 7.0)** is computed on Reset. Nudges, replies, reminder, enrolments and sanity flags all land at
     their own times.
   - **PLAN (Day 7.0)** is built when the pointer reaches 7.0, using the ASM's Keep/Drop decisions so far. It is rebuilt if a
     custom group is added before approval.
   - **Segment B (Day 8 → 30)** is computed once no plan row is Pending (or by Autopilot at Day 7 10:00). Then RESULTS and
     LEARN run at Day 30.
   - Keep/Drop affects only numbers and confidence, never behaviour, so Segment A never needs recomputing.
3. **State lives in the DB, not in LangGraph.** The graph carries only `run_id`, `stage` and `day`. Every node reads and
   writes run tables and emits `events`. That keeps it restart-safe, with no checkpointer dependency.
4. **The LLM writes templates, code fills numbers.** Nudge and CTA text is generated once per *(cohort/row × language)* with
   placeholders (`{owner_first}`, `{target}`, `{asm}`). Code substitutes per distributor. This keeps the call count small
   (≈ 40 per run), keeps numbers code-owned, and keeps the replay cache small.
5. **`sim_traits` is quarantined.** Only `app/simulation/traits.py` may read it. A test greps every API response and every
   rendered prompt for all 16 trait column names and for raw trait values of the anchors.

---

## 1. Phases → tasks

### Phase 0 — Scaffold
| Task | Files |
|---|---|
| Root task runner (works without `make` on Windows); `Makefile` delegates to it | `tasks.py`, `Makefile` |
| Env template | `.env.example` (as CLAUDE.md), `.gitignore` |
| Backend skeleton + `/health` | `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/config.py` |
| Next.js App Router + TS + Tailwind, fonts (Bricolage Grotesque, Instrument Sans, **Noto Sans Bengali / Devanagari** for BN/HI text) | `frontend/package.json`, `frontend/app/layout.tsx`, `frontend/app/globals.css` (tokens as CSS vars) |
| Shell: navy sidebar with `emami-logo-reverse.png`, nav groups (ASM workspace / Channels / Demo), Approvals badge, sidebar scheme-status card, user card; top bar with breadcrumb, "Concept prototype · synthetic data" pill, ASM workspace / Distributor view toggle | `frontend/components/shell/{Sidebar,TopBar,ViewToggle,StatusCard}.tsx` |
| `<LoopStepper day stage/>` (4 steps, links to page@day) | `frontend/components/loop-stepper/LoopStepper.tsx` |
| Card primitives: Card, Tile, Pill, ProgressBar, AiPanel | `frontend/components/cards/*` |
| 7 routes with placeholders: `/` `/cohorts` `/survey` `/approvals` `/distributor` `/results` `/simulation` | `frontend/app/*/page.tsx` |
| Sim-day context (reads `/sim/state`, follows SSE, honours `?day=`) | `frontend/lib/useSimDay.ts`, `frontend/lib/api.ts` |
| Date helper "Day 9 · Sat 10 Oct", `formatINR()` | `frontend/lib/format.ts`, `backend/app/simclock.py` |

### Phase 1 — Data + cohorts
| Task | Files |
|---|---|
| `make seed` → generator; provided tests green | `tasks.py seed` |
| DB layer: open runs DB, attach world read-only, query helpers | `backend/app/db/{conn.py,schema.sql,queries.py}` |
| Rule loader (yaml → Pydantic) | `backend/app/rules/loader.py` |
| Cohort agent: re-applies `cohorts.yaml` to `distributor_features`, returns cohort + plain reasons; must equal `cohort_assignments` | `backend/app/engines/cohorts.py` |
| Endpoints: territory, cohorts, distributor list/detail (Day-0 fields only so far) | `backend/app/api/{territory,cohorts,distributors}.py` |
| Pydantic response models | `backend/app/models.py` |
| Tests: cohort engine reproduces assignments; no trait leakage | `backend/tests/test_cohorts.py`, `test_no_leak.py` |

### Phase 2 — Simulator engine + Simulation tab (the core)
| Task | Files |
|---|---|
| Clock: float day ↔ datetime, stage table, stage-for-day | `backend/app/simulation/clock.py` |
| Traits access (only reader of `sim_traits`), scenario multipliers | `backend/app/simulation/{traits.py,scenarios.py}` |
| Behaviour model (§3 of spec): per-(seed, dist, purpose) RNG; reply, intent, ratings, Q6, Q7, survey time, low-effort, duplicates, pre-CTA enrolment, CTA effect, October sales; anchor overrides | `backend/app/simulation/behaviour.py` |
| Comment text bank (~6 per theme × EN/BN, each tagged with its theme) + junk lines | `backend/app/simulation/text_bank.yaml` |
| Engine: `reset`, `build_segment_a`, `on_reach_day`, `build_plan`, `build_segment_b`, `results`, `learn`; writes rows + events | `backend/app/simulation/engine.py` |
| Player: asyncio ticker (1/2/5 s per sim day), pause, autopilot, SSE broadcaster | `backend/app/simulation/player.py` |
| Sanity-check engine (real module, yaml-driven) | `backend/app/engines/sanity_checks.py` |
| CTA planner: cohort CTA, individual attention, confidence, priority, custom groups | `backend/app/engines/cta_planner.py` |
| Persona updater (incremental + Day 30) | `backend/app/engines/persona.py` |
| Results engine (5 questions) | `backend/app/engines/results.py` |
| LangGraph loop graph (§4) | `backend/app/agents/loop_graph.py`, `backend/app/agents/nodes/*.py` |
| LLM client with 4 modes + fixtures for the prompts the sim needs | `backend/app/llm/{client.py,cache/,fixtures/,prompts/}` |
| Sim API | `backend/app/api/sim.py` |
| Seed search for the calibration band | `backend/scripts/find_seed.py` |
| Simulation tab: controls / loop + big date + 6 counters / live feed; approval banner | `frontend/app/simulation/page.tsx`, `frontend/components/sim/*` |
| Tests: determinism (hash of run tables), calibration bands, anchors, `?day=` filtering, reject-lowers-joins, no leakage | `backend/tests/test_simulator.py`, `test_anchors.py`, `test_time_aware.py` |

### Phase 3 — Survey page
| Task | Files |
|---|---|
| Left: "What we sent, by cohort": cohort pills, EN / বাংলা / हिन्दी toggle, nudge message, Q1 chips, Q2–Q7 with cohort-specific Q6 | `frontend/app/survey/page.tsx`, `components/survey/QuestionList.tsx` |
| Right: Replies by day (bars, reminder bar orange, today blue, median reply time) · Sanity checks (Clean/Check/Flagged) · Flagged answers with Keep/Drop (≤ 4 + "N more to check") · Intents incl. "No reply yet" · Ratings "% who said 4 or 5" · comment theme chips | `components/survey/*`, `components/charts/RepliesByDay.tsx` |
| Endpoints + Keep/Drop | `backend/app/api/survey.py` |
| Comment themes: LLM assigns each comment to a theme, **code counts** | `engines/themes.py`, prompt `comment_themes` |

### Phase 4 — Approval matrix
| Task | Files |
|---|---|
| Summary strip ("59 distributors haven't joined yet…"), **Approve all 70%+**, **+ Custom group** | `frontend/app/approvals/page.tsx` |
| Table: Group · Who · Follow-up (+ one-line why) · Confidence bar · Priority pill · ✓/✗; Individual attention row expands to the people list (≤ 5 + "+N more") | `components/approvals/*` |
| Custom group modal (pick distributors, pick CTA from catalogue) — re-plans that group only | `components/approvals/CustomGroupDialog.tsx` |
| Decisions resume the run when **no row is Pending** | `backend/app/api/plan.py` |
| CTA text via LLM (`cta_message`) | prompt + fixtures |

### Phase 5 — Distributor view + Command centre + 360
| Task | Files |
|---|---|
| Phone mockup: WhatsApp chat built from run rows up to `day` — Day-0 nudge card with target table, quick replies, survey, Day-3 reminder, Day-8 CTA (voice-note bubble + card), enrolment confirmation | `components/phone/*`, `app/distributor/page.tsx` |
| Scenario cards: Maa Tara · Ruplekha · Pal Brothers (+ any distributor via search) and profile card | same |
| "Behind the conversation" timeline from `events` with agent badges | `components/phone/AgentTimeline.tsx` |
| "Type as distributor": chat agent (LLM intent + code tools), writes `chat_messages` + events | `backend/app/agents/chat_graph.py`, `api/chat.py` |
| Command centre: stepper, 4 tiles, Needs you today (≤ 3), Emami AI "first week in short", Progress by cohort | `app/page.tsx`, `api/territory.py` |
| Cohorts page: 5 cohort cards with joined bar, cohort table (≤ 7 + Show all), Distributor 360 with journey + **What we've learned** | `app/cohorts/page.tsx`, `components/cohorts/*` |

### Phase 6 — Day-30 results + persona learning
| Task | Files |
|---|---|
| Five cards (joined by cohort · beat prediction + sales vs normal · speed stacked bar · Day-0 asks · CTA win rates) | `app/results/page.tsx`, `components/results/*` |
| "What we learned" (LLM 3 lines over computed numbers) + 4 persona-change chips | prompt `results_summary` |
| **Apply to the next scheme**: copies personas into `next_cycle_profiles`, emits PERSONA event, shows a preview of next cycle's nudge for 3 anchors | `api/results.py`, `engines/persona.py` |

### Phase 7 — Demo hardening
| Task | Files |
|---|---|
| Record every demo-path LLM call (`tasks.py record-demo` plays the demo path in `record`) and commit the cache | `backend/app/llm/cache/*.json` |
| Offline run in `replay` with the network off; `make demo` = reset seed + replay | `tasks.py demo` |
| Optional Playwright smoke test that opens every page at Day 0/7/9/30 | `frontend/tests/smoke.spec.ts` |
| `docs/DEMO_SCRIPT.md` (click-by-click, ~8 min, §13), `README.md` (≤ 5 setup commands) | docs |

---

## 2. Run-table schema (`runs.sqlite`)

Spec tables, plus a few columns and tables needed by the UI (marked **+**). Times are stored as `sim_day REAL` (0–30). The
clock helper derives display times.

```sql
loop_runs(run_id TEXT PK, seed INT, scenario TEXT, autopilot INT, scheme_id TEXT, current_day REAL, stage TEXT,
          segment_b_built INT, applied_to_next INT, created_at TEXT, is_active INT)
events(event_id INT PK AUTOINC, run_id, sim_day REAL, type TEXT, agent TEXT+, distributor_id TEXT NULL, text TEXT,
       payload_json TEXT+)            -- agent ∈ Nudge agent | Survey agent | CTA agent | You | Execution | Persona
nudges(run_id, distributor_id, cohort, language, sent_at REAL, text, kind TEXT+)   -- kind: nudge | reminder
survey_responses(run_id, response_id PK, distributor_id, started_at REAL, submitted_at REAL, survey_seconds INT,
                 q1_intent, q2 INT, q3 INT, q4 INT, q5 INT, q6 TEXT, q7_text, q7_language, q7_theme TEXT+,
                 is_duplicate INT, is_latest INT+)
sanity_flags(run_id, response_id, code, severity, label, asm_decision NULL, decided_at REAL+)
cta_plan(run_id, row_id PK, group_type, group_name, distributor_id NULL, cta_code, cta_variant TEXT+ (call|visit),
         text_en, text_bn, text_hi+, members INT, member_ids_json+, confidence REAL NULL, priority, revenue_at_stake_l+,
         reason, why+ , status, decided_at REAL+, parent_row_id+)   -- individual people point at the "Individual attention" row
cta_deliveries(run_id, distributor_id, row_id, cta_code, language, sent_at REAL, text+)
asm_calls+(run_id, distributor_id, row_id, sim_day REAL, kind (call|visit), outcome TEXT)
enrolments(run_id, distributor_id, sim_day REAL, path)   -- before_nudge? (none in data) | after_nudge | self | after_cta | after_asm_call
october_sales(run_id, distributor_id, baseline_l, predicted_l, actual_l, hit_prediction INT)
personas(run_id, distributor_id, language, language_on_file+, language_changed, best_time, best_hour+, reply_speed,
         reply_hours+, prefers, what_worked, next_time, updated_day REAL+)
chat_messages+(run_id, distributor_id, sim_day REAL, sender (distributor|desk), text, intent NULL, tool NULL)
next_cycle_profiles+(distributor_id PK, language, best_hour, prefers, next_time, from_run_id, applied_at)
```

Indexes on `(run_id, sim_day)` and `(run_id, distributor_id)`.

---

## 3. Simulator module design and event model

```
simulation/
  clock.py       DAY0 = 2026-10-01 00:00; day_to_dt(), fmt("Day 9 · Sat 10 Oct"), fmt_time("13:05"), STAGES
  traits.py      load_traits(run) -> dict[dist_id, Traits]   # ONLY place that touches sim_traits; applies scenario
  scenarios.py   typical | low_response (resp×0.6) | messy_survey (low_effort×3) | great_uptake (enrol probs×1.2, ≤0.98)
  behaviour.py   pure functions: rng(seed, dist, purpose); reply_time(); intent(); ratings(); q6(); comment();
                 survey_seconds(); pre_cta_enrolment(); cta_join(); october_sales()   # anchors override inside each
  engine.py      orchestrates segments, writes rows + events through db/queries.py, calls engines/*
  player.py      Player(run_id).play(speed) / pause(); advance_to(day) moves current_day, triggers on_reach_day hooks
                 (7.0 → PLAN; if autopilot → approve at 7.4167; 30.0 → RESULTS, LEARN); broadcasts SSE
```

**Advance semantics.** `advance(to_day)` moves the pointer to `min(to_day, gate)`, where `gate = 7.0` while any plan row is
Pending and autopilot is off. `next_stage` jumps to the next stage boundary. Play ticks the pointer by
`Δ = tick / speed_seconds_per_day` (tick 250 ms) and stops at the gate with `waiting_for_approval = true`.

**Event types** (spec list + 4 extras): `NUDGE_SENT`, `REPLY`, `FLAG`, `REMINDER`, `PLAN_READY`, `APPROVED`, `REJECTED`,
`CTA_SENT`, `ASM_CALL`, `ENROLLED`, `RESULTS`, `PERSONA`, plus `FLAG_DECISION` (Keep/Drop), `CUSTOM_GROUP`, `CHAT`,
`SIM_CONTROL` (reset/autopilot).

Cohort-level sends get one aggregate event ("Nudge sent to 19 Scheme-hesitant distributors (14 in Bengali)") plus silent
per-distributor rows in `nudges`. That keeps the feed readable while the 360 and phone still have per-person data.
Event `text` is the plain sentence the feed shows, built by code.

**Behaviour notes / spec gaps filled**
- Reply time is nudged into `active_window` (Morning 9–12, Afternoon 12–16, Evening 17–21). Anchors use
  `scripted_response_hours` exactly (Maa Tara 10:00 + 3 h → 13:05; small minute jitter is code-fixed for realism).
- "I've enrolled" → enrolled at reply time with 85 %. Otherwise CONTRADICTION at submit (DMS check = `enrolments` at that time).
- An anchor's scripted join day applies when its expected CTA is **approved**. If the ASM rejects it, the normal model
  (× 0.2) applies. The anchor test runs with approve-all.
- ASM calls are scheduled Day 9–13 in priority order (≤ 4 per day, Rahul's capacity). Join = call day + 1 with the
  matching-CTA prob.
- Calibration: `find_seed.py` searches seeds 1–200 in `mock`. If seed 7 misses a band, `.env.example` gets the first seed
  that passes everything and the anchors are re-verified.

---

## 4. Engines (real product logic)

- **sanity_checks.py**: `check(response, enrolled_at_submit, prior_submissions) -> [Flag]`, driven by the yaml. Survey
  numbers exclude a response if it has a red flag and `asm_decision != 'Keep'`, or if it was Dropped. DUPLICATE keeps the
  latest.
- **cta_planner.py**
  1. Not-enrolled members at Day 7 per cohort.
  2. Need → CTA map: I'll enrol → QUICK_REMINDER · Explain again → EXPLAIN_SIMPLE (VOICE_EXPLAINER if Bengali or the
     comment asks for voice) · Explain in Bengali → VOICE_EXPLAINER · Talk to my ASM → ASM_CALL · No reply → RE_NUDGE
     (At-risk: ASM_CALL) · Champions and Growth builders also use rating cues.
  3. Cohort CTA = mode. Confidence = share pointing to it × clean share of the cohort's replies.
  4. **Individual attention** = matches a yaml rule **and** the personal CTA differs from the cohort CTA. Red-flagged and
     "Talk to my ASM" always qualify. At-risk no-reply qualifies as an ASM **visit** (`cta_variant`) when billing has been
     down 3+ months (this puts Ganguly in and keeps most At-risk in the cohort row, as in render 4).
  5. Personal confidence = how strongly their own signals point to the CTA (asked explicitly 0.9, inferred 0.7–0.8, flagged
     0.8).
  6. Priority = revenue-at-stake tertiles across rows (individual rows ranked among individuals).
- **results.py**: the five questions as SQL (joined by cohort vs Monsoon, beat prediction + sales vs baseline,
  speed buckets same day / first week / after follow-up / never, intents incl. no reply, CTA win rates = joined ÷ received
  by `cta_code`).
- **persona.py**: spec §4 rules. `best_time` = reply hour rounded to the hour ("Around 1 pm"); bucket counts feed
  "21 reply best in the evening". `next_time` rule-built, then optionally polished by `persona_next_time`.

---

## 5. LangGraph

**Loop graph** (`agents/loop_graph.py`). State = `{run_id, stage, day}`.

```
router ─┬─ NUDGE   → cohort_agent → nudge_agent(LLM) → END
        ├─ COLLECT → survey_agent (sanity checks; themes LLM at Day 7 / on demand) → END
        ├─ PLAN    → cta_agent (planner + LLM text/why) → approval_gate ─┬ pending → END (stage=APPROVAL)
        │                                                                 └ decided → execution_agent
        ├─ SEND    → execution_agent (deliveries, calls, joins, sales; Segment B) → END
        └─ RESULTS → results_agent(LLM summary) → persona_agent(LLM next_time) → END
```

The engine invokes the graph at stage boundaries. The router picks the branch from `stage`, so re-invoking after approval
continues the loop with no checkpointer needed. Every node writes an `events` row.

**Chat graph** (`agents/chat_graph.py`) for "Type as distributor":
`classify(LLM: intent ∈ 5 quick replies + 'question' + 'other')` → `tool` (code: `get_my_target`, `explain_scheme(lang)`,
`enrol_me`, `request_asm_call`, `slab_progress`) → `reply(LLM, gets tool output only)`. In mock it uses keyword intent and
fixture replies. Enrolments from chat are written as `path='self'` at the current sim day.

LLM-calling nodes: nudge_agent, survey_agent (themes), cta_agent, results_agent, persona_agent, chat classify + reply,
plus the command-centre summary.

---

## 6. Prompts (`backend/app/llm/prompts/<id>.md`, each with a Pydantic output schema + fixture)

| id | Inputs (no traits) | Output |
|---|---|---|
| `nudge_message` | cohort, nudge_brief, scheme rules, language, placeholders | `{text}` with `{owner_first}`/`{target}`/`{asm}` |
| `cta_message` | cta_code + label (catalogue only), group, aggregate needs, language | `{text, why}` |
| `comment_themes` | list of comments (EN/BN) + allowed theme list | `{assignments:[{id, theme}]}`; code counts |
| `chat_reply` | distributor public profile, tool result, language, last messages | `{reply, language}` |
| `results_summary` | computed results JSON | `{lines:[3]}` |
| `persona_next_time` | persona fields | `{next_time}` |
| `first_week_summary` | computed Day-7 numbers | `{lines:[3], highlight}` (command-centre panel) |
| `chat_intent` | message text | `{intent, confidence}` |

The client is `complete(prompt_id, inputs, schema)`. Cache key = sha256(prompt_id + prompt version + canonical inputs). It
uses a timeout (8 s) + 1 retry, then cache, then fixture. On 429 it backs off once and falls back to fixture. Fixtures are
hand-written EN + BN (+ HI for nudges), so `mock` looks real.

---

## 7. API per page (all accept `?run_id=&day=`, Pydantic in/out)

| Page | Endpoints |
|---|---|
| Shell | `GET /sim/state` (day, stage, label, waiting_for_approval, pending_rows) · `GET /sim/stream` |
| Command centre `/` | `GET /territory/summary` (tiles, needs_today ≤ 3, cohort_progress, ai_summary) |
| Cohorts `/cohorts` | `GET /cohorts` · `GET /cohorts/{name}/distributors` · `GET /distributors/{id}` (profile, this-cycle journey, persona) · `POST /groups` |
| Survey `/survey` | `GET /survey/questions?cohort=&lang=` · `GET /survey/results` · `POST /survey/flags/{response_id}` `{decision}` |
| Approvals `/approvals` | `GET /plan` · `POST /plan/rows/{row_id}/decision` · `POST /plan/approve-high-confidence` `{min:0.7}` · `POST /plan/custom-group` |
| Distributor `/distributor` | `GET /chat/scenarios` · `GET /chat/{id}/conversation` · `GET /distributors/{id}/events` · `POST /chat/{id}/message` |
| Results `/results` | `GET /results` · `POST /results/apply` |
| Simulation `/simulation` | `POST /sim/reset` · `/sim/advance` · `/sim/play` · `/sim/pause` · `/sim/autopilot` · `GET /sim/events?since_id=` |

## 8. Time-aware pages

- `useSimDay()` returns `day = ?day=` if present, else the live `current_day` from `/sim/state`, updated by SSE.
  `lib/api.ts` appends it to every call.
- When viewing a past day, a small "Viewing Day 3 · Sun 4 Oct — Back to live" pill appears in the top bar.
- Stepper chips link to `/survey?day=7`, `/approvals?day=7`, `/distributor?day=9`, `/results?day=30`.
- Backend: one `at_day(run, day)` helper. Any `day > current_day` is clamped. Data that doesn't exist yet returns an empty
  state (e.g. Results before Day 30 shows "Results on Day 30 · Sat 31 Oct").

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Calibration lands outside bands for seed 7 | `find_seed.py`. Bands are tests, not hopes; the trait model is tuned only if no seed fits |
| Render numbers and anchors disagree with the model (e.g. 10 individual attention) | Planner rules above; small differences are fine per spec |
| Python 3.14 + LangGraph/google-genai wheels | Try 3.14 first; fall back to 3.12 venv (`py -3.12`) if a wheel is missing |
| No `make` on Windows | `tasks.py` does the work; `Makefile` is a thin wrapper for Mac/Linux |
| Free-tier Gemini 429s while recording | Record once, sequentially, with backoff; replay for the demo |
| Fonts need network at first build | First `npm run build` online; after that offline is fine |
| Bengali text rendering | Noto Sans Bengali via `next/font`; fixtures checked by eye |
| SSE through Next dev proxy | Frontend talks to `:8000` directly (CORS) for the stream |
| 3-day timeline | Phases 2 and 5 are the big ones; Hindi, Playwright and custom-group polish are cut first if late |

## 10. Assumptions (logged)
1. Run tables in `backend/data/runs.sqlite`, not in the provided DB (the provided test enforces 12 tables).
2. The run resumes when **no plan row is Pending**. "Approve all 70%+" approves rows with confidence ≥ 0.70 and every
   individual row ≥ 0.70. The rest need a ✓/✗.
3. Ruplekha stays in Individual attention whether the ASM keeps or drops her survey (the flag is the reason).
4. Hindi: the survey toggle and nudges support हिन्दी (6 KN distributors are on file as Hindi). CTAs and chat do EN/BN,
   and HI only via fixtures.
5. Voice notes are a voice-note bubble + card text. No audio.
6. "Apply to next scheme" saves personas to `next_cycle_profiles` and previews the next nudge. It does not start a new run.
7. One active run at a time; Reset replaces it (old runs kept for the determinism test only).
8. Company-wide numbers (1,104 / 14 territories) appear only as context. The loop runs for Kolkata North only.

## 11. Decisions from Rishi (2026-10-15)
1. **Maa Tara's best time = "around 1 pm"** (follows the data). `DEMO_SCRIPT.md` will say "Bengali voice note, around 1 pm".
2. **LLM:** hand-written EN + BN fixtures for every prompt now. Live inference credentials come later. Default
   `LLM_MODE=mock` until then.
3. **Python:** the existing conda env `pmo-intel-engine` (Python 3.11: fastapi, pydantic 2, langgraph, google-genai, openai,
   pyyaml, pytest). No new installs: SSE uses FastAPI `StreamingResponse` (no sse-starlette). `tasks.py` uses that
   interpreter (override with `EMAMI_PYTHON`). `Makefile` is a thin wrapper.
4. **No git operations.** Rishi handles git.
5. **Look and feel:** Tailwind CSS plus the `motion` library for smooth, simple motion: page/card fade-up with stagger,
   number count-ups, bar fills, a sliding pill for the view toggle and active nav, layout transitions on expand/collapse.
   Durations 200–500 ms with gentle easing, and `prefers-reduced-motion` is honoured. Motion never adds clutter.

## 12. Done / Next

### Phase 0 — done (2026-10-15)
- `tasks.py` (seed/dev/test/demo) + `Makefile` wrapper, `.env.example` (`LLM_MODE=mock` default), `.gitignore`.
- Backend: `app/main.py` (`/health`, CORS), `app/config.py`, `app/simulation/clock.py` (labels, stages, loop steps),
  `app/models.py`, `/sim/state` **stub** (Day 0; Phase 2 replaces it). `tests/test_scaffold.py` checks weekdays
  (Day 0 Thu 1 Oct … Day 30 Sat 31 Oct).
- Frontend: Next.js 16.4 (App Router, Turbopack, Cache Components on), Tailwind v4 tokens in `globals.css`, fonts via
  `next/font` (Instrument Sans, Bricolage Grotesque, Noto Sans Bengali/Devanagari), `motion`, `lucide-react`, `recharts`.
  Shell: navy sidebar (sliding active pill, approvals badge, live scheme-status card, user card), mobile drawer below
  1024 px, `PageHeader` with the ASM / Distributor toggle, shared `LoopStepper` (animated connectors, pulsing current
  step, links to page@day), cards (`Tile` with count-up, `Pill`, `ProgressBar`, `AiPanel`), page fade transition
  (`app/template.tsx`), `lib/api.ts`, `lib/sim.tsx` (`useSim`, `useViewDay` for `?day=`), `lib/format.ts`.
- All 7 routes render with placeholders laid out like their renders.
- `python tasks.py test`: 12 pytest pass (incl. the 9 provided data tests), lint clean, build clean.

**Notes**
- The provided generator prints `₹`, which crashes on a Windows cp1252 console. `tasks.py` sets `PYTHONUTF8=1`.
- The provided `test_deterministic` leaves a SQLite handle open inside a TemporaryDirectory, and Windows can't delete
  it. `tests/conftest.py` sets `ignore_cleanup_errors=True` on Windows only. The provided test is unchanged.
- The shell falls back to an offline Day-0 state if the API is down ("Simulator offline"), so the UI never breaks.

### Phase 1 — done (2026-10-15)
_(Phase 0/1 notes kept below for history.)_
- `app/db/conn.py`: main DB = `runs.sqlite`; the Day-0 world is ATTACHed **read-only** as `world` (writes raise).
- `app/rules/loader.py`: yaml → models for all four rule files.
- `app/engines/cohorts.py` (Cohort agent): parses the `when` expressions in `cohorts.yaml` (OR of ANDs, `otherwise`)
  and builds reasons from the clauses that held. It reproduces **all 1,104** stored cohorts *and* reason strings
  exactly. Display order, plain copy and colours come from the renders.
- `app/db/queries.py` + routers: `GET /territory/summary`, `GET /cohorts`, `GET /cohorts/{name}/distributors`,
  `GET /distributors?q=&cohort=`, `GET /distributors/{id}` (Kolkata North only; others 404). All accept `?day=`,
  which is echoed back (Day-0 data doesn't change with the day yet).
- Tests: `test_cohorts.py` (engine = provided assignments + reasons; KN counts 14/22/19/18/13; Monsoon join
  93/68/21/39/0 %), `test_world_api.py` (₹18.4 Cr, +9.2 %, 31 %, 39 joined, Maa Tara 360, Annapurna English on file),
  `test_no_leak.py` (no trait column, `scripted_*` value or note in any response; only `simulation/traits.py` may name
  the table). **22 pass.** `tasks.py seed` regenerates byte-identical data.
- Frontend: Cohorts page wired to real data. Five cohort cards (count-up, animated "Joined last scheme" bar, sliding
  selection ring), members table (≤ 7 + "Show all", reasons, last scheme, language), Distributor 360 (billing FYTD,
  October target, why this cohort, last 3 schemes, 6-month billing bars, and a "What we've learned" panel that shows only
  what's on file on Day 0). Selection lives in the URL (`?cohort=&id=`). `lib/useApi.ts` keeps previous data on screen
  while the next request loads.

**Assumptions added**
9. On Day 0 the cohort table shows *Why this cohort · Last scheme · Language*. From Phase 5 it switches to the render's
   *Replied on Day 0 · Festive Scheme · Language* once the run has data.
10. "Custom group" (render 2 and 4) is built in Phase 4 with the approval matrix, then also surfaced on this page.

### Phase 2 — done (2026-10-15)
**Backend**
- `db/schema.sql`: all run tables (+ `asm_calls`, `chat_messages`, `next_cycle_profiles`; `events.feed`/`agent`).
  WAL on `main` only (the world DB stays read-only).
- `simulation/`: `clock.py`, `scenarios.py`, `traits.py` (the only reader of the hidden traits), `behaviour.py`
  (spec §3, one RNG stream per seed:distributor:purpose, anchor overrides), `text_bank.yaml` (EN/BN comments tagged by
  theme + junk), `engine.py` (reset / advance / next stage / gate / decisions / state / counters / feed),
  `player.py` (server-side Play/Pause, stops at the gate, resumes after approval).
- `engines/`: `sanity_checks.py`, `cta_planner.py`, `persona.py`, `results.py` (all plain modules).
- `db/run_queries.py`: `facts(con, run_id, day)` is the single place every time filter lives.
- `agents/nodes.py` + `agents/loop_graph.py`: LangGraph `start → day0 | plan | execute` (see §5); every node writes `events`.
- `llm/client.py`: live / record / replay / mock, cache by hash, 8 s timeout + 1 retry, 429 back-off, **refuses any
  hidden-trait key**. Prompts `nudge_message`, `cta_message`. Hand-written EN/BN/HI fixtures (15 nudges + reminder,
  6 CTAs × 3 languages).
- API: `/sim/{state,scenarios,reset,advance,play,pause,speed,autopilot,events,stream}`,
  `/plan/rows/{id}/decision`, `/plan/approve-high-confidence`, `/survey/flags/{id}`.
- `scripts/sim_report.py` (one run's calibration numbers), `scripts/find_seed.py` (searches 1–200).

**Calibration (default seed 42, typical, approve-all)** — inside every §8 band:
replied 60 · median first reply 4.9 h · red-flagged 4 (amber 6) · intents 27 / 10 / 12 / 7 / 4 · joined by Day 7 = 27 ·
by Day 30 = 51 (59 %) · beat prediction 41 · Individual attention 11 · personas: 3 → Bengali, 8 prefer a call,
16 evening, 10 visit. Plan: Growth builders · Scheme-hesitant (voice note, 70 %) · Individual attention · At-risk
(Rahul calls) · Champions · Dormant (re-send, 91 %), which is the same six rows as render 4.

**Tests (41 pass, `LLM_MODE=mock`, temp DB):** determinism (hash of all run tables), calibration bands, every anchor's
script (intent, timing, flags, plan row, delivery language, join day/path, sales, persona), reset sends nothing, gate
→ approve → continue, autopilot, next-stage walk, numbers at a day = SQL up to that day, reject lowers joins, Drop is
time-aware, scenarios move numbers but not anchors, only catalogue CTA codes, sanity rules, LLM modes + leak guard, no
hidden trait in any prompt of a full run or any API response.

**Frontend:** Simulation tab = Controls (Play/Pause, Next stage, speed 1/2/5 s, Autopilot switch, Scenario, Seed,
Reset) · Loop (compact stepper, big sim clock, Day 0→30 track, approval banner → approval matrix, six counters
with count-up) · Live feed (newest first, agent pills, slide-in). The shell now follows `/sim/stream` (SSE) with a
5 s poll fallback; the sidebar status card and Approvals badge are live. Checked with Playwright: Reset → Play → gate
→ approve → resumes → Day 30, with no console errors.

**Assumptions added**
11. **Default seed is 42, not 7.** Seed 7 lands outside the bands (Individual attention 15, beat prediction 34);
    42 is the closest of the 30+ in-band seeds. Every number in the renders is still "± a few".
12. The plan is built and the gate sits at **Day 7 10:00**, as in the spec's feed example. Autopilot approves at the
    same moment.
13. Event feed paging is by sim time (`after_day`) plus `since_id`, because events are written ahead and revealed by
    the clock. `/sim/events?since_id=` alone would miss them.
14. **Individual attention:** asked for Rahul, red-flagged and key accounts not joined always qualify. At-risk
    non-responders qualify only for a **visit**, when billing is down 4+ months and the account is class A/B.
    Otherwise they stay in the At-risk row ("Rahul calls"). This gives about 10 people, as in render 4.
15. A cohort's "explain" need counts both explainers together. The voice note is chosen when most askers speak Bengali.
16. Persona "ASM visit" goes to people who ignored the nudge, the reminder *and* the re-send, or whose visit didn't
    land. Sarkar & Sons' best time comes out as ~12 pm (scripted reply 26 h after 10:00), not the "evenings" in §4.
17. The persona `next_time` line is rule-built for now. LLM polish (`persona_next_time`) comes with Phase 6.
18. Replies arrive front-loaded (≈ 56 by Day 2, as the trait model's medians imply). Render 3's bar curve
    (38 → 62) will show the real curve.

### Phase 3 — done (2026-10-15)
- `GET /survey/questions?cohort=&lang=&day=` gives the cohort's nudge, filled for its first member (Scheme-hesitant →
  Maa Tara, ₹7.8 L), and Q1–Q7 with the cohort's Q6 options. English / বাংলা / हिन्दी come from hand-written
  `app/content/survey_i18n.yaml` (Hindi quick replies are gender-neutral); stored values stay the five English intents.
  The ASM's name is written in script in BN/HI messages (রাহুল / राहुल).
- `GET /survey/results?day=`: cumulative replies D0–D7, median reply time, Clean / Check / Flagged, the red list
  (Keep/Drop) and the amber "to check" list, intents among answers that count + no reply + left out, the four
  ratings as % 4–5, and top comment themes. Red answers stay out of every number until kept; Drop is permanent.
- `engines/themes.py` + prompt `comment_themes`: the LLM only labels each comment with an allowed theme and code
  counts. With no LLM (or a skipped comment) it falls back to the tag the simulated comment carries.
- Page (render 3): "What we sent, by cohort" (sliding language and cohort pills, nudge box, Q1 chips, Q2–Q7 with tags)
  · Replies by day (reminder bar orange, latest blue) · Sanity checks · Flagged answers (Keep / Drop, "N more to check")
  · What would you like to do? · How they rate the scheme + comment chips. Time-aware (`?day=`); Keep/Drop are only
  enabled on the live day. Cohort and language live in the URL.
- Tests: `test_survey.py` (per cohort/language, values vs labels, numbers add up to 86, day filtering, Keep brings
  Ruplekha back into the counts). **44 pass.**

**Changed:** replies that land after someone's usual window now carry over to the next morning 25 % of the time
(spec's "nudged into their active window"). Without it 51 of 60 replied on Day 0 and the chart was flat; now it's
45 → 54 → 57 → 60. Seed 42 is still inside every band (median reply 5.6 h).

**Assumptions added**
19. "What would you like to do?" counts only answers that count; flagged ones show as "N flagged answers left out".
    It sums to 86 with "No reply yet" once they're kept.
20. Ratings come out lower than render 3 (clear 45 %, helps 55 %, target 38 %, payouts 27 %), because the spec's rating
    model centres payouts on 3.2. These are honest numbers from the simulator.

### Phase 4 — done (2026-10-15)
- `GET /plan?day=`: top rows (cohorts, custom groups, Individual attention with its people), each with follow-up,
  reason, LLM "why", confidence, priority, status as of the day shown, and an EN/BN message preview filled for one
  member. Not ready before Day 7 10:00.
- `POST /plan/rows/{id}/decision` (the Individual-attention row decides everyone; people can then differ),
  `POST /plan/approve-high-confidence`, `POST /plan/custom-group`, `GET /plan/candidates`, `GET /plan/catalogue`.
- Custom groups: an event stores the hand-picked ids and an optional CTA from the catalogue (or "let Emami AI pick").
  The plan is rebuilt and **keeps every decision already made**; members leave their cohort row.
- **Decisions stay open until the clock moves.** Day 8–30 is played out when Play / Next stage takes the clock past
  Day 7 10:00, not on the last click, so Rahul can change his mind. Approving everything while playing resumes the run.
- Page (render 4): summary strip + **Approve all 70%+** + **Custom group** · one compact table (Group · Who ·
  Follow-up · Confidence · Priority · ✓/✗) · click a follow-up to read the message (EN + বাংলা + why) · "Hide individual
  attention · N people" with 5 shown + "+N more · names" · footnote on confidence/priority. Custom-group dialog
  (search, checkboxes, name, follow-up). The sidebar badge counts rows still waiting.
- Tests: `test_plan.py` (rows per spec, time-aware, 70%+ then the rest, Individual row cascades, custom group keeps
  decisions and moves members, unknown CTA refused, decisions changeable until the clock moves). **49 pass.**

**Assumptions added**
21. Custom groups are built at the Day-7 plan (a CTA, not a separate Day-0 nudge). The Cohorts page's "+ Custom group"
    links here.
22. Confidence colour: green ≥ 70 %, orange below, as in render 4.

### Phase 5 — done (2026-10-15)
**LLM.** Rishi's Gemini key is in the git-ignored `.env` (`LLM_MODE=replay`, `LLM_CHAT_LIVE=true`,
`GEMINI_MODEL=gemini-2.5-flash`, thinking off → 2–3 s). The free tier allows **5 requests/minute**, so:
- the client has a **429 circuit breaker** (no calls until Gemini's retry time; instant fallback);
- chat classifies by keywords first and calls the LLM only for messages keywords can't place;
- `complete(…, fallback=…)`: text built in code from computed numbers is the fallback, so numbers are always right;
- **reply guard**: an LLM chat reply is used only if it's one clean paragraph with exactly the amounts the tool returned
  (Gemini sometimes garbles ₹ — caught and replaced by the code-built reply).
Gemini needs a timeout of at least 10 s (now 15 s). `tests/` always run in `mock`.

**Backend**
- `GET /command?day=`: greeting by sim time · 4 tiles · "Needs you today" ≤ 3, rule-built by stage (send nudge →
  approve plan / review flags / call who asked → booked calls → results) · Emami AI 3 lines (code drafts from numbers,
  `first_week_summary` only polishes) · progress by cohort.
- `GET /chat/scenarios`, `GET /chat/{id}?day=` (WhatsApp conversation built from run tables: nudge + card, quick
  replies, tapped reply, survey card, desk auto-replies, reminder, Day-8 follow-up (voice note bubble), calls, JOIN,
  joined confirmation, live chat), `POST /chat/{id}/message`.
- `agents/chat_graph.py`: LangGraph classify → act → reply. Tools in code: `enrol_me` (joins now; refreshes the
  Day-30 sales row if it exists), `get_my_target`, `explain_scheme`, `request_asm_call` (books Rahul tomorrow 11:00).
  Replies in the language they wrote in (EN / বাংলা / हिन्दी).
- "Behind the conversation" = that distributor's events + the approval of their plan row, merged into plain lines
  with agent badges. The 360 adds Festive status, "This scheme" milestones, the persona so far (language, best time,
  replies, prefers, what worked; "Next time" from Day 30), and this cycle's follow-up. The cohort list and members
  gained time-aware fields (Day-0 reply, flagged, joined day, learned language).
- Tests: `test_distributor_view.py` (Maa Tara's conversation and timeline, scenarios, live chat join in Bengali, chat
  helpers + guard, Command centre by stage, 360 time-aware). **55 pass.**

**Frontend**
- Command centre (render 1), Distributor view (render 5: scenarios + any distributor, profile card, phone with
  WhatsApp bubbles, voice note, typing indicator, live "Type as distributor", agent timeline), Cohorts + 360 now
  follow the cycle (render 2: "Joined Festive", "Replied on Day 0 · Festive Scheme · Language (was English)", "This
  scheme", "What we've learned", "Next time"). Checked in a real browser, no console errors.

**Assumptions added**
23. A chat "JOIN" enrols the distributor at that moment (and replaces a later join the run had planned). This is a
    presenter action, like an approval; determinism holds for the same inputs.
24. On Day 0 before 10:00 the chat is closed (nothing has been sent yet).
25. Emami AI's lines are code-written from the numbers; the LLM may only rephrase them (same count, same numbers).

**Open question (parked for the partner review, 2026-10-15):** should a "JOIN" typed in the Distributor view
enrol the distributor on the spot (current behaviour, assumption 23), or stay a demo-only reply that doesn't change
the run? Untouched until Rishi decides.

### Phase 6 — done (2026-10-15)
- `GET /results?day=`: not ready before Day 30 (shows joined so far). From Day 30: headline ("51 of 86 joined. Up
  from 45% last time."), the five questions from `engines/results.py` (joined by cohort vs Monsoon · beat / fell short +
  October sales vs normal for joiners and non-joiners · same day / first week / after follow-up / never + median reply
  and join times · Day-0 asks incl. no reply · join rate per follow-up), "What we learned" (3 lines written by code
  from the numbers — biggest cohort move and its follow-up, weakest follow-up, sales — then polished by
  `results_summary`), and four persona chips.
- `POST /results/apply` saves all 86 learned personas into `next_cycle_profiles` (idempotent), logs a PERSONA event,
  and returns a preview for Maa Tara, Annapurna and Nabadiganta. `GET /results/applied` re-reads it.
- The persona agent now polishes each "Next time" line with `persona_next_time`. A guard keeps the rule-built line if
  the LLM changes the language or the time.
- Page (render 6): the five cards with animated bars, "What we learned" panel with chips and **Apply to the next
  scheme** → "Saved for the next scheme" + three "Next time" lines that link to each 360.
- Tests: `test_results.py` (not ready before Day 30, every card adds up to 86, rates sorted, apply saves and is
  idempotent, the next-time guard). **59 pass.** Checked in a real browser, no console errors.

Seed 42 at Day 30: 51 joined (59 %) vs 45 % · 41 beat the prediction, 10 fell short · joiners +18 % vs normal,
non-joiners −1 % · same day 18 / first week 9 / after follow-up 24 / never 35 · voice note 64 %, quick reminder 56 %,
call/visit 28 %, re-send 9 % · 3 → Bengali, 8 prefer a call, 14 evening, 10 visit.

**Assumptions added**
26. "Apply to next scheme" saves the profiles and shows what the next nudge will do. It does **not** start a new run or
    change this run, so a Reset still reproduces the calibrated demo. (Next step if wanted: a new run's nudge agent
    reads `next_cycle_profiles` for language and send time.)
27. "What did they ask for on Day 0?" counts every reply, including flagged ones (it's what they said). The Survey
    page's intent card leaves red-flagged answers out until kept.

### Next: Phase 7 — Demo hardening (on Rishi's go).
