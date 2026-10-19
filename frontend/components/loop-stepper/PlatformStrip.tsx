"use client";

import Link from "next/link";
import { ChevronRight, RefreshCw } from "lucide-react";

const STEPS = [
  { label: "Potential + performance", href: "/setup/cohorts" },
  { label: "Cohorts", href: "/cohorts" },
  { label: "Survey", href: "/survey" },
  { label: "Next best action", href: "/approvals" },
  { label: "Results", href: "/results" },
  { label: "Next quarter", href: "/results#next-quarter" },
];

/** The platform in one line: cohorts come from performance data; the survey enriches them; together they drive the
 *  next best action; results feed the next quarter. The trade scheme is this cycle's use case, not the product. */
export function PlatformStrip({ day }: { day: number }) {
  const current = day < 0.42 ? 1 : day < 7.4 ? 2 : day < 30 ? 3 : 4;
  return (
    <nav aria-label="How the loop works" className="mb-5 flex flex-wrap items-center gap-x-1 gap-y-2 text-[13px]">
      {STEPS.map((s, i) => (
        <span key={s.label} className="flex items-center gap-1">
          <Link
            href={s.href}
            aria-current={i === current ? "step" : undefined}
            className={`inline-flex min-h-8 items-center gap-1 rounded-full px-3 font-medium transition-colors ${
              i === current ? "bg-navy-800 text-white" : "bg-white text-muted ring-1 ring-card-border hover:text-ink"
            }`}
          >
            {i === STEPS.length - 1 && <RefreshCw className="size-3" aria-hidden />}
            {s.label}
          </Link>
          {i < STEPS.length - 1 && <ChevronRight className="size-3.5 text-muted/60" aria-hidden />}
        </span>
      ))}
    </nav>
  );
}
