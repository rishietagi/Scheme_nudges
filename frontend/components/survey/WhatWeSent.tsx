"use client";

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { ArrowRight, MessageCircle, Sparkles } from "lucide-react";
import type { CohortName, Language, SurveyQuestions } from "@/lib/api";
import { COHORT_ORDER } from "@/lib/cohorts";
import { Card } from "@/components/cards/Card";
import { EASE } from "@/components/motion/Motion";

const LANG_LABEL: Record<Language, string> = { English: "English", Bengali: "বাংলা", Hindi: "हिन्दी" };
const INTENT_TONE: Record<string, string> = {
  "I've enrolled": "bg-green-soft text-green-text",
  "I'll enrol": "bg-blue-soft text-emami-blue",
  "Explain again": "bg-orange-soft text-amber",
  "Explain in Bengali": "bg-orange-soft text-amber",
  "Talk to my ASM": "bg-blue-soft text-emami-blue",
};

/** The cohort-tailored nudge + survey, exactly as sent (keep this design — the client liked it). */
export function WhatWeSent({
  data,
  cohort,
  lang,
  onCohort,
  onLang,
}: {
  data: SurveyQuestions | undefined;
  cohort: CohortName;
  lang: Language;
  onCohort: (c: CohortName) => void;
  onLang: (l: Language) => void;
}) {
  const [q1, ...rest] = data?.questions ?? [];
  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-[19px] font-semibold text-ink">What we sent, by cohort</h2>
        <div className="flex rounded-full bg-[#E8ECF1] p-1" role="group" aria-label="Message language">
          {(Object.keys(LANG_LABEL) as Language[]).map((l) => (
            <button
              key={l}
              type="button"
              aria-pressed={lang === l}
              onClick={() => onLang(l)}
              className={`relative min-h-9 rounded-full px-3.5 text-[14px] font-medium ${lang === l ? "text-ink" : "text-muted hover:text-ink"}`}
            >
              {lang === l && (
                <motion.span layoutId="lang-pill" className="absolute inset-0 rounded-full bg-white shadow-[var(--shadow-card)]" transition={{ duration: 0.3, ease: EASE }} />
              )}
              <span className="relative">{LANG_LABEL[l]}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2 border-b border-card-border pb-4" role="group" aria-label="Cohort">
        {COHORT_ORDER.map((c) => (
          <button
            key={c}
            type="button"
            aria-pressed={cohort === c}
            onClick={() => onCohort(c)}
            className={`relative min-h-10 rounded-full border px-4 text-[14px] font-medium transition-colors ${
              cohort === c ? "border-transparent text-white" : "border-card-border text-ink hover:bg-bg"
            }`}
          >
            {cohort === c && <motion.span layoutId="cohort-pill" className="absolute inset-0 rounded-full bg-navy-800" transition={{ duration: 0.35, ease: EASE }} />}
            <span className="relative">{c}</span>
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {data && (
          <motion.div
            key={`${data.cohort}:${data.language}`}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
          >
            <div className="mt-4 rounded-2xl bg-bg p-4">
              <p className="flex items-center gap-2 text-[12px] font-semibold uppercase tracking-[0.1em] text-muted">
                <MessageCircle className="size-4 text-emami-blue" aria-hidden />
                Nudge message
              </p>
              <p className="mt-1.5 text-[15px] leading-relaxed text-ink" lang={lang === "Bengali" ? "bn" : lang === "Hindi" ? "hi" : "en"}>
                {data.nudge_text}
              </p>
              <p className="mt-2 text-[12px] text-muted">
                {data.nudge_note} · example: {data.example_distributor}
              </p>
            </div>

            {q1 && (
              <div className="mt-4 rounded-2xl border border-card-border p-4">
                <p className="flex items-start gap-3 text-[15px] font-semibold text-ink">
                  <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-navy-800 text-[13px] text-white">1</span>
                  {q1.text}
                </p>
                <div className="mt-3 flex flex-wrap gap-2 pl-10">
                  {q1.options.map((o) => (
                    <span key={o.value} className={`rounded-full px-3 py-1 text-[14px] font-medium ${INTENT_TONE[o.value] ?? "bg-bg text-ink"}`}>
                      {o.label}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <ol className="mt-2">
              {rest.map((q, i) => (
                <li key={q.id} className="flex items-start gap-3 border-b border-card-border py-3.5 last:border-0">
                  <span
                    className={`grid size-7 shrink-0 place-items-center rounded-lg text-[13px] font-semibold ${
                      q.source === "ai" ? "bg-blue-soft text-emami-blue" : "bg-bg text-ink"
                    }`}
                  >
                    {i + 2}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[15px] text-ink">
                      {q.text}
                      {q.type === "single_choice" && <span className="text-muted"> {q.options.map((o) => o.label).join(" · ")}</span>}
                    </p>
                    {q.source !== "comment" && (
                      <p className="mt-1 text-[12px] text-muted">
                        {q.source === "ai" ? (
                          <span className="inline-flex items-center gap-1 font-semibold text-emami-blue">
                            <Sparkles className="size-3" aria-hidden /> Emami AI
                          </span>
                        ) : (
                          <span className="font-semibold text-amber">Must ask{q.source === "must_cohort" ? ` · ${cohort}` : ""}</span>
                        )}
                        {q.bucket && q.bucket !== "Overall" ? ` · ${q.bucket}` : ""}
                      </p>
                    )}
                  </div>
                  {q.tag && <span className="shrink-0 rounded-full bg-bg px-2.5 py-0.5 text-[12px] font-medium text-muted">{q.tag}</span>}
                </li>
              ))}
            </ol>
            <Link href="/setup/survey" className="mt-2 inline-flex min-h-11 items-center gap-1 text-[14px] font-semibold text-emami-blue hover:underline">
              Change the survey for the next cycle <ArrowRight className="size-4" aria-hidden />
            </Link>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
