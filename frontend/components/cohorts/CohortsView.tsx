"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { api, type CohortName } from "@/lib/api";
import { DEFAULT_COHORT, isCohort } from "@/lib/cohorts";
import { useViewDay } from "@/lib/sim";
import { useApi } from "@/lib/useApi";
import { dayLabel } from "@/lib/format";
import { PageHeader } from "@/components/shell/PageHeader";
import { Placeholder } from "@/components/cards/Placeholder";
import { PlatformStrip } from "@/components/loop-stepper/PlatformStrip";
import { CohortCards } from "./CohortCards";
import { Distributor360 } from "./Distributor360";
import { MembersTable } from "./MembersTable";

export function CohortsView() {
  const { day } = useViewDay();
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const raw = params.get("cohort");
  const cohort: CohortName = isCohort(raw) ? raw : DEFAULT_COHORT;

  const dayKey = day.toFixed(2);
  const cycle = day >= 0.42;
  const cohorts = useApi(`cohorts:${dayKey}`, () => api.cohorts(day));
  const members = useApi(`members:${cohort}:${dayKey}`, () => api.cohortMembers(cohort, day));
  // Keep the previous cohort's rows on screen until the new ones land (smooth swap, no empty flash).
  const shown = members.data;
  const fresh = shown?.cohort === cohort;
  const selectedId = params.get("id") ?? (fresh ? shown.items[0]?.distributor_id ?? null : null);
  const detail = useApi(selectedId ? `360:${selectedId}:${dayKey}` : null, () => api.distributor(selectedId!, day));

  function update(next: Record<string, string | null>) {
    const p = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(next)) {
      if (v === null) p.delete(k);
      else p.set(k, v);
    }
    router.replace(`${pathname}?${p.toString()}`, { scroll: false });
  }

  return (
    <>
      <PageHeader
        eyebrow={`Q3 FY27 cycle · cohorts set on Day 0 from business potential and performance · rules ${cohorts.data?.rule_version ?? "v4.0"}${cycle ? ` · showing ${dayLabel(day).split(" · ")[0]}` : ""}`}
        title="Where to invest, fix, protect or exit"
      />
      <PlatformStrip day={day} />
      {cohorts.data ? (
        <CohortCards
          data={cohorts.data}
          selected={cohort}
          cycle={cycle}
          onSelect={(c) => update({ cohort: c, id: null })}
          selectedId={selectedId}
          onPick={(pt) => update({ cohort: pt.cohort, id: pt.distributor_id })}
        />
      ) : (
        <Placeholder title={cohorts.error ? "Can't reach the simulator" : "Loading cohorts"} phase={1} lines={2} />
      )}
      <div className="mt-5 grid items-start gap-5 xl:grid-cols-[1.25fr_1fr]">
        <MembersTable
          cohort={shown?.cohort ?? cohort}
          rows={shown?.items ?? []}
          selectedId={selectedId}
          onSelect={(id) => update({ id })}
          cycle={cycle}
        />
        <Distributor360 d={detail.data} />
      </div>
    </>
  );
}
