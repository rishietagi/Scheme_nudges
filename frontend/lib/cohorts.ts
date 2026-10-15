import type { CohortColor, CohortName } from "./api";

export const COHORT_ORDER: CohortName[] = ["Champions", "Growth builders", "Scheme-hesitant", "At-risk", "Dormant"];

export const COHORT_HEX: Record<CohortColor, string> = {
  blue: "var(--emami-blue)",
  cyan: "var(--cyan)",
  orange: "var(--orange)",
  red: "var(--red)",
  grey: "var(--grey-cohort)",
};

const BY_NAME: Record<CohortName, CohortColor> = {
  Champions: "blue",
  "Growth builders": "cyan",
  "Scheme-hesitant": "orange",
  "At-risk": "red",
  Dormant: "grey",
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
