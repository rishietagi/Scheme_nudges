"""Pydantic response models shared by the API."""
from __future__ import annotations

from pydantic import BaseModel


class Health(BaseModel):
    status: str
    llm_mode: str
    world_db: bool


class LoopStep(BaseModel):
    key: str
    label: str
    day: int
    day_label: str


class SimCounters(BaseModel):
    sent: int
    replied: int
    flagged: int
    joined: int
    follow_ups: int
    beat_prediction: int


class SimState(BaseModel):
    run_id: str
    seed: int
    scenario: str
    autopilot: bool
    day: float
    day_label: str
    stage: str
    status_text: str              # sidebar line, e.g. "Waiting for your approval"
    waiting_for_approval: bool
    pending_rows: int             # approval-matrix rows still waiting (sidebar badge)
    counters: SimCounters
    playing: bool
    speed_seconds_per_day: float
    steps: list[LoopStep]


class SimEvent(BaseModel):
    event_id: int
    sim_day: float
    day_label: str
    time_label: str
    type: str
    agent: str
    distributor_id: str | None
    text: str


class SimEvents(BaseModel):
    run_id: str
    day: float
    events: list[SimEvent]


# ---------------------------------------------------------------- Day-0 world (Phase 1)
class TerritorySummary(BaseModel):
    day: float
    territory_id: str
    name: str
    zone: str
    asm_name: str
    distributors: int
    secondary_fytd_l: float
    yoy_growth: float
    focus_share_q2: float
    joined_last_scheme: int
    last_scheme_name: str
    scheme_id: str
    scheme_name: str
    scheme_rules: str
    company_distributors: int
    company_territories: int
    cohorts: dict[str, int]


class CohortCard(BaseModel):
    joined_festive: int = 0
    replied: int = 0
    name: str
    tag: str
    description: str
    color: str
    count: int
    joined_last_scheme: int


class CohortList(BaseModel):
    day: float
    rule_version: str
    cohorts: list[CohortCard]


class DistributorRow(BaseModel):
    distributor_id: str
    intent: str | None = None          # Day-0 reply (as of the day shown)
    flagged: bool = False
    joined_day: int | None = None
    language_now: str | None = None    # persona language so far
    language_changed: bool = False
    name: str
    owner_name: str
    town: str
    classification: str
    language_on_file: str
    cohort: str
    reasons: list[str]
    secondary_fytd_l: float
    yoy_growth: float
    joined_last_scheme: bool
    target_l: float


class DistributorList(BaseModel):
    day: float
    cohort: str | None
    total: int
    items: list[DistributorRow]


class MonthBilling(BaseModel):
    month: str
    secondary_l: float


class SchemeHistory(BaseModel):
    scheme: str
    enrolled: bool
    achieved: bool


class Distributor360(BaseModel):
    day: float
    distributor_id: str
    name: str
    owner_name: str
    town: str
    classification: str
    key_account: bool
    partner_since: int
    language_on_file: str
    reply_window: str
    phone_masked: str
    channel: str
    cohort: str
    cohort_tag: str
    reasons: list[str]
    secondary_fytd_l: float
    yoy_growth: float
    qoq_growth: float
    focus_share_q2: float
    unique_skus_sep: int
    days_since_last_invoice: int
    past_schemes_joined: int
    baseline_forecast_l: float
    target_l: float
    stretch_target_l: float
    predicted_sales_if_enrolled_l: float
    reward_text: str
    billing: list[MonthBilling]
    history: list[SchemeHistory]
    festive_joined: bool = False
    festive_join_label: str | None = None
    this_cycle: str | None = None
    milestones: list["Milestone"] = []
    persona: "PersonaView | None" = None


# ---------------------------------------------------------------- Survey (Phase 3)
class Choice(BaseModel):
    value: str                    # stored value (English label, e.g. an intent)
    label: str                    # shown in the chosen language


class Question(BaseModel):
    id: str
    type: str
    text: str
    tag: str | None
    options: list[Choice]


class SurveyQuestions(BaseModel):
    day: float
    cohort: str
    language: str
    languages: list[str]
    cohorts: list[str]
    members: int
    example_distributor: str
    nudge_text: str
    nudge_note: str
    nudge_sent: bool
    questions: list[Question]


class SanitySummary(BaseModel):
    clean: int
    check: int
    flagged: int


class FlagItem(BaseModel):
    response_id: str
    distributor_id: str
    name: str
    reason: str
    codes: list[str]
    decision: str | None


class RatingItem(BaseModel):
    question: str
    label: str
    pct: float | None             # share who said 4 or 5
    answered: int


class ThemeItem(BaseModel):
    theme: str
    label: str
    count: int


class SurveyResults(BaseModel):
    day: float
    day_label: str
    sent: bool
    open: bool
    closed: bool
    total: int
    replied: int
    replies_by_day: list[int]     # cumulative replies at the end of D0, D1, … (up to the day shown)
    reminder_day: int
    median_reply_hours: float | None
    sanity: SanitySummary
    flagged: list[FlagItem]       # red — left out until kept
    to_check: list[FlagItem]      # amber — counted, worth a look
    intents: dict[str, int]       # among answers that count
    no_reply: int
    left_out: int                 # flagged answers not (yet) kept
    ratings: list[RatingItem]
    themes: list[ThemeItem]
    comments: int


# ---------------------------------------------------------------- Approval matrix (Phase 4)
class PlanRow(BaseModel):
    row_id: str
    group_type: str               # cohort | custom | individual_group | individual
    group_name: str
    distributor_id: str | None
    cta_code: str | None
    cta_variant: str | None
    label: str                    # the follow-up, in plain words
    reason: str                   # what the answers showed
    why: str | None               # one line from the LLM
    members: int
    confidence: float | None
    priority: str
    status: str                   # Pending | Approved | Rejected (as of the day shown)
    preview: dict[str, str]       # message as it will go out, for one member (English / Bengali)
    children: list["PlanRow"]


class PlanView(BaseModel):
    day: float
    day_label: str
    plan_day_label: str
    send_label: str
    ready: bool
    decided: bool
    sent: bool
    not_joined: int
    individual: int
    rows: list[PlanRow]


class CatalogueItem(BaseModel):
    code: str
    label: str


class Candidate(BaseModel):
    distributor_id: str
    name: str
    town: str
    cohort: str
    intent: str | None
    in_group: str | None


# ---------------------------------------------------------------- Distributor view, Command centre, 360 (Phase 5)
class Scenario(BaseModel):
    distributor_id: str
    title: str
    subtitle: str
    icon: str


class Message(BaseModel):
    id: str
    sender: str                   # desk | distributor | system
    kind: str                     # nudge | quick_replies | text | survey | voice | call | enrolled
    sim_day: float
    day_label: str
    time_label: str
    text: str
    language: str | None = None
    card: dict | None = None
    options: list[str] | None = None
    answers: list[dict] | None = None
    seconds: int | None = None
    tapped: bool | None = None
    cta: str | None = None
    note: str | None = None
    live: bool | None = None


class JourneyItem(BaseModel):
    type: str
    agent: str
    sim_day: float
    day_label: str
    time_label: str
    text: str


class ChatView(BaseModel):
    day: float
    distributor_id: str
    name: str
    owner_name: str
    town: str
    initials: str
    cohort: str
    key_account: bool
    language: str
    language_changed: bool
    billing_fytd: str
    best_time: str
    best_time_learned: bool
    this_cycle: str
    messages: list[Message]
    journey: list[JourneyItem]


class Tile(BaseModel):
    key: str
    label: str
    value: int
    sub: str


class NeedItem(BaseModel):
    tone: str                     # orange | red | blue
    title: str
    sub: str
    href: str
    action: str


class SummaryLine(BaseModel):
    text: str
    bold: bool


class CohortProgress(BaseModel):
    name: str
    color: str
    distributors: int
    replied: int
    joined: int


class CommandView(BaseModel):
    day: float
    day_label: str
    greeting: str
    eyebrow: str
    tiles: list[Tile]
    needs: list[NeedItem]
    summary_label: str
    summary: list[SummaryLine]
    cohorts: list[CohortProgress]


class PersonaView(BaseModel):
    language: str
    language_on_file: str
    language_changed: bool
    best_time: str | None
    replies: str
    prefers: str | None
    what_worked: str | None
    next_time: str | None


class Milestone(BaseModel):
    day_label: str
    time_label: str | None
    text: str


Distributor360.model_rebuild()


# ---------------------------------------------------------------- Day-30 results (Phase 6)
class AppliedProfile(BaseModel):
    distributor_id: str
    name: str
    cohort: str
    language: str
    prefers: str
    next_time: str


class ResultsView(BaseModel):
    day: float
    day_label: str
    ready: bool
    results_day_label: str
    joined_so_far: int
    total: int
    headline: str | None = None
    results: dict | None = None          # engines/results.compute output (five questions)
    learned: list[SummaryLine] = []
    chips: list[dict] = []
    applied: bool
    applied_at: str | None = None
    run_scenario: str | None = None
