from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    db_path: Path
    local_codex_base_url: str
    local_codex_model: str
    local_codex_api_key: str | None


def load_config() -> AppConfig:
    return AppConfig(
        db_path=Path(os.getenv("TRADING_LEARNING_DB_PATH", "data/local/trading_learning.sqlite3")),
        local_codex_base_url=os.getenv("LOCAL_CODEX_BASE_URL", "http://127.0.0.1:61771/v1"),
        local_codex_model=os.getenv("LOCAL_CODEX_MODEL", "gpt-5.4-mini"),
        local_codex_api_key=os.getenv("LOCAL_CODEX_API_KEY"),
    )
