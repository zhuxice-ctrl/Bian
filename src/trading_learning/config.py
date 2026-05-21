from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ALLOWED_SYMBOLS = ("BTCUSDT", "ETHUSDT")


@dataclass(frozen=True)
class AppConfig:
    db_path: Path
    local_codex_base_url: str
    local_codex_model: str
    local_codex_api_key: str | None
    binance_testnet_base_url: str
    binance_testnet_api_key: str | None
    binance_testnet_api_secret: str | None
    feishu_verification_token: str | None
    feishu_encrypt_key: str | None
    feishu_user_map: str
    feishu_app_id: str | None
    feishu_app_secret: str | None
    allowed_symbols: tuple[str, ...] = DEFAULT_ALLOWED_SYMBOLS


def load_config() -> AppConfig:
    return AppConfig(
        db_path=Path(os.getenv("TRADING_LEARNING_DB_PATH", "data/local/trading_learning.sqlite3")),
        local_codex_base_url=os.getenv("LOCAL_CODEX_BASE_URL", "http://127.0.0.1:61771/v1"),
        local_codex_model=os.getenv("LOCAL_CODEX_MODEL", "gpt-5.4-mini"),
        local_codex_api_key=os.getenv("LOCAL_CODEX_API_KEY"),
        binance_testnet_base_url=os.getenv("BINANCE_TESTNET_BASE_URL", "https://testnet.binance.vision"),
        binance_testnet_api_key=os.getenv("BINANCE_TESTNET_API_KEY"),
        binance_testnet_api_secret=os.getenv("BINANCE_TESTNET_API_SECRET"),
        feishu_verification_token=os.getenv("FEISHU_VERIFICATION_TOKEN"),
        feishu_encrypt_key=os.getenv("FEISHU_ENCRYPT_KEY"),
        feishu_user_map=os.getenv("FEISHU_USER_MAP", ""),
        feishu_app_id=os.getenv("FEISHU_APP_ID"),
        feishu_app_secret=os.getenv("FEISHU_APP_SECRET"),
        allowed_symbols=parse_symbols(os.getenv("TRADING_LEARNING_ALLOWED_SYMBOLS", ",".join(DEFAULT_ALLOWED_SYMBOLS))),
    )


def parse_symbols(value: str) -> tuple[str, ...]:
    return tuple(symbol.strip().upper() for symbol in value.split(",") if symbol.strip())
