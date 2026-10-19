# Project Context — Emami Distributor Experience Platform (POC) · closed-loop edition

> **Updates:**
> - **2026-10-16:** the survey is generated per cohort and the product is a platform (`docs/PLAN.md` §13–§14).
> - **2026-10-19:** cohorts are a configurable 2×2 of business potential × performance (Invest / Expand · Replace /
>   Reassess · Protect · Exit / Watchlist), the Cohorts page is the landing page, and next best actions can be
>   accepted, modified or rejected (§15).
>
> Where this file and PLAN §13–§15 disagree, the PLAN wins.

> Read this fully before planning. `CLAUDE.md` holds the working rules; this file holds the *what* and *why*.
> Also read: `docs/SIMULATION_SPEC.md` (the loop simulator — the engine behind the whole demo), `docs/DATA_DICTIONARY.md`,
> the rule files in `backend/app/rules/`, and the renders in `docs/renders/`.
> **Where a render and this file disagree, this file wins.** Numbers on screen always come from the data/simulator.

---

## 1. What this is

KPMG Digital Solutions is building a **2–3 day proof of concept** for **Emami** (Indian FMCG): a **closed-loop distributor
experience system** for trade schemes. It will be shown to Emami leadership, possibly at board level. Synthetic data only;
WhatsApp, DMS and CRM are simulated.

**The pitch in one line:** *Every scheme gets a nudge, a survey, a targeted follow-up and a 30-day check — and the system
remembers what worked for each distributor next time.*

**Design principle — keep it simple.** Easy to read, easy to use, not everything at once. Plain words ("joined the scheme",
"needs a call"), one main number per card, at most ~5 items in a list before "Show all". If a screen needs a paragraph to
explain, it's too busy.

## 2. The problem
- Schemes are announced to every distributor, but many don't understand them, don't join, or join late.
- Nobody asks distributors what they need, and when they do, answers aren't checked or acted on.
- Follow-ups are generic, so the same distributors miss out every cycle.
- Nobody measures 30 days later who joined, who hit their numbers, and what made the difference.

## 3. The closed loop (one scheme cycle)

The scheme (**Festive Scheme · Oct 2026**) has already been communicated to all distributors. Day 0 = **Thu 1 Oct 2026**.

| When | Step | What happens | Who decides |
|---|---|---|---|
| Day 0 | **Nudge + survey** | One WhatsApp message **per cohort** with quick replies: *I've enrolled · I'll enrol · Explain again · Explain in Bengali · Talk to my ASM*, then 5 short questions + optional comment (`rules/survey.yaml`). | Code picks cohort; LLM writes the wording |
| Day 3 | Reminder | One automatic reminder to non-responders at their usual reply time. | Code |
| Days 0–7 | **Survey dashboard + sanity checks** | Responses come in; every response is checked (`rules/sanity_checks.yaml`): under 30 s, same rating for everything, < 3 answers, contradictions, duplicates, junk text. Red-flagged answers stay out of the numbers until the ASM keeps or drops them. | Code; ASM reviews flags |
| Day 7 | **Call-to-action plan** | One CTA **per cohort** for members not yet enrolled, plus an **Individual attention** list with personal CTAs (asked for ASM, key accounts not enrolled, flagged answers, At-risk with no reply). The ASM can move any distributor to a personal CTA. (`rules/ctas.yaml`) | Code picks; LLM writes; ASM approves |
| Day 7 | **Approval matrix** | Rows = cohorts + individual attention. Columns = **who · CTA · confidence · priority · approve/reject**. Nothing else. | **ASM** |
| Day 8 | CTAs sent | Each CTA goes out in the distributor's preferred language (from the persona). | Code |
| Days 8–30 | Enrolments + sales | Enrolments, ASM calls and October sales accrue. | Simulator |
| Day 30 | **Results** | Joined vs didn't · of those who joined, who hit the predicted sales boost · how fast they reacted · what they picked · who never replied · which CTA worked. In plain words. | Code computes; LLM writes the 3-line summary |
| Day 30 | **Persona update** | Each distributor's persona learns: real language, reply time, reply speed, wants ASM, what worked → used for the next cycle's nudge. | Code; LLM writes the one-line "next time" note |

## 4. Demo world (keep consistent across data, simulator and UI)

- **Rahul Sen**, ASM, **Kolkata North**, **86 distributors**. The app is logged in as Rahul. Company-wide: 1,104 distributors, 14 territories.
- Monthly billing is complete through **Sep 2026**; Indian FY (Apr–Mar). Currency INR (₹18.4 Cr, ₹6.2 L).
- UI in English; distributor messages in **Bengali / English** (Hindi optional). Product name: **Emami — Distributor Experience Platform**; the AI is **"Emami AI"**; WhatsApp sender **"Emami Distributor Desk"**.

### Kolkata North on Day 0 (from the generated data — tests verify)
| Metric | Value |
|---|---|
| Cohorts | Champions 14 · Growth builders 22 · Scheme-hesitant 19 · At-risk 18 · Dormant 13 |
| Secondary billing FYTD | ₹18.4 Cr, +9.2% YoY · focus-SKU share 31% |
| Joined the last scheme (Monsoon) | 39 of 86 = 45% — the bar the Festive loop should beat |
| Festive Scheme | Every distributor has a personal target, a baseline October forecast and a **predicted sales boost if they join** (`scheme_targets`) |

### Expected loop outcome with the default simulator seed (calibration targets — ± a few)
| Stage | Target |
|---|---|
| Replied by Day 7 | ~62 of 86 (≈72%) · median reply time ≈ 4 h |
| Sanity checks | ≈ 54 clean · 4 check (amber) · 4 flagged (red) |
| Day-0 intents (of replies) | I've enrolled ≈ 26 · I'll enrol ≈ 10 · Explain again ≈ 12 · Explain in Bengali ≈ 7 · Talk to my ASM ≈ 7 |
| Joined by Day 7 | ≈ 27 (31%) |
| Joined by Day 30 | ≈ 55 (64%) vs 45% last scheme |
| Hit predicted sales boost | ≈ 41 of the 55 who joined |
| Persona changes | ≈ 5 switched to Bengali (of the 7 whose real language differs from the file) · 7 prefer an ASM call · ~21 reply best in the evening · ~11 non-responders to try an ASM visit next time |

### Anchor distributors (scripted in `sim_traits` so the demo story is always the same)
| Distributor | Cohort | Day-0 behaviour | What happens |
|---|---|---|---|
| **Maa Tara Distributors** (DST-0001), Biswajit Das, Barasat | Scheme-hesitant · A | Replies in 3 h: **Explain in Bengali** | Key account, so she lands in Individual attention with a personal **voice explainer in Bengali** on Day 8; joins Day 9. Persona: Bengali voice note, mornings. |
| **Sarkar & Sons** (DST-0002), Subhas Sarkar | Scheme-hesitant | Replies after 26 h: **Explain again**; comment asks for a short Bengali voice note | Joins Day 10 after the explainer. Persona: Bengali voice note, evenings. |
| **Ruplekha Traders** (DST-0006) | Scheme-hesitant | Survey in **19 s, all 5s, says "I've enrolled" but isn't** | **Red-flagged** (too fast, same rating, contradiction) → individual attention → ASM call → joins Day 15. |
| **Pal Brothers** (DST-0005), key account (A) | Scheme-hesitant | **Talk to my ASM** in 1.5 h; wants better margins | Individual attention; ASM call; **doesn't join** — logged as "margin, not scheme". |
| **Annapurna Distributors** (DST-0007) | Scheme-hesitant | On file as English but asks **Explain in Bengali** | Joins Day 9. **Persona switches her to Bengali.** |
| **Debnath Agencies** (DST-0004) | Scheme-hesitant | **I'll enrol** | Joins Day 5, before any CTA. |
| **Shree Durga Agencies** (DST-0008) | Growth builders · A | **I've enrolled** within the hour | Beats his predicted sales boost. |
| **Bose Distribution** (DST-0009) | Champions · A | **I've enrolled** within 25 min | Hits the stretch slab. |
| **Ganguly Traders** (DST-0010) | At-risk | **No reply** (billing down 4 months) | Individual attention → ASM visit; still no join. |
| **Nabadiganta Enterprises** (DST-0011) | Dormant | **No reply**, ignores the reminder | Stays out; persona: "try an ASM visit, not WhatsApp". |
Product names are generic (e.g. "Cooling Oil 200 ml"). People and businesses are fictional.

## 5. Data

**Provided, Day-0 world** (`backend/data/emami_dx.sqlite`, 12 tables — see `docs/DATA_DICTIONARY.md`): hierarchy, distributors,
SKUs, monthly primary/secondary billing (Apr 2025–Sep 2026), schemes, last-3-scheme history, Festive targets + predictions,
derived features, cohort assignments, and **hidden `sim_traits`** (simulator only — never shown in the UI or sent to the LLM).

**Written at runtime by the simulator** (tables you create, all keyed by `run_id`): `loop_runs`, `nudges`, `survey_responses`
(with `started_at`, `submitted_at`, `survey_seconds`, answers), `sanity_flags`, `cta_plan` (cohort + individual rows),
`approvals`, `cta_deliveries`, `enrolments` (with day and path: before nudge / after nudge / after CTA / after ASM),
`october_sales` (actual vs predicted), `personas` (learned preferences), `events` (timeline/log). Schema in `SIMULATION_SPEC.md`.

## 6. Cohorts (rules, as of Day 0) — `rules/cohorts.yaml`

| Order | Cohort | Rule | KN |
|---|---|---|---|
| 1 | Dormant | No invoice in the last 30 days | 13 |
| 2 | At-risk | Billing down 2+ months in a row OR SKU range down 5+/month vs last quarter | 18 |
| 3 | Champions | YoY > 10% AND focus-SKU share > 35% | 14 |
| 4 | Scheme-hesitant | YoY ≥ 0 AND joined ≤ 1 of the last 3 schemes | 19 |
| 5 | Growth builders | Everyone else (healthy, regular scheme joiner) | 22 |

Cohorts are fixed at Day 0 for the whole cycle. The ASM can also build a **custom group** (any hand-picked distributors) and
give it its own nudge or CTA; custom groups appear as extra rows in the approval matrix.

## 7. Survey and sanity checks

- Questions: `rules/survey.yaml`. Q1 = intent (quick reply), Q2–Q5 = 1–5 ratings (clear · helps business · confident of target ·
  happy with payouts), Q6 = "what would help" with **options per cohort**, Q7 optional comment. Keep the cohort-tailored question
  view the client liked.
- Survey dashboard (plain words): replied / not replied, reply-time curve, intent breakdown, the 4 ratings as "% who said 4 or 5",
  top themes from comments (LLM), and a **Sanity checks** card: Clean · Check · Flagged, with a short list of flagged responses,
  each showing its reason ("Filled in 19 seconds") and **Keep / Drop** buttons. All survey numbers exclude red flags unless kept.

## 8. Call-to-action plan and the approval matrix — `rules/ctas.yaml`

- CTA types: Slab progress · Quick reminder · Simple explainer · Voice explainer (in their language) · ASM call · Re-nudge.
- **One CTA per cohort** (for members not enrolled by Day 7), chosen in code from the cohort's answers; **personal CTAs** for the
  individual-attention list. The LLM only writes the message text and a one-line "why".
- **Confidence** (code): share of the cohort's not-enrolled members whose answers point to that CTA × share of clean responses.
- **Priority** (code): High / Medium / Low by revenue at stake (sum of predicted uplift of not-enrolled members).
- **Approval matrix** = one compact table: *Group · Who (count) · Call to action · Confidence · Priority · ✓ / ✗*.
  Individual attention is one more row that expands to a short list (name · reason · personal CTA · ✓ / ✗).
  "Approve all high-confidence" button. **No channel, owner, expected-impact or approval-type columns.**

## 9. Day-30 results (plain words)

Answer five questions, one card each:
1. **Did they join?** 55 of 86 joined (64%) — last scheme 45%. By cohort.
2. **Did joining pay off?** Of the 55 who joined, 41 hit their predicted sales boost, 14 fell short. Joined vs didn't: October sales vs forecast.
3. **How fast did they react?** Joined the same day / within the first week / after the follow-up / never. Median reply time.
4. **What did they ask for?** Count per quick reply (enrolled · will enrol · explain again · Bengali · ASM) and **no reply**.
5. **Which follow-up worked?** Join rate after each CTA type.
Plus a 3-line "What we learned" (LLM over computed numbers) and "Apply to next scheme" (writes persona updates).

## 10. Persona — what the system learns per distributor

Shown on the Distributor 360 as **"What we've learned"**: preferred language (learned vs on file), best time to message,
reply speed, prefers (WhatsApp text / voice note / ASM call), what worked last time, and a one-line **"Next time"** rule
(e.g. *"Send in Bengali as a voice note around 10 am"*). The next cycle's nudge uses it automatically.

## 11. Agents — code vs LLM

| Agent | Code does | LLM does |
|---|---|---|
| Cohort agent | Applies `cohorts.yaml` | — |
| Nudge agent | Picks template per cohort, language from persona | Writes the cohort message (EN/BN/HI) |
| Survey agent | Collects answers, runs sanity checks, computes all survey numbers | Groups comments into themes |
| CTA agent | Chooses CTA per cohort, individual list, confidence, priority | Writes CTA text + one-line why |
| Execution agent | Sends (simulated), records deliveries/replies/enrolments | Handles free-text replies in the chat (intent + answer) |
| Results agent | Joined, hit-prediction, speed, intents, CTA win rates | 3-line plain summary |
| Persona agent | Updates learned fields from behaviour | One-line "Next time" note |

The LLM never computes numbers, never invents CTA types, never sees `sim_traits`.

## 12. Screens (renders in `docs/renders/`)

Shell: navy sidebar (Emami logo, Distributor Experience Platform), nav, user card; top bar with **ASM workspace | Distributor view**;
"Concept prototype · synthetic data" badge. A **loop stepper** (Day 0 Nudge → Day 7 Plan → Day 8 Send → Day 30 Results) sits at
the top of the main pages and shows where the current scheme cycle is.

1. **Command centre** — loop stepper, 4 tiles (Replied · Joined so far · Waiting for your approval · Need individual attention),
   "Needs you today" (≤ 3 items), cohort mix.
2. **Cohorts & Distributor 360** — cohort cards + list; 360 with **What we've learned** (persona) and this cycle's journey.
3. **Survey** — questions per cohort (keep as is) + results + **Sanity checks** card with Keep/Drop.
4. **Approval matrix** — the compact table from §8.
5. **Distributor view** — phone mockup: Day-0 nudge with quick replies and the survey inside WhatsApp, Day-8 CTA, enrolment;
   scenarios Maa Tara (Bengali), Ruplekha (flagged), Pal Brothers (ASM). "Behind the conversation" timeline on the side.
   A "Type as distributor" box answers live (LLM + tools).
6. **Day-30 results** — the five cards from §9.
7. **Simulation** — not rendered; built from `docs/SIMULATION_SPEC.md`. Runs the whole loop for the demo.

Render files (exported by Rishi into `docs/renders/`): `01-command-centre.png` · `02-cohorts-360.png` · `03-survey.png` ·
`04-approval-matrix.png` · `05-distributor-view.png` · `06-day30-results.png`.

## 13. Demo script (~8 min)
1. **Simulation** tab → Reset → Play to Day 0: nudges go out by cohort.
2. Fast-forward to Day 7 → **Survey**: 62 replied; open **Sanity checks** → Ruplekha flagged (19 s, all 5s) → Drop.
3. **Approval matrix** → one CTA per cohort + individual attention (Pal Brothers, Ruplekha, Ganguly) → Approve all.
4. **Distributor view** → Maa Tara: asked for Bengali on Day 0 → Bengali voice note Day 8 → joins Day 9. Type a live message.
5. Fast-forward to Day 30 → **Results**: 55 joined vs 45% last time; 41 beat the prediction; what worked.
6. **Distributor 360** → Maa Tara's persona: "Next time: Bengali voice note, 10 am". Close the loop: "Apply to next scheme".

## 14. People
**Ashish** (KPMG Partner) — agent structure, human approval, business case · **Devika** (Emami) — requirements, validation, wants
conceptual flexibility · **Akshay** (KPMG) — business case on distributor productivity · **Rishi** — building the POC.

## 15. Out of scope
Real integrations (DMS, CRM, WhatsApp Business API), auth, production hosting, real data, ML cohorting, pricing.
