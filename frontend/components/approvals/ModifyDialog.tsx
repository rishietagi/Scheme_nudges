"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { Sparkles, X } from "lucide-react";
import { api, type CatalogueItem, type PlanRow } from "@/lib/api";
import { EASE } from "@/components/motion/Motion";

/** Change what Emami AI proposed for a row: pick another action from the catalogue and/or edit the message.
 *  Saving accepts the row with your changes; "Restore suggestion" in the table undoes it. */
export function ModifyDialog({
  row,
  onClose,
  onSave,
}: {
  row: PlanRow | null;
  onClose: () => void;
  onSave: (body: {
    cta_code: string;
    text_en?: string;
    text_bn?: string;
    note?: string;
  }) => Promise<void>;
}) {
  return (
    <AnimatePresence>
      {row && (
        <Editor key={row.row_id} row={row} onClose={onClose} onSave={onSave} />
      )}
    </AnimatePresence>
  );
}

function Editor({
  row,
  onClose,
  onSave,
}: {
  row: PlanRow;
  onClose: () => void;
  onSave: (body: {
    cta_code: string;
    text_en?: string;
    text_bn?: string;
    note?: string;
  }) => Promise<void>;
}) {
  const [items, setItems] = useState<CatalogueItem[] | null>(null);
  const [code, setCode] = useState(row.cta_code ?? "");
  const [en, setEn] = useState(row.template.English ?? "");
  const [bn, setBn] = useState(row.template.Bengali ?? "");
  const [note, setNote] = useState(row.note ?? "");
  const [busy, setBusy] = useState(false);
  const first = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    api.planCatalogue(row.row_id).then(setItems, () => setItems([]));
    const t = setTimeout(() => first.current?.focus(), 80);
    return () => clearTimeout(t);
  }, [row.row_id]);

  function pick(c: CatalogueItem) {
    setCode(c.code);
    if (c.code === row.cta_code) {
      setEn(row.template.English ?? "");
      setBn(row.template.Bengali ?? "");
    } else {
      setEn(c.template.English ?? "");
      setBn(c.template.Bengali ?? "");
    }
  }

  async function save() {
    setBusy(true);
    try {
      await onSave({ cta_code: code, text_en: en, text_bn: bn, note });
      onClose();
    } finally {
      setBusy(false);
    }
  }

  return (
    <motion.div
      className="fixed inset-0 z-50 grid place-items-center bg-ink/40 p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      onKeyDown={(e) => e.key === "Escape" && onClose()}
    >
      <motion.div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modify-title"
        initial={{ y: 12, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 12, opacity: 0 }}
        transition={{ duration: 0.3, ease: EASE }}
        onClick={(e) => e.stopPropagation()}
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-[var(--radius-card)] bg-white p-6 shadow-[var(--shadow-lift)]"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2
              id="modify-title"
              className="font-display text-[20px] font-semibold text-ink"
            >
              Modify the next best action · {row.group_name}
            </h2>
            <p className="mt-1 text-[14px] text-muted">
              <Sparkles
                className="mr-1 inline size-3.5 text-emami-blue"
                aria-hidden
              />
              Emami AI suggested{" "}
              <strong className="font-semibold text-ink">
                {(row.was_label ?? row.label).toLowerCase()}
              </strong>{" "}
              because {row.survey_note ?? row.reason}. Pick another action or
              change the message; saving accepts it with your changes.
            </p>
          </div>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="grid size-11 shrink-0 place-items-center rounded-xl hover:bg-bg"
          >
            <X className="size-5" aria-hidden />
          </button>
        </div>

        <fieldset className="mt-5">
          <legend className="text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">
            Action
          </legend>
          <div className="mt-2 grid gap-2 sm:grid-cols-2" role="radiogroup">
            {(items ?? []).map((c, i) => (
              <button
                key={c.code}
                ref={i === 0 ? first : undefined}
                type="button"
                role="radio"
                aria-checked={code === c.code}
                onClick={() => pick(c)}
                className={`min-h-11 rounded-xl border px-3 py-2.5 text-left transition-colors ${
                  code === c.code
                    ? "border-emami-blue bg-blue-soft"
                    : "border-card-border hover:bg-bg"
                }`}
              >
                <span className="block text-[14px] font-semibold text-ink">
                  {c.label}
                  {c.code === row.cta_code && (
                    <span className="ml-1.5 text-[12px] font-medium text-muted">
                      (current)
                    </span>
                  )}
                </span>
                <span className="block text-[12px] text-muted">
                  For: {c.description}
                </span>
              </button>
            ))}
            {!items && (
              <p className="text-[14px] text-muted">Loading the actions…</p>
            )}
          </div>
        </fieldset>

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">
              Message · English
            </span>
            <textarea
              rows={5}
              value={en}
              onChange={(e) => setEn(e.target.value)}
              className="mt-1 w-full rounded-xl border border-card-border px-3 py-2 text-[14px] text-ink outline-none focus:border-emami-blue focus:ring-2 focus:ring-blue-soft"
            />
          </label>
          <label className="block">
            <span className="text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">
              Message · বাংলা
            </span>
            <textarea
              rows={5}
              lang="bn"
              value={bn}
              onChange={(e) => setBn(e.target.value)}
              className="mt-1 w-full rounded-xl border border-card-border px-3 py-2 text-[14px] text-ink outline-none focus:border-emami-blue focus:ring-2 focus:ring-blue-soft"
            />
          </label>
        </div>
        <p className="mt-1 text-[12px] text-muted">
          Keep <code>{"{owner_first}"}</code>, <code>{"{target}"}</code> and{" "}
          <code>{"{stretch}"}</code> — they&apos;re filled in for each
          distributor. Hindi follows Emami AI&apos;s draft for the action you
          pick.
        </p>

        <label className="mt-4 block">
          <span className="text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">
            Why you changed it (optional)
          </span>
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. I know them — a call works better"
            className="mt-1 h-11 w-full rounded-xl border border-card-border px-3 text-[14px] text-ink outline-none focus:border-emami-blue focus:ring-2 focus:ring-blue-soft"
          />
        </label>

        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="min-h-11 rounded-xl border border-card-border px-4 text-[15px] font-medium text-ink hover:bg-bg"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!code || busy}
            onClick={save}
            className="min-h-11 rounded-xl bg-navy-800 px-5 text-[15px] font-semibold text-white hover:bg-navy-900 disabled:opacity-40"
          >
            Save and accept
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
