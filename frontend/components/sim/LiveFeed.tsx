"use client";

import { AnimatePresence, motion } from "motion/react";
import { useSim } from "@/lib/sim";
import { Card } from "@/components/cards/Card";
import { EASE } from "@/components/motion/Motion";

const AGENT_TONE: Record<string, string> = {
  "Cohort agent": "bg-[#EEF1F5] text-muted",
  "Nudge agent": "bg-blue-soft text-emami-blue",
  "Survey agent": "bg-blue-soft text-emami-blue",
  "CTA agent": "bg-orange-soft text-amber",
  You: "bg-navy-800 text-white",
  Autopilot: "bg-navy-800 text-white",
  Execution: "bg-green-soft text-green-text",
  "Results agent": "bg-green-soft text-green-text",
  Persona: "bg-[#EEF1F5] text-muted",
};

/** Newest first, plain sentences. */
export function LiveFeed() {
  const { feed, online } = useSim();
  return (
    <Card className="flex max-h-[760px] flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-card-border px-5 py-4">
        <h2 className="font-display text-[19px] font-semibold text-ink">Live feed</h2>
        <span className="flex items-center gap-2 text-[12px] text-muted">
          <span className={`size-2 rounded-full ${online ? "bg-green-text" : "bg-grey-cohort"}`} aria-hidden />
          {online ? "Live" : "Offline"}
        </span>
      </div>
      <ol className="flex-1 overflow-y-auto px-5 py-2" aria-live="polite">
        {feed.length === 0 && <li className="py-10 text-center text-[14px] text-muted">Press Play or Next stage to start the loop.</li>}
        <AnimatePresence initial={false}>
          {feed.map((e) => (
            <motion.li
              key={e.event_id}
              layout
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35, ease: EASE }}
              className="border-b border-card-border py-3 last:border-0"
            >
              <div className="flex flex-wrap items-center gap-2 text-[12px] text-muted">
                <span className="tabular">
                  {e.day_label.split(" · ")[0]} · {e.time_label}
                </span>
                <span className={`rounded-full px-2 py-0.5 font-medium ${AGENT_TONE[e.agent] ?? AGENT_TONE["Cohort agent"]}`}>{e.agent}</span>
              </div>
              <p className="mt-1 text-[14px] leading-snug text-ink">{e.text}</p>
            </motion.li>
          ))}
        </AnimatePresence>
      </ol>
    </Card>
  );
}
