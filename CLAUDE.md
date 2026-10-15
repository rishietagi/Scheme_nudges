# CLAUDE.md — Emami Distributor Experience Platform (POC)

Closed-loop distributor-experience POC for Emami, built by KPMG: **nudge + survey → sanity checks → cohort CTAs →
ASM approval → Day-30 results → persona update → next cycle.** Synthetic data only. Demo-first. **Keep it simple.**

**Start here in a new session:** `docs/logs.md` (where things stand, machine setup, decisions, gotchas, next steps),
then `docs/PLAN.md` (design + per-phase notes + assumptions). Append a dated entry to `docs/logs.md` at the end of
every session.

**Before any work, read, in order:** `docs/PROJECT_CONTEXT.md` · `docs/SIMULATION_SPEC.md` · `docs/DATA_DICTIONARY.md` ·
`backend/app/rules/*.yaml` · every image in `docs/renders/`.

**Provided — build on these, don't rewrite them:** the Day-0 dataset (`backend/data/`), its generator
(`backend/scripts/generate_data.py`) and tests (`backend/tests/test_generated_data.py`), and the rule files
(`cohorts.yaml`, `survey.yaml`, `sanity_checks.yaml`, `ctas.yaml`). If something needs more Day-0 data, extend the generator,
re-run `make seed`, keep the tests green. Never hand-edit the SQLite.

## Ground rules
- **Plan before code.** Each phase: plan in plan mode, wait for approval, implement. Keep `docs/PLAN.md` updated.
- **Simple beats complete.** Plain words, one main number per card, ≤ 5 items before "Show all", no jargon, no walls of data.
  If a screen needs a paragraph to explain, cut it. Match the renders' calm density.
- **One engine, time-aware pages.** The loop simulator (`SIMULATION_SPEC.md`) produces everything after Day 0. Every page reads
  the active run at the current sim day (`?day=`).
- **Hidden truth stays hidden.** `sim_traits` is for the simulator only — never in an API response, the UI or an LLM prompt.
- **Code does every number** (rates, confidence, priority, lifts, sanity flags). The LLM writes text only, and picks nothing
  outside the CTA catalogue.
- **Synthetic data only**; simulated things are labelled (WhatsApp, DMS). No real Emami product names or people.
- **The demo must never break.** Every LLM call has a cached/fixture fallback; the full loop runs in `LLM_MODE=mock` offline.
- Match the renders for layout, hierarchy, copy and colour (1440 px comps; responsive to ~1024 px, readable on a phone).
- Small and readable: no auth, no microservices, no Docker unless asked. Ambiguity → choose what serves the 8-minute demo,
  note it in `docs/PLAN.md` → "Assumptions".

## Stack
| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind CSS, `lucide-react` icons, `recharts`, `next/font` (Bricolage Grotesque for display/numbers, Instrument Sans for UI) |
| Backend | Python 3.11+, FastAPI, Pydantic v2, LangGraph (agent orchestration), SSE for the simulation stream |
| Data | SQLite (`backend/data/emami_dx.sqlite`) + run tables created by the app |
| LLM | Provider-agnostic wrapper. Default **Gemini Flash** via `google-genai` (free tier OK for dev, synthetic data only); alternate OpenAI-compatible (GPT-4o-mini / Azure) via env |
| Tests | `pytest` (backend), `npm run build` + `npm run lint`, optional Playwright smoke test of every page |
| Python env | `uv` if available, else `python -m venv .venv` + pip |

## Repo layout (target)
```
emami-dx-poc/
├── CLAUDE.md · .env.example · Makefile
├── docs/
│   ├── PROJECT_CONTEXT.md · SIMULATION_SPEC.md · DATA_DICTIONARY.md      # PROVIDED
│   ├── PLAN.md · DEMO_SCRIPT.md                                          # you create
│   └── renders/                                                          # 01…06 PNGs from Rishi
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/            # routers: sim, territory, cohorts, distributors, survey, plan (approval matrix), results, chat
│   │   ├── simulation/     # engine.py (clock, events, behaviour model), scenarios.py, text_bank.yaml
│   │   ├── engines/        # sanity_checks.py, cta_planner.py, results.py, persona.py (real product logic)
│   │   ├── agents/         # langgraph graph: nudge, survey, cta, execution, results, persona agents
│   │   ├── llm/            # client.py (provider + modes), prompts/, cache/, fixtures/
│   │   ├── rules/          # cohorts.yaml · survey.yaml · sanity_checks.yaml · ctas.yaml   (PROVIDED)
│   │   ├── db/             # schema for run tables, queries
│   │   └── models.py
│   ├── scripts/generate_data.py   # PROVIDED
│   ├── data/                      # PROVIDED (regenerate with make seed)
│   └── tests/                     # PROVIDED test_generated_data.py + yours
└── frontend/
    ├── app/                # / (command centre) · /cohorts · /survey · /approvals · /distributor · /results · /simulation
    ├── components/         # shell/, loop-stepper/, cards/, charts/, phone/, chat/
    ├── lib/api.ts
    └── public/brand/       # emami-logo.png (transparent), emami-logo-reverse.png (white wordmark, for dark bg)
```

## Commands (create these)
- `make seed` — `python backend/scripts/generate_data.py`
- `make dev` — FastAPI (`:8000`) + Next.js (`:3000`)
- `make test` — pytest (incl. data + simulator calibration tests) + frontend build/lint
- `make demo` — reset the simulator to the default seed with `LLM_MODE=replay`

## Environment (`.env.example`)
```
LLM_PROVIDER=gemini            # gemini | openai
GEMINI_API_KEY=
GEMINI_MODEL=                  # current Flash model id from Google AI Studio
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=
LLM_MODE=record                # live | record | replay | mock
SIM_SEED=7
SIM_SCENARIO=typical           # typical | low_response | messy_survey | great_uptake
SIM_AUTOPILOT=false            # true = auto-approve the CTA plan at Day 7
```

## LLM modes (`backend/app/llm/client.py`)
- `live` call the provider · `record` call and cache by hash(prompt_id + inputs) · `replay` cache only, fixture on miss
  (**use for the board demo**) · `mock` fixtures only, no network (tests/offline).
- One entry point, e.g. `complete(prompt_id, inputs, schema)` → validated Pydantic object (structured JSON).
- Prompts in `app/llm/prompts/<prompt_id>.md`: role, inputs, allowed CTA catalogue where relevant, output schema, language rules
  (Bengali/English/Hindi). Prompt ids at least: `nudge_message`, `cta_message`, `comment_themes`, `chat_reply`,
  `results_summary`, `persona_next_time`.
- Timeout + one retry, then cache/fixture. Handle 429 gracefully. Only synthetic data to free-tier APIs.

## Design tokens (from the renders)
| Token | Hex | Use |
|---|---|---|
| `--emami-blue` | `#005DA0` | primary, links, active, Champions |
| `--navy-900` | `#0A2647` | sidebar |
| `--navy-800` | `#0B3B70` | AI summary panels, phone chat header |
| `--orange` | `#F4751A` | primary CTA, accents, Scheme-hesitant (text on it `#13232A`) |
| `--orange-light` | `#FFB067` | accent text on navy |
| `--cyan` | `#2E9BD6` | Growth builders |
| `--red` | `#E8452C` | At-risk, red flags |
| `--amber` | `#C2560F` on `#FEEBDD` | "Check" flags |
| `--grey-cohort` | `#94A3B8` | Dormant |
| `--green-text` | `#0B6B4E` on `#E3F4EC` | positive, approved, clean |
| `--ink` / `--muted` | `#13232A` / `#5B6672` | text (muted ≥ 4.5:1) |
| `--bg` / `--card-border` | `#F4F6FA` / `#E3E8EC` | page / cards |
Cards: white, 16 px radius, 1 px border, soft shadow. Pills 999 px. No gradient washes, no emoji.

## Conventions
- Money in ₹ lakh (`_l`); `formatINR()` for Cr/L. Dates from the sim clock: Day 0 = Thu 1 Oct 2026; show "Day 9 · Sat 10 Oct" (check weekdays).
- Intents are exactly the five quick-reply labels in `survey.yaml`; CTA codes exactly those in `ctas.yaml`; flag codes exactly those in `sanity_checks.yaml`.
- Backend: Pydantic in/out on every endpoint; every agent/engine step writes an `events` row (the "Behind the conversation" and Simulation feeds read it).
- Frontend: one `lib/api.ts`; a shared `<LoopStepper day=…/>` on main pages; accessibility (real buttons/links, labels, focus, 44 px targets).
- Copy: short, plain, specific; reuse the renders' wording.

## Definition of done (per phase)
1. `make test` passes; no TS errors; no console errors on touched pages.
2. Pages match their renders in structure and feel.
3. The demo path for the phase works with `LLM_MODE=replay` (and the simulator in `mock`) with the network off.
4. `docs/PLAN.md` updated (done, assumptions, open questions). Then stop and summarise for Rishi.
