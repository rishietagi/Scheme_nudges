"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { api } from "@/lib/api";
import { cohortColor } from "@/lib/cohorts";
import { useApi } from "@/lib/useApi";
import { EASE } from "@/components/motion/Motion";

/** Hand-pick distributors who haven't joined and give them their own follow-up (a new row in the matrix). */
export function CustomGroupDialog({
  open,
  onClose,
  onCreate,
}: {
  open: boolean;
  onClose: () => void;
  onCreate: (name: string, ids: string[], cta: string | null) => Promise<void>;
}) {
  return <AnimatePresence>{open && <Dialog onClose={onClose} onCreate={onCreate} />}</AnimatePresence>;
}

function Dialog({ onClose, onCreate }: { onClose: () => void; onCreate: (name: string, ids: string[], cta: string | null) => Promise<void> }) {
  const candidates = useApi("candidates", api.planCandidates);
  const catalogue = useApi("catalogue", api.planCatalogue);
  const [name, setName] = useState("Custom group");
  const [q, setQ] = useState("");
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [cta, setCta] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const first = useRef<HTMLInputElement>(null);

  useEffect(() => {
    first.current?.select();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const list = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (candidates.data ?? []).filter(
      (c) => !needle || c.name.toLowerCase().includes(needle) || c.town.toLowerCase().includes(needle) || c.cohort.toLowerCase().includes(needle),
    );
  }, [candidates.data, q]);

  function toggle(id: string) {
    setPicked((p) => {
      const n = new Set(p);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  async function create() {
    setBusy(true);
    try {
      await onCreate(name, [...picked], cta || null);
      onClose();
    } finally {
      setBusy(false);
    }
  }

  return (
    <motion.div className="fixed inset-0 z-50 grid place-items-center p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="absolute inset-0 bg-navy-900/40 backdrop-blur-[2px]" onClick={onClose} aria-hidden />
      <motion.div
        role="dialog"
        aria-modal="true"
        aria-labelledby="cg-title"
        initial={{ opacity: 0, y: 16, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 8, scale: 0.98 }}
        transition={{ duration: 0.3, ease: EASE }}
        className="relative flex max-h-[86vh] w-full max-w-[560px] flex-col rounded-[20px] bg-white shadow-[var(--shadow-lift)]"
      >
        <div className="flex items-start justify-between gap-4 border-b border-card-border px-6 py-5">
          <div>
            <h2 id="cg-title" className="font-display text-[21px] font-semibold text-ink">
              Custom group
            </h2>
            <p className="text-[14px] text-muted">Pick distributors who aren&apos;t participating yet. They leave their cohort row and get this follow-up.</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close" className="grid size-10 shrink-0 place-items-center rounded-xl hover:bg-bg">
            <X className="size-5" aria-hidden />
          </button>
        </div>

        <div className="space-y-4 px-6 pt-5">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-[13px] text-muted">
              Name
              <input
                ref={first}
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 min-h-11 w-full rounded-xl border border-card-border px-3 text-[15px] text-ink"
              />
            </label>
            <label className="block text-[13px] text-muted">
              Follow-up
              <select
                value={cta}
                onChange={(e) => setCta(e.target.value)}
                className="mt-1 min-h-11 w-full rounded-xl border border-card-border bg-white px-3 text-[15px] text-ink"
              >
                <option value="">Let Emami AI pick from their answers</option>
                {(catalogue.data ?? []).map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="relative block">
            <span className="sr-only">Search distributors</span>
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search by name, town or cohort"
              className="min-h-11 w-full rounded-xl border border-card-border pl-9 pr-3 text-[15px] text-ink"
            />
          </label>
        </div>

        <ul className="mt-3 flex-1 overflow-y-auto px-6">
          {list.map((c) => (
            <li key={c.distributor_id} className="border-b border-card-border last:border-0">
              <label className="flex min-h-12 cursor-pointer items-center gap-3 py-2">
                <input
                  type="checkbox"
                  checked={picked.has(c.distributor_id)}
                  onChange={() => toggle(c.distributor_id)}
                  className="size-5 accent-[var(--emami-blue)]"
                />
                <span className="size-2.5 shrink-0 rounded-[3px]" style={{ backgroundColor: cohortColor(c.cohort) }} aria-hidden />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[15px] font-medium text-ink">{c.name}</span>
                  <span className="block truncate text-[12px] text-muted">
                    {c.town} · {c.intent ?? "no reply"} · now in {c.in_group ?? c.cohort}
                  </span>
                </span>
              </label>
            </li>
          ))}
          {candidates.data && list.length === 0 && <li className="py-8 text-center text-[14px] text-muted">Nobody matches.</li>}
        </ul>

        <div className="flex items-center justify-between gap-3 border-t border-card-border px-6 py-4">
          <span className="text-[14px] text-muted">{picked.size} picked</span>
          <button
            type="button"
            disabled={!picked.size || busy}
            onClick={create}
            className="min-h-11 rounded-xl bg-navy-800 px-5 text-[15px] font-semibold text-white hover:bg-navy-900 disabled:opacity-40"
          >
            Add to the plan
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
