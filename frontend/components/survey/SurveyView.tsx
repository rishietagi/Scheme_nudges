"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { api, type CohortName, type FlagItem, type Language } from "@/lib/api";
import { isCohort } from "@/lib/cohorts";
import { useSim, useViewDay } from "@/lib/sim";
import { useApi } from "@/lib/useApi";
import { Card } from "@/components/cards/Card";
import { PageHeader } from "@/components/shell/PageHeader";
import { Stagger, StaggerItem } from "@/components/motion/Motion";
import { FlaggedAnswers, IntentsCard, RatingsCard, RepliesByDay, SanityCard } from "./ResultsCards";
import { WhatWeSent } from "./WhatWeSent";

const LANGS: Language[] = ["English", "Bengali", "Hindi"];

export function SurveyView() {
  const { day, live } = useViewDay();
  const { apply } = useSim();
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [version, setVersion] = useState(0);

  const rawCohort = params.get("cohort");
  const cohort: CohortName = isCohort(rawCohort) ? rawCohort : "Scheme-hesitant";
  const rawLang = params.get("lang") as Language | null;
  const lang: Language = rawLang && LANGS.includes(rawLang) ? rawLang : "English";
  const dayKey = day.toFixed(2);

  const questions = useApi(`q:${cohort}:${lang}:${dayKey}`, () => api.surveyQuestions(cohort, lang, day));
  const results = useApi(`r:${dayKey}:${version}`, () => api.surveyResults(day));
  const r = results.data;

  function update(k: string, v: string) {
    const p = new URLSearchParams(params.toString());
    p.set(k, v);
    router.replace(`${pathname}?${p.toString()}`, { scroll: false });
  }

  async function decide(item: FlagItem, d: "Keep" | "Drop") {
    apply(await api.flagDecision(item.response_id, d));
    setVersion((v) => v + 1);
  }

  const eyebrow = !r
    ? "Day-0 nudge + survey"
    : !r.sent
      ? "Day-0 nudge + survey · goes out Day 0 · 10:00"
      : r.closed
        ? `Day-0 nudge + survey · closed on Day 7 · ${r.replied} of ${r.total} replied`
        : `Day-0 nudge + survey · open until Day 7 · ${r.replied} of ${r.total} replied so far`;

  return (
    <>
      <PageHeader eyebrow={eyebrow} title="What distributors told us" />
      <div className="grid items-start gap-5 xl:grid-cols-[1.05fr_1fr]">
        <WhatWeSent
          data={questions.data}
          cohort={cohort}
          lang={lang}
          onCohort={(c) => update("cohort", c)}
          onLang={(l) => update("lang", l)}
        />
        {r && r.sent && r.replied > 0 ? (
          <Stagger className="min-w-0 space-y-5">
            <StaggerItem>
              <RepliesByDay r={r} />
            </StaggerItem>
            <StaggerItem>
              <SanityCard r={r} />
            </StaggerItem>
            <StaggerItem>
              <FlaggedAnswers r={r} live={live} onDecide={decide} />
            </StaggerItem>
            <StaggerItem>
              <IntentsCard r={r} />
            </StaggerItem>
            <StaggerItem>
              <RatingsCard r={r} />
            </StaggerItem>
          </Stagger>
        ) : (
          <Card className="grid min-h-60 place-items-center p-8 text-center">
            <div>
              <p className="font-display text-[19px] font-semibold text-ink">{r?.sent ? "Waiting for the first replies" : "The survey goes out on Day 0 at 10:00"}</p>
              <p className="mt-1 text-[14px] text-muted">Press Play or Next stage on the Simulation tab.</p>
            </div>
          </Card>
        )}
      </div>
    </>
  );
}
