"use client";

import { Lock, Sparkles } from "lucide-react";
import type { GeneratedQuestion, Language } from "@/lib/api";

const TYPE_TAG: Record<GeneratedQuestion["type"], string> = {
  quick_reply: "Quick reply",
  rating_1_5: "1–5",
  single_choice: "Pick one",
  open_text: "Optional",
};

/** A generated questionnaire: number, question, where it came from (must ask / Emami AI · why), bucket. */
export function GeneratedList({ questions, lang, cohort }: { questions: GeneratedQuestion[]; lang: Language; cohort: string }) {
  return (
    <ol className="divide-y divide-card-border">
      {questions.map((q, i) => (
        <li key={q.id} className="flex items-start gap-3 py-3.5">
          <span
            className={`grid size-7 shrink-0 place-items-center rounded-lg text-[13px] font-semibold ${
              q.source === "ai" ? "bg-blue-soft text-emami-blue" : q.source === "comment" ? "bg-bg text-muted" : "bg-navy-800 text-white"
            }`}
          >
            {i + 1}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[15px] text-ink" lang={lang === "Bengali" ? "bn" : lang === "Hindi" ? "hi" : "en"}>
              {q.text[lang] ?? q.text.English}
            </p>
            <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-muted">
              <Source q={q} cohort={cohort} />
              {q.why && <span>{q.why}</span>}
            </p>
          </div>
          <span className="flex shrink-0 flex-col items-end gap-1">
            <span className="rounded-full bg-bg px-2.5 py-0.5 text-[12px] font-medium text-muted">{TYPE_TAG[q.type]}</span>
            {q.bucket !== "Overall" && <span className="text-[11px] text-muted">{q.bucket}</span>}
          </span>
        </li>
      ))}
    </ol>
  );
}

function Source({ q, cohort }: { q: GeneratedQuestion; cohort: string }) {
  if (q.source === "ai")
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-blue-soft px-2 py-0.5 font-semibold text-emami-blue">
        <Sparkles className="size-3" aria-hidden /> Emami AI
      </span>
    );
  if (q.source === "comment") return <span className="rounded-full bg-bg px-2 py-0.5 font-semibold">Always last</span>;
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-orange-soft px-2 py-0.5 font-semibold text-amber">
      {q.locked && <Lock className="size-3" aria-hidden />}
      Must ask · {q.source === "must_all" ? "everyone" : cohort}
    </span>
  );
}
