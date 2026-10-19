"use client";

import Link from "next/link";
import { ArrowRight, SlidersHorizontal } from "lucide-react";
import type { CohortList, CohortName, CohortPoint } from "@/lib/api";
import { COHORT_HEX } from "@/lib/cohorts";
import { Card, CardTitle, ProgressBar } from "@/components/cards/Card";
import { InfoTip } from "@/components/cards/InfoTip";
import { CohortMatrix } from "./CohortMatrix";
import { CohortScatter } from "./CohortScatter";

/** The 2×2 (each cell selects a cohort), how cohorts are set, and every distributor on the same 2×2. */
export function CohortCards({
  data,
  selected,
  onSelect,
  cycle,
  selectedId,
  onPick,
}: {
  data: CohortList;
  selected: CohortName;
  onSelect: (c: CohortName) => void;
  cycle: boolean;
  selectedId: string | null;
  onPick: (p: CohortPoint) => void;
}) {
  const cells = data.cohorts.map((c) => {
    const joined = cycle ? c.joined_festive : c.joined_last_scheme;
    const color = COHORT_HEX[c.color];
    return {
      ...c,
      definition: c.description,
      footer: (
        <>
          {c.kpis && (
            <span className="block text-[13px] text-muted">
              ₹{c.kpis.potential_l.toFixed(0)} L/month potential · selling ₹{c.kpis.current_l.toFixed(0)} L · avg score{" "}
              {Math.round(c.kpis.avg_score)}
            </span>
          )}
          <span className="mt-3 flex items-center justify-between text-[13px] text-muted">
            {cycle ? "Participating in Festive" : "Took part in last scheme"}
            <span className="font-semibold text-ink tabular">
              {joined} / {c.count}
            </span>
          </span>
          <ProgressBar value={c.count ? joined / c.count : 0} color={color} className="mt-2" />
        </>
      ),
    };
  });

  return (
    <>
      <div className="grid items-start gap-5 xl:grid-cols-[1.6fr_1fr]">
        <CohortMatrix
          cells={cells}
          potential={data.potential}
          performance={data.performance}
          potentialHigh={data.potential_high}
          performanceHigh={data.performance_high}
          selected={selected}
          onSelect={onSelect}
        />
        <Card className="p-6">
          <p className="flex items-center gap-2 text-[13px] font-semibold uppercase tracking-[0.1em] text-muted">
            <SlidersHorizontal className="size-4" aria-hidden />
            How cohorts are set
          </p>
          <p className="mt-3 text-[15px] leading-relaxed text-ink">
            Two questions, from data only, on Day 0: is their market big, and are they performing? The survey adds to what we know
            about each cohort; it never moves anyone.
          </p>
          <dl className="mt-4 space-y-3 text-[14px]">
            <Rule term={data.potential.label} text={`${data.potential.rule}.`} />
            <Rule term={data.performance.label} text={`${data.performance.rule}.`} tip={data.pillars_rule} />
            {data.benchmark && <Rule term="Sources" text={data.benchmark} />}
          </dl>
          <Link
            href="/setup/cohorts"
            className="mt-5 inline-flex min-h-11 items-center gap-1.5 text-[15px] font-semibold text-emami-blue hover:underline"
          >
            Edit cohort rules <ArrowRight className="size-4" aria-hidden />
          </Link>
        </Card>
      </div>

      <Card className="mt-5 p-6">
        <CardTitle
          action={
            <span className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-muted">
              {data.cohorts.map((c) => (
                <span key={c.name} className="flex items-center gap-1.5">
                  <span className="size-2.5 rounded-full" style={{ backgroundColor: COHORT_HEX[c.color] }} aria-hidden />
                  {c.name}
                </span>
              ))}
            </span>
          }
        >
          <span className="flex items-center gap-1">
            All {data.points.length} distributors on the 2×2
            <InfoTip label="How to read this chart" align="left">
              Each dot is a distributor. Across: performance score (0–100). Up: business potential of their market (₹ L/month, capped at
              20 on the chart). Dashed lines are the cut-offs: score {data.performance_high}, potential ₹{data.potential_high} L. Click a
              dot to open their 360.
            </InfoTip>
          </span>
        </CardTitle>
        <div className="mt-3">
          <CohortScatter
            points={data.points}
            potentialHigh={data.potential_high}
            performanceHigh={data.performance_high}
            selectedId={selectedId}
            onSelect={onPick}
          />
        </div>
      </Card>
    </>
  );
}

function Rule({ term, text, tip }: { term: string; text: string; tip?: string }) {
  return (
    <div className="border-t border-card-border pt-3 first:border-0 first:pt-0">
      <dt className="flex items-center gap-1 font-semibold text-ink">
        {term}
        {tip && (
          <InfoTip label={`How ${term.toLowerCase()} is scored`} align="left">
            {tip}
          </InfoTip>
        )}
      </dt>
      <dd className="mt-0.5 text-muted">{text}</dd>
    </div>
  );
}
