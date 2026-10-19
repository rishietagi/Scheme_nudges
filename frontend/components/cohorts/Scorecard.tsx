"use client";

import type { Scorecard as Card } from "@/lib/api";
import { pct } from "@/lib/format";
import { ProgressBar } from "@/components/cards/Card";
import { InfoTip } from "@/components/cards/InfoTip";

/** Why this distributor sits in its cohort: the potential of their market and the four performance pillars. */
export function Scorecard({ s, cohort }: { s: Card; cohort: string }) {
  const p = s.potential;
  return (
    <div className="mt-6">
      <h3 className="flex items-center gap-1 text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">
        Why {cohort}
        <InfoTip label="How cohorts are decided" align="left">
          Two questions, from data only. Is their market big (business potential ≥ ₹{p.threshold_l} L/month)? Are they
          performing (score ≥ {s.threshold}/100)? The answers place them on the 2×2.
        </InfoTip>
      </h3>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl bg-bg p-3.5">
          <p className="flex items-center gap-1 text-[12px] text-muted">
            Business potential
            <InfoTip label="How business potential is worked out" align="left">
              {p.town}&apos;s Emami potential is ₹{p.town_potential_l.toFixed(1)} L/month (modelled category TAM of ₹
              {p.town_tam_l.toFixed(0)} L/month × Emami&apos;s fair share). They cover {p.outlets_covered} outlets — {pct(p.coverage_share)} of
              the town — so their share is ₹{p.potential_l.toFixed(1)} L/month. Synthetic TAM for this demo.
            </InfoTip>
          </p>
          <p className={`mt-0.5 font-display text-[22px] font-semibold ${p.high ? "text-emami-blue" : "text-ink"}`}>
            ₹{p.potential_l.toFixed(1)} L<span className="text-[13px] font-medium text-muted">/month</span>
          </p>
          <p className="mt-1 text-[12px] text-muted">
            Selling ₹{p.current_l.toFixed(1)} L now ·{" "}
            {p.headroom_l >= 0 ? `₹${p.headroom_l.toFixed(1)} L headroom` : "already above its modelled share"}
          </p>
        </div>
        <div className="rounded-xl bg-bg p-3.5">
          <p className="flex items-center gap-1 text-[12px] text-muted">
            Performance score
            <InfoTip label="How the performance score is worked out" align="right">
              The weighted average of the four pillar scores below (each 0–100). {s.high ? "At or above" : "Below"} the line of{" "}
              {s.threshold}, so they count as {s.high ? "high" : "low"} performance.
            </InfoTip>
          </p>
          <p className={`mt-0.5 font-display text-[22px] font-semibold ${s.high ? "text-green-text" : "text-amber"}`}>
            {Math.round(s.score)}
            <span className="text-[13px] font-medium text-muted"> / 100 · line at {s.threshold}</span>
          </p>
          <ProgressBar value={s.score / 100} color={s.high ? "var(--green-text)" : "var(--orange)"} className="mt-2" />
        </div>
      </div>

      <ul className="mt-3 space-y-2.5">
        {s.pillars.map((x) => (
          <li key={x.key} className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1">
            <span className="flex items-center gap-1 text-[14px] text-ink">
              {x.label}
              <InfoTip label={`How ${x.label.toLowerCase()} is scored`} align="left">
                {x.explain} Weight {x.weight.toFixed(0)}% of the score.
              </InfoTip>
              <span className="text-[12px] text-muted">· {x.raw}</span>
            </span>
            <span className="text-right text-[14px] font-semibold text-ink tabular">{Math.round(x.score)}</span>
            <ProgressBar value={x.score / 100} color={x.score >= 50 ? "var(--emami-blue)" : "var(--orange)"} className="col-span-2" />
          </li>
        ))}
      </ul>
    </div>
  );
}
