"use client";

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { ArrowRight, CheckCheck, MessageCircle, Send, SquareCheckBig, TrendingUp, Users, type LucideIcon, Flag } from "lucide-react";
import { useSim } from "@/lib/sim";
import { timeLabel } from "@/lib/format";
import { LoopStepper } from "@/components/loop-stepper/LoopStepper";
import { Card } from "@/components/cards/Card";
import { CountUp, EASE } from "@/components/motion/Motion";

const MARKS = [
  { day: 0, label: "Day 0" },
  { day: 7.5, label: "Day 7–8" },
  { day: 30, label: "Day 30" },
];

export function LoopPanel() {
  const { state } = useSim();
  const c = state.counters;
  const counters: { label: string; value: number; icon: LucideIcon; tone: string }[] = [
    { label: "Sent", value: c.sent, icon: Send, tone: "bg-blue-soft text-emami-blue" },
    { label: "Replied", value: c.replied, icon: MessageCircle, tone: "bg-blue-soft text-emami-blue" },
    { label: "Flagged", value: c.flagged, icon: Flag, tone: "bg-red-soft text-red" },
    { label: "Joined", value: c.joined, icon: CheckCheck, tone: "bg-green-soft text-green-text" },
    { label: "Follow-ups sent", value: c.follow_ups, icon: Users, tone: "bg-orange-soft text-amber" },
    { label: "Beat prediction", value: c.beat_prediction, icon: TrendingUp, tone: "bg-green-soft text-green-text" },
  ];

  return (
    <div className="min-w-0">
      <LoopStepper day={state.day} compact />

      <Card className="p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[13px] font-medium uppercase tracking-[0.1em] text-muted">Sim clock</p>
            <motion.p
              key={state.day_label}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: EASE }}
              className="mt-1 font-display text-[32px] font-semibold leading-none tracking-[-0.02em] text-ink sm:text-[38px]"
            >
              {state.day_label}
            </motion.p>
          </div>
          <div className="text-right">
            <p className="font-display text-[22px] font-semibold text-ink tabular">{timeLabel(state.day)}</p>
            <p className="text-[13px] text-muted">{state.status_text}</p>
          </div>
        </div>

        {/* Day 0 → 30 track */}
        <div className="relative mt-6 pb-6">
          <div className="h-2 overflow-hidden rounded-full bg-track">
            <motion.div
              className="h-full origin-left rounded-full bg-emami-blue"
              animate={{ scaleX: state.day / 30 }}
              transition={{ duration: state.playing ? 0.3 : 0.6, ease: state.playing ? "linear" : EASE }}
            />
          </div>
          {MARKS.map((m, i) => (
            <span
              key={m.day}
              className={`absolute top-3.5 whitespace-nowrap text-[11px] text-muted ${
                i === 0 ? "" : i === MARKS.length - 1 ? "-translate-x-full" : "-translate-x-1/2"
              }`}
              style={{ left: `${(m.day / 30) * 100}%` }}
            >
              {m.label}
            </span>
          ))}
        </div>

        <AnimatePresence>
          {state.waiting_for_approval && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.35, ease: EASE }}
              className="overflow-hidden"
            >
              <Link
                href="/approvals"
                className="mt-2 flex min-h-12 items-center gap-3 rounded-xl bg-orange-soft px-4 py-3 text-[15px] font-semibold text-amber hover:brightness-[0.98]"
              >
                <SquareCheckBig className="size-5 shrink-0" aria-hidden />
                Waiting for your approval
                <span className="ml-auto flex items-center gap-1">
                  Open approval matrix <ArrowRight className="size-4" aria-hidden />
                </span>
              </Link>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-2 2xl:grid-cols-3">
        {counters.map(({ label, value, icon: Icon, tone }) => (
          <Card key={label} className="p-4">
            <div className="flex items-center justify-between gap-2">
              <p className="text-[13px] text-muted">{label}</p>
              <span className={`grid size-8 place-items-center rounded-lg ${tone}`}>
                <Icon className="size-4" aria-hidden />
              </span>
            </div>
            <CountUp value={value} className="mt-1 block font-display text-[32px] font-semibold leading-none text-ink tabular" />
          </Card>
        ))}
      </div>
    </div>
  );
}
