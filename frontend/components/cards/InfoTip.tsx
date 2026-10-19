"use client";

import { AnimatePresence, motion } from "motion/react";
import { useId, useRef, useState } from "react";
import { Info } from "lucide-react";
import { EASE } from "@/components/motion/Motion";

/** "How is this worked out?" — a real button that shows a short explanation on hover, focus or tap. */
export function InfoTip({
  children,
  label = "How is this worked out?",
  align = "center",
  tone = "light",
  className = "",
}: {
  children: React.ReactNode;
  label?: string;
  align?: "center" | "left" | "right";
  tone?: "light" | "dark";
  className?: string;
}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const pinned = useRef(false);
  const side = align === "left" ? "left-0" : align === "right" ? "right-0" : "left-1/2 -translate-x-1/2";

  return (
    <span
      className={`relative inline-flex align-middle ${className}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => !pinned.current && setOpen(false)}
    >
      <button
        type="button"
        aria-label={label}
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        onClick={() => {
          pinned.current = !open;
          setOpen(!open);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          pinned.current = false;
          setOpen(false);
        }}
        onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
        className={`-m-3 grid size-11 place-items-center rounded-full transition-colors ${
          tone === "dark" ? "text-white/60 hover:text-white" : "text-muted hover:text-emami-blue"
        }`}
      >
        <Info className="size-4" aria-hidden />
      </button>
      <AnimatePresence>
        {open && (
          <motion.span
            id={id}
            role="tooltip"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.18, ease: EASE }}
            className={`absolute top-full z-50 mt-2 block w-72 rounded-xl border border-card-border bg-white p-3 text-left text-[13px] font-normal normal-case leading-relaxed tracking-normal text-ink shadow-[var(--shadow-lift)] ${side}`}
          >
            {children}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}
