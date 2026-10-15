# Simulation spec — the closed-loop simulator and the Simulation tab

The demo runs on **one deterministic loop simulator**. It plays a full scheme cycle (Day 0 → Day 30) for Kolkata North,
writes everything to run tables, and every page in the app reads from the **active run at the current sim day**.
The **Simulation tab** is the remote control. There is no render for it — build it from this spec, keep it simple.

---

## 1. Principles
- **Deterministic:** same seed + scenario + ASM decisions → identical results. No wall-clock randomness.
- **Code makes every number.** The LLM only writes text (nudge/CTA wording, theme names, summaries, live chat replies).
  The simulator never needs the LLM to run; in `LLM_MODE=mock` it uses fixture text.
- **Hidden truth stays hidden.** `sim_traits` drives behaviour but is never shown in the UI, returned by the API or sent to
  the LLM. The app must *discover* preferences from behaviour (that's the persona story).
- **Anchors are scripted.** Rows in `sim_traits` with `scripted_*` values override the random model (see PROJECT_CONTEXT §4).
- **Pages are time-aware.** Every data endpoint accepts `?day=` (default = the run's current day) and only returns what was
  known by then.

## 2. Clock and stages

`sim_day` is a float from 0 to 30 (Day 0 = Thu 1 Oct 2026, 00:00). Stages:

| Stage | Sim day | What the engine does |
|---|---|---|
| `NUDGE` | 0.0 | Send the cohort nudge (+ survey) to all 86 at each distributor's usual reply time (default 10:00). |
| `COLLECT` | 0 → 7 | Replies arrive at their reply times; sanity checks run on each as it lands; enrolments from "I've/I'll enrol". |
| `REMINDER` | 3.0 | One reminder to non-responders. |
| `PLAN` | 7.0 | Build the CTA plan (cohort rows + individual attention), confidence, priority. |
| `APPROVAL` | 7.0 | **Pause** until the ASM approves/rejects in the Approval matrix — unless **Autopilot** is on (auto-approve everything at Day 7 10:00). |
| `SEND_CTA` | 8.0 | Deliver approved CTAs in the persona language; ASM calls/visits get scheduled (Day 9–13). |
| `CONVERT` | 8 → 30 | Enrolments after CTAs/calls; October sales accrue. |
| `RESULTS` | 30.0 | Compute Day-30 results. |
| `LEARN` | 30.0 | Update personas; write "Next time" notes. |

## 3. Behaviour model (per distributor, using `sim_traits`; anchors use their `scripted_*` values instead)

Use one `random.Random(f"{seed}:{distributor_id}:{purpose}")` stream per distributor and purpose, so changing one thing
does not reshuffle everyone.

**Reply.** Replies with probability `response_prob`. Reply time = `median_response_hours × lognormal(0, 0.8)` hours after the
nudge, nudged into their `active_window`, capped at Day 7. Non-responders get a second chance after the Day-3 reminder with
probability `0.3 × response_prob`.

**Intent (Q1).** In order: enrol now with prob `enrol_prob_day0` → *I've enrolled*; else with prob `wants_asm_prob` →
*Talk to my ASM*; else if `understanding < 0.45` → *Explain in Bengali* if `true_language == Bengali`, else *Explain again*;
else if `understanding < 0.6` → *Explain again*; else → *I'll enrol*.

**Ratings (Q2–Q5).** Q2 clarity ≈ `1 + 4 × understanding`; Q3 helps business ≈ cohort base (Champions 4.4 … Dormant 2.6);
Q4 confidence ≈ Q3 − 0.4; Q5 payouts ≈ 3.2; each + noise N(0, 0.7), rounded and clipped to 1–5.
**Q6** = the cohort option that matches their intent (e.g. Explain in Bengali → "Explanation in Bengali"), else random.
**Q7** comment with prob 0.35, from a small EN/BN text bank (`backend/app/simulation/text_bank.yaml`, write ~6 per theme;
examples: "Every scheme comes as a long PDF. Just tell me my target." · "স্কিমের নিয়ম খুব জটিল, স্ল্যাব বুঝতে পারি না।"
· "আমার ইনসেনটিভ এখনও পাইনি।"). Language = `true_language` when they reply in their own words.

**Survey time.** Normal: `survey_seconds = 110 × lognormal(0, 0.35)`. **Low-effort** (prob `low_effort_prob`):
seconds 8–28, all ratings identical, 30% answer only 2 questions, comment (if any) is junk ("ok", "....").
2% of replies are submitted twice (DUPLICATE).

**Enrolment before CTAs.** *I've enrolled* → enrolled at reply time (85%); the other 15% say so but aren't →
CONTRADICTION. *I'll enrol* → 60% enrol on a random day 1–6.

**CTA effect (Day 8+).** Each not-enrolled distributor gets their approved CTA (cohort or personal).
- CTA **matches their need** (Explain in Bengali ↔ Voice explainer, delivered in Bengali; Explain again ↔ Simple explainer or Voice explainer;
  asked ASM / key account / At-risk ↔ ASM call; I'll enrol ↔ Quick reminder; no reply ↔ Re-nudge) →
  join prob = `enrol_prob_after_matching_cta`.
- Mismatched CTA → × 0.4. Non-responder with Re-nudge → × 0.45. CTA **rejected** by the ASM → × 0.2 (natural drift).
- Join day = 8 + lognormal(median 2 days) for messages; call day + 1 for ASM calls (calls happen Day 9–13).

**October sales (Day 30).** Joined: hits the prediction with prob `hit_prediction_prob` (× 0.8 if they joined after Day 15) →
actual = `predicted_sales_if_enrolled_l × U(1.00, 1.12)`, else `× U(0.85, 0.99)`. Not joined: `baseline_forecast_l × U(0.92, 1.05)`.

## 4. Engines that run inside the loop (the real product logic — build them as normal modules, the simulator just calls them)
- **Sanity checks** — `rules/sanity_checks.yaml`, run on every response at arrival; red = excluded until ASM *Keep*.
- **CTA planner** — `rules/ctas.yaml`; one CTA per cohort for not-enrolled members, individual-attention rules, confidence,
  priority. Custom groups made by the ASM are planned the same way.
- **Results** — the five Day-30 questions (PROJECT_CONTEXT §9), all SQL/pandas over run tables.
- **Persona updater** (Day 30, and incrementally as behaviour arrives):
  - `language` = Bengali if they chose *Explain in Bengali*, wrote in Bengali, or joined after a Bengali CTA; else on-file.
  - `best_time` = bucket of their reply hour (Morning/Afternoon/Evening); `reply_speed` = Fast (< 2 h) / Normal / Slow (> 24 h) / No reply.
  - `prefers` = ASM call (asked for ASM, or joined after a call) · Voice note (asked for one, or joined after one) · WhatsApp text.
  - `what_worked` = the step right before they joined (nudge / reminder / CTA type / ASM call) or "Nothing yet".
  - `next_time` = one line, rule-built then polished by the LLM: e.g. "Bengali voice note at ~10 am", "Skip WhatsApp — ASM visit".

## 5. Run tables (create in SQLite; every row has `run_id`)
| Table | Key columns |
|---|---|
| `loop_runs` | run_id, seed, scenario, autopilot, scheme_id, current_day, stage, created_at |
| `events` | run_id, sim_day, sim_time, type (NUDGE_SENT, REPLY, FLAG, REMINDER, PLAN_READY, APPROVED, REJECTED, CTA_SENT, ASM_CALL, ENROLLED, RESULTS, PERSONA), distributor_id?, text |
| `nudges` | run_id, distributor_id, cohort, language, sent_at, text |
| `survey_responses` | run_id, response_id, distributor_id, started_at, submitted_at, survey_seconds, q1_intent, q2..q5, q6, q7_text, q7_language, is_duplicate |
| `sanity_flags` | run_id, response_id, code, severity, label, asm_decision (Keep/Drop/null) |
| `cta_plan` | run_id, row_id, group_type (cohort/individual/custom), group_name, distributor_id?, cta_code, text_en, text_bn, members, confidence, priority, reason, status (Pending/Approved/Rejected) |
| `cta_deliveries` | run_id, distributor_id, row_id, cta_code, language, sent_at |
| `enrolments` | run_id, distributor_id, sim_day, path (after_nudge / self / after_cta / after_asm_call) |
| `october_sales` | run_id, distributor_id, baseline_l, predicted_l, actual_l, hit_prediction |
| `personas` | run_id, distributor_id, language, language_changed, best_time, reply_speed, prefers, what_worked, next_time |

## 6. API
```
POST /sim/reset      {seed: 7, scenario: "typical", autopilot: false}   -> new run_id, day 0, stage NUDGE (nothing sent yet)
POST /sim/advance    {to_day: 7.0} | {step: "next_stage"}              -> runs events up to there (stops at APPROVAL if not autopilot)
POST /sim/play       {speed_seconds_per_day: 2}                        -> server ticks; clients follow via the stream
POST /sim/pause
GET  /sim/state                                                         -> run_id, day, stage, counters, waiting_for_approval
GET  /sim/events?since_id=                                              -> event feed
GET  /sim/stream                                                        -> Server-Sent Events: day ticks + new events
```
All page endpoints accept `?run_id=&day=`; default to the active run and its current day.
Approving/rejecting in the Approval matrix writes `cta_plan.status`, emits APPROVED/REJECTED events and lets the run continue.

## 7. The Simulation tab (UI)
One page, three zones, nothing else:
- **Controls (left, narrow):** Reset · Play / Pause · Next stage · Speed (1 day = 1 s / 2 s / 5 s) · Scenario (Typical,
  Low response, Messy survey, Great uptake) · Seed · Autopilot approvals (toggle).
- **Loop (centre):** the same loop stepper as the other pages, a big "Day 12 · Tue 13 Oct" and six live counters:
  Sent · Replied · Flagged · Joined · Follow-ups sent · Beat prediction.
- **Live feed (right):** newest first, plain sentences, e.g.
  "Day 0 · 10:00 — Nudge sent to 19 Scheme-hesitant distributors (14 in Bengali)" ·
  "Day 0 · 13:05 — Maa Tara Distributors asked for an explanation in Bengali" ·
  "Day 0 · 10:12 — Ruplekha Traders' survey flagged: 19 seconds, same rating everywhere" ·
  "Day 7 · 10:00 — Follow-up plan ready: 5 cohort CTAs, 10 individual. Waiting for Rahul's approval".
- When the run pauses for approval: a single banner **"Waiting for your approval → Open approval matrix"**.
- Each stage chip in the stepper links to the page that shows it (Survey, Approval matrix, Results) **at that day**.

Scenarios: `typical` (traits as generated) · `low_response` (response_prob × 0.6) · `messy_survey` (low_effort_prob × 3) ·
`great_uptake` (all enrol probs × 1.2, capped at 0.98). Anchors stay scripted in every scenario.

## 8. Calibration targets (default: seed 7, scenario typical, autopilot approve-all)
| Metric | Target | Tolerance |
|---|---|---|
| Replied by Day 7 | 62 / 86 | ± 4 |
| Red-flagged replies | 4 | 2–7 |
| Intents (of replies) | enrolled 26 · will enrol 10 · explain again 12 · Bengali 7 · ASM 7 | ± 4 each |
| Joined by Day 7 | 27 | ± 4 |
| Joined by Day 30 | 55 | ± 5 |
| Beat prediction (of joined) | 41 | ± 5 |
| Median reply time | ≈ 4 h | 2–6 h |
If the default seed lands outside the band, pick another seed (search 1–200) rather than tuning the model to the decimal.
The renders use these target numbers; small differences on screen are fine.

## 9. Tests (must pass in `LLM_MODE=mock`, network off)
- Same seed/scenario/decisions → identical run tables (hash compare).
- Default run lands inside every calibration band.
- Every anchor behaves exactly as scripted (intent, timing, flags, join day, persona outcome).
- No API response or LLM prompt contains any `sim_traits` column.
- Page numbers = SQL over run tables at that `day` (e.g. Survey at Day 3 shows only replies with `submitted_at <= Day 3`).
- Rejecting a cohort CTA lowers that cohort's joins vs approving it (same seed).
