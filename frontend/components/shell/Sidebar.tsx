"use client";

import { motion } from "motion/react";
import { SignOut } from "./SignOut";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSim } from "@/lib/sim";
import { EASE } from "@/components/motion/Motion";
import { isActive, NAV } from "./nav";

export function Sidebar({ onNavigate, layoutId = "nav-active" }: { onNavigate?: () => void; layoutId?: string }) {
  const pathname = usePathname();
  const { state, online } = useSim();

  return (
    <div className="flex h-full flex-col bg-navy-900 px-4 pb-5 pt-7 text-white">
      <Link href="/cohorts" onClick={onNavigate} className="block px-2" aria-label="Emami — Distributor Experience Platform, home">
        <Image src="/brand/emami-logo-reverse.png" alt="Emami" width={92} height={83} priority className="h-auto w-[92px]" />
        <p className="mt-2 text-[13px] font-semibold leading-tight text-white/90">
          Distributor Experience
          <br />
          Platform
        </p>
      </Link>

      <nav className="mt-8 flex-1 space-y-6" aria-label="Main">
        {NAV.map((group) => (
          <div key={group.section}>
            <p className="px-3 pb-2 text-[11px] font-medium uppercase tracking-[0.12em] text-white/50">{group.section}</p>
            <ul className="space-y-1">
              {group.items.map((item) => {
                const active = isActive(pathname, item.href);
                const Icon = item.icon;
                const badge = item.badge === "approvals" && state.pending_rows > 0 ? state.pending_rows : null;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={onNavigate}
                      aria-current={active ? "page" : undefined}
                      className={`relative flex min-h-11 items-center gap-3 rounded-xl px-3 text-[15px] transition-colors ${
                        active ? "text-white" : "text-white/75 hover:text-white"
                      }`}
                    >
                      {active && (
                        <motion.span
                          layoutId={layoutId}
                          className="absolute inset-0 rounded-xl bg-white/10"
                          transition={{ duration: 0.35, ease: EASE }}
                        />
                      )}
                      <Icon className="relative size-[18px] shrink-0" strokeWidth={1.75} aria-hidden />
                      <span className="relative font-medium">{item.label}</span>
                      {item.hint && <span className="relative ml-auto whitespace-nowrap text-[11px] text-white/50">{item.hint}</span>}
                      {badge !== null && (
                        <motion.span
                          initial={{ scale: 0.6, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          className="relative ml-auto grid h-5 min-w-5 place-items-center rounded-full bg-orange px-1.5 text-[11px] font-semibold text-ink"
                        >
                          {badge}
                        </motion.span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Scheme status: where the loop is right now */}
      <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3.5">
        <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-white/50">Q3 cycle · Festive</p>
        <motion.p
          key={state.day_label}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: EASE }}
          className="mt-1 font-display text-[17px] font-semibold"
        >
          {state.day_label}
        </motion.p>
        <p className="mt-1 flex items-center gap-2 text-[13px] text-orange-light">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-orange opacity-60" />
            <span className="relative inline-flex size-2 rounded-full bg-orange" />
          </span>
          {online ? state.status_text : "Simulator offline"}
        </p>
      </div>

      <div className="mt-4 flex items-center gap-3 px-1">
        <span className="grid size-10 place-items-center rounded-full bg-navy-800 text-sm font-semibold" aria-hidden>
          RS
        </span>
        <div className="leading-tight">
          <p className="text-[14px] font-semibold">Rahul Sen</p>
          <p className="text-[12px] text-white/60">ASM · Kolkata North</p>
        </div>
        <SignOut />
      </div>
    </div>
  );
}
