"use client";

import { motion } from "motion/react";
import type { CohortCard, CohortName } from "@/lib/api";
import { COHORT_HEX } from "@/lib/cohorts";
import { CountUp, EASE, Stagger, StaggerItem } from "@/components/motion/Motion";
import { ProgressBar } from "@/components/cards/Card";

/** The five cohort cards; one is selected and drives the list below. */
export function CohortCards({
  cohorts,
  selected,
  onSelect,
}: {
  cohorts: CohortCard[];
  selected: CohortName;
  onSelect: (c: CohortName) => void;
}) {
  return (
    <Stagger className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
      {cohorts.map((c) => {
        const active = c.name === selected;
        const color = COHORT_HEX[c.color];
        return (
          <StaggerItem key={c.name} className="h-full">
            <motion.button
              type="button"
              onClick={() => onSelect(c.name)}
              aria-pressed={active}
              whileHover={{ y: -2 }}
              transition={{ duration: 0.25, ease: EASE }}
              className="relative flex h-full w-full flex-col rounded-[var(--radius-card)] border border-card-border bg-white p-5 text-left shadow-[var(--shadow-card)] transition-shadow hover:shadow-[var(--shadow-lift)]"
            >
              {active && (
                <motion.span
                  layoutId="cohort-selected"
                  className="pointer-events-none absolute -inset-px rounded-[var(--radius-card)] border-2"
                  style={{ borderColor: color, boxShadow: `0 0 0 4px color-mix(in srgb, ${color} 12%, transparent)` }}
                  transition={{ duration: 0.4, ease: EASE }}
                />
              )}
              <span className="flex items-center justify-between">
                <span className="size-3 rounded-[4px]" style={{ backgroundColor: color }} aria-hidden />
                <span className="text-[13px] text-muted">{c.tag}</span>
              </span>
              <span className="mt-3 text-[17px] font-semibold text-ink">{c.name}</span>
              <CountUp value={c.count} className="mt-1 font-display text-[40px] font-semibold leading-none text-ink tabular" />
              <span className="mt-3 flex-1 text-[14px] leading-snug text-muted">{c.description}</span>
              <span className="mt-4 flex items-center justify-between text-[13px] text-muted">
                Joined last scheme
                <span className="font-semibold text-ink tabular">
                  {c.joined_last_scheme} / {c.count}
                </span>
              </span>
              <ProgressBar value={c.count ? c.joined_last_scheme / c.count : 0} color={color} className="mt-2" />
            </motion.button>
          </StaggerItem>
        );
      })}
    </Stagger>
  );
}
