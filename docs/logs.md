# Working log — Emami Distributor Experience Platform (POC)

> **Read this first in a new session**, then `docs/PLAN.md` (full design, per-phase "done" notes, assumptions 1–27),
> then the docs listed in `CLAUDE.md`. This file is the hand-off: where things stand, how the machine is set up,
> decisions Rishi made, gotchas, and what's next. Append a dated entry whenever a session ends.

---

## Where things stand (2026-10-19, end of session 3 — see the session-3 entry below; §15 in PLAN)

- **Phases 0–6 done, plus the partner-review changes** (PLAN.md §13). The demo now shows four cohorts on a configurable
  performance 2×2: Grow with · Develop · Invest in · Reassess (KN 36 / 15 / 9 / 26 after the §14 market benchmark). It also has two Set-up pages
  (Cohort rules, Survey generator), a generated per-cohort survey that the simulated loop answers, "next best action"
  framing with cohort + survey drivers, and a Next-quarter card on Results.
- `python tasks.py test` → **66 backend tests pass**, lint + build clean (10 routes). Every page checked in a real
  browser, and `presenter_flow.py` passes with no console errors. The renders still show the old 5 cohorts; the app now
  differs from them on purpose.
- Only **Phase 7 (demo hardening)** is left. Wait for Rishi's go, and for Devika's deck (the real cohort definitions
  and CX questions).
- App servers are **stopped** (end of session 2). Start with `python tasks.py dev`. If you edit backend code while a
  page holds the SSE stream open, restart the API by port, because `--reload` hangs.
- Open questions from session 2b, both offered and waiting on Rishi:
  - Priority could become expected uplift (₹ at stake × confidence) or use fixed ₹ thresholds instead of thirds.
  - Confidence could apply the sanity-check factor only to members who replied.
  - Other use cases: group survey results by use case, and add non-scheme next best actions.

### Open questions (waiting on Rishi / partner review)
0. **Devika's deck**: the real four cohort definitions / 2×2 and the CX questions per bucket → edit `cohorts.yaml` and
   `survey_bank.yaml` (both are config; no code change expected).
1. **Chat "JOIN"** — typing "JOIN" / "আমি যোগ দিতে চাই" in the Distributor view enrols the distributor *at that moment*
   (replaces any later join the run planned; refreshes their Day-30 sales row). Keep, or make chat replies demo-only?
   (PLAN assumption 23.) Untouched until he decides.
2. **"Apply to next scheme"** only saves profiles (`next_cycle_profiles`) and previews them; it doesn't start a new run.
   Option offered: a new run's nudge agent could use the learned language/send time (would change calibration after Apply).
3. Ratings on the Survey page are lower than render 3 (clear 45 %, payouts 27 %) because the spec's rating model centres
   payouts on 3.2 — offered to tune if he wants render-like numbers.
4. Phase 7 recording: keep Gemini's wording or the hand-written fixtures (Gemini text was rougher in tests).

---

## Machine / environment (Windows 11, Rishi's laptop)

| Thing | Value |
|---|---|
| Repo | `C:\Users\rishi\Desktop\distributor` — a git repo, but **never run git** (Rishi does git himself) |
| Python | conda env **`pmo-intel-engine`** (`C:\miniconda\envs\pmo-intel-engine\python.exe`, Py 3.11) — has fastapi, pydantic 2, langgraph 1.2.6, google-genai, openai, pyyaml, pytest. Don't pip-install into it without asking. |
| Runner | `python tasks.py seed|dev|test|demo` (no `make`/`uv` on this machine; `Makefile` just wraps tasks.py). tasks.py sets `PYTHONUTF8=1`. |
| Node | v24, Next.js **16.4** (App Router, Turbopack, Cache Components on — wrap `useSearchParams` users in Suspense; read `frontend/node_modules/next/dist/docs/` before Next API changes), Tailwind v4, `motion` 14, lucide-react 1.57, recharts 3 |
| Browser checks | Playwright lives in the **`mmsa`** conda env (`C:\miniconda\envs\mmsa\python.exe`), browsers installed. Scripts: `backend/scripts/ui/shot.py` (screenshots + console errors), `presenter_flow.py` (Reset → Play → gate → approve → Day 30). Run with `PYTHONUTF8=1`. |
| LLM | Gemini key is in the git-ignored **`.env` only** — never copy it anywhere. `.env`: `LLM_MODE=replay`, `LLM_CHAT_LIVE=true`, `GEMINI_MODEL=gemini-2.5-flash`. Tests always force `mock`. |

### Gotchas learned the hard way
- **Stopping servers:** kill by port, not by name (`netstat -ano | grep ":3000 .*LISTEN"` → `taskkill //F //T //PID <pid>`).
  Killing the `npx` wrapper leaves the Node child running; `taskkill /IM node.exe` would kill Rishi's other Node apps.
- **Headless Chrome** `--virtual-time-budget` hangs forever because of the open SSE stream; use Playwright (above).
  Only kill Chrome processes whose command line contains `--headless`.
- Windows console is cp1252: the provided generator prints ₹ → needs `PYTHONUTF8=1` (tasks.py does it).
- Provided `test_deterministic` leaves a SQLite handle open in a TemporaryDirectory → `tests/conftest.py` sets
  `ignore_cleanup_errors=True` on Windows (provided test file untouched). conftest also points `RUNS_DB` at a temp file
  and forces `LLM_MODE=mock`.
- `PRAGMA journal_mode` must be `main.`-scoped (the world DB is attached read-only).
- **Gemini free tier = 5 requests/minute/model**; deadlines must be ≥ 10 s (we use 15 s); `gemini-flash-latest` and
  `gemini-3.5-flash` were overloaded (503) when tried; 2.5-flash with thinking off answers in 2–3 s. Gemini sometimes
  garbles ₹ (`\textsuperscript…U+20B9`, `\nH6.3`) → chat replies go through `chat_graph.safe()`.
- Heredoc + Python `sub()` edits mangle backslashes in regexes — edit regex lines with the Edit tool.
- `useApi` keys include the sim day, so pages refetch as the clock moves; keep previous data on screen (no flash).

---

## Architecture in one screen (details in PLAN.md §0–§8)

- **Two SQLite files:** `backend/data/emami_dx.sqlite` = provided Day-0 world, ATTACHed **read-only** as `world`
  (`test_counts` requires exactly 12 tables). `backend/data/runs.sqlite` = run tables (`db/schema.sql`), git-ignored,
  safe to delete (recreated on start).
- **Compute ahead, reveal by clock:** Reset computes Days 0–7; the plan is built when the clock reaches **Day 7 10:00**
  (`PLAN_AT`); Days 8–30 are computed when the clock moves past the gate (decisions stay changeable until then).
  Every query filters `<= day` via `db/run_queries.facts(con, run_id, day)` — the single place time filtering lives.
- **Hidden traits:** only `app/simulation/traits.py` reads `sim_traits` (test-enforced); `llm/client.complete` refuses
  any trait key.
- **LangGraph:** `agents/loop_graph.py` (start → day0 | plan | execute; state = run_id/step/con; tables are the state)
  and `agents/chat_graph.py` (classify → act → respond; keyword intent first to save quota).
- **LLM:** `complete(prompt_id, inputs, schema, fixture_key, mode, fallback)`; modes live/record/replay/mock; cache in
  `app/llm/cache/`; hand-written EN/BN/HI fixtures in `app/llm/fixtures/`; 429 circuit breaker; `fallback=` lets
  code-built text (with computed numbers) be the answer when there's no LLM. Prompts: nudge_message, cta_message,
  comment_themes, chat_intent, chat_reply, first_week_summary, results_summary, persona_next_time.
- **Default seed 42** (seed 7 missed the bands). `backend/scripts/find_seed.py` / `sim_report.py` re-check calibration.

### Seed 42 numbers (what the demo shows)
_Session 2: same headline numbers with the 4-cohort 2×2. The plan rows are Grow with · Develop (voice note 70 %) ·
Individual attention 11 · Invest in · Reassess (re-send). The dealer score is 3.8; next quarter, 17 change cohort.
Older cohort names below are from session 1._
Day 7: 60 replied (70 %), median 5.6 h · 50 clean / 6 check / 4 flagged (Ruplekha 19 s) · intents 27/10/12/7/4 ·
27 joined (31 %) · plan = Growth builders, Scheme-hesitant (voice note 70 %), Individual attention (11), At-risk, Champions,
Dormant (re-send 91 %) · "Approve all 70%+" leaves Growth builders 31 %, At-risk 51 %, Champions 50 % to click.
Day 30: 51 of 86 joined (59 %) vs 45 % · 41 beat prediction, 10 short · joiners +18 % vs normal, non-joiners −1 % ·
voice note 64 %, quick reminder 56 %, call/visit 28 %, re-send 9 % · personas 3 → Bengali, 8 prefer a call, 14 evening,
10 visit. Maa Tara: Explain in Bengali (13:00) → Bengali voice note Day 8 → joins Day 9 → "Next time: Send the scheme as
a Bengali voice note around 1 pm".

---

## Decisions Rishi made
- 2026-10-15: Maa Tara's best time = **"around 1 pm"** (follow the data, not §13's "10 am").
- 2026-10-15: Hand-written EN/BN fixtures first; he provided a Gemini key later the same day (in `.env`).
- 2026-10-15: Use the existing conda env; **no git operations**.
- 2026-10-15: Tailwind + smooth, simple fluid motion (motion library; respects reduced motion).
- 2026-10-15: Park the chat-JOIN behaviour until the partner review.

---

## Session log

### 2026-10-15 — session 1 (Phases 0–6)
- Read all docs, rules, data and the six renders; wrote `docs/PLAN.md`; Rishi answered the four questions.
- **P0** scaffold: tasks.py/Makefile/.env.example, FastAPI health, Next.js shell (sidebar, toggle, LoopStepper, cards, motion).
- **P1** cohort agent reproduces all 1,104 cohorts + reasons from `cohorts.yaml`; territory/cohort/distributor APIs; Cohorts page.
- **P2** simulator (behaviour model, engines, LangGraph loop, LLM client, SSE player, Simulation tab); calibrated → seed 42.
- **P3** Survey page (cohort/language toggle, replies by day, sanity checks with Keep/Drop, intents, ratings, themes).
  Reply carry-over 25 % so the D0–D7 curve isn't flat.
- **P4** Approval matrix (previews, Individual attention, custom groups that keep decisions, approve all 70%+);
  decisions stay open until the clock moves.
- **P5** Gemini wired (circuit breaker, reply guard); Command centre, Distributor view (WhatsApp phone, live chat,
  agents' timeline), time-aware Cohorts + 360.
- **P6** Day-30 results (five cards, what we learned, chips), Apply to next scheme, LLM-polished "Next time" with guard.
- Gave Rishi demo pointers; he ran the app, then asked to stop it and preserve context (this file).

### 2026-10-16 — session 2 (partner-review changes)
- Rishi shared the meeting notes and screenshots (Copilot summary + KPMG CX survey slides 2, 4–6). He asked for
  cohorts named Invest in / Grow with / Reassess / Develop, with definitions, based on the existing data and
  configurable, and for a configurable survey with must-ask ("pakka") questions.
- His choices: **2×2 = momentum × engagement**; **survey fully live** through the loop.
- Built PLAN.md §13 in five blocks:
  - A: config-driven 2×2 + per-run snapshot + Cohort rules page + Cohorts dashboard;
  - B: CX question bank + Survey generator engine and page;
  - C: generic answers through the simulator, sanity checks, Survey page, phone and 360;
  - D: next-best-action drivers, loop strip, stepper wording, Next-quarter card;
  - E: tests and docs.
- Seed 42 numbers held: 60 replied · 27 by Day 7 · 51 by Day 30 · 41 beat. Every anchor is unchanged.

### Gotchas learned (session 2)
- `uvicorn --reload` hangs while a browser holds the SSE stream open, so code changes don't load. Kill :8000 by port
  and start uvicorn without `--reload`. The helper script used this session lived in the temp dir; recreate it if
  needed.
- After an edit, Next dev can log a one-off hydration warning on the first load (stale server render). Reload and it's
  gone.
- `CountUp` only animates when in view, so full-page Playwright screenshots show 0 for tiles below the fold. That's not
  a bug.
- `runs.sqlite` has a schema version (`PRAGMA user_version` = 3). An older file is rebuilt automatically, and saved
  Set-up edits go with it.
- Bash heredocs that contain `'''` break the tool. Put multi-line Python in a scratch file instead.

### 2026-10-16 — session 2b (FMCG terminology + research-based cohort logic)
- Researched Indian FMCG trade terms and benchmarks (PLAN.md §14 has the sources).
- Distributors now *participate* in schemes: quick replies say "Already participating / Will participate", scheme
  payouts are credit notes, slabs are named, and the app says secondary sales / predicted uplift / no billing.
  Stored values are unchanged.
- Cohort growth floor 0 % → 3 % (FMCG market growth, NielsenIQ Q1 2026). Kolkata North is now 36 / 15 / 9 / 26.
  Seed 42: 60 / 27 / 50 / 41.
- 69 backend tests (new `test_terminology.py`), lint and build are green. `presenter_flow.py` passes, with no console
  errors.
- Prompt wording changed, so the replay cache keys changed. The demo falls back to fixtures until Phase 7 re-records.

### 2026-10-19 — session 3 (potential × performance cohorts, new data, editable actions)
- PLAN.md §15 has the details.
- **Data:** regenerated with a modelled TAM per town, distributor catchments, retailer delivery (OTIF) and four
  performance pillars. Five combined CSVs instead of 12.
- **Cohorts:** Invest / Expand 21 · Replace / Reassess 23 · Protect 21 · Exit / Watchlist 21.
- **Pages:** Cohorts is the landing page, with a 2×2, a scatter and the 360 scorecard. The Command centre is removed.
  Cohort rules has thresholds, weights and pillar targets.
- **Next best actions:** Accept / Modify / Reject, no confidence, priority ⓘ. ⓘ tips across Survey, Results and
  Simulation.
- **Checks:** 72 backend tests, lint and build are green. `presenter_flow.py` now modifies a row through the UI. No
  console errors on any page.
- **Gotchas:**
  - `redirect()` inside `app/page.tsx` breaks Cache Components validation in dev; use `redirects()` in `next.config.ts`.
  - Cohort names contain "/", so cohort routes and plan-row routes use `{name:path}` / `{row_id:path}`, and the
    frontend uses `encodeURIComponent`.
  - Restart `next dev` after editing `next.config.ts`.

## Next
1. Rishi reviews the new pages (Cohort rules, Survey generator, Cohorts, Approvals, Results → Next quarter) and shows
   the partners. Swap in Devika's definitions when they arrive.
2. Then Phase 7 (PLAN.md §1): throttled `record` of demo-path LLM calls (~12 s/call), offline `replay` check,
   `tasks.py demo` resets seed 42, `docs/DEMO_SCRIPT.md` (~8 min, §13), README (≤ 5 setup commands), final polish.
