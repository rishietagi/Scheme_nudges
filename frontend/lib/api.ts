// The one place the frontend talks to the backend.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type LoopStep = { key: "nudge" | "plan" | "send" | "results"; label: string; day: number; day_label: string };

export type SimCounters = {
  sent: number;
  replied: number;
  flagged: number;
  joined: number;
  follow_ups: number;
  beat_prediction: number;
};

export type SimState = {
  run_id: string | null;
  seed: number;
  scenario: string;
  autopilot: boolean;
  day: number;
  day_label: string;
  stage: string;
  status_text: string;
  waiting_for_approval: boolean;
  pending_rows: number;
  counters: SimCounters;
  playing: boolean;
  speed_seconds_per_day: number;
  steps: LoopStep[];
};

export type SimEvent = {
  event_id: number;
  sim_day: number;
  day_label: string;
  time_label: string;
  type: string;
  agent: string;
  distributor_id: string | null;
  text: string;
};

export type SimScenarios = { scenarios: Record<string, string>; speeds: number[]; default_seed: number };

type Query = Record<string, string | number | boolean | undefined | null>;

function url(path: string, query?: Query): string {
  const u = new URL(path, API_URL);
  for (const [k, v] of Object.entries(query ?? {})) if (v !== undefined && v !== null) u.searchParams.set(k, String(v));
  return u.toString();
}

export async function get<T>(path: string, query?: Query): Promise<T> {
  const res = await fetch(url(path, query), { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function post<T>(path: string, body?: unknown, query?: Query): Promise<T> {
  const res = await fetch(url(path, query), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export type CohortName = "Champions" | "Growth builders" | "Scheme-hesitant" | "At-risk" | "Dormant";
export type CohortColor = "blue" | "cyan" | "orange" | "red" | "grey";

export type TerritorySummary = {
  day: number;
  territory_id: string;
  name: string;
  zone: string;
  asm_name: string;
  distributors: number;
  secondary_fytd_l: number;
  yoy_growth: number;
  focus_share_q2: number;
  joined_last_scheme: number;
  last_scheme_name: string;
  scheme_id: string;
  scheme_name: string;
  scheme_rules: string;
  company_distributors: number;
  company_territories: number;
  cohorts: Record<CohortName, number>;
};

export type CohortCard = {
  name: CohortName;
  tag: string;
  description: string;
  color: CohortColor;
  count: number;
  joined_last_scheme: number;
};

export type CohortList = { day: number; rule_version: string; cohorts: CohortCard[] };

export type DistributorRow = {
  distributor_id: string;
  name: string;
  owner_name: string;
  town: string;
  classification: "A" | "B" | "C";
  language_on_file: string;
  cohort: CohortName;
  reasons: string[];
  secondary_fytd_l: number;
  yoy_growth: number;
  joined_last_scheme: boolean;
  target_l: number;
};

export type DistributorList = { day: number; cohort: CohortName | null; total: number; items: DistributorRow[] };

export type Distributor360 = DistributorRow & {
  day: number;
  key_account: boolean;
  partner_since: number;
  reply_window: string;
  phone_masked: string;
  channel: string;
  cohort_tag: string;
  qoq_growth: number;
  focus_share_q2: number;
  unique_skus_sep: number;
  days_since_last_invoice: number;
  past_schemes_joined: number;
  baseline_forecast_l: number;
  stretch_target_l: number;
  predicted_sales_if_enrolled_l: number;
  reward_text: string;
  billing: { month: string; secondary_l: number }[];
  history: { scheme: string; enrolled: boolean; achieved: boolean }[];
};

export type Language = "English" | "Bengali" | "Hindi";

export type SurveyQuestions = {
  day: number;
  cohort: CohortName;
  language: Language;
  languages: Language[];
  cohorts: CohortName[];
  members: number;
  example_distributor: string;
  nudge_text: string;
  nudge_note: string;
  nudge_sent: boolean;
  questions: { id: string; type: string; text: string; tag: string | null; options: { value: string; label: string }[] }[];
};

export type FlagItem = { response_id: string; distributor_id: string; name: string; reason: string; codes: string[]; decision: "Keep" | "Drop" | null };

export type SurveyResults = {
  day: number;
  day_label: string;
  sent: boolean;
  open: boolean;
  closed: boolean;
  total: number;
  replied: number;
  replies_by_day: number[];
  reminder_day: number;
  median_reply_hours: number | null;
  sanity: { clean: number; check: number; flagged: number };
  flagged: FlagItem[];
  to_check: FlagItem[];
  intents: Record<string, number>;
  no_reply: number;
  left_out: number;
  ratings: { question: string; label: string; pct: number | null; answered: number }[];
  themes: { theme: string; label: string; count: number }[];
  comments: number;
};

export type PlanStatus = "Pending" | "Approved" | "Rejected";

export type PlanRow = {
  row_id: string;
  group_type: "cohort" | "custom" | "individual_group" | "individual";
  group_name: string;
  distributor_id: string | null;
  cta_code: string | null;
  cta_variant: string | null;
  label: string;
  reason: string;
  why: string | null;
  members: number;
  confidence: number | null;
  priority: "High" | "Medium" | "Low";
  status: PlanStatus;
  preview: Partial<Record<Language, string>>;
  children: PlanRow[];
};

export type PlanView = {
  day: number;
  day_label: string;
  plan_day_label: string;
  send_label: string;
  ready: boolean;
  decided: boolean;
  sent: boolean;
  not_joined: number;
  individual: number;
  rows: PlanRow[];
};

export type Candidate = { distributor_id: string; name: string; town: string; cohort: CohortName; intent: string | null; in_group: string | null };

export const api = {
  simState: () => get<SimState>("/sim/state"),
  simScenarios: () => get<SimScenarios>("/sim/scenarios"),
  simEvents: (limit = 200) => get<{ run_id: string; day: number; events: SimEvent[] }>("/sim/events", { limit }),
  simReset: (seed: number, scenario: string, autopilot: boolean) => post<SimState>("/sim/reset", { seed, scenario, autopilot }),
  simPlay: (speed: number) => post<SimState>("/sim/play", { speed_seconds_per_day: speed }),
  simPause: () => post<SimState>("/sim/pause"),
  simSpeed: (speed: number) => post<SimState>("/sim/speed", { speed_seconds_per_day: speed }),
  simNextStage: () => post<SimState>("/sim/advance", { step: "next_stage" }),
  simAdvance: (toDay: number) => post<SimState>("/sim/advance", { to_day: toDay }),
  simAutopilot: (on: boolean) => post<SimState>("/sim/autopilot", { on }),
  territory: (day: number) => get<TerritorySummary>("/territory/summary", { day }),
  cohorts: (day: number) => get<CohortList>("/cohorts", { day }),
  cohortMembers: (name: CohortName, day: number) => get<DistributorList>(`/cohorts/${encodeURIComponent(name)}/distributors`, { day }),
  distributors: (q: string, day: number) => get<DistributorList>("/distributors", { q, day }),
  distributor: (id: string, day: number) => get<Distributor360>(`/distributors/${id}`, { day }),
  surveyQuestions: (cohort: CohortName, lang: Language, day: number) => get<SurveyQuestions>("/survey/questions", { cohort, lang, day }),
  surveyResults: (day: number) => get<SurveyResults>("/survey/results", { day }),
  plan: (day: number) => get<PlanView>("/plan", { day }),
  planCatalogue: () => get<{ code: string; label: string }[]>("/plan/catalogue"),
  planCandidates: () => get<Candidate[]>("/plan/candidates"),
  planDecide: (rowId: string, decision: "Approved" | "Rejected") =>
    post<SimState>(`/plan/rows/${encodeURIComponent(rowId)}/decision`, { decision }),
  planApproveHigh: (min = 0.7) => post<SimState>("/plan/approve-high-confidence", { min }),
  planCustomGroup: (name: string, memberIds: string[], ctaCode: string | null) =>
    post<SimState>("/plan/custom-group", { name, member_ids: memberIds, cta_code: ctaCode }),
  flagDecision: (responseId: string, decision: "Keep" | "Drop") =>
    post<SimState>(`/survey/flags/${encodeURIComponent(responseId)}`, { decision }),
};
