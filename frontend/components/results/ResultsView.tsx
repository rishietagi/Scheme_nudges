"use client";

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useState } from "react";
import { ArrowRight, CheckCheck, Lightbulb, RefreshCw } from "lucide-react";
import { api, type AppliedProfile, type NextQuarter, type ResultsData, type ResultsView as View } from "@/lib/api";
import { COHORT_HEX } from "@/lib/cohorts";
import { useViewDay } from "@/lib/sim";
import { useApi } from "@/lib/useApi";
import { Card, ProgressBar } from "@/components/cards/Card";
import { CountUp, EASE, Stagger, StaggerItem } from "@/components/motion/Motion";
import { InfoTip } from "@/components/cards/InfoTip";
import { LoopStepper } from "@/components/loop-stepper/LoopStepper";
import { PageHeader } from "@/components/shell/PageHeader";

export function ResultsView() {
  const { day } = useViewDay();
  const res = useApi(`results:${day.toFixed(2)}`, () => api.results(day));
  const v = res.data;

  return (
    <>
      <PageHeader
        eyebrow={`${v?.results_day_label ?? "Day 30 · Sat 31 Oct"} · Q3 cycle results · use case: Festive Scheme`}
        title={v?.ready && v.headline ? v.headline : "Results arrive on Day 30"}
      />
      <LoopStepper />
      {!v ? null : !v.ready || !v.results ? (
        <Card className="grid min-h-60 place-items-center p-8 text-center">
          <div>
            <p className="font-display text-[19px] font-semibold text-ink">Results arrive on {v.results_day_label}</p>
            <p className="mt-1 text-[15px] text-muted">
              {v.joined_so_far} of {v.total} have joined so far.{" "}
              <Link href="/simulation" className="font-semibold text-emami-blue hover:underline">
                Run the loop to Day 30
              </Link>
            </p>
          </div>
        </Card>
      ) : (
        <Stagger className="grid gap-5 lg:grid-cols-2">
          <StaggerItem>
            <Joined r={v.results} />
          </StaggerItem>
          <StaggerItem>
            <PaidOff r={v.results} />
          </StaggerItem>
          <StaggerItem>
            <Speed r={v.results} />
          </StaggerItem>
          <StaggerItem>
            <Asked r={v.results} />
          </StaggerItem>
          <StaggerItem>
            <Worked r={v.results} />
          </StaggerItem>
          <StaggerItem>
            <Learned v={v} />
          </StaggerItem>
          {v.next_quarter && (
            <StaggerItem className="lg:col-span-2">
              <NextQuarterCard q={v.next_quarter} />
            </StaggerItem>
          )}
        </Stagger>
      )}
    </>
  );
}

function Q({ n, title, tip, children }: { n: number; title: string; tip?: React.ReactNode; children: React.ReactNode }) {
  return (
    <Card className="h-full p-6">
      <h2 className="flex items-center gap-3 font-display text-[20px] font-semibold text-ink">
        <span className="grid size-8 place-items-center rounded-lg bg-navy-800 text-[14px] text-white">{n}</span>
        {title}
        {tip && (
          <InfoTip label={`How "${title}" is worked out`} align="left">
            {tip}
          </InfoTip>
        )}
      </h2>
      <div className="mt-4">{children}</div>
    </Card>
  );
}

function Joined({ r }: { r: ResultsData }) {
  const pct = Math.round((100 * r.joined) / r.total);
  return (
    <Q
      n={1}
      title="Did they participate?"
      tip="Distributors recorded as participating in the Festive Scheme in the DMS (simulated) by Day 30, against those who took part in the last scheme (Monsoon). By cohort as set on Day 0."
    >
      <p className="flex items-baseline gap-2">
        <CountUp value={r.joined} className="font-display text-[52px] font-semibold leading-none text-emami-blue tabular" />
        <span className="text-[17px] text-muted">
          of {r.total} participating · <span className="font-semibold text-green-text">{pct}%</span>
        </span>
      </p>
      <p className="mt-3 text-[14px] text-muted">
        Last scheme (Monsoon): {r.last_scheme_joined} participated · {Math.round((100 * r.last_scheme_joined) / r.total)}%
      </p>
      <ul className="mt-3 space-y-2.5">
        {r.joined_by_cohort.map((c) => (
          <li key={c.cohort} className="grid grid-cols-[130px_1fr_56px] items-center gap-3 text-[15px]">
            <span className="text-ink">{c.cohort}</span>
            <ProgressBar value={c.joined / c.total} color={COHORT_HEX[c.color]} className="h-2.5" />
            <span className="text-right font-semibold text-ink tabular">
              {c.joined} / {c.total}
            </span>
          </li>
        ))}
      </ul>
    </Q>
  );
}

function lift(x: number | null): string {
  return x === null ? "–" : `${x >= 0 ? "+" : ""}${Math.round(x * 100)}%`;
}

function PaidOff({ r }: { r: ResultsData }) {
  const share = r.joined ? r.beat_prediction / r.joined : 0;
  return (
    <Q
      n={2}
      title="Did participating pay off?"
      tip="Predicted uplift = the October sales forecast if they participate (from the scheme plan) vs their baseline forecast if they don't. 'Beat' = actual October secondary sales at or above that prediction. The two boxes compare actual sales to the baseline for participants and non-participants."
    >
      <p className="flex items-baseline gap-2">
        <CountUp value={r.beat_prediction} className="font-display text-[52px] font-semibold leading-none text-green-text tabular" />
        <span className="text-[17px] text-muted">of {r.joined} beat their predicted uplift</span>
      </p>
      <div className="mt-5 flex h-3 overflow-hidden rounded-full bg-[#F8C79F]">
        <motion.div
          className="h-full origin-left bg-green-text"
          style={{ width: `${share * 100}%` }}
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 0.8, ease: EASE }}
        />
      </div>
      <p className="mt-2 flex justify-between text-[14px] text-muted">
        <span>{r.beat_prediction} beat it</span>
        <span>{r.fell_short} fell short</span>
      </p>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-green-soft p-4">
          <p className="text-[13px] text-green-text">Participating · October secondary sales vs baseline</p>
          <p className="mt-1 font-display text-[30px] font-semibold text-green-text">{lift(r.sales_lift_joined)}</p>
        </div>
        <div className="rounded-xl bg-bg p-4">
          <p className="text-[13px] text-muted">Not participating</p>
          <p className="mt-1 font-display text-[30px] font-semibold text-ink">{lift(r.sales_lift_not_joined)}</p>
        </div>
      </div>
    </Q>
  );
}

const SPEED_COLOR = { "Same day": "var(--green-text)", "First week": "var(--cyan)", "After follow-up": "var(--orange)", Never: "#CBD3DC" } as const;

function Speed({ r }: { r: ResultsData }) {
  const keys = Object.keys(SPEED_COLOR) as (keyof typeof SPEED_COLOR)[];
  return (
    <Q
      n={3}
      title="How fast did they react?"
      tip="When each distributor started participating: on Day 0, in the first week (before the actions went out), after the Day-8 action, or not at all."
    >
      <div className="flex h-4 overflow-hidden rounded-full" role="img" aria-label="Started participating the same day, in the first week, after the follow-up, or never">
        {keys.map((k, i) => (
          <motion.div
            key={k}
            style={{ backgroundColor: SPEED_COLOR[k] }}
            initial={{ width: 0 }}
            animate={{ width: `${(100 * r.speed[k]) / r.total}%` }}
            transition={{ duration: 0.7, ease: EASE, delay: i * 0.08 }}
          />
        ))}
      </div>
      <ul className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 text-[15px]">
        {keys.map((k) => (
          <li key={k} className="flex items-center gap-2.5">
            <span className="size-3 rounded-[4px]" style={{ backgroundColor: SPEED_COLOR[k] }} aria-hidden />
            <span className="flex-1 text-ink">{k}</span>
            <span className="font-semibold text-ink tabular">{r.speed[k]}</span>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-[14px] leading-relaxed text-muted">
        First replies came in a median of <span className="font-semibold text-ink">{r.median_first_reply_hours} hours</span>; participation after the
        action took a median of <span className="font-semibold text-ink">{r.median_join_days_after_follow_up} days</span>.
      </p>
    </Q>
  );
}

const ASK_COLOR: Record<string, string> = {
  "I've enrolled": "var(--green-text)",
  "I'll enrol": "var(--cyan)",
  "Explain again": "var(--orange)",
  "Explain in Bengali": "var(--orange)",
  "Talk to my ASM": "var(--emami-blue)",
  "No reply": "var(--grey-cohort)",
};

function Asked({ r }: { r: ResultsData }) {
  return (
    <Q
      n={4}
      title="What did they ask for on Day 0?"
      tip="The quick reply each distributor tapped in the Day-0 survey (every reply, flagged ones included — it's what they said). 'No reply' never answered."
    >
      <ul className="space-y-2.5">
        {Object.entries(r.asked).map(([k, n]) => (
          <li key={k} className="grid grid-cols-[150px_1fr_36px] items-center gap-3 text-[15px]">
            <span className="text-ink">{r.asked_labels?.[k] ?? k}</span>
            <ProgressBar value={n / r.total} color={ASK_COLOR[k]} className="h-2.5" />
            <span className="text-right font-semibold text-ink tabular">{n}</span>
          </li>
        ))}
      </ul>
    </Q>
  );
}

function rateTone(x: number): string {
  if (x >= 0.6) return "text-green-text";
  if (x >= 0.3) return "text-amber";
  return "text-red";
}

function Worked({ r }: { r: ResultsData }) {
  return (
    <Q
      n={5}
      title="Which action worked?"
      tip="Of everyone who received an action on Day 8 (including actions you modified), the share who then started participating. Calls and visits from Rahul count as one action."
    >
      <ul>
        {r.follow_ups.map((f) => (
          <li key={f.cta_code} className="grid grid-cols-[1fr_auto_56px] items-center gap-4 border-b border-card-border py-3.5 text-[15px] last:border-0">
            <span className="text-ink">{f.label}</span>
            <span className="text-[14px] text-muted tabular">
              {f.joined} of {f.received} participating
            </span>
            <span className={`text-right font-semibold tabular ${rateTone(f.rate)}`}>{Math.round(f.rate * 100)}%</span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-[14px] text-muted">Share of people who got that action and then started participating.</p>
    </Q>
  );
}

function Learned({ v }: { v: View }) {
  const [applied, setApplied] = useState<AppliedProfile[] | null>(null);
  const [busy, setBusy] = useState(false);
  const saved = useApi(v.applied ? "applied" : null, api.applied);
  const preview = applied ?? (v.applied ? saved.data ?? null : null);

  async function apply() {
    setBusy(true);
    try {
      setApplied(await api.applyToNext());
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="h-full rounded-[var(--radius-card)] bg-navy-800 p-6 text-white shadow-[var(--shadow-card)]">
      <p className="flex items-center gap-2 text-[13px] font-semibold uppercase tracking-[0.1em] text-orange-light">
        <Lightbulb className="size-4" aria-hidden /> What we learned
      </p>
      <div className="mt-3 space-y-3 text-[16px] leading-relaxed text-white/90">
        {v.learned.map((l, i) => (
          <motion.p key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE, delay: 0.1 + i * 0.12 }}>
            {l.text}
          </motion.p>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {v.chips.map((c) => (
          <div key={c.label} className="rounded-xl bg-white/[0.08] px-4 py-3 text-[15px]">
            <span className="font-display text-[20px] font-semibold text-orange-light">{c.value}</span> {c.label}
          </div>
        ))}
      </div>
      <AnimatePresence mode="wait">
        {preview ? (
          <motion.div key="done" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE }} className="mt-5">
            <p className="flex items-center gap-2 text-[15px] font-semibold text-[#9BE3C3]">
              <CheckCheck className="size-5" aria-hidden /> Saved for the next cycle · every distributor&apos;s profile and cohort
            </p>
            <ul className="mt-3 space-y-2">
              {preview.map((p) => (
                <li key={p.distributor_id} className="rounded-xl bg-white/[0.06] px-4 py-3">
                  <Link href={`/cohorts?cohort=${encodeURIComponent(p.cohort)}&id=${p.distributor_id}`} className="block hover:underline">
                    <span className="block text-[14px] text-white/70">{p.name}</span>
                    <span className="block text-[15px]">
                      <span className="font-semibold text-orange-light">Next time: </span>
                      {p.next_time}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </motion.div>
        ) : (
          <motion.button
            key="apply"
            type="button"
            whileTap={{ scale: 0.97 }}
            onClick={apply}
            disabled={busy}
            className="mt-5 flex min-h-12 items-center gap-2 rounded-xl bg-orange px-5 text-[16px] font-semibold text-ink hover:brightness-105 disabled:opacity-60"
          >
            <ArrowRight className="size-5" aria-hidden />
            Apply to the next cycle
          </motion.button>
        )}
      </AnimatePresence>
    </section>
  );
}

/** The loop closes: cohorts re-set from October's performance, and the dealer score each cohort starts the next quarter on. */
function NextQuarterCard({ q }: { q: NextQuarter }) {
  return (
    <Card className="p-6">
      <div id="next-quarter" className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 font-display text-[19px] font-semibold text-ink">
            <RefreshCw className="size-4 text-emami-blue" aria-hidden /> Next quarter starts here
            <InfoTip label="How cohorts are refreshed" align="left">
              The same cohort rules, re-run on data moved on by one cycle: October joins sales growth, and qualifying in the Festive
              Scheme counts towards scheme qualification. Business potential and delivery stay as they were. Dealer score = the
              average answer to &quot;Overall, how easy is Emami to do business with?&quot; (1–5).
            </InfoTip>
          </h2>
          <p className="mt-0.5 text-[14px] text-muted">Cohorts re-set from October&apos;s performance · dealer score is the bar to beat</p>
        </div>
        {q.dealer_score !== null && (
          <span className="rounded-xl bg-navy-800 px-4 py-2 text-white">
            <span className="font-display text-[24px] font-semibold tabular">{q.dealer_score.toFixed(1)}</span>
            <span className="text-[13px] text-white/70"> / 5 dealer score</span>
          </span>
        )}
      </div>
      <div className="mt-5 grid gap-6 lg:grid-cols-2">
        <table className="w-full text-[14px]">
          <thead>
            <tr className="text-left text-[12px] font-semibold uppercase tracking-[0.08em] text-muted">
              <th scope="col" className="pb-2">Cohort</th>
              <th scope="col" className="pb-2 text-right">This quarter</th>
              <th scope="col" className="pb-2 text-right">Next</th>
              <th scope="col" className="pb-2 text-right">Dealer score</th>
            </tr>
          </thead>
          <tbody>
            {q.cohorts.map((c) => (
              <tr key={c.name} className="border-t border-card-border">
                <td className="py-2.5">
                  <span className="flex items-center gap-2 font-medium text-ink">
                    <span className="size-2.5 rounded-[3px]" style={{ backgroundColor: COHORT_HEX[c.color] }} aria-hidden />
                    {c.name}
                  </span>
                </td>
                <td className="py-2.5 text-right tabular text-muted">{c.now}</td>
                <td className="py-2.5 text-right font-semibold tabular text-ink">
                  {c.next}
                  {c.next !== c.now && (
                    <span className={`ml-1.5 text-[12px] ${c.next > c.now === (c.name === "Invest / Expand" || c.name === "Protect") ? "text-green-text" : "text-amber"}`}>
                      {c.next > c.now ? "+" : ""}
                      {c.next - c.now}
                    </span>
                  )}
                </td>
                <td className="py-2.5 text-right tabular text-ink">{c.dealer_score?.toFixed(1) ?? "–"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div>
          <h3 className="text-[14px] font-semibold text-ink">{q.moved} distributors change cohort</h3>
          <ul className="mt-1">
            {q.moves.slice(0, 4).map((m) => (
              <li key={`${m.from_cohort}-${m.to_cohort}`} className="border-b border-card-border py-2 text-[14px] last:border-0">
                <span className="flex items-center gap-1.5 font-medium text-ink">
                  {m.count} · {m.from_cohort} <ArrowRight className="size-3.5 text-muted" aria-hidden /> {m.to_cohort}
                </span>
                <span className="text-[13px] text-muted">
                  {m.names.join(", ")}
                  {m.count > m.names.length ? ` and ${m.count - m.names.length} more` : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}
