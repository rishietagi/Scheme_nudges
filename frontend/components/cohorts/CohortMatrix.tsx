"use client";

import { motion } from "motion/react";
import type { AxisInfo, CohortColor, CohortName } from "@/lib/api";
import { COHORT_HEX } from "@/lib/cohorts";
import { CountUp, EASE } from "@/components/motion/Motion";
import { InfoTip } from "@/components/cards/InfoTip";

export type MatrixCell = {
  name: CohortName;
  color: CohortColor;
  count: number;
  definition: string;
  high_potential: boolean;
  high_performance: boolean;
  tag?: string;
  footer?: React.ReactNode;
};

/** The 2×2: business potential down the side (high on top), distributor performance across (high on the left). */
export function CohortMatrix({
  cells,
  potential,
  performance,
  potentialHigh,
  performanceHigh,
  selected,
  onSelect,
  compact = false,
}: {
  cells: MatrixCell[];
  potential: AxisInfo;
  performance: AxisInfo;
  potentialHigh: number;
  performanceHigh: number;
  selected?: CohortName;
  onSelect?: (c: CohortName) => void;
  compact?: boolean;
}) {
  const at = (hp: boolean, hperf: boolean) => cells.find((c) => c.high_potential === hp && c.high_performance === hperf);
  return (
    <div className="grid grid-cols-[auto_1fr_1fr] gap-x-3 gap-y-3">
      <span aria-hidden />
      {[
        { label: performance.high, rule: `Performance score ${performanceHigh} or more out of 100.` },
        { label: performance.low, rule: `Performance score below ${performanceHigh}.` },
      ].map((h) => (
        <span key={h.label} className="flex items-center justify-center gap-1 text-[12px] font-semibold uppercase tracking-[0.08em] text-muted">
          {h.label}
          <InfoTip label={`What ${h.label.toLowerCase()} means`}>
            {h.rule} {performance.rule}
          </InfoTip>
        </span>
      ))}
      {[true, false].map((hp) => (
        <Row
          key={String(hp)}
          label={hp ? potential.high : potential.low}
          tip={`${hp ? `₹${potentialHigh} L/month or more` : `Below ₹${potentialHigh} L/month`} of Emami potential in their catchment. ${potential.rule}.`}
        >
          {[true, false].map((hperf) => {
            const c = at(hp, hperf);
            return c ? (
              <Cell key={c.name} c={c} active={c.name === selected} onSelect={onSelect} compact={compact} />
            ) : (
              <span key={String(hperf)} />
            );
          })}
        </Row>
      ))}
    </div>
  );
}

function Row({ label, tip, children }: { label: string; tip: string; children: React.ReactNode }) {
  return (
    <>
      <span className="flex flex-col items-center justify-center gap-1">
        <span className="rotate-180 text-[12px] font-semibold uppercase tracking-[0.08em] text-muted [writing-mode:vertical-rl]">{label}</span>
        <InfoTip label={`What ${label.toLowerCase()} means`} align="left">
          {tip}
        </InfoTip>
      </span>
      {children}
    </>
  );
}

function Cell({ c, active, onSelect, compact }: { c: MatrixCell; active: boolean; onSelect?: (c: CohortName) => void; compact: boolean }) {
  const color = COHORT_HEX[c.color];
  const body = (
    <>
      {active && (
        <motion.span
          layoutId="matrix-selected"
          className="pointer-events-none absolute -inset-px rounded-[var(--radius-card)] border-2"
          style={{ borderColor: color, boxShadow: `0 0 0 4px color-mix(in srgb, ${color} 12%, transparent)` }}
          transition={{ duration: 0.4, ease: EASE }}
        />
      )}
      <span className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-2">
          <span className="size-3 rounded-[4px]" style={{ backgroundColor: color }} aria-hidden />
          <span className="text-[17px] font-semibold text-ink">{c.name}</span>
        </span>
        {c.tag && <span className="text-[13px] text-muted">{c.tag}</span>}
      </span>
      <CountUp value={c.count} className={`mt-2 block font-display font-semibold leading-none text-ink tabular ${compact ? "text-[32px]" : "text-[40px]"}`} />
      <span className="mt-2 block flex-1 text-[14px] leading-snug text-muted">{c.definition}</span>
      {c.footer && <span className="mt-3 block">{c.footer}</span>}
    </>
  );
  const cls =
    "relative flex h-full w-full flex-col rounded-[var(--radius-card)] border border-card-border bg-white p-4 text-left shadow-[var(--shadow-card)] sm:p-5";
  if (!onSelect) return <div className={cls}>{body}</div>;
  return (
    <motion.button
      type="button"
      onClick={() => onSelect(c.name)}
      aria-pressed={active}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.25, ease: EASE }}
      className={`${cls} transition-shadow hover:shadow-[var(--shadow-lift)]`}
    >
      {body}
    </motion.button>
  );
}
