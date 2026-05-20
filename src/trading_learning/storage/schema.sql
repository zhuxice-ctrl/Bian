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
