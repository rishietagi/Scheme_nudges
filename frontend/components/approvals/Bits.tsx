"use client";

import { motion } from "motion/react";
import { Check, X } from "lucide-react";
import type { PlanRow, PlanStatus } from "@/lib/api";
import { cohortColor, isCohort } from "@/lib/cohorts";
import { EASE } from "@/components/motion/Motion";

export function DecisionButtons({
  status,
  name,
  disabled,
  onDecide,
  size = "md",
}: {
  status: PlanStatus;
  name: string;
  disabled: boolean;
  onDecide: (d: "Approved" | "Rejected") => void;
  size?: "md" | "sm";
}) {
  const box = size === "md" ? "size-11" : "size-10";
  const on = (s: PlanStatus) => status === s;
  return (
    <div className="flex justify-end gap-2">
      <motion.button
        type="button"
        whileTap={{ scale: 0.92 }}
        aria-label={`Approve ${name}`}
        aria-pressed={on("Approved")}
        disabled={disabled}
        onClick={() => onDecide("Approved")}
        className={`grid ${box} place-items-center rounded-xl transition-colors disabled:cursor-not-allowed ${
          on("Approved") ? "bg-green-text text-white" : "bg-green-soft text-green-text hover:brightness-95"
        } ${on("Rejected") ? "opacity-40" : ""}`}
      >
        <Check className="size-5" strokeWidth={2.25} aria-hidden />
      </motion.button>
      <motion.button
        type="button"
        whileTap={{ scale: 0.92 }}
        aria-label={`Reject ${name}`}
        aria-pressed={on("Rejected")}
        disabled={disabled}
        onClick={() => onDecide("Rejected")}
        className={`grid ${box} place-items-center rounded-xl transition-colors disabled:cursor-not-allowed ${
          on("Rejected") ? "bg-red text-white" : "bg-red-soft text-red hover:brightness-95"
        } ${on("Approved") ? "opacity-40" : ""}`}
      >
        <X className="size-5" strokeWidth={2.25} aria-hidden />
      </motion.button>
    </div>
  );
}

export function PriorityPill({ p }: { p: PlanRow["priority"] }) {
  const cls = { High: "bg-red-soft text-red", Medium: "bg-orange-soft text-amber", Low: "bg-[#EEF1F5] text-muted" }[p];
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-[13px] font-medium ${cls}`}>{p}</span>;
}

export function ConfidenceBar({ value }: { value: number | null }) {
  if (value === null)
    return (
      <span className="flex items-center gap-3">
        <span className="h-2 w-28 rounded-full bg-track" />
        <span className="w-10 text-right font-semibold text-ink">–</span>
      </span>
    );
  const color = value >= 0.7 ? "var(--green-text)" : "var(--orange)";
  return (
    <span className="flex items-center gap-3">
      <span className="h-2 w-28 overflow-hidden rounded-full bg-track">
        <motion.span
          className="block h-full origin-left rounded-full"
          style={{ backgroundColor: color }}
          initial={{ scaleX: 0 }}
          animate={{ scaleX: value }}
          transition={{ duration: 0.7, ease: EASE }}
        />
      </span>
      <span className="w-10 text-right font-semibold text-ink tabular">{Math.round(value * 100)}%</span>
    </span>
  );
}

export function GroupDot({ row }: { row: PlanRow }) {
  const color =
    row.group_type === "individual_group" ? "var(--navy-800)" : isCohort(row.group_name) ? cohortColor(row.group_name) : "var(--orange-light)";
  return <span className="size-3 shrink-0 rounded-[4px]" style={{ backgroundColor: color }} aria-hidden />;
}
