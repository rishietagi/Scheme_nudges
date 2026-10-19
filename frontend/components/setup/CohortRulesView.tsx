"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, RotateCcw, Save } from "lucide-react";
import { api, type CohortConfig, type CohortConfigIn, type Threshold } from "@/lib/api";
import { Card, CardTitle, Pill } from "@/components/cards/Card";
import { InfoTip } from "@/components/cards/InfoTip";
import { PageHeader } from "@/components/shell/PageHeader";
import { Placeholder } from "@/components/cards/Placeholder";
import { CohortMatrix } from "@/components/cohorts/CohortMatrix";
import { CohortScatter } from "@/components/cohorts/CohortScatter";

/** The business sets the 2×2: where "big market" and "performing" start, and how the four pillars are weighted.
 *  A live preview shows who would move. Saved rules apply from the next cycle. */
export function CohortRulesView() {
  const [saved, setSaved] = useState<CohortConfig | null>(null);
  const [draft, setDraft] = useState<CohortConfigIn | null>(null);
  const [preview, setPreview] = useState<CohortConfig | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load(c: CohortConfig) {
    setSaved(c);
    setPreview(c);
    setDraft({
      thresholds: Object.fromEntries(c.thresholds.map((t) => [t.key, t.value])),
      weights: Object.fromEntries(c.weights.map((w) => [w.key, w.value])),
      definitions: Object.fromEntries(c.cohorts.map((x) => [x.name, x.definition])),
    });
  }

  useEffect(() => {
    api.cohortConfig().then(load, () => setError("Can't reach the simulator"));
  }, []);

  const dirty = useMemo(() => {
    if (!saved || !draft) return false;
    return (
      saved.thresholds.some((t) => draft.thresholds[t.key] !== t.value) ||
      saved.weights.some((w) => draft.weights[w.key] !== w.value) ||
      saved.cohorts.some((c) => (draft.definitions[c.name] ?? "").trim() !== c.definition)
    );
  }, [saved, draft]);

  useEffect(() => {
    if (!draft || !dirty) return;
    const t = setTimeout(() => api.cohortConfigPreview(draft).then(setPreview, () => {}), 250);
    return () => clearTimeout(t);
  }, [draft, dirty]);

  async function act(fn: () => Promise<CohortConfig>) {
    setBusy(true);
    try {
      load(await fn());
    } finally {
      setBusy(false);
    }
  }

  const shown = dirty ? preview : saved;

  return (
    <>
      <PageHeader eyebrow="Set up · cohort rules apply from the next cycle" title="Cohort rules" />
      {!saved || !draft || !shown ? (
        <Placeholder title={error ?? "Loading cohort rules"} phase={1} lines={3} />
      ) : (
        <div className="grid items-start gap-5 xl:grid-cols-[1fr_1.15fr]">
          <div className="space-y-5">
            <Card className="p-6">
              <CardTitle action={saved.customised ? <Pill tone="orange">Edited</Pill> : <Pill>Default</Pill>}>
                Where the lines are
              </CardTitle>
              <p className="mt-1 text-[14px] text-muted">Two questions put every distributor on the 2×2.</p>
              <Group title="Is their market big?" tip={shown.potential.rule}>
                <ThresholdInput t={byKey(saved, "potential_high")} draft={draft} setDraft={setDraft} />
              </Group>
              <Group title="Are they performing?" tip={shown.performance.rule}>
                <ThresholdInput t={byKey(saved, "performance_high")} draft={draft} setDraft={setDraft} />
              </Group>
            </Card>

            <Card className="p-6">
              <CardTitle
                action={
                  <span className={`text-[13px] font-semibold tabular ${weightSum(draft) === 100 ? "text-green-text" : "text-amber"}`}>
                    {weightSum(draft)}% of 100
                  </span>
                }
              >
                How performance is scored
              </CardTitle>
              <p className="mt-1 text-[14px] text-muted">
                Four pillars, each scored 0–100, weighted into one score. Weights are re-scaled to add up to 100 when you save.
              </p>
              <div className="mt-4 space-y-3">
                {saved.weights.map((w) => (
                  <div key={w.key} className="flex items-center justify-between gap-4">
                    <label htmlFor={`w-${w.key}`} className="flex items-center gap-1 text-[14px] text-ink">
                      {w.label}
                      <InfoTip label={`About ${w.label.toLowerCase()}`} align="left">
                        {w.explain}
                      </InfoTip>
                      {draft.weights[w.key] !== w.default && <span className="ml-1 text-[12px] text-muted">default {w.default}</span>}
                    </label>
                    <span className="flex shrink-0 items-center gap-2">
                      <input
                        id={`w-${w.key}`}
                        type="range"
                        min={0}
                        max={60}
                        step={5}
                        value={draft.weights[w.key] ?? w.value}
                        onChange={(e) => setDraft({ ...draft, weights: { ...draft.weights, [w.key]: Number(e.target.value) } })}
                        className="w-32 accent-[var(--emami-blue)]"
                      />
                      <span className="w-10 text-right text-[15px] font-semibold text-ink tabular">{draft.weights[w.key]}%</span>
                    </span>
                  </div>
                ))}
              </div>
              <Group title="Pillar targets" tip={shown.pillars_rule}>
                {["market_growth", "focus_target", "otif_floor", "otif_ceiling"].map((k) => (
                  <ThresholdInput key={k} t={byKey(saved, k)} draft={draft} setDraft={setDraft} />
                ))}
              </Group>
              {shown.benchmark && <p className="mt-3 text-[12px] text-muted">{shown.benchmark}</p>}
            </Card>

            <Card className="p-6">
              <CardTitle>What each cohort means</CardTitle>
              <div className="mt-4 space-y-4">
                {saved.cohorts.map((c) => (
                  <label key={c.name} className="block">
                    <span className="text-[14px] font-semibold text-ink">{c.name}</span>
                    <textarea
                      rows={2}
                      value={draft.definitions[c.name] ?? ""}
                      onChange={(e) => setDraft({ ...draft, definitions: { ...draft.definitions, [c.name]: e.target.value } })}
                      className="mt-1 w-full resize-none rounded-xl border border-card-border bg-white px-3 py-2 text-[14px] text-ink outline-none focus:border-emami-blue focus:ring-2 focus:ring-blue-soft"
                    />
                  </label>
                ))}
              </div>
            </Card>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                disabled={!dirty || busy}
                onClick={() => act(() => api.cohortConfigSave(draft))}
                className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-orange px-5 text-[15px] font-semibold text-ink transition-opacity disabled:opacity-40"
              >
                <Save className="size-4" aria-hidden /> Save for next cycle
              </button>
              <button
                type="button"
                disabled={!saved.customised || busy}
                onClick={() => act(api.cohortConfigReset)}
                className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-card-border bg-white px-4 text-[15px] font-medium text-ink transition-opacity disabled:opacity-40"
              >
                <RotateCcw className="size-4" aria-hidden /> Reset to default
              </button>
              {dirty && (
                <button type="button" onClick={() => load(saved)} className="min-h-11 px-2 text-[14px] text-muted hover:text-ink">
                  Discard changes
                </button>
              )}
            </div>
            {saved.current_run_differs && !dirty && (
              <p className="text-[14px] text-muted">
                Saved. The running cycle keeps its cohorts; these rules start with the next one.{" "}
                <Link href="/simulation" className="font-semibold text-emami-blue hover:underline">
                  Start a new cycle in Simulation
                </Link>
              </p>
            )}
          </div>

          <Card className="p-6 xl:sticky xl:top-6">
            <CardTitle action={dirty ? <Pill tone="blue">Preview</Pill> : null}>Kolkata North with these rules</CardTitle>
            <div className="mt-4">
              <CohortMatrix
                compact
                cells={shown.cohorts.map((c) => ({ ...c, definition: (draft.definitions[c.name] ?? c.definition) || c.definition }))}
                potential={shown.potential}
                performance={shown.performance}
                potentialHigh={shown.potential_high}
                performanceHigh={shown.performance_high}
              />
            </div>
            <div className="mt-4">
              <CohortScatter points={shown.points} potentialHigh={shown.potential_high} performanceHigh={shown.performance_high} height={260} />
            </div>
            <h3 className="mt-4 text-[15px] font-semibold text-ink">
              {shown.moves.length ? `${shown.moves.reduce((s, m) => s + m.count, 0)} would move vs this cycle` : "Nobody moves vs this cycle"}
            </h3>
            <ul className="mt-2 divide-y divide-card-border">
              {shown.moves.slice(0, 5).map((m) => (
                <li key={`${m.from_cohort}-${m.to_cohort}`} className="py-2.5 text-[14px]">
                  <span className="flex items-center gap-1.5 font-medium text-ink">
                    {m.count} · {m.from_cohort} <ArrowRight className="size-3.5 text-muted" aria-hidden /> {m.to_cohort}
                  </span>
                  <span className="text-muted">
                    {m.names.join(", ")}
                    {m.count > m.names.length ? ` and ${m.count - m.names.length} more` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}
    </>
  );
}

function byKey(c: CohortConfig, k: string): Threshold {
  return c.thresholds.find((t) => t.key === k)!;
}

function weightSum(d: CohortConfigIn): number {
  return Math.round(Object.values(d.weights).reduce((a, b) => a + b, 0));
}

function Group({ title, tip, children }: { title: string; tip?: string; children: React.ReactNode }) {
  return (
    <fieldset className="mt-5 border-t border-card-border pt-4">
      <legend className="sr-only">{title}</legend>
      <p className="flex items-center gap-1 text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">
        {title}
        {tip && (
          <InfoTip label={`About: ${title}`} align="left">
            {tip}
          </InfoTip>
        )}
      </p>
      <div className="mt-2 space-y-2">{children}</div>
    </fieldset>
  );
}

function ThresholdInput({ t, draft, setDraft }: { t: Threshold; draft: CohortConfigIn; setDraft: (d: CohortConfigIn) => void }) {
  const v = draft.thresholds[t.key] ?? t.value;
  const id = `th-${t.key}`;
  return (
    <div className="flex items-center justify-between gap-4">
      <label htmlFor={id} className="text-[14px] text-ink">
        {t.label}
        {v !== t.default && <span className="ml-2 text-[12px] text-muted">default {t.default}</span>}
      </label>
      <span className="flex shrink-0 items-center gap-2">
        <input
          id={id}
          type="number"
          min={t.min}
          max={t.max}
          step={t.key === "potential_high" ? 0.5 : 1}
          value={v}
          onChange={(e) => {
            const n = Number(e.target.value);
            if (Number.isFinite(n)) setDraft({ ...draft, thresholds: { ...draft.thresholds, [t.key]: Math.min(t.max, Math.max(t.min, n)) } });
          }}
          className="h-11 w-20 rounded-xl border border-card-border px-3 text-right text-[15px] font-semibold text-ink tabular outline-none focus:border-emami-blue focus:ring-2 focus:ring-blue-soft"
        />
        <span className="w-16 text-[13px] text-muted">{t.unit}</span>
      </span>
    </div>
  );
}
