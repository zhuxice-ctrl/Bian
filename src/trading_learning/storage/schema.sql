create table if not exists trades (
  id integer primary key autoincrement,
  external_id text not null unique,
  symbol text not null,
  side text not null check (side in ('BUY', 'SELL')),
  quantity real not null,
  price real not null,
  fee real not null default 0,
  timestamp text not null,
  reason text not null,
  source text not null default 'backtest',
  created_at text not null default CURRENT_TIMESTAMP
);

create table if not exists daily_reviews (
  id integer primary key autoincrement,
  external_id text not null unique,
  review_date text not null,
  symbols_watched text not null,
  trade_count integer not null,
  plan_followed integer not null check (plan_followed in (0, 1)),
  pnl real not null default 0,
  mistake_tags text not null default '[]',
  emotion_note text not null default '',
  lesson text not null default '',
  created_at text not null default CURRENT_TIMESTAMP,
  updated_at text not null default CURRENT_TIMESTAMP
);

create table if not exists knowledge_cards (
  id integer primary key autoincrement,
  external_id text not null unique,
  title text not null,
  category text not null,
  content text not null,
  source text not null default 'manual',
  status text not null default 'active',
  created_at text not null default CURRENT_TIMESTAMP,
  updated_at text not null default CURRENT_TIMESTAMP
);

create table if not exists strategy_hypotheses (
  id integer primary key autoincrement,
  external_id text not null unique,
  title text not null,
  statement text not null,
  status text not null default 'draft',
  created_at text not null default CURRENT_TIMESTAMP,
  updated_at text not null default CURRENT_TIMESTAMP
);

create table if not exists hypothesis_log (
  id integer primary key autoincrement,
  hypothesis_id text not null unique,
  title text not null,
  created_at text not null,
  description text not null,
  parent_iteration text not null,
  change_summary text not null,
  predicted text not null,
  decision_rule text not null,
  ran_at text,
  actual text not null default '{}',
  decision text not null default '',
  reason text not null default '',
  hindsight_notes text not null default '',
  code_commit text not null default '',
  backtest_run_id text not null default '',
  updated_at text not null default CURRENT_TIMESTAMP,
  check (decision in ('', 'kept', 'rejected', 'inconclusive', 'risk_reduction_kept'))
);

create table if not exists strategy_experiments (
  id integer primary key autoincrement,
  external_id text not null unique,
  strategy_name text not null,
  symbol text not null,
  interval text not null,
  source_csv text not null,
  parameters text not null default '{}',
  metrics text not null default '{}',
  note text not null default '',
  created_at text not null default CURRENT_TIMESTAMP,
  updated_at text not null default CURRENT_TIMESTAMP
);

create table if not exists ai_drafts (
  id integer primary key autoincrement,
  external_id text not null unique,
  task_type text not null,
  source_external_id text not null,
  content text not null,
  status text not null default 'draft',
  created_at text not null default CURRENT_TIMESTAMP
);

create table if not exists brain_audit_logs (
  id integer primary key autoincrement,
  external_id text not null unique,
  user_id text not null,
  command_text text not null,
  status text not null,
  response text not null,
  created_at text not null default CURRENT_TIMESTAMP
);

create table if not exists brain_pending_confirmations (
  id integer primary key autoincrement,
  code text not null unique,
  user_id text not null,
  command_text text not null,
  payload text not null,
  created_at text not null default CURRENT_TIMESTAMP
);

create table if not exists trading_plans (
  id integer primary key autoincrement,
  external_id text not null unique,
  plan_date text not null unique,
  symbols text not null,
  max_trades integer not null,
  bias text not null default '',
  conditions text not null default '',
  forbidden text not null default '',
  created_at text not null default CURRENT_TIMESTAMP,
  updated_at text not null default CURRENT_TIMESTAMP
);

create table if not exists pre_trade_checklists (
  id integer primary key autoincrement,
  external_id text not null unique,
  checklist_date text not null,
  symbol text not null,
  plan_ok integer not null check (plan_ok in (0, 1)),
  setup_ok integer not null check (setup_ok in (0, 1)),
  risk_ok integer not null check (risk_ok in (0, 1)),
  emotion text not null default '',
  emotion_ok integer not null check (emotion_ok in (0, 1)),
  created_at text not null default CURRENT_TIMESTAMP
);

create table if not exists knowledge_card_tags (
  id integer primary key autoincrement,
  card_external_id text not null,
  tag text not null,
  created_at text not null default CURRENT_TIMESTAMP,
  unique (card_external_id, tag)
);

create table if not exists mistake_knowledge_links (
  id integer primary key autoincrement,
  review_external_id text not null,
  card_external_id text not null,
  tag text not null,
  created_at text not null default CURRENT_TIMESTAMP,
  unique (review_external_id, card_external_id, tag)
);

create table if not exists review_experiment_links (
  id integer primary key autoincrement,
  review_external_id text not null,
  experiment_external_id text not null,
  tag text not null default '',
  note text not null default '',
  created_at text not null default CURRENT_TIMESTAMP,
  unique (review_external_id, experiment_external_id, tag)
);

create table if not exists learning_reports (
  id integer primary key autoincrement,
  external_id text not null unique,
  report_type text not null,
  period_start text not null,
  period_end text not null,
  content text not null,
  created_at text not null default CURRENT_TIMESTAMP,
  updated_at text not null default CURRENT_TIMESTAMP,
  unique (report_type, period_start, period_end)
);

create table if not exists experiment_review_drafts (
  id integer primary key autoincrement,
  external_id text not null unique,
  experiment_external_id text not null unique,
  content text not null,
  status text not null default 'draft',
  created_at text not null default CURRENT_TIMESTAMP,
  updated_at text not null default CURRENT_TIMESTAMP
);

create table if not exists experiment_decisions (
  id integer primary key autoincrement,
  experiment_external_id text not null unique,
  decision text not null check (decision in ('rejected', 'needs_more_data', 'continue_research', 'testnet_candidate', 'archived')),
  reason text not null default '',
  created_at text not null default CURRENT_TIMESTAMP,
  updated_at text not null default CURRENT_TIMESTAMP
);

create table if not exists brain_suggested_commands (
  id integer primary key autoincrement,
  external_id text not null unique,
  user_id text not null,
  command_text text not null,
  source_text text not null,
  status text not null default 'pending',
  result text not null default '{}',
  created_at text not null default CURRENT_TIMESTAMP,
  updated_at text not null default CURRENT_TIMESTAMP
);

create table if not exists remote_tasks (
  id integer primary key autoincrement,
  external_id text not null unique,
  requester_user_id text not null,
  command_text text not null,
  task_type text not null,
  risk_level text not null,
  payload text not null default '{}',
  state text not null default 'queued',
  runner_id text not null default '',
  result_summary text not null default '',
  result_payload text not null default '{}',
  error_message text not null default '',
  created_at text not null default CURRENT_TIMESTAMP,
  claimed_at text,
  completed_at text,
  updated_at text not null default CURRENT_TIMESTAMP
);

create table if not exists experiment_proposals (
  id integer primary key autoincrement,
  external_id text not null unique,
  hypothesis_external_id text not null,
  source_experiment_external_id text not null default '',
  content text not null,
  status text not null default 'proposed',
  outcome text not null default '{}',
  created_at text not null default CURRENT_TIMESTAMP,
  updated_at text not null default CURRENT_TIMESTAMP
);

create table if not exists strategy_profiles (
  id integer primary key autoincrement,
  external_id text not null unique,
  name text not null unique,
  strategy_name text not null,
  symbol text not null,
  interval text not null,
  source_csv text not null,
  parameters text not null default '{}',
  description text not null default '',
  created_at text not null default CURRENT_TIMESTAMP,
  updated_at text not null default CURRENT_TIMESTAMP
);

create table if not exists parameter_sweeps (
  id integer primary key autoincrement,
  external_id text not null unique,
  strategy_name text not null,
  symbol text not null,
  interval text not null,
  source_csv text not null,
  grid text not null default '{}',
  result text not null default '{}',
  created_at text not null default CURRENT_TIMESTAMP,
  updated_at text not null default CURRENT_TIMESTAMP
);

create table if not exists testnet_order_records (
  id integer primary key autoincrement,
  external_id text not null unique,
  user_id text not null,
  action text not null,
  symbol text not null,
  side text not null default '',
  order_type text not null default '',
  quote_order_qty real,
  order_id text not null default '',
  status text not null default '',
  experiment_external_id text not null default '',
  signal_id text not null default '',
  plan_external_id text not null default '',
  checklist_external_id text not null default '',
  review_external_id text not null default '',
  request_payload text not null default '{}',
  response_payload text not null default '{}',
  created_at text not null default CURRENT_TIMESTAMP
);
