"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { EASE } from "@/components/motion/Motion";
import { useViewDay } from "@/lib/sim";
import { dayLabel } from "@/lib/format";

type Props = {
  eyebrow: React.ReactNode;
  title: React.ReactNode;
  badge?: string;
};

/** Breadcrumb line + "Concept prototype" pill, big title, and the ASM / Distributor toggle (as in every render). */
export function PageHeader({ eyebrow, title, badge = "Concept prototype · synthetic data" }: Props) {
  const { day, live } = useViewDay();
  const pathname = usePathname();

  return (
    <header className="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[13px] text-muted">
          <span>{eyebrow}</span>
          <span className="rounded-full bg-orange-soft px-2.5 py-0.5 text-[12px] font-semibold text-amber">{badge}</span>
          {!live && (
            <Link
              href={pathname}
              className="rounded-full bg-blue-soft px-2.5 py-0.5 text-[12px] font-semibold text-emami-blue hover:underline"
            >
              Viewing {dayLabel(day)} · back to live
            </Link>
          )}
        </div>
        <motion.h1
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE }}
          className="mt-2 font-display text-[30px] font-semibold leading-[1.1] tracking-[-0.02em] text-ink sm:text-[38px]"
        >
          {title}
        </motion.h1>
      </div>
      <ViewToggle />
    </header>
  );
}

export function ViewToggle() {
  const pathname = usePathname();
  const distributor = pathname.startsWith("/distributor");
  const options = [
    { href: "/", label: "ASM workspace", active: !distributor },
    { href: "/distributor", label: "Distributor view", active: distributor },
  ];
  return (
    <nav aria-label="Workspace" className="flex shrink-0 self-start rounded-full bg-[#E8ECF1] p-1">
      {options.map((o) => (
        <Link
          key={o.href}
          href={o.href}
          aria-current={o.active ? "page" : undefined}
          className={`relative flex min-h-10 items-center rounded-full px-4 text-[14px] font-medium transition-colors ${
            o.active ? "text-ink" : "text-muted hover:text-ink"
          }`}
        >
          {o.active && (
            <motion.span
              layoutId="view-toggle"
              className="absolute inset-0 rounded-full bg-white shadow-[var(--shadow-card)]"
              transition={{ duration: 0.35, ease: EASE }}
            />
          )}
          <span className="relative">{o.label}</span>
        </Link>
      ))}
    </nav>
  );
}
