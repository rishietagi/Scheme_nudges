-- Run tables (SIMULATION_SPEC §5). Every row has run_id. Times are sim days (float, Day 0 = Thu 1 Oct 2026 00:00).
-- Pages read rows with sim time <= the requested day.
PRAGMA main.journal_mode = WAL;

CREATE TABLE IF NOT EXISTS loop_runs (
  run_id TEXT PRIMARY KEY,
  seed INTEGER NOT NULL,
  scenario TEXT NOT NULL,
  autopilot INTEGER NOT NULL DEFAULT 0,
  scheme_id TEXT NOT NULL,
  current_day REAL NOT NULL DEFAULT 0,
  stage TEXT NOT NULL DEFAULT 'NUDGE',
  plan_built INTEGER NOT NULL DEFAULT 0,
  segment_b_built INTEGER NOT NULL DEFAULT 0,
  applied_to_next INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  sim_day REAL NOT NULL,
  type TEXT NOT NULL,
  agent TEXT NOT NULL,
  distributor_id TEXT,
  text TEXT NOT NULL,
  feed INTEGER NOT NULL DEFAULT 1,          -- 1 = shown in the Simulation live feed; 0 = per-distributor detail only
  payload_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_events_run_day ON events (run_id, sim_day);
CREATE INDEX IF NOT EXISTS ix_events_run_dist ON events (run_id, distributor_id);

CREATE TABLE IF NOT EXISTS nudges (
  run_id TEXT NOT NULL,
  distributor_id TEXT NOT NULL,
  cohort TEXT NOT NULL,
  kind TEXT NOT NULL,                       -- nudge | reminder
  language TEXT NOT NULL,
  sent_at REAL NOT NULL,
  text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_nudges_run ON nudges (run_id, distributor_id);

CREATE TABLE IF NOT EXISTS survey_responses (
  run_id TEXT NOT NULL,
  response_id TEXT NOT NULL,
  distributor_id TEXT NOT NULL,
  started_at REAL NOT NULL,
  submitted_at REAL NOT NULL,
  survey_seconds INTEGER NOT NULL,
  q1_intent TEXT,
  q2 INTEGER, q3 INTEGER, q4 INTEGER, q5 INTEGER,
  q6 TEXT,
  q7_text TEXT,
  q7_language TEXT,
  q7_theme TEXT,
  is_duplicate INTEGER NOT NULL DEFAULT 0,
  is_latest INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (run_id, response_id)
);
CREATE INDEX IF NOT EXISTS ix_resp_run_day ON survey_responses (run_id, submitted_at);

CREATE TABLE IF NOT EXISTS sanity_flags (
  run_id TEXT NOT NULL,
  response_id TEXT NOT NULL,
  code TEXT NOT NULL,
  severity TEXT NOT NULL,
  label TEXT NOT NULL,
  asm_decision TEXT,                        -- Keep | Drop | NULL
  decided_at REAL
);
CREATE INDEX IF NOT EXISTS ix_flags_run ON sanity_flags (run_id, response_id);

CREATE TABLE IF NOT EXISTS cta_plan (
  run_id TEXT NOT NULL,
  row_id TEXT NOT NULL,
  group_type TEXT NOT NULL,                 -- cohort | individual | custom | individual_group
  group_name TEXT NOT NULL,
  parent_row_id TEXT,                       -- individual people point at the 'Individual attention' row
  distributor_id TEXT,
  cta_code TEXT,                            -- NULL only on the 'Individual attention' parent row
  cta_variant TEXT,                         -- call | visit (ASM_CALL only)
  label TEXT NOT NULL,                      -- plain follow-up line shown in the matrix
  text_en TEXT, text_bn TEXT, text_hi TEXT,
  members INTEGER NOT NULL,
  member_ids_json TEXT NOT NULL,
  confidence REAL,
  priority TEXT NOT NULL,
  revenue_at_stake_l REAL NOT NULL,
  reason TEXT NOT NULL,
  why TEXT,
  status TEXT NOT NULL DEFAULT 'Pending',   -- Pending | Approved | Rejected
  created_at REAL NOT NULL,
  decided_at REAL,
  sort_order INTEGER NOT NULL,
  PRIMARY KEY (run_id, row_id)
);

CREATE TABLE IF NOT EXISTS cta_deliveries (
  run_id TEXT NOT NULL,
  distributor_id TEXT NOT NULL,
  row_id TEXT NOT NULL,
  cta_code TEXT NOT NULL,
  language TEXT NOT NULL,
  sent_at REAL NOT NULL,
  text TEXT
);

CREATE TABLE IF NOT EXISTS asm_calls (
  run_id TEXT NOT NULL,
  distributor_id TEXT NOT NULL,
  row_id TEXT NOT NULL,
  sim_day REAL NOT NULL,
  kind TEXT NOT NULL,                       -- call | visit
  outcome TEXT
);

CREATE TABLE IF NOT EXISTS enrolments (
  run_id TEXT NOT NULL,
  distributor_id TEXT NOT NULL,
  sim_day REAL NOT NULL,
  path TEXT NOT NULL,                       -- after_nudge | self | after_cta | after_asm_call
  cta_code TEXT,
  PRIMARY KEY (run_id, distributor_id)
);

CREATE TABLE IF NOT EXISTS october_sales (
  run_id TEXT NOT NULL,
  distributor_id TEXT NOT NULL,
  baseline_l REAL NOT NULL,
  predicted_l REAL NOT NULL,
  actual_l REAL NOT NULL,
  hit_prediction INTEGER NOT NULL,
  PRIMARY KEY (run_id, distributor_id)
);

CREATE TABLE IF NOT EXISTS personas (
  run_id TEXT NOT NULL,
  distributor_id TEXT NOT NULL,
  language TEXT NOT NULL,
  language_on_file TEXT NOT NULL,
  language_changed INTEGER NOT NULL,
  best_time TEXT,
  best_hour INTEGER,
  reply_speed TEXT NOT NULL,
  reply_hours REAL,
  prefers TEXT NOT NULL,
  what_worked TEXT NOT NULL,
  next_time TEXT NOT NULL,
  updated_day REAL NOT NULL,
  PRIMARY KEY (run_id, distributor_id)
);

CREATE TABLE IF NOT EXISTS chat_messages (
  run_id TEXT NOT NULL,
  distributor_id TEXT NOT NULL,
  sim_day REAL NOT NULL,
  sender TEXT NOT NULL,                     -- distributor | desk
  text TEXT NOT NULL,
  intent TEXT,
  tool TEXT
);

CREATE TABLE IF NOT EXISTS next_cycle_profiles (
  distributor_id TEXT PRIMARY KEY,
  language TEXT NOT NULL,
  best_hour INTEGER,
  prefers TEXT NOT NULL,
  next_time TEXT NOT NULL,
  from_run_id TEXT NOT NULL,
  applied_at TEXT NOT NULL
);
