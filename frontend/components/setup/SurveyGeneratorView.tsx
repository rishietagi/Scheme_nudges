"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { Lock, Plus, RotateCcw, Send, X } from "lucide-react";
import { api, type CohortName, type Language, type MustAsk, type SurveyConfig, type SurveyConfigIn } from "@/lib/api";
import { COHORT_HEX } from "@/lib/cohorts";
import { Card, CardTitle, Pill } from "@/components/cards/Card";
import { EASE } from "@/components/motion/Motion";
import { PageHeader } from "@/components/shell/PageHeader";
import { Placeholder } from "@/components/cards/Placeholder";
import { GeneratedList } from "@/components/survey/GeneratedList";

const LANG_LABEL: Record<Language, string> = { English: "English", Bengali: "বাংলা", Hindi: "हिन्दी" };
const OWN = "__own__";

/** Business controls (count, must-ask by scope) on the left; Emami AI's questionnaire per cohort on the right. */
export function SurveyGeneratorView() {
  const [saved, setSaved] = useState<SurveyConfig | null>(null);
  const [draft, setDraft] = useState<SurveyConfigIn | null>(null);
  const [preview, setPreview] = useState<SurveyConfig | null>(null);
  const [cohort, setCohort] = useState<CohortName>("Replace / Reassess");
  const [lang, setLang] = useState<Language>("English");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load(c: SurveyConfig) {
    setSaved(c);
    setPreview(c);
    setDraft({ questions_per_survey: c.questions_per_survey, must_ask: c.must_ask });
  }

  useEffect(() => {
    api.surveyConfig().then(load, () => setError("Can't reach the simulator"));
  }, []);

  const dirty = useMemo(
    () =>
      !!saved &&
      !!draft &&
      JSON.stringify({ n: draft.questions_per_survey, m: draft.must_ask }) !==
        JSON.stringify({ n: saved.questions_per_survey, m: saved.must_ask }),
    [saved, draft],
  );

  useEffect(() => {
    if (!draft || !dirty) return;
    const t = setTimeout(() => api.surveyConfigPreview(draft).then(setPreview, () => {}), 250);
    return () => clearTimeout(t);
  }, [draft, dirty]);

  async function act(fn: () => Promise<SurveyConfig>) {
    setBusy(true);
    try {
      load(await fn());
    } finally {
      setBusy(false);
    }
  }

  const shown = dirty ? preview : saved;
  if (!saved || !draft || !shown) {
    return (
      <>
        <PageHeader eyebrow="Set up · the survey for the next cycle" title="Survey generator" />
        <Placeholder title={error ?? "Loading the survey"} phase={1} lines={3} />
      </>
    );
  }

  const nMust = (c: string) => draft.must_ask.filter((m) => m.scope === "all" || m.scope === c).length;
  const tooMany = shown.cohorts.some((c) => nMust(c.name) > draft.questions_per_survey);

  return (
    <>
      <PageHeader eyebrow="Set up · the survey for the next cycle" title="Survey generator" />

      <Card className="mb-5 flex flex-wrap items-center gap-x-6 gap-y-3 p-5">
        <div>
          <p className="text-[12px] font-semibold uppercase tracking-[0.1em] text-muted">Use case this cycle</p>
          <p className="mt-0.5 text-[16px] font-semibold text-ink">
            {saved.use_case} <span className="font-normal text-muted">· {saved.use_case_detail}</span>
          </p>
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[12px] font-semibold uppercase tracking-[0.1em] text-muted">The question bank also covers</p>
          <p className="mt-1 flex flex-wrap gap-1.5">
            {saved.use_cases
              .filter((u) => u !== "Trade schemes")
              .map((u) => (
                <span key={u} className="rounded-full bg-bg px-2.5 py-0.5 text-[13px] text-ink">
                  {u}
                </span>
              ))}
          </p>
        </div>
      </Card>

      <div className="grid items-start gap-5 xl:grid-cols-[1fr_1.2fr]">
        <div className="space-y-5">
          <Card className="p-6">
            <CardTitle action={saved.customised ? <Pill tone="orange">Edited</Pill> : <Pill>Default</Pill>}>Business controls</CardTitle>
            <label className="mt-4 flex items-center justify-between gap-4 border-b border-card-border pb-4">
              <span>
                <span className="block text-[15px] font-medium text-ink">Questions per survey</span>
                <span className="text-[13px] text-muted">Plus an optional comment at the end</span>
              </span>
              <select
                value={draft.questions_per_survey}
                onChange={(e) => setDraft({ ...draft, questions_per_survey: Number(e.target.value) })}
                className="h-11 rounded-xl border border-card-border bg-white px-3 text-[15px] font-semibold text-ink outline-none focus:border-emami-blue focus:ring-2 focus:ring-blue-soft"
              >
                {Array.from({ length: saved.max_questions - saved.min_questions + 1 }, (_, i) => saved.min_questions + i).map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>

            <h3 className="mt-4 text-[15px] font-medium text-ink">Must ask</h3>
            <p className="text-[13px] text-muted">Asked before anything Emami AI adds. Set one for everyone or for one cohort.</p>
            <ul className="mt-3 space-y-2">
              {draft.must_ask.map((m, i) => (
                <MustRow
                  key={`${m.id}-${m.scope}-${i}`}
                  m={m}
                  label={m.text ?? saved.bank.find((b) => b.id === m.id)?.text ?? m.id}
                  cohorts={shown.cohorts.map((c) => c.name)}
                  onScope={(scope) => setDraft({ ...draft, must_ask: draft.must_ask.map((x, j) => (j === i ? { ...x, scope } : x)) })}
                  onRemove={() => setDraft({ ...draft, must_ask: draft.must_ask.filter((_, j) => j !== i) })}
                />
              ))}
            </ul>
            <AddMust saved={saved} draft={draft} onAdd={(m) => setDraft({ ...draft, must_ask: [...draft.must_ask, m] })} />
            {tooMany && (
              <p className="mt-3 text-[13px] text-amber">Some cohorts have more must-ask questions than the survey length. Raise the number or remove one.</p>
            )}
          </Card>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={!dirty || busy}
              onClick={() => act(() => api.surveyConfigSave(draft))}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-orange px-5 text-[15px] font-semibold text-ink transition-opacity disabled:opacity-40"
            >
              <Send className="size-4" aria-hidden /> Publish for next cycle
            </button>
            <button
              type="button"
              disabled={!saved.customised || busy}
              onClick={() => act(api.surveyConfigReset)}
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
              Published. The running cycle keeps the survey it sent; this one goes out with the next.{" "}
              <Link href="/simulation" className="font-semibold text-emami-blue hover:underline">
                Start a new cycle in Simulation
              </Link>
            </p>
          )}
        </div>

        <Card className="p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle action={dirty ? <Pill tone="blue">Preview</Pill> : null}>What each cohort gets</CardTitle>
            <div className="flex rounded-full bg-[#E8ECF1] p-1" role="group" aria-label="Question language">
              {(Object.keys(LANG_LABEL) as Language[]).map((l) => (
                <button
                  key={l}
                  type="button"
                  aria-pressed={lang === l}
                  onClick={() => setLang(l)}
                  className={`relative min-h-9 rounded-full px-3.5 text-[14px] font-medium ${lang === l ? "text-ink" : "text-muted hover:text-ink"}`}
                >
                  {lang === l && (
                    <motion.span layoutId="gen-lang" className="absolute inset-0 rounded-full bg-white shadow-[var(--shadow-card)]" transition={{ duration: 0.3, ease: EASE }} />
                  )}
                  <span className="relative">{LANG_LABEL[l]}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2 border-b border-card-border pb-4" role="group" aria-label="Cohort">
            {shown.cohorts.map((c) => (
              <button
                key={c.name}
                type="button"
                aria-pressed={cohort === c.name}
                onClick={() => setCohort(c.name)}
                className={`relative inline-flex min-h-10 items-center gap-2 rounded-full border px-4 text-[14px] font-medium transition-colors ${
                  cohort === c.name ? "border-transparent text-white" : "border-card-border text-ink hover:bg-bg"
                }`}
              >
                {cohort === c.name && (
                  <motion.span layoutId="gen-cohort" className="absolute inset-0 rounded-full bg-navy-800" transition={{ duration: 0.35, ease: EASE }} />
                )}
                <span className="relative size-2.5 rounded-[3px]" style={{ backgroundColor: COHORT_HEX[c.color] }} aria-hidden />
                <span className="relative">
                  {c.name} · {c.count}
                </span>
              </button>
            ))}
          </div>
          <p className="mt-3 text-[13px] text-muted">{shown.cohorts.find((c) => c.name === cohort)?.definition}</p>
          <GeneratedList questions={shown.questionnaires[cohort] ?? []} lang={lang} cohort={cohort} />
        </Card>
      </div>
    </>
  );
}

function MustRow({
  m,
  label,
  cohorts,
  onScope,
  onRemove,
}: {
  m: MustAsk;
  label: string;
  cohorts: string[];
  onScope: (s: string) => void;
  onRemove: () => void;
}) {
  return (
    <li className="flex items-center gap-2 rounded-xl border border-card-border px-3 py-2">
      <span className="min-w-0 flex-1 text-[14px] text-ink">
        {m.locked && <Lock className="mr-1.5 inline size-3.5 text-muted" aria-label="Always asked" />}
        {label}
      </span>
      <select
        aria-label="Ask whom"
        value={m.scope}
        disabled={m.locked}
        onChange={(e) => onScope(e.target.value)}
        className="h-10 rounded-lg border border-card-border bg-white px-2 text-[13px] text-ink disabled:bg-bg"
      >
        <option value="all">Everyone</option>
        {cohorts.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
      <button
        type="button"
        aria-label={`Remove ${label}`}
        disabled={m.locked}
        onClick={onRemove}
        className="grid size-10 place-items-center rounded-lg text-muted hover:bg-red-soft hover:text-red disabled:opacity-30 disabled:hover:bg-transparent"
      >
        <X className="size-4" aria-hidden />
      </button>
    </li>
  );
}

function AddMust({ saved, draft, onAdd }: { saved: SurveyConfig; draft: SurveyConfigIn; onAdd: (m: MustAsk) => void }) {
  const [pick, setPick] = useState("");
  const [own, setOwn] = useState("");
  const [scope, setScope] = useState("all");
  const taken = new Set(draft.must_ask.filter((m) => m.scope === scope).map((m) => m.id));
  const groups = saved.use_cases.map((u) => ({ u, qs: saved.bank.filter((b) => b.use_case === u && b.type !== "quick_reply" && !taken.has(b.id)) }));
  const ready = pick === OWN ? own.trim().length > 5 : pick !== "";

  return (
    <div className="mt-4 rounded-xl bg-bg p-3">
      <div className="flex flex-wrap gap-2">
        <select
          aria-label="Question to add"
          value={pick}
          onChange={(e) => setPick(e.target.value)}
          className="h-10 min-w-0 flex-1 rounded-lg border border-card-border bg-white px-2 text-[14px] text-ink"
        >
          <option value="">Add a question from the bank…</option>
          {groups.map(
            (g) =>
              g.qs.length > 0 && (
                <optgroup key={g.u} label={g.u}>
                  {g.qs.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.text}
                    </option>
                  ))}
                </optgroup>
              ),
          )}
          <option value={OWN}>Write our own question…</option>
        </select>
        <select
          aria-label="Ask whom"
          value={scope}
          onChange={(e) => setScope(e.target.value)}
          className="h-10 rounded-lg border border-card-border bg-white px-2 text-[14px] text-ink"
        >
          <option value="all">Everyone</option>
          {saved.cohorts.map((c) => (
            <option key={c.name} value={c.name}>
              {c.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={!ready}
          onClick={() => {
            onAdd(pick === OWN ? { id: "custom", scope, text: own.trim() } : { id: pick, scope });
            setPick("");
            setOwn("");
          }}
          className="inline-flex h-10 items-center gap-1.5 rounded-lg bg-navy-800 px-3 text-[14px] font-semibold text-white disabled:opacity-40"
        >
          <Plus className="size-4" aria-hidden /> Add
        </button>
      </div>
      {pick === OWN && (
        <input
          aria-label="Your question"
          value={own}
          onChange={(e) => setOwn(e.target.value)}
          placeholder="e.g. How likely are you to recommend Emami to another distributor?"
          className="mt-2 h-10 w-full rounded-lg border border-card-border bg-white px-3 text-[14px] text-ink outline-none focus:border-emami-blue"
        />
      )}
      <p className="mt-2 text-[12px] text-muted">Your own questions are asked on a 1–5 scale.</p>
    </div>
  );
}
