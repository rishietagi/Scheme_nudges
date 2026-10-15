"use client";

import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis } from "recharts";
import { ChevronDown, Flag } from "lucide-react";
import type { FlagItem, SurveyResults } from "@/lib/api";
import { Card, CardTitle, ProgressBar } from "@/components/cards/Card";
import { CountUp, EASE } from "@/components/motion/Motion";

/** Cumulative replies D0–D7. Reminder day in orange, the latest day in Emami blue. */
export function RepliesByDay({ r }: { r: SurveyResults }) {
  const last = r.replies_by_day.length - 1;
  const data = Array.from({ length: 8 }, (_, i) => ({ d: `D${i}`, v: r.replies_by_day[i] ?? null }));
  return (
    <Card className="p-6">
      <CardTitle action={<span className="text-[13px] text-muted">reminder on D{r.reminder_day}</span>}>Replies by day</CardTitle>
      <div className="mt-4 h-44" aria-label={`Replies so far: ${r.replied} of ${r.total}`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 20, right: 0, bottom: 0, left: 0 }} barCategoryGap="12%">
            <XAxis dataKey="d" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "var(--muted)" }} />
            <Bar dataKey="v" radius={[6, 6, 2, 2]} animationDuration={700}>
              {data.map((_, i) => (
                <Cell key={i} fill={i === last ? "var(--emami-blue)" : i === r.reminder_day ? "var(--orange)" : "#CFE0EF"} />
              ))}
              <LabelList dataKey="v" position="top" style={{ fontSize: 12, fill: "var(--muted)" }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-[14px] text-muted">
        Median reply time <span className="font-semibold text-ink">{r.median_reply_hours ?? "–"} hours</span>
      </p>
    </Card>
  );
}

export function SanityCard({ r }: { r: SurveyResults }) {
  const tiles = [
    { label: "Clean", value: r.sanity.clean, cls: "bg-green-soft text-green-text" },
    { label: "Check", value: r.sanity.check, cls: "bg-orange-soft text-amber" },
    { label: "Flagged", value: r.sanity.flagged, cls: "bg-red-soft text-red" },
  ];
  return (
    <Card className="p-6">
      <CardTitle action={<Flag className="size-5 text-red" aria-hidden />}>Sanity checks</CardTitle>
      <div className="mt-4 grid grid-cols-3 gap-3">
        {tiles.map((t) => (
          <div key={t.label} className={`rounded-xl px-3 py-3 text-center ${t.cls}`}>
            <CountUp value={t.value} className="block font-display text-[28px] font-semibold leading-none tabular" />
            <span className="mt-1 block text-[13px]">{t.label}</span>
          </div>
        ))}
      </div>
      <p className="mt-3 text-[14px] text-muted">Flagged answers are left out of the numbers until you keep them.</p>
    </Card>
  );
}

const FIRST = 4;

export function FlaggedAnswers({
  r,
  live,
  onDecide,
}: {
  r: SurveyResults;
  live: boolean;
  onDecide: (item: FlagItem, d: "Keep" | "Drop") => Promise<void>;
}) {
  const [showChecks, setShowChecks] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [all, setAll] = useState(false);
  const shown = all ? r.flagged : r.flagged.slice(0, FIRST);

  async function decide(item: FlagItem, d: "Keep" | "Drop") {
    setBusy(item.response_id);
    try {
      await onDecide(item, d);
    } finally {
      setBusy(null);
    }
  }

  if (!r.flagged.length && !r.to_check.length) return null;
  return (
    <Card className="p-6">
      <CardTitle>Flagged answers</CardTitle>
      <ul className="mt-2">
        <AnimatePresence initial={false}>
          {shown.map((f) => (
            <motion.li
              key={f.response_id}
              layout
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: EASE }}
              className="flex flex-wrap items-center gap-3 border-b border-card-border py-3 last:border-0"
            >
              <div className="min-w-0 flex-1">
                <p className={`text-[15px] font-semibold ${f.decision === "Drop" ? "text-muted line-through" : "text-ink"}`}>{f.name}</p>
                <p className="text-[14px] text-red">{f.reason}</p>
              </div>
              {f.decision ? (
                <span className={`rounded-full px-3 py-1 text-[13px] font-medium ${f.decision === "Keep" ? "bg-green-soft text-green-text" : "bg-red-soft text-red"}`}>
                  {f.decision === "Keep" ? "Kept" : "Dropped"}
                </span>
              ) : (
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={!live || busy === f.response_id}
                    onClick={() => decide(f, "Keep")}
                    className="min-h-11 rounded-xl border border-card-border bg-white px-4 text-[14px] font-semibold text-ink hover:bg-bg disabled:opacity-40"
                  >
                    Keep
                  </button>
                  <button
                    type="button"
                    disabled={!live || busy === f.response_id}
                    onClick={() => decide(f, "Drop")}
                    className="min-h-11 rounded-xl bg-red-soft px-4 text-[14px] font-semibold text-red hover:brightness-95 disabled:opacity-40"
                  >
                    Drop
                  </button>
                </div>
              )}
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>
      {r.flagged.length > FIRST && (
        <button type="button" onClick={() => setAll(!all)} className="mt-2 text-[14px] font-semibold text-emami-blue hover:underline">
          {all ? "Show fewer" : `Show all ${r.flagged.length} flagged`}
        </button>
      )}
      {r.to_check.length > 0 && (
        <div className="mt-2">
          <button
            type="button"
            aria-expanded={showChecks}
            onClick={() => setShowChecks(!showChecks)}
            className="flex min-h-11 items-center gap-1.5 text-[14px] font-semibold text-emami-blue hover:underline"
          >
            {r.to_check.length} more to check ({checkKinds(r.to_check)})
            <motion.span animate={{ rotate: showChecks ? 180 : 0 }} transition={{ duration: 0.25 }}>
              <ChevronDown className="size-4" aria-hidden />
            </motion.span>
          </button>
          <AnimatePresence>
            {showChecks && (
              <motion.ul
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3, ease: EASE }}
                className="overflow-hidden"
              >
                {r.to_check.map((f) => (
                  <li key={f.response_id} className="flex justify-between gap-3 border-b border-card-border py-2 text-[14px] last:border-0">
                    <span className="text-ink">{f.name}</span>
                    <span className="text-amber">{f.reason}</span>
                  </li>
                ))}
              </motion.ul>
            )}
          </AnimatePresence>
        </div>
      )}
      {!live && <p className="mt-2 text-[12px] text-muted">Viewing an earlier day — go back to live to keep or drop.</p>}
    </Card>
  );
}

function checkKinds(items: FlagItem[]): string {
  const kinds = new Set<string>();
  for (const f of items)
    for (const c of f.codes)
      kinds.add({ CONTRADICTION: "answers don't match", DUPLICATE: "submitted twice", JUNK_TEXT: "junk comment" }[c] ?? "");
  kinds.delete("");
  return [...kinds].join(", ");
}

const INTENT_COLOR: Record<string, string> = {
  "I've enrolled": "var(--green-text)",
  "I'll enrol": "var(--cyan)",
  "Explain again": "var(--orange)",
  "Explain in Bengali": "var(--orange)",
  "Talk to my ASM": "var(--emami-blue)",
  "No reply yet": "var(--grey-cohort)",
};

export function IntentsCard({ r }: { r: SurveyResults }) {
  const rows = [...Object.entries(r.intents), ["No reply yet", r.no_reply] as [string, number]];
  return (
    <Card className="p-6">
      <CardTitle action={<span className="text-[13px] text-muted">all {r.total} distributors</span>}>What would you like to do?</CardTitle>
      <ul className="mt-4 space-y-2.5">
        {rows.map(([label, n]) => (
          <li key={label} className="grid grid-cols-[150px_1fr_32px] items-center gap-3 text-[15px]">
            <span className="text-ink">{label}</span>
            <ProgressBar value={n / r.total} color={INTENT_COLOR[label]} />
            <span className="text-right font-semibold text-ink tabular">{n}</span>
          </li>
        ))}
      </ul>
      {r.left_out > 0 && <p className="mt-3 text-[13px] text-muted">{r.left_out} flagged answers left out until you keep them.</p>}
    </Card>
  );
}

function tone(p: number | null): string {
  if (p === null) return "text-muted";
  if (p >= 0.6) return "text-green-text";
  if (p >= 0.45) return "text-amber";
  return "text-red";
}

const THEME_TONE = ["bg-orange-soft text-amber", "bg-[#EEF1F5] text-ink", "bg-red-soft text-red"];

export function RatingsCard({ r }: { r: SurveyResults }) {
  return (
    <Card className="p-6">
      <CardTitle action={<span className="text-[13px] text-muted">% who said 4 or 5</span>}>How they rate the scheme</CardTitle>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {r.ratings.map((x) => (
          <div key={x.question} className="rounded-xl bg-bg p-4">
            {x.pct === null ? (
              <span className="font-display text-[28px] font-semibold text-muted">–</span>
            ) : (
              <CountUp value={Math.round(x.pct * 100)} suffix="%" className={`block font-display text-[30px] font-semibold leading-none tabular ${tone(x.pct)}`} />
            )}
            <span className="mt-2 block text-[14px] leading-snug text-muted">{x.label}</span>
          </div>
        ))}
      </div>
      {r.themes.length > 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-2 text-[14px]">
          <span className="text-muted">From comments:</span>
          {r.themes.map((t, i) => (
            <motion.span
              key={t.theme}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, ease: EASE, delay: i * 0.06 }}
              className={`rounded-full px-3 py-1 font-medium ${THEME_TONE[i] ?? THEME_TONE[1]}`}
            >
              {t.label} · {t.count}
            </motion.span>
          ))}
        </div>
      )}
    </Card>
  );
}
