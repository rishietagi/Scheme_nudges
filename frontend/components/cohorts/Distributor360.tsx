"use client";

import { AnimatePresence, motion } from "motion/react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { Check, Clock, Globe, Lightbulb, MessageCircle, Mic, X } from "lucide-react";
import type { Distributor360 as D360 } from "@/lib/api";
import { initials } from "@/lib/cohorts";
import { formatINR } from "@/lib/format";
import { EASE } from "@/components/motion/Motion";

const MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function Distributor360({ d }: { d: D360 | undefined }) {
  return (
    <section className="rounded-[var(--radius-card)] border border-orange/40 bg-white p-6 shadow-[var(--shadow-card)]">
      <AnimatePresence mode="wait">
        {d ? (
          <motion.div
            key={d.distributor_id}
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -8 }}
            transition={{ duration: 0.35, ease: EASE }}
          >
            <Header d={d} />
            <div className="mt-5 grid grid-cols-3 gap-2.5">
              <Stat label="Billing FYTD" value={formatINR(d.secondary_fytd_l)} />
              <Stat label="October target" value={formatINR(d.target_l)} />
              <Stat label="Festive Scheme" value="Not yet" muted />
            </div>

            <h3 className="mt-6 text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">Why this cohort</h3>
            <ul className="mt-2 space-y-1.5">
              {d.reasons.map((r) => (
                <li key={r} className="flex items-start gap-2 text-[15px] text-ink">
                  <span className="mt-2 size-1.5 shrink-0 rounded-full bg-emami-blue" aria-hidden />
                  {r}
                </li>
              ))}
            </ul>

            <h3 className="mt-6 text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">Last 3 schemes</h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {d.history.map((h) => (
                <span
                  key={h.scheme}
                  className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[13px] font-medium ${
                    h.enrolled ? "bg-green-soft text-green-text" : "bg-[#EEF1F5] text-muted"
                  }`}
                >
                  {h.enrolled ? <Check className="size-3.5" aria-hidden /> : <X className="size-3.5" aria-hidden />}
                  {h.scheme.split(" · ")[0]}
                </span>
              ))}
            </div>

            <h3 className="mt-6 text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">Billing, last 6 months</h3>
            <Sparkbars d={d} />

            <Learned d={d} />
          </motion.div>
        ) : (
          <motion.p key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="py-16 text-center text-[15px] text-muted">
            Pick a distributor to see their 360.
          </motion.p>
        )}
      </AnimatePresence>
    </section>
  );
}

function Header({ d }: { d: D360 }) {
  return (
    <div className="flex items-center gap-4">
      <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-navy-800 font-display text-[20px] font-semibold text-orange-light">
        {initials(d.name)}
      </span>
      <div className="min-w-0">
        <p className="text-[12px] font-semibold uppercase tracking-[0.1em] text-amber">Distributor 360</p>
        <h2 className="truncate font-display text-[22px] font-semibold leading-tight text-ink">{d.name}</h2>
        <p className="text-[14px] text-muted">
          {d.owner_name} · {d.town}
          {d.key_account && " · key account"}
        </p>
      </div>
    </div>
  );
}

function Stat({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <div className="rounded-xl bg-bg px-3 py-3">
      <p className="text-[12px] text-muted">{label}</p>
      <p className={`mt-0.5 font-display text-[20px] font-semibold tabular ${muted ? "text-muted" : "text-ink"}`}>{value}</p>
    </div>
  );
}

function Sparkbars({ d }: { d: D360 }) {
  const data = d.billing.slice(-6).map((m) => ({ m: MONTH[Number(m.month.slice(5)) - 1], v: m.secondary_l }));
  return (
    <div className="mt-2 h-24" aria-label={`Monthly billing from ${data[0]?.m} to ${data.at(-1)?.m}`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
          <XAxis dataKey="m" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "var(--muted)" }} />
          <Tooltip
            cursor={{ fill: "var(--bg)" }}
            formatter={(v) => [formatINR(Number(v)), "Billing"]}
            contentStyle={{ borderRadius: 12, border: "1px solid var(--card-border)", fontSize: 13 }}
          />
          <Bar dataKey="v" barSize={22} radius={[6, 6, 2, 2]} animationDuration={700}>
            {data.map((_, i) => (
              <Cell key={i} fill={i === data.length - 1 ? "var(--emami-blue)" : "#C9DDEE"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Persona panel. On Day 0 the system only knows the file; it learns from this cycle's behaviour. */
function Learned({ d }: { d: D360 }) {
  const rows = [
    { icon: Globe, label: "Language", value: d.language_on_file, note: "on file" },
    { icon: Clock, label: "Best time", value: d.reply_window, note: "on file" },
    { icon: MessageCircle, label: "Replies", value: "Not yet" },
    { icon: Mic, label: "Prefers", value: "Not yet" },
  ];
  return (
    <div className="mt-6 rounded-2xl bg-navy-800 p-5 text-white">
      <p className="flex items-center gap-2 text-[14px] font-semibold text-orange-light">
        <Lightbulb className="size-4" aria-hidden /> What we&apos;ve learned
      </p>
      <ul className="mt-2 divide-y divide-white/10">
        {rows.map(({ icon: Icon, label, value, note }) => (
          <li key={label} className="flex items-center gap-3 py-2.5 text-[15px]">
            <Icon className="size-4 text-white/70" aria-hidden />
            <span className="text-white/80">{label}</span>
            <span className="ml-auto font-semibold">
              {value}
              {note && <span className="ml-1.5 text-[12px] font-normal text-white/50">{note}</span>}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-3 rounded-xl bg-white/[0.06] px-3.5 py-2.5 text-[14px] text-white/80">
        Fills in from this cycle&apos;s replies and follow-ups.
      </p>
    </div>
  );
}
