"use client";

import { motion } from "motion/react";
import { useState } from "react";
import { Pause, Play, RotateCcw, SkipForward } from "lucide-react";
import { api, type SimState } from "@/lib/api";
import { useSim } from "@/lib/sim";
import { useApi } from "@/lib/useApi";
import { Card } from "@/components/cards/Card";
import { EASE } from "@/components/motion/Motion";

const SCENARIO_LABEL: Record<string, string> = {
  typical: "Typical",
  low_response: "Low response",
  messy_survey: "Messy survey",
  great_uptake: "Great uptake",
};

export function Controls() {
  const { state, apply } = useSim();
  const meta = useApi("scenarios", api.simScenarios);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scenario, setScenario] = useState<string | null>(null);
  const [seed, setSeed] = useState<string | null>(null);
  const speeds = meta.data?.speeds ?? [1, 2, 5];
  const done = state.day >= 30;

  async function run(fn: () => Promise<SimState>) {
    setBusy(true);
    setError(null);
    try {
      apply(await fn());
    } catch {
      setError("The simulator didn't answer. Is the backend running?");
    } finally {
      setBusy(false);
    }
  }

  const pickedScenario = scenario ?? state.scenario;
  const pickedSeed = seed ?? String(state.seed);

  return (
    <Card className="p-5">
      <h2 className="font-display text-[19px] font-semibold text-ink">Controls</h2>

      <div className="mt-4 grid gap-2">
        <motion.button
          type="button"
          whileTap={{ scale: 0.97 }}
          disabled={busy || done || (state.waiting_for_approval && !state.playing)}
          onClick={() => run(() => (state.playing ? api.simPause() : api.simPlay(state.speed_seconds_per_day)))}
          className="flex min-h-12 items-center justify-center gap-2 rounded-xl bg-orange px-4 text-[15px] font-semibold text-ink transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          {state.playing ? <Pause className="size-4" aria-hidden /> : <Play className="size-4" aria-hidden />}
          {state.playing ? "Pause" : "Play"}
        </motion.button>
        <motion.button
          type="button"
          whileTap={{ scale: 0.97 }}
          disabled={busy || done || state.playing}
          onClick={() => run(api.simNextStage)}
          className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-card-border bg-white px-4 text-[15px] font-semibold text-ink hover:bg-bg disabled:opacity-40"
        >
          <SkipForward className="size-4" aria-hidden />
          Next stage
        </motion.button>
      </div>

      <fieldset className="mt-5">
        <legend className="text-[13px] font-medium text-muted">Speed · 1 day =</legend>
        <div className="mt-2 flex rounded-full bg-[#E8ECF1] p-1">
          {speeds.map((s) => {
            const active = state.speed_seconds_per_day === s;
            return (
              <button
                key={s}
                type="button"
                aria-pressed={active}
                onClick={() => run(() => api.simSpeed(s))}
                className={`relative min-h-10 flex-1 rounded-full text-[14px] font-medium ${active ? "text-ink" : "text-muted hover:text-ink"}`}
              >
                {active && (
                  <motion.span layoutId="speed-pill" className="absolute inset-0 rounded-full bg-white shadow-[var(--shadow-card)]" transition={{ duration: 0.3, ease: EASE }} />
                )}
                <span className="relative">{s} s</span>
              </button>
            );
          })}
        </div>
      </fieldset>

      <div className="mt-5 flex items-center justify-between gap-3 rounded-xl bg-bg px-3.5 py-3">
        <span className="leading-tight">
          <span className="block text-[14px] font-semibold text-ink">Autopilot approvals</span>
          <span className="block text-[12px] text-muted">Approve the plan on Day 7 by itself</span>
        </span>
        <button
          type="button"
          role="switch"
          aria-checked={state.autopilot}
          aria-label="Autopilot approvals"
          disabled={busy}
          onClick={() => run(() => api.simAutopilot(!state.autopilot))}
          className={`relative h-7 w-12 shrink-0 rounded-full transition-colors ${state.autopilot ? "bg-emami-blue" : "bg-[#CBD3DC]"}`}
        >
          <motion.span
            className="absolute top-1 size-5 rounded-full bg-white shadow"
            animate={{ left: state.autopilot ? 24 : 4 }}
            transition={{ duration: 0.25, ease: EASE }}
          />
        </button>
      </div>

      <div className="mt-6 border-t border-card-border pt-5">
        <p className="text-[13px] font-medium text-muted">New run</p>
        <label className="mt-3 block text-[13px] text-muted" htmlFor="scenario">
          Scenario
        </label>
        <select
          id="scenario"
          value={pickedScenario}
          onChange={(e) => setScenario(e.target.value)}
          className="mt-1 min-h-11 w-full rounded-xl border border-card-border bg-white px-3 text-[15px] text-ink"
        >
          {Object.keys(meta.data?.scenarios ?? SCENARIO_LABEL).map((k) => (
            <option key={k} value={k}>
              {SCENARIO_LABEL[k] ?? k}
            </option>
          ))}
        </select>
        <p className="mt-1 text-[12px] text-muted">{meta.data?.scenarios[pickedScenario]}</p>
        <label className="mt-3 block text-[13px] text-muted" htmlFor="seed">
          Seed
        </label>
        <input
          id="seed"
          inputMode="numeric"
          value={pickedSeed}
          onChange={(e) => setSeed(e.target.value.replace(/\D/g, ""))}
          className="mt-1 min-h-11 w-full rounded-xl border border-card-border bg-white px-3 text-[15px] text-ink tabular"
        />
        <motion.button
          type="button"
          whileTap={{ scale: 0.97 }}
          disabled={busy}
          onClick={() =>
            run(() => api.simReset(Number(pickedSeed) || meta.data?.default_seed || 42, pickedScenario, state.autopilot)).then(() => {
              setScenario(null);
              setSeed(null);
            })
          }
          className="mt-4 flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-card-border bg-white text-[15px] font-semibold text-ink hover:bg-bg disabled:opacity-40"
        >
          <RotateCcw className="size-4" aria-hidden />
          Reset to Day 0
        </motion.button>
      </div>
      {error && <p className="mt-3 text-[13px] text-red" role="alert">{error}</p>}
    </Card>
  );
}
