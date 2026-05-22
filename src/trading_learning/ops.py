from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


CORE_TABLES = (
    "daily_reviews",
    "knowledge_cards",
    "strategy_experiments",
    "learning_reports",
    "remote_tasks",
    "testnet_order_records",
)


def build_local_health(db_path: Path) -> dict[str, Any]:
    health: dict[str, Any] = {
        "status": "ok",
        "database": {
            "path": str(db_path),
            "exists": db_path.exists(),
        },
        "counts": {},
        "checks": [],
    }
    if not db_path.exists():
        health["status"] = "missing_database"
        health["checks"].append({"name": "database", "status": "missing"})
        return health
    try:
        with sqlite3.connect(db_path) as conn:
            for table in CORE_TABLES:
                try:
                    health["counts"][table] = int(conn.execute(f"select count(*) from {table}").fetchone()[0])
                    health["checks"].append({"name": table, "status": "ok"})
                except sqlite3.Error as exc:
                    health["status"] = "degraded"
                    health["counts"][table] = 0
                    health["checks"].append({"name": table, "status": "failed", "message": str(exc)})
    except sqlite3.Error as exc:
        health["status"] = "failed"
        health["checks"].append({"name": "database_open", "status": "failed", "message": str(exc)})
    return health


def backup_database(db_path: Path, backup_dir: Path) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"database not found: {db_path}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"{db_path.stem}-{timestamp}.sqlite3"
    shutil.copy2(db_path, backup_path)
    return {
        "status": "ok",
        "source_path": str(db_path),
        "backup_path": str(backup_path),
        "bytes": backup_path.stat().st_size,
    }


def restore_database(backup_path: str | Path, target_path: Path) -> dict[str, Any]:
    backup = Path(backup_path)
    if not backup.exists():
        raise FileNotFoundError(f"backup not found: {backup}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, target_path)
    return {
        "status": "ok",
        "backup_path": str(backup),
        "target_path": str(target_path),
        "bytes": target_path.stat().st_size,
    }
