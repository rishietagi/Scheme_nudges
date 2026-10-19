"use client";

import { AnimatePresence, motion } from "motion/react";
import { Fragment, useState } from "react";
import { ChevronDown, MessageSquareText } from "lucide-react";
import type { PlanRow } from "@/lib/api";
import { Card } from "@/components/cards/Card";
import { EASE } from "@/components/motion/Motion";
import { InfoTip } from "@/components/cards/InfoTip";
import { DecisionButtons, GroupDot, ModifiedNote, PriorityPill } from "./Bits";

type Decide = (row: PlanRow, d: "Approved" | "Rejected") => void;
type Act = (row: PlanRow) => void;

export const PRIORITY_RULE =
  "Priority = sales at stake: the predicted uplift (₹) of the people in this row who aren't participating yet — what " +
  "October should add if they join. Rows are ranked by it: the top third are High, the middle third Medium, the bottom " +
  "third Low. People in Individual attention are ranked among themselves.";

/** Group · Who · Next best action · Priority · Decision. Each action shows what drove it: cohort + survey. */
export function MatrixTable({
  rows,
  locked,
  onDecide,
  onModify,
  onRestore,
}: {
  rows: PlanRow[];
  locked: boolean;
  onDecide: Decide;
  onModify: Act;
  onRestore: Act;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const [showPeople, setShowPeople] = useState(true);
  const ia = rows.find((r) => r.group_type === "individual_group");

  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[880px] table-fixed text-left">
          <colgroup>
            <col className="w-[20%]" />
            <col className="w-[7%]" />
            <col className="w-[43%]" />
            <col className="w-[13%]" />
            <col className="w-[17%]" />
          </colgroup>
          <thead>
            <tr className="border-b border-card-border text-[12px] font-semibold uppercase tracking-[0.08em] text-muted">
              <th scope="col" className="px-6 py-4">Group</th>
              <th scope="col" className="px-3 py-4">Who</th>
              <th scope="col" className="px-3 py-4">
                <span className="flex items-center gap-1">
                  Next best action
                  <InfoTip label="How the next best action is chosen" align="left">
                    Emami AI starts from the cohort (business potential × performance) and adds what the survey said: each
                    distributor&apos;s answer points to one action, and the cohort gets the one most of them point to. Code picks
                    the action from a fixed catalogue; the AI only writes the message. Click an action to read the message.
                  </InfoTip>
                </span>
              </th>
              <th scope="col" className="px-3 py-4">
                <span className="flex items-center gap-1">
                  Priority
                  <InfoTip label="How priority is worked out">{PRIORITY_RULE}</InfoTip>
                </span>
              </th>
              <th scope="col" className="px-6 py-4 text-right">
                <span className="inline-flex items-center gap-1">
                  Decision
                  <InfoTip label="What accept, modify and reject do" align="right">
                    ✓ Accept sends Emami AI&apos;s suggestion. ✎ Modify lets you pick another action or change the message, then
                    accepts it. ✗ Reject sends nothing to this group. You can change your mind until the clock moves past Day 7.
                  </InfoTip>
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const expanded = open === r.row_id;
              const isIa = r.group_type === "individual_group";
              return (
                <Fragment key={r.row_id}>
                  <motion.tr
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.35, ease: EASE, delay: i * 0.04 }}
                    className={`border-b border-card-border ${isIa ? "bg-bg/70" : ""}`}
                  >
                    <td className="px-6 py-4">
                      <span className="flex items-center gap-3 text-[15px] font-semibold text-ink">
                        <GroupDot row={r} />
                        {r.group_name}
                        {r.group_type === "custom" && <span className="rounded-full bg-orange-soft px-2 py-0.5 text-[11px] font-medium text-amber">custom</span>}
                      </span>
                    </td>
                    <td className="px-3 py-4 text-[15px] font-semibold text-ink tabular">{r.members}</td>
                    <td className="px-3 py-4">
                      {isIa ? (
                        <>
                          <span className="block text-[15px] font-medium text-ink">{r.label}</span>
                          <span className="block text-[13px] text-muted">{r.reason}</span>
                        </>
                      ) : (
                        <button
                          type="button"
                          aria-expanded={expanded}
                          onClick={() => setOpen(expanded ? null : r.row_id)}
                          className="group text-left"
                        >
                          <span className="flex items-center gap-1.5 text-[15px] font-medium text-ink">
                            {r.label}
                            <MessageSquareText className="size-3.5 text-muted opacity-0 transition-opacity group-hover:opacity-100" aria-hidden />
                          </span>
                          {r.cohort_note ? <Drivers cohort={r.cohort_note} survey={r.survey_note} /> : <span className="block text-[13px] text-muted">{r.reason}</span>}
                        </button>
                      )}
                      {!isIa && <ModifiedNote row={r} locked={locked} onRestore={() => onRestore(r)} />}
                    </td>
                    <td className="px-3 py-4">
                      <PriorityPill p={r.priority} note={r.priority_note} />
                    </td>
                    <td className="px-6 py-4">
                      <DecisionButtons
                        status={r.status}
                        modified={r.modified}
                        name={r.group_name}
                        disabled={locked}
                        onDecide={(d) => onDecide(r, d)}
                        onModify={isIa ? undefined : () => onModify(r)}
                      />
                    </td>
                  </motion.tr>
                  <AnimatePresence initial={false}>
                    {expanded && (
                      <tr className="border-b border-card-border bg-bg/60">
                        <td colSpan={5} className="p-0">
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.3, ease: EASE }}
                            className="overflow-hidden"
                          >
                            <Preview row={r} />
                          </motion.div>
                        </td>
                      </tr>
                    )}
                  </AnimatePresence>
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {ia && (
        <div className="border-t border-card-border px-4 pb-5 pt-2 sm:px-6">
          <button
            type="button"
            aria-expanded={showPeople}
            onClick={() => setShowPeople(!showPeople)}
            className="flex min-h-11 items-center gap-2 text-[15px] font-semibold text-emami-blue hover:underline"
          >
            <motion.span animate={{ rotate: showPeople ? 0 : -90 }} transition={{ duration: 0.25 }}>
              <ChevronDown className="size-4" aria-hidden />
            </motion.span>
            {showPeople ? "Hide" : "Show"} individual attention · {ia.children.length} people
          </button>
          <AnimatePresence initial={false}>
            {showPeople && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.35, ease: EASE }}
                className="overflow-hidden"
              >
                <People people={ia.children} locked={locked} onDecide={onDecide} onModify={onModify} onRestore={onRestore} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </Card>
  );
}

const FIRST = 5;

function People({
  people,
  locked,
  onDecide,
  onModify,
  onRestore,
}: {
  people: PlanRow[];
  locked: boolean;
  onDecide: Decide;
  onModify: Act;
  onRestore: Act;
}) {
  const [all, setAll] = useState(false);
  const shown = all ? people : people.slice(0, FIRST);
  const rest = people.slice(FIRST);
  return (
    <div className="mt-1 rounded-2xl border border-card-border">
      <ul>
        {shown.map((p) => (
          <motion.li
            key={p.row_id}
            layout
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-1 items-center gap-3 border-b border-card-border px-5 py-3.5 last:border-0 md:grid-cols-[1.2fr_1.4fr_120px_auto]"
          >
            <span>
              <span className="block text-[16px] font-semibold text-ink">{p.group_name}</span>
              <span className="block text-[13px] text-muted">
                {p.reason}
                {p.cohort_note ? ` · ${p.cohort_note}` : ""}
              </span>
            </span>
            <span className="text-[15px] text-ink">
              {p.label}
              <ModifiedNote row={p} locked={locked} onRestore={() => onRestore(p)} />
            </span>
            <span className="md:text-right">
              <PriorityPill p={p.priority} note={p.priority_note} />
            </span>
            <DecisionButtons
              status={p.status}
              modified={p.modified}
              name={p.group_name}
              disabled={locked}
              size="sm"
              onDecide={(d) => onDecide(p, d)}
              onModify={() => onModify(p)}
            />
          </motion.li>
        ))}
      </ul>
      {rest.length > 0 && (
        <button
          type="button"
          onClick={() => setAll(!all)}
          className="block min-h-11 w-full px-5 py-3 text-left text-[14px] text-muted hover:bg-bg"
        >
          {all ? (
            "Show fewer"
          ) : (
            <>
              + {rest.length} more · {rest.slice(0, 3).map((p) => p.group_name).join(", ")}
              {rest.length > 3 && ` and ${rest.length - 3} others`}
            </>
          )}
        </button>
      )}
    </div>
  );
}

function Preview({ row }: { row: PlanRow }) {
  return (
    <div className="grid gap-4 px-6 py-4 md:grid-cols-[1fr_1fr_0.8fr]">
      {(["English", "Bengali"] as const).map(
        (l) =>
          row.preview[l] && (
            <div key={l}>
              <p className="text-[12px] font-semibold uppercase tracking-[0.08em] text-muted">Message · {l === "English" ? "English" : "বাংলা"}</p>
              <p className="mt-1 text-[14px] leading-relaxed text-ink" lang={l === "Bengali" ? "bn" : "en"}>
                {row.preview[l]}
              </p>
            </div>
          ),
      )}
      {row.why && (
        <div>
          <p className="text-[12px] font-semibold uppercase tracking-[0.08em] text-muted">Why · Emami AI</p>
          <p className="mt-1 text-[14px] leading-relaxed text-ink">{row.why}</p>
        </div>
      )}
    </div>
  );
}

/** "Cohort + survey → next best action": the two inputs behind a row, one short line each. */
function Drivers({ cohort, survey }: { cohort: string; survey: string | null }) {
  return (
    <span className="mt-1 block space-y-0.5 text-[13px] leading-snug">
      <span className="block text-muted">
        <span className="mr-1.5 inline-block w-14 font-semibold text-ink/70">Cohort</span>
        {cohort}
      </span>
      {survey && (
        <span className="block text-muted">
          <span className="mr-1.5 inline-block w-14 font-semibold text-ink/70">Survey</span>
          {survey}
        </span>
      )}
    </span>
  );
}
