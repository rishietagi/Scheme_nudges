"use client";

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useState } from "react";
import { Check, CheckCheck, Plus } from "lucide-react";
import { api, type PlanRow } from "@/lib/api";
import { useSim, useViewDay } from "@/lib/sim";
import { useApi } from "@/lib/useApi";
import { Card } from "@/components/cards/Card";
import { EASE } from "@/components/motion/Motion";
import { LoopStepper } from "@/components/loop-stepper/LoopStepper";
import { PageHeader } from "@/components/shell/PageHeader";
import { CustomGroupDialog } from "./CustomGroupDialog";
import { MatrixTable } from "./MatrixTable";
import { ModifyDialog } from "./ModifyDialog";

export function ApprovalsView() {
  const { day, live } = useViewDay();
  const { apply } = useSim();
  const [version, setVersion] = useState(0);
  const [dialog, setDialog] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const plan = useApi(`plan:${day.toFixed(2)}:${version}`, () => api.plan(day));
  const p = plan.data;
  // Decisions stay open on Day 7 until the clock moves on (Play / Next stage).
  const locked = !live || !p || p.day > 7.4168;
  const canBulk = !!p && p.rows.some((r) => r.status === "Pending");
  const [editing, setEditing] = useState<PlanRow | null>(null);

  async function act(fn: () => Promise<Parameters<typeof apply>[0]>) {
    setError(null);
    try {
      apply(await fn());
      setVersion((v) => v + 1);
    } catch {
      setError("That didn't go through. Try again.");
    }
  }

  const decide = (row: PlanRow, d: "Approved" | "Rejected") => act(() => api.planDecide(row.row_id, d));
  const restore = (row: PlanRow) => act(() => api.planRestore(row.row_id));

  return (
    <>
      <PageHeader eyebrow={`Next best actions · cohort + survey · ${p?.plan_day_label ?? "Day 7 · Thu 8 Oct"}`} title="Accept, modify or reject the next best actions" />
      <LoopStepper />

      {!p ? null : !p.ready ? (
        <Card className="grid min-h-60 place-items-center p-8 text-center">
          <div>
            <p className="font-display text-[19px] font-semibold text-ink">The next best actions are ready on Day 7 at 10:00</p>
            <p className="mt-1 text-[14px] text-muted">
              It uses every survey answer that passed the sanity checks.{" "}
              <Link href="/simulation" className="font-semibold text-emami-blue hover:underline">
                Run the loop
              </Link>
            </p>
          </div>
        </Card>
      ) : (
        <>
          <Card className="mb-5 flex flex-col gap-4 p-6 lg:flex-row lg:items-center lg:justify-between">
            <AnimatePresence mode="wait">
              <motion.p
                key={p.sent ? "sent" : p.decided ? "decided" : "open"}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25, ease: EASE }}
                className="max-w-[720px] text-[16px] leading-relaxed text-ink"
              >
                {p.sent ? (
                  <>
                    <strong className="font-semibold">Actions went out on Day 8 · {p.send_label}.</strong> Results show on the Day-30 page.
                  </>
                ) : p.decided ? (
                  <>
                    <strong className="font-semibold">All decided.</strong> Accepted actions go out tomorrow, <strong className="font-semibold">{p.send_label}</strong>, in
                    each distributor&apos;s own language. You can still change a decision until the clock moves on.
                  </>
                ) : (
                  <>
                    <strong className="font-semibold">{p.not_joined} distributors aren&apos;t participating yet.</strong> Each cohort gets one next best action, chosen from its performance and its survey answers;{" "}
                    {p.individual} people get a personal one. Accept, modify or reject each. Accepted actions go out tomorrow, <strong className="font-semibold">{p.send_label}</strong>, in each
                    distributor&apos;s own language.
                  </>
                )}
              </motion.p>
            </AnimatePresence>
            <div className="flex shrink-0 flex-wrap gap-2">
              {!p.decided && (
                <motion.button
                  type="button"
                  whileTap={{ scale: 0.97 }}
                  disabled={locked || !canBulk}
                  onClick={() => act(api.planAcceptAll)}
                  className="flex min-h-12 items-center gap-2 rounded-xl bg-navy-800 px-5 text-[15px] font-semibold text-white hover:bg-navy-900 disabled:opacity-40"
                >
                  <Check className="size-5" aria-hidden />
                  Accept all remaining
                </motion.button>
              )}
              {p.decided && !p.sent && (
                <span className="flex min-h-12 items-center gap-2 rounded-xl bg-green-soft px-5 text-[15px] font-semibold text-green-text">
                  <CheckCheck className="size-5" aria-hidden />
                  Ready to send
                </span>
              )}
              <motion.button
                type="button"
                whileTap={{ scale: 0.97 }}
                disabled={locked}
                onClick={() => setDialog(true)}
                className="flex min-h-12 items-center gap-2 rounded-xl border border-card-border bg-white px-5 text-[15px] font-semibold text-ink hover:bg-bg disabled:opacity-40"
              >
                <Plus className="size-5" aria-hidden />
                Custom group
              </motion.button>
            </div>
          </Card>

          <MatrixTable rows={p.rows} locked={locked} onDecide={decide} onModify={setEditing} onRestore={restore} />

          {error && (
            <p className="mt-3 text-[14px] text-red" role="alert">
              {error}
            </p>
          )}
          <p className="mt-4 text-[14px] text-muted">
            Priority = sales at stake (predicted uplift of those not participating yet), ranked into thirds. Click an action to read the
            message; ✎ to change it.
          </p>
        </>
      )}

      <ModifyDialog
        row={editing}
        onClose={() => setEditing(null)}
        onSave={async (body) => {
          if (editing) await act(() => api.planModify(editing.row_id, body));
        }}
      />
      <CustomGroupDialog
        open={dialog}
        onClose={() => setDialog(false)}
        onCreate={(name, ids, cta) => act(() => api.planCustomGroup(name, ids, cta))}
      />
    </>
  );
}
