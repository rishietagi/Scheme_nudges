"use client";

import { motion } from "motion/react";
import type { LucideIcon } from "lucide-react";
import { CountUp, EASE } from "@/components/motion/Motion";

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-[var(--radius-card)] border border-card-border bg-white shadow-[var(--shadow-card)] ${className}`}>
      {children}
    </section>
  );
}

export function CardTitle({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <h2 className="font-display text-[19px] font-semibold tracking-[-0.01em] text-ink">{children}</h2>
      {action}
    </div>
  );
}

const TONES = {
  blue: "bg-blue-soft text-emami-blue",
  green: "bg-green-soft text-green-text",
  orange: "bg-orange-soft text-amber",
  red: "bg-red-soft text-red",
} as const;

/** Stat tile: label, icon chip, one big number, one plain line. */
export function Tile({
  label,
  value,
  sub,
  icon: Icon,
  tone = "blue",
}: {
  label: string;
  value: number;
  sub: React.ReactNode;
  icon: LucideIcon;
  tone?: keyof typeof TONES;
}) {
  return (
    <motion.div whileHover={{ y: -2 }} transition={{ duration: 0.25, ease: EASE }} className="h-full">
      <Card className="h-full p-5 transition-shadow hover:shadow-[var(--shadow-lift)]">
        <div className="flex items-start justify-between gap-3">
          <p className="text-[14px] text-muted">{label}</p>
          <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${TONES[tone]}`}>
            <Icon className="size-5" strokeWidth={1.75} aria-hidden />
          </span>
        </div>
        <CountUp value={value} className="mt-2 block font-display text-[44px] font-semibold leading-none tracking-[-0.02em] text-ink tabular" />
        <p className="mt-3 text-[13px] text-muted">{sub}</p>
      </Card>
    </motion.div>
  );
}

const PILL_TONES = {
  neutral: "bg-[#EEF1F5] text-muted",
  green: "bg-green-soft text-green-text",
  orange: "bg-orange-soft text-amber",
  red: "bg-red-soft text-red",
  blue: "bg-blue-soft text-emami-blue",
} as const;

export function Pill({ children, tone = "neutral" }: { children: React.ReactNode; tone?: keyof typeof PILL_TONES }) {
  return <span className={`inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-1 text-[13px] font-medium ${PILL_TONES[tone]}`}>{children}</span>;
}

/** Animated fill bar (0–1). */
export function ProgressBar({ value, color = "var(--emami-blue)", className = "" }: { value: number; color?: string; className?: string }) {
  return (
    <div className={`h-2 overflow-hidden rounded-full bg-track ${className}`} role="presentation">
      <motion.div
        className="h-full origin-left rounded-full"
        style={{ backgroundColor: color }}
        initial={{ scaleX: 0 }}
        animate={{ scaleX: Math.max(0, Math.min(1, value)) }}
        transition={{ duration: 0.8, ease: EASE }}
      />
    </div>
  );
}

/** Navy "Emami AI" summary panel. */
export function AiPanel({ label, children, icon: Icon }: { label: string; children: React.ReactNode; icon: LucideIcon }) {
  return (
    <section className="rounded-[var(--radius-card)] bg-navy-800 p-6 text-white shadow-[var(--shadow-card)]">
      <p className="flex items-center gap-2 text-[13px] font-semibold uppercase tracking-[0.1em] text-orange-light">
        <Icon className="size-4" aria-hidden />
        {label}
      </p>
      <div className="mt-3 space-y-3 text-[16px] leading-relaxed text-white/90">{children}</div>
    </section>
  );
}
