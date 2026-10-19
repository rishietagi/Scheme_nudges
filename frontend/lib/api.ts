// The one place the frontend talks to the backend. Locally the API runs on :8000; in the hosted container it sits
// behind the same origin at /api (next.config.ts forwards /api/* to it), so NEXT_PUBLIC_API_URL=/api.
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

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
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) if (v !== undefined && v !== null) qs.set(k, String(v));
  const q = qs.toString();
  return `${API_URL}${path}${q ? `?${q}` : ""}`;
}

export async function get<T>(path: string, query?: Query): Promise<T> {
  const res = await fetch(url(path, query), { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function post<T>(path: string, body?: unknown, query?: Query, method: "POST" | "PUT" | "DELETE" = "POST"): Promise<T> {
  const res = await fetch(url(path, query), {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

// Cohort names are fixed in backend/app/rules/cohorts.yaml (the business edits thresholds and definitions).
export type CohortName = "Invest / Expand" | "Replace / Reassess" | "Protect" | "Exit / Watchlist";
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
  joined_festive: number;
  replied: number;
  name: CohortName;
  tag: string;
  description: string;
  color: CohortColor;
  count: number;
  joined_last_scheme: number;
  high_potential: boolean;
  high_performance: boolean;
  kpis: { potential_l: number; current_l: number; avg_score: number; pillars: Record<Pillar, number>; billing_fytd_l: number } | null;
};

export type Pillar = "growth" | "schemes" | "focus" | "delivery";
export type AxisInfo = { label: string; high: string; low: string; rule: string };
export type WeightOut = { key: Pillar; label: string; explain: string; value: number; default: number };
export type CohortPoint = { distributor_id: string; name: string; town: string; cohort: CohortName; potential_l: number; score: number };

export type CohortRules = {
  potential: AxisInfo;
  performance: AxisInfo;
  pillars_rule: string;
  benchmark: string;
  potential_high: number;
  performance_high: number;
  weights: WeightOut[];
  points: CohortPoint[];
};

export type CohortList = CohortRules & { day: number; rule_version: string; cohorts: CohortCard[] };

export type Threshold = { key: string; label: string; unit: string; value: number; default: number; min: number; max: number };

export type CohortCount = {
  name: CohortName;
  color: CohortColor;
  count: number;
  definition: string;
  high_potential: boolean;
  high_performance: boolean;
};

export type CohortConfig = CohortRules & {
  version: string;
  thresholds: Threshold[];
  cohorts: CohortCount[];
  customised: boolean;
  saved_at: string | null;
  moves: { from_cohort: CohortName; to_cohort: CohortName; count: number; names: string[] }[];
  current_run_differs: boolean;
};

export type QuestionSource = "must_all" | "must_cohort" | "ai" | "comment";

export type GeneratedQuestion = {
  id: string;
  type: "quick_reply" | "rating_1_5" | "single_choice" | "open_text";
  bucket: string;
  use_case: string;
  topic: string;
  short: string;
  text: Record<Language, string>;
  source: QuestionSource;
  why: string | null;
  locked: boolean;
};

export type MustAsk = { id: string; scope: string; locked?: boolean; text?: string | null };

export type SurveyConfig = {
  use_case: string;
  use_case_detail: string;
  questions_per_survey: number;
  min_questions: number;
  max_questions: number;
  must_ask: MustAsk[];
  buckets: Record<string, string>;
  use_cases: string[];
  bank: { id: string; type: string; bucket: string; use_case: string; topic: string; text: string }[];
  cohorts: CohortCount[];
  questionnaires: Record<CohortName, GeneratedQuestion[]>;
  customised: boolean;
  saved_at: string | null;
  current_run_differs: boolean;
};

export type SurveyConfigIn = { questions_per_survey: number; must_ask: MustAsk[] };

export type CohortConfigIn = { thresholds: Record<string, number>; definitions: Record<string, string>; weights: Record<string, number> };

export type Scorecard = {
  potential: {
    town: string;
    town_potential_l: number;
    town_tam_l: number;
    outlets_covered: number;
    coverage_share: number;
    potential_l: number;
    current_l: number;
    headroom_l: number;
    threshold_l: number;
    high: boolean;
  };
  pillars: { key: Pillar; label: string; explain: string; raw: string; score: number; weight: number }[];
  score: number;
  threshold: number;
  high: boolean;
};

export type DistributorRow = {
  distributor_id: string;
  intent: string | null;
  flagged: boolean;
  joined_day: number | null;
  language_now: string | null;
  language_changed: boolean;
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
  scorecard: Scorecard | null;
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
  festive_joined: boolean;
  festive_join_label: string | null;
  this_cycle: string | null;
  milestones: { day_label: string; time_label: string | null; text: string }[];
  persona: PersonaView | null;
};

export type PersonaView = {
  language: string;
  language_on_file: string;
  language_changed: boolean;
  best_time: string | null;
  replies: string;
  prefers: string | null;
  what_worked: string | null;
  next_time: string | null;
};

export type Message = {
  id: string;
  sender: "desk" | "distributor" | "system";
  kind: "nudge" | "quick_replies" | "text" | "survey" | "voice" | "call" | "enrolled";
  sim_day: number;
  day_label: string;
  time_label: string;
  text: string;
  language?: string | null;
  card?: { target: string; hit: string; stretch: string; beat: string } | null;
  options?: string[] | null;
  answers?: { q: string; a: string }[] | null;
  seconds?: number | null;
  tapped?: boolean | null;
  cta?: string | null;
  note?: string | null;
  live?: boolean | null;
};

export type JourneyItem = { type: string; agent: string; sim_day: number; day_label: string; time_label: string; text: string };

export type ChatView = {
  day: number;
  distributor_id: string;
  name: string;
  owner_name: string;
  town: string;
  initials: string;
  cohort: CohortName;
  key_account: boolean;
  language: string;
  language_changed: boolean;
  billing_fytd: string;
  best_time: string;
  best_time_learned: boolean;
  this_cycle: string;
  messages: Message[];
  journey: JourneyItem[];
};

export type Scenario = { distributor_id: string; title: string; subtitle: string; icon: "bengali" | "flag" | "call" };

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
  questions: {
    id: string;
    type: string;
    text: string;
    tag: string | null;
    options: { value: string; label: string }[];
    source: QuestionSource;
    why: string | null;
    bucket: string;
  }[];
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
  intent_labels?: Record<string, string>;
  no_reply: number;
  left_out: number;
  ratings: { question: string; label: string; pct: number | null; answered: number; bucket: string; average: number | null; asked_in: string[] }[];
  themes: { theme: string; label: string; count: number }[];
  comments: number;
  dealer_score: ScoreItem | null;
  buckets: ScoreItem[];
  dealer_by_cohort: ScoreItem[];
};

export type ScoreItem = { name: string; headline: string; average: number | null; pct: number | null; answered: number };

export type PlanStatus = "Pending" | "Approved" | "Rejected";

export type CatalogueItem = { code: string; label: string; description: string; template: Partial<Record<Language, string>> };

export type PlanRow = {
  cohort_note: string | null;
  survey_note: string | null;
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
  priority: "High" | "Medium" | "Low";
  status: PlanStatus;
  preview: Partial<Record<Language, string>>;
  children: PlanRow[];
  template: Partial<Record<Language, string>>;
  revenue_at_stake_l: number;
  priority_note: string;
  modified: boolean;
  was_label: string | null;
  note: string | null;
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

export type ResultsData = {
  joined: number;
  total: number;
  last_scheme_joined: number;
  joined_by_cohort: { cohort: CohortName; joined: number; total: number; color: CohortColor }[];
  beat_prediction: number;
  fell_short: number;
  sales_lift_joined: number | null;
  sales_lift_not_joined: number | null;
  speed: Record<"Same day" | "First week" | "After follow-up" | "Never", number>;
  median_first_reply_hours: number | null;
  median_join_days_after_follow_up: number | null;
  asked: Record<string, number>;
  asked_labels?: Record<string, string>;
  follow_ups: { cta_code: string; label: string; received: number; joined: number; rate: number }[];
};

export type ResultsView = {
  day: number;
  day_label: string;
  ready: boolean;
  results_day_label: string;
  joined_so_far: number;
  total: number;
  headline: string | null;
  results: ResultsData | null;
  learned: { text: string; bold: boolean }[];
  chips: { value: number; label: string }[];
  applied: boolean;
  applied_at: string | null;
  next_quarter: NextQuarter | null;
};

export type NextQuarter = {
  cohorts: { name: CohortName; color: CohortColor; now: number; next: number; dealer_score: number | null }[];
  dealer_score: number | null;
  moves: { from_cohort: CohortName; to_cohort: CohortName; count: number; names: string[] }[];
  moved: number;
};

export type AppliedProfile = { distributor_id: string; name: string; cohort: string; language: string; prefers: string; next_time: string };

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
  planCatalogue: (rowId?: string) => get<CatalogueItem[]>("/plan/catalogue", { row_id: rowId }),
  planCandidates: () => get<Candidate[]>("/plan/candidates"),
  planDecide: (rowId: string, decision: "Approved" | "Rejected") =>
    post<SimState>(`/plan/rows/${encodeURIComponent(rowId)}/decision`, { decision }),
  planAcceptAll: () => post<SimState>("/plan/accept-all"),
  planModify: (rowId: string, body: { cta_code: string; text_en?: string; text_bn?: string; note?: string }) =>
    post<SimState>(`/plan/rows/${encodeURIComponent(rowId)}/modify`, body),
  planRestore: (rowId: string) => post<SimState>(`/plan/rows/${encodeURIComponent(rowId)}/restore`),
  planCustomGroup: (name: string, memberIds: string[], ctaCode: string | null) =>
    post<SimState>("/plan/custom-group", { name, member_ids: memberIds, cta_code: ctaCode }),
  results: (day: number) => get<ResultsView>("/results", { day }),
  applyToNext: () => post<AppliedProfile[]>("/results/apply"),
  applied: () => get<AppliedProfile[]>("/results/applied"),
  scenarios: (day: number) => get<Scenario[]>("/chat/scenarios", { day }),
  chat: (id: string, day: number) => get<ChatView>(`/chat/${id}`, { day }),
  chatSend: (id: string, text: string) => post<ChatView>(`/chat/${id}/message`, { text }),
  cohortConfig: () => get<CohortConfig>("/config/cohorts"),
  cohortConfigPreview: (body: CohortConfigIn) => post<CohortConfig>("/config/cohorts/preview", body),
  cohortConfigSave: (body: CohortConfigIn) => post<CohortConfig>("/config/cohorts", body, undefined, "PUT"),
  cohortConfigReset: () => post<CohortConfig>("/config/cohorts", undefined, undefined, "DELETE"),
  surveyConfig: () => get<SurveyConfig>("/config/survey"),
  surveyConfigPreview: (body: SurveyConfigIn) => post<SurveyConfig>("/config/survey/preview", body),
  surveyConfigSave: (body: SurveyConfigIn) => post<SurveyConfig>("/config/survey", body, undefined, "PUT"),
  surveyConfigReset: () => post<SurveyConfig>("/config/survey", undefined, undefined, "DELETE"),
  flagDecision: (responseId: string, decision: "Keep" | "Drop") =>
    post<SimState>(`/survey/flags/${encodeURIComponent(responseId)}`, { decision }),
};
