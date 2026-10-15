"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { Check } from "lucide-react";
import { EASE } from "@/components/motion/Motion";
import { useSim, useViewDay } from "@/lib/sim";

// Which page shows each step, and the day to open it at.
const STEP_LINK: Record<string, { href: string; day: number }> = {
  nudge: { href: "/survey", day: 7 },
  plan: { href: "/approvals", day: 7 },
  send: { href: "/distributor", day: 9 },
  results: { href: "/results", day: 30 },
};

/** Day 0 Nudge → Day 7 Plan → Day 8 Send → Day 30 Results. `day` defaults to the page's view day. */
export function LoopStepper({ day: dayProp, compact = false }: { day?: number; compact?: boolean }) {
  const { state } = useSim();
  const { day: viewDay } = useViewDay();
  const day = dayProp ?? viewDay;
  const steps = state.steps;
  const current = steps.reduce((acc, s, i) => (day >= s.day ? i : acc), 0);

  return (
    <nav aria-label="Scheme loop" className="mb-6 rounded-[var(--radius-card)] border border-card-border bg-white px-4 py-4 shadow-[var(--shadow-card)] sm:px-6">
      <ol className={compact ? "grid grid-cols-2 gap-x-4 gap-y-4" : "grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2 md:flex md:items-center md:gap-0"}>
        {steps.map((s, i) => {
          const status = i < current ? "done" : i === current ? "current" : "todo";
          const link = STEP_LINK[s.key];
          const reached = status !== "todo";
          const body = (
            <span className="flex items-center gap-3">
              <StepDot status={status} />
              <span className="min-w-0 leading-tight">
                <span className={`block text-[15px] font-semibold ${reached ? "text-ink" : "text-muted"}`}>{s.label}</span>
                <span className="block text-[13px] text-muted">{s.day_label}</span>
              </span>
            </span>
          );
          return (
            <li key={s.key} className={compact ? "flex items-center" : "flex items-center md:flex-1 md:last:flex-none"}>
              {reached ? (
                <Link
                  href={`${link.href}?day=${Math.min(link.day, state.day)}`}
                  className="-m-1.5 rounded-xl p-1.5 transition-colors hover:bg-bg"
                >
                  {body}
                </Link>
              ) : (
                <span className="p-0">{body}</span>
              )}
              {!compact && i < steps.length - 1 && (
                <span className="mx-5 hidden h-[3px] flex-1 overflow-hidden rounded-full bg-track md:block" aria-hidden>
                  <motion.span
                    className="block h-full origin-left rounded-full bg-emami-blue"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: i < current ? 1 : 0 }}
                    transition={{ duration: 0.6, ease: EASE, delay: 0.1 + i * 0.12 }}
                  />
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function StepDot({ status }: { status: "done" | "current" | "todo" }) {
  if (status === "done")
    return (
      <motion.span
        initial={{ scale: 0.7 }}
        animate={{ scale: 1 }}
        transition={{ duration: 0.35, ease: EASE }}
        className="grid size-9 shrink-0 place-items-center rounded-full bg-emami-blue text-white"
      >
        <Check className="size-[18px]" strokeWidth={2.5} aria-hidden />
        <span className="sr-only">Done</span>
      </motion.span>
    );
  if (status === "current")
    return (
      <span className="relative grid size-9 shrink-0 place-items-center">
        <motion.span
          className="absolute inset-[-5px] rounded-full bg-orange/20"
          animate={{ scale: [1, 1.12, 1] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
          aria-hidden
        />
        <span className="relative grid size-9 place-items-center rounded-full bg-orange">
          <span className="size-3 rounded-full bg-white" />
        </span>
        <span className="sr-only">Current step</span>
      </span>
    );
  return <span className="size-9 shrink-0 rounded-full border-2 border-[#CBD3DC] bg-white" aria-hidden />;
}
