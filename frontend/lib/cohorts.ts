import type { CohortColor, CohortName } from "./api";

// The 2×2 in display order (backend/app/rules/cohorts.yaml v4). Colours follow the design tokens.
export const COHORT_ORDER: CohortName[] = ["Invest / Expand", "Replace / Reassess", "Protect", "Exit / Watchlist"];
export const DEFAULT_COHORT: CohortName = "Replace / Reassess";

export const COHORT_HEX: Record<CohortColor, string> = {
  blue: "var(--emami-blue)",
  cyan: "var(--cyan)",
  orange: "var(--orange)",
  red: "var(--red)",
  grey: "var(--grey-cohort)",
};

const BY_NAME: Record<CohortName, CohortColor> = {
  "Invest / Expand": "blue",
  "Replace / Reassess": "orange",
  Protect: "cyan",
  "Exit / Watchlist": "red",
};

export function cohortColor(name: CohortName): string {
  return COHORT_HEX[BY_NAME[name]];
}

export function isCohort(x: string | null): x is CohortName {
  return x !== null && (COHORT_ORDER as string[]).includes(x);
}

export function initials(name: string): string {
  return name
    .split(/[\s&]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join("");
}
