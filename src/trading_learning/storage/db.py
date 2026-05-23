from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def connect_readonly(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    schema = schema_path.read_text(encoding="utf-8")
    try:
        conn.executescript(f"BEGIN;\n{schema}\nCOMMIT;")
        _apply_lightweight_migrations(conn)
    except sqlite3.Error:
        conn.rollback()
        raise


def _apply_lightweight_migrations(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("pragma table_info(testnet_order_records)").fetchall()}
    for name in (
        "experiment_external_id",
        "signal_id",
        "plan_external_id",
        "checklist_external_id",
        "review_external_id",
    ):
        if name not in columns:
            conn.execute(f"alter table testnet_order_records add column {name} text not null default ''")
    _migrate_hypothesis_log_decisions(conn)
    conn.commit()


def _migrate_hypothesis_log_decisions(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "select sql from sqlite_master where type = 'table' and name = 'hypothesis_log'"
    ).fetchone()
    if row is None or "deferred" in str(row["sql"]):
        return
    conn.executescript(
        """
        alter table hypothesis_log rename to hypothesis_log_old;
        create table hypothesis_log (
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
          check (decision in ('', 'kept', 'rejected', 'inconclusive', 'risk_reduction_kept', 'deferred'))
        );
        insert into hypothesis_log (
          id, hypothesis_id, title, created_at, description, parent_iteration,
          change_summary, predicted, decision_rule, ran_at, actual, decision,
          reason, hindsight_notes, code_commit, backtest_run_id, updated_at
        )
        select
          id, hypothesis_id, title, created_at, description, parent_iteration,
          change_summary, predicted, decision_rule, ran_at, actual, decision,
          reason, hindsight_notes, code_commit, backtest_run_id, updated_at
        from hypothesis_log_old;
        drop table hypothesis_log_old;
        """
    )
