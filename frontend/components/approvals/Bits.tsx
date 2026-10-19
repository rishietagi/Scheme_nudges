"use client";

import { motion } from "motion/react";
import { Check, Pencil, Undo2, X } from "lucide-react";
import type { PlanRow, PlanStatus } from "@/lib/api";
import { cohortColor, isCohort } from "@/lib/cohorts";
import { InfoTip } from "@/components/cards/InfoTip";

/** Accept · Modify · Reject. Modify opens the editor (different action and/or message); saving it also accepts. */
export function DecisionButtons({
  status,
  modified = false,
  name,
  disabled,
  onDecide,
  onModify,
  size = "md",
}: {
  status: PlanStatus;
  modified?: boolean;
  name: string;
  disabled: boolean;
  onDecide: (d: "Approved" | "Rejected") => void;
  onModify?: () => void;
  size?: "md" | "sm";
}) {
  const box = size === "md" ? "size-11" : "size-10";
  const accepted = status === "Approved" && !modified;
  const rejected = status === "Rejected";
  return (
    <div className="flex justify-end gap-2">
      <motion.button
        type="button"
        whileTap={{ scale: 0.92 }}
        aria-label={`Accept the suggestion for ${name}`}
        title="Accept"
        aria-pressed={accepted}
        disabled={disabled}
        onClick={() => onDecide("Approved")}
        className={`grid ${box} place-items-center rounded-xl transition-colors disabled:cursor-not-allowed ${
          accepted ? "bg-green-text text-white" : "bg-green-soft text-green-text hover:brightness-95"
        } ${rejected || modified ? "opacity-40" : ""}`}
      >
        <Check className="size-5" strokeWidth={2.25} aria-hidden />
      </motion.button>
      {onModify && (
        <motion.button
          type="button"
          whileTap={{ scale: 0.92 }}
          aria-label={`Modify the suggestion for ${name}`}
          title="Modify"
          aria-pressed={modified}
          disabled={disabled}
          onClick={onModify}
          className={`grid ${box} place-items-center rounded-xl transition-colors disabled:cursor-not-allowed ${
            modified ? "bg-emami-blue text-white" : "bg-blue-soft text-emami-blue hover:brightness-95"
          } ${rejected || accepted ? "opacity-40" : ""}`}
        >
          <Pencil className="size-[18px]" strokeWidth={2.25} aria-hidden />
        </motion.button>
      )}
      <motion.button
        type="button"
        whileTap={{ scale: 0.92 }}
        aria-label={`Reject the suggestion for ${name}`}
        title="Reject"
        aria-pressed={rejected}
        disabled={disabled}
        onClick={() => onDecide("Rejected")}
        className={`grid ${box} place-items-center rounded-xl transition-colors disabled:cursor-not-allowed ${
          rejected ? "bg-red text-white" : "bg-red-soft text-red hover:brightness-95"
        } ${status === "Approved" ? "opacity-40" : ""}`}
      >
        <X className="size-5" strokeWidth={2.25} aria-hidden />
      </motion.button>
    </div>
  );
}

export function PriorityPill({ p, note }: { p: PlanRow["priority"]; note?: string }) {
  const cls = { High: "bg-red-soft text-red", Medium: "bg-orange-soft text-amber", Low: "bg-[#EEF1F5] text-muted" }[p];
  return (
    <span className="inline-flex items-center gap-1">
      <span className={`inline-flex rounded-full px-2.5 py-1 text-[13px] font-medium ${cls}`}>{p}</span>
      {note && (
        <InfoTip label={`Why ${p.toLowerCase()} priority`} align="right">
          {note}
        </InfoTip>
      )}
    </span>
  );
}

/** Shown under an action Rahul changed: what Emami AI had suggested, his note, and a way back. */
export function ModifiedNote({ row, locked, onRestore }: { row: PlanRow; locked: boolean; onRestore: () => void }) {
  if (!row.modified) return null;
  return (
    <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px]">
      <span className="rounded-full bg-blue-soft px-2 py-0.5 font-semibold text-emami-blue">Modified by you</span>
      {row.was_label && <span className="text-muted">Emami AI suggested: {row.was_label.toLowerCase()}</span>}
      {row.note && <span className="text-muted">· “{row.note}”</span>}
      {!locked && (
        <button
          type="button"
          onClick={onRestore}
          className="inline-flex min-h-8 items-center gap-1 font-semibold text-emami-blue hover:underline"
        >
          <Undo2 className="size-3.5" aria-hidden /> Restore suggestion
        </button>
      )}
    </span>
  );
}

export function GroupDot({ row }: { row: PlanRow }) {
  const color =
    row.group_type === "individual_group" ? "var(--navy-800)" : isCohort(row.group_name) ? cohortColor(row.group_name) : "var(--orange-light)";
  return <span className="size-3 shrink-0 rounded-[4px]" style={{ backgroundColor: color }} aria-hidden />;
}
