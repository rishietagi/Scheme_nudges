import {
  CirclePlay,
  ClipboardList,
  ListChecks,
  type LucideIcon,
  SlidersHorizontal,
  Smartphone,
  SquareCheckBig,
  TrendingUp,
  Users,
} from "lucide-react";

export type NavItem = { href: string; label: string; icon: LucideIcon; hint?: string; badge?: "approvals" };

export const NAV: { section: string; items: NavItem[] }[] = [
  {
    section: "ASM workspace",
    items: [
      { href: "/cohorts", label: "Cohorts", icon: Users },
      { href: "/survey", label: "Survey", icon: ClipboardList },
      { href: "/approvals", label: "Approvals", icon: SquareCheckBig, badge: "approvals" },
      { href: "/results", label: "Day-30 results", icon: TrendingUp },
    ],
  },
  {
    section: "Set up",
    items: [
      { href: "/setup/cohorts", label: "Cohort rules", icon: SlidersHorizontal },
      { href: "/setup/survey", label: "Survey generator", icon: ListChecks },
    ],
  },
  { section: "Channels", items: [{ href: "/distributor", label: "Distributor view", icon: Smartphone }] },
  { section: "Demo", items: [{ href: "/simulation", label: "Simulation", icon: CirclePlay, hint: "run the loop" }] },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}
