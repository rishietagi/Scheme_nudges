"use client";

import { CartesianGrid, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import type { CohortName, CohortPoint } from "@/lib/api";
import { COHORT_ORDER, cohortColor } from "@/lib/cohorts";

const CAP = 20; // ₹ L/month — a few very large catchments are drawn at the edge

/** Every distributor on the 2×2: performance score across, business potential up. Dashed lines = the thresholds. */
export function CohortScatter({
  points,
  potentialHigh,
  performanceHigh,
  selectedId,
  onSelect,
  height = 320,
}: {
  points: CohortPoint[];
  potentialHigh: number;
  performanceHigh: number;
  selectedId?: string | null;
  onSelect?: (p: CohortPoint) => void;
  height?: number;
}) {
  const byCohort = COHORT_ORDER.map((c) => ({
    cohort: c,
    data: points.filter((p) => p.cohort === c).map((p) => ({ ...p, y: Math.min(p.potential_l, CAP) })),
  }));
  return (
    <div style={{ height }} role="img" aria-label="Scatter plot of distributors: performance score against business potential">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 12, bottom: 22, left: 0 }}>
          <CartesianGrid stroke="var(--track)" />
          <XAxis
            type="number"
            dataKey="score"
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            tick={{ fontSize: 12, fill: "var(--muted)" }}
            label={{ value: "Performance score →", position: "insideBottom", offset: -12, fontSize: 12, fill: "var(--muted)" }}
          />
          <YAxis
            type="number"
            dataKey="y"
            domain={[0, CAP]}
            tick={{ fontSize: 12, fill: "var(--muted)" }}
            width={44}
            label={{ value: "₹ L/month", angle: -90, position: "insideLeft", offset: 12, fontSize: 12, fill: "var(--muted)" }}
          />
          <ZAxis range={[70, 70]} />
          <ReferenceLine x={performanceHigh} stroke="var(--ink)" strokeDasharray="4 4" strokeOpacity={0.4} />
          <ReferenceLine y={potentialHigh} stroke="var(--ink)" strokeDasharray="4 4" strokeOpacity={0.4} />
          <Tooltip cursor={false} content={<Tip />} />
          {byCohort.map(({ cohort, data }) => (
            <Scatter
              key={cohort}
              name={cohort}
              data={data}
              fill={cohortColor(cohort as CohortName)}
              fillOpacity={0.85}
              onClick={(d) => onSelect?.((d as unknown as { payload: CohortPoint }).payload)}
              shape={(props: unknown) => {
                const { cx, cy, payload } = props as { cx: number; cy: number; payload: CohortPoint };
                const sel = payload.distributor_id === selectedId;
                return (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={sel ? 8 : 5}
                    fill={cohortColor(payload.cohort)}
                    fillOpacity={sel ? 1 : 0.8}
                    stroke={sel ? "var(--ink)" : "white"}
                    strokeWidth={sel ? 2 : 1}
                    style={{ cursor: onSelect ? "pointer" : "default" }}
                  />
                );
              }}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

function Tip({ active, payload }: { active?: boolean; payload?: { payload: CohortPoint }[] }) {
  const p = active && payload?.[0]?.payload;
  if (!p) return null;
  return (
    <div className="rounded-xl border border-card-border bg-white p-3 text-[13px] shadow-[var(--shadow-lift)]">
      <p className="font-semibold text-ink">{p.name}</p>
      <p className="text-muted">
        {p.town} · {p.cohort}
      </p>
      <p className="mt-1 text-ink">
        Potential ₹{p.potential_l.toFixed(1)} L/month · score {Math.round(p.score)}/100
      </p>
    </div>
  );
}
