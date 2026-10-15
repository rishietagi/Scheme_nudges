"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { Check, ChevronRight, Flag, MessageCircle, Sparkles, SquareCheckBig } from "lucide-react";
import { api, type CommandView as Data } from "@/lib/api";
import { COHORT_HEX } from "@/lib/cohorts";
import { useViewDay } from "@/lib/sim";
import { useApi } from "@/lib/useApi";
import { AiPanel, Card, CardTitle, ProgressBar, Tile } from "@/components/cards/Card";
import { EASE, Stagger, StaggerItem } from "@/components/motion/Motion";
import { LoopStepper } from "@/components/loop-stepper/LoopStepper";
import { PageHeader } from "@/components/shell/PageHeader";

const TILE_META = {
  replied: { icon: MessageCircle, tone: "blue" },
  joined: { icon: Check, tone: "green" },
  waiting: { icon: SquareCheckBig, tone: "orange" },
  individual: { icon: Flag, tone: "red" },
} as const;

const DOT = { orange: "bg-orange", red: "bg-red", blue: "bg-emami-blue" } as const;

export function CommandView() {
  const { day } = useViewDay();
  const res = useApi(`command:${day.toFixed(2)}`, () => api.command(day));
  const c = res.data;

  return (
    <>
      <PageHeader eyebrow={c?.eyebrow ?? "Festive Scheme · Oct 2026 · Kolkata North · 86 distributors"} title={c?.greeting ?? "Good morning, Rahul"} />
      <LoopStepper />
      {c && (
        <>
          <Stagger className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {c.tiles.map((t) => (
              <StaggerItem key={t.key} className="h-full">
                <Tile label={t.label} value={t.value} sub={t.sub} icon={TILE_META[t.key].icon} tone={TILE_META[t.key].tone} />
              </StaggerItem>
            ))}
          </Stagger>

          <div className="mt-5 grid gap-5 lg:grid-cols-[1.25fr_1fr]">
            <Needs c={c} />
            <AiPanel label={c.summary_label} icon={Sparkles}>
              {c.summary.map((l, i) => (
                <motion.p
                  key={`${i}:${l.text}`}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, ease: EASE, delay: 0.1 + i * 0.12 }}
                  className={l.bold ? "font-semibold text-white" : ""}
                >
                  {l.text}
                </motion.p>
              ))}
            </AiPanel>
          </div>

          <Progress c={c} />
        </>
      )}
    </>
  );
}

function Needs({ c }: { c: Data }) {
  return (
    <Card className="p-6">
      <CardTitle>Needs you today</CardTitle>
      {c.needs.length === 0 ? (
        <p className="mt-4 text-[15px] text-muted">Nothing needs you right now. The loop is running.</p>
      ) : (
        <ul className="mt-2">
          {c.needs.map((n, i) => (
            <motion.li
              key={n.title}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.35, ease: EASE, delay: i * 0.08 }}
              className="border-b border-card-border last:border-0"
            >
              <Link href={n.href} className="group flex min-h-16 items-center gap-4 py-3.5">
                <span className={`size-2.5 shrink-0 rounded-full ${DOT[n.tone]}`} aria-hidden />
                <span className="min-w-0 flex-1">
                  <span className="block text-[16px] font-semibold text-ink">{n.title}</span>
                  <span className="block text-[14px] text-muted">{n.sub}</span>
                </span>
                <span className="flex shrink-0 items-center gap-1 text-[15px] font-semibold text-emami-blue">
                  {n.action}
                  <ChevronRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
                </span>
              </Link>
            </motion.li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function Progress({ c }: { c: Data }) {
  return (
    <Card className="mt-5 overflow-hidden">
      <div className="px-6 pt-5">
        <CardTitle
          action={
            <Link href="/cohorts" className="text-[15px] font-semibold text-emami-blue hover:underline">
              Open cohorts
            </Link>
          }
        >
          Progress by cohort
        </CardTitle>
      </div>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[620px] text-left">
          <thead>
            <tr className="border-y border-card-border text-[12px] font-semibold uppercase tracking-[0.08em] text-muted">
              <th scope="col" className="px-6 py-3">Cohort</th>
              <th scope="col" className="px-3 py-3">Distributors</th>
              <th scope="col" className="px-3 py-3">Replied</th>
              <th scope="col" className="px-6 py-3">Joined so far</th>
            </tr>
          </thead>
          <tbody>
            {c.cohorts.map((r) => (
              <tr key={r.name} className="border-b border-card-border last:border-0">
                <td className="px-6 py-3.5">
                  <span className="flex items-center gap-3 text-[15px] font-medium text-ink">
                    <span className="size-3 rounded-[4px]" style={{ backgroundColor: COHORT_HEX[r.color] }} aria-hidden />
                    {r.name}
                  </span>
                </td>
                <td className="px-3 py-3.5 text-[15px] text-ink tabular">{r.distributors}</td>
                <td className="px-3 py-3.5 text-[15px] text-ink tabular">{r.replied}</td>
                <td className="px-6 py-3.5">
                  <span className="flex items-center gap-4">
                    <ProgressBar value={r.joined / r.distributors} color={COHORT_HEX[r.color]} className="flex-1" />
                    <span className="w-14 text-right text-[15px] font-semibold text-ink tabular">
                      {r.joined} / {r.distributors}
                    </span>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
