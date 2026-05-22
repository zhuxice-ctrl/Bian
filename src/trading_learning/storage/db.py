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
    conn.commit()
