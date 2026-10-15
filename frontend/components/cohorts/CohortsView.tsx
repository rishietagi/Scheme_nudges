"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { api, type CohortName } from "@/lib/api";
import { isCohort } from "@/lib/cohorts";
import { useViewDay } from "@/lib/sim";
import { useApi } from "@/lib/useApi";
import { PageHeader } from "@/components/shell/PageHeader";
import { Placeholder } from "@/components/cards/Placeholder";
import { CohortCards } from "./CohortCards";
import { Distributor360 } from "./Distributor360";
import { MembersTable } from "./MembersTable";

export function CohortsView() {
  const { day } = useViewDay();
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const raw = params.get("cohort");
  const cohort: CohortName = isCohort(raw) ? raw : "Scheme-hesitant";

  const cohorts = useApi(`cohorts:${day}`, () => api.cohorts(day));
  const members = useApi(`members:${cohort}:${day}`, () => api.cohortMembers(cohort, day));
  // Keep the previous cohort's rows on screen until the new ones land (smooth swap, no empty flash).
  const shown = members.data;
  const fresh = shown?.cohort === cohort;
  const selectedId = params.get("id") ?? (fresh ? shown.items[0]?.distributor_id ?? null : null);
  const detail = useApi(selectedId ? `360:${selectedId}:${day}` : null, () => api.distributor(selectedId!, day));

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
        eyebrow={`Cohorts are set on Day 0 · rules ${cohorts.data?.rule_version ?? "v2.0"}`}
        title="Five cohorts, one follow-up each"
      />
      {cohorts.data ? (
        <CohortCards cohorts={cohorts.data.cohorts} selected={cohort} onSelect={(c) => update({ cohort: c, id: null })} />
      ) : (
        <Placeholder title={cohorts.error ? "Can't reach the simulator" : "Loading cohorts"} phase={1} lines={2} />
      )}
      <div className="mt-5 grid items-start gap-5 xl:grid-cols-[1.25fr_1fr]">
        <MembersTable
          cohort={shown?.cohort ?? cohort}
          rows={shown?.items ?? []}
          selectedId={selectedId}
          onSelect={(id) => update({ id })}
        />
        <Distributor360 d={detail.data} />
      </div>
    </>
  );
}
