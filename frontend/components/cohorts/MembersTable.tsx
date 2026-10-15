"use client";

import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import Link from "next/link";
import { ChevronDown, Plus } from "lucide-react";
import type { DistributorRow } from "@/lib/api";
import { Card, Pill } from "@/components/cards/Card";
import { EASE } from "@/components/motion/Motion";

const FIRST = 7;

/** Cohort members, plain columns, ≤ 7 rows before "Show all". */
export function MembersTable({
  cohort,
  rows,
  selectedId,
  onSelect,
  cycle,
}: {
  cohort: string;
  rows: DistributorRow[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  cycle: boolean;
}) {
  const [expandedFor, setExpandedFor] = useState<string | null>(null);
  const showAll = expandedFor === cohort;
  const visible = showAll ? rows : rows.slice(0, FIRST);

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-3 px-6 pb-4 pt-5">
        <div>
          <h2 className="font-display text-[19px] font-semibold text-ink">
            {cohort} · {rows.length} distributors
          </h2>
          <p className="mt-0.5 text-[14px] text-muted">
            Showing {visible.length} · {cycle ? "how each one replied and what happened" : "why each one is in this cohort on Day 0"}
          </p>
        </div>
        <Link
          href="/approvals"
          className="flex min-h-11 items-center gap-2 rounded-xl border border-card-border px-4 text-[14px] font-semibold text-ink hover:bg-bg"
        >
          <Plus className="size-4" aria-hidden />
          Custom group
        </Link>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-left">
          <thead>
            <tr className="border-y border-card-border text-[12px] font-semibold uppercase tracking-[0.08em] text-muted">
              <th scope="col" className="w-[36%] px-6 py-3 font-semibold">Distributor</th>
              <th scope="col" className="px-3 py-3 font-semibold">{cycle ? "Replied on Day 0" : "Why this cohort"}</th>
              <th scope="col" className="px-3 py-3 font-semibold">{cycle ? "Festive Scheme" : "Last scheme"}</th>
              <th scope="col" className="px-6 py-3 font-semibold">Language</th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence initial={false}>
              {visible.map((r, i) => {
                const active = r.distributor_id === selectedId;
                return (
                  <motion.tr
                    key={r.distributor_id}
                    layout
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.3, ease: EASE, delay: Math.min(i, 8) * 0.025 }}
                    onClick={() => onSelect(r.distributor_id)}
                    className={`cursor-pointer border-b border-card-border transition-colors last:border-0 ${
                      active ? "bg-orange-soft/60" : "hover:bg-bg"
                    }`}
                  >
                    <td className="px-6 py-3.5">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelect(r.distributor_id);
                        }}
                        aria-pressed={active}
                        className="text-left"
                      >
                        <span className="block text-[15px] font-semibold text-ink">{r.name}</span>
                        <span className="block text-[13px] text-muted">
                          {r.town}
                          {r.classification === "A" && " · key account"}
                        </span>
                      </button>
                    </td>
                    {cycle ? (
                      <>
                        <td className="px-3 py-3.5 text-[14px] text-ink">
                          {r.intent ?? <span className="text-muted">No reply</span>}
                          {r.flagged && <span className="block text-[12px] text-red">(flagged)</span>}
                        </td>
                        <td className="px-3 py-3.5">
                          {r.joined_day !== null ? <Pill tone="green">Joined · Day {r.joined_day}</Pill> : <Pill>Not joined</Pill>}
                        </td>
                        <td className="px-6 py-3.5 text-[14px] text-ink">
                          {r.language_now}
                          {r.language_changed && <span className="block text-[12px] text-muted">(was {r.language_on_file})</span>}
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-3 py-3.5 text-[13px] leading-snug text-muted">{r.reasons.join(" · ")}</td>
                        <td className="px-3 py-3.5">
                          {r.joined_last_scheme ? <Pill tone="green">Joined</Pill> : <Pill>Didn&apos;t join</Pill>}
                        </td>
                        <td className="px-6 py-3.5 text-[14px] text-ink">{r.language_on_file}</td>
                      </>
                    )}
                  </motion.tr>
                );
              })}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
      {rows.length > FIRST && (
        <button
          type="button"
          onClick={() => setExpandedFor(showAll ? null : cohort)}
          className="flex min-h-12 w-full items-center gap-2 border-t border-card-border px-6 text-[14px] font-semibold text-emami-blue hover:bg-bg"
          aria-expanded={showAll}
        >
          <motion.span animate={{ rotate: showAll ? 180 : 0 }} transition={{ duration: 0.3, ease: EASE }}>
            <ChevronDown className="size-4" aria-hidden />
          </motion.span>
          {showAll ? "Show fewer" : `Show all ${rows.length}`}
        </button>
      )}
    </Card>
  );
}
