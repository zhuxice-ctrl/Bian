# Phase 1 Local Trading Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first local trading-learning loop: load historical candles, backtest a moving-average strategy, store trades and reviews in SQLite, create learning records, call a local Codex-compatible assistant for draft-only summaries, and export portable data.

**Architecture:** Use a small Python package with explicit boundaries: `market_data` loads candles, `strategy` creates signals, `backtest` simulates fills, `storage` owns SQLite, `journal` and `learning` own review data, `ai_assistant` writes draft suggestions, and `export_import` creates JSONL/Markdown/ZIP exports. Phase 1 has no Binance API dependency and cannot place live orders.

**Tech Stack:** Python 3.11+, SQLite, `argparse`, `dataclasses`, `urllib.request`, `pytest`.

---

## File Structure

- Create: `pyproject.toml` - package metadata and pytest config.
- Create: `.gitignore` - ignores local databases, exports, secrets, caches.
- Create: `.env.example` - documents local Codex environment variables without secrets.
- Create: `src/trading_learning/__init__.py` - package marker.
- Create: `src/trading_learning/models.py` - shared dataclasses and typed enums.
- Create: `src/trading_learning/config.py` - environment-based runtime config.
- Create: `src/trading_learning/storage/schema.sql` - SQLite tables.
- Create: `src/trading_learning/storage/db.py` - connection and schema initialization.
- Create: `src/trading_learning/market_data/csv_loader.py` - load OHLCV candles from CSV.
- Create: `src/trading_learning/strategy/moving_average.py` - baseline moving-average crossover strategy.
- Create: `src/trading_learning/backtest/engine.py` - deterministic long-only spot backtest engine.
- Create: `src/trading_learning/journal/repository.py` - trade and daily review persistence.
- Create: `src/trading_learning/learning/repository.py` - knowledge cards and strategy hypotheses.
- Create: `src/trading_learning/ai_assistant/local_codex.py` - local Codex-compatible chat adapter.
- Create: `src/trading_learning/ai_assistant/tasks.py` - build review-summary requests and store drafts.
- Create: `src/trading_learning/export_import/exporter.py` - JSONL, Markdown, and ZIP export.
- Create: `src/trading_learning/cli.py` - command line entrypoint.
- Create: `tests/fixtures/btcusdt_1h_sample.csv` - deterministic candle fixture.
- Create: `tests/test_csv_loader.py` - candle loading tests.
- Create: `tests/test_moving_average.py` - signal tests.
- Create: `tests/test_backtest_engine.py` - trade count and PnL tests.
- Create: `tests/test_storage.py` - schema and repository tests.
- Create: `tests/test_ai_assistant.py` - local API adapter tests with a fake HTTP server.
- Create: `tests/test_exporter.py` - export package tests.

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/trading_learning/__init__.py`
- Create: `src/trading_learning/models.py`
- Create: `src/trading_learning/config.py`

- [ ] **Step 1: Create package metadata**

Write `pyproject.toml`:

```toml
[project]
name = "trading-learning"
version = "0.1.0"
description = "Local low-frequency crypto trading learning system"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
trading-learning = "trading_learning.cli:main"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Create local ignore rules**

Write `.gitignore`:

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
*.sqlite
*.sqlite3
.env
exports/
data/local/
```

- [ ] **Step 3: Document local environment variables**

Write `.env.example`:

```env
TRADING_LEARNING_DB_PATH=data/local/trading_learning.sqlite3
LOCAL_CODEX_BASE_URL=http://127.0.0.1:61771/v1
LOCAL_CODEX_MODEL=gpt-5.4-mini
LOCAL_CODEX_API_KEY=replace_with_local_only_key
```

- [ ] **Step 4: Define shared models**

Write `src/trading_learning/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Candle:
    symbol: str
    opened_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Signal:
    symbol: str
    timestamp: datetime
    action: SignalAction
    reason: str


@dataclass(frozen=True)
class Trade:
    external_id: str
    symbol: str
    side: Side
    quantity: float
    price: float
    fee: float
    timestamp: datetime
    reason: str


@dataclass(frozen=True)
class BacktestResult:
    symbol: str
    starting_cash: float
    ending_cash: float
    position_quantity: float
    trade_count: int
    trades: tuple[Trade, ...]
```

- [ ] **Step 5: Define environment config**

Write `src/trading_learning/config.py`:

```python
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
```

- [ ] **Step 6: Run scaffold check**

Run: `python -m pytest`

Expected: pytest starts and reports no collected tests or only import-related collection success after tests are added in later tasks.

- [ ] **Step 7: Commit scaffold**

Run:

```bash
git add pyproject.toml .gitignore .env.example src/trading_learning
git commit -m "chore: scaffold trading learning package"
```

Expected: commit succeeds.

## Task 2: SQLite Schema And Repositories

**Files:**
- Create: `src/trading_learning/storage/schema.sql`
- Create: `src/trading_learning/storage/db.py`
- Create: `src/trading_learning/storage/__init__.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing schema initialization test**

Write `tests/test_storage.py`:

```python
from trading_learning.storage.db import connect, initialize_schema


def test_initialize_schema_creates_core_tables(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    with connect(db_path) as conn:
        initialize_schema(conn)
        table_names = {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table'"
            ).fetchall()
        }

    assert {
        "trades",
        "daily_reviews",
        "knowledge_cards",
        "strategy_hypotheses",
        "ai_drafts",
    }.issubset(table_names)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_storage.py -v`

Expected: FAIL with `ModuleNotFoundError` for `trading_learning.storage`.

- [ ] **Step 3: Write schema**

Write `src/trading_learning/storage/schema.sql`:

```sql
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
```

- [ ] **Step 4: Write database helpers**

Write `src/trading_learning/storage/db.py`:

```python
from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()
```

Create `src/trading_learning/storage/__init__.py` as an empty file.

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_storage.py -v`

Expected: PASS.

- [ ] **Step 6: Commit storage base**

Run:

```bash
git add src/trading_learning/storage tests/test_storage.py
git commit -m "feat: add sqlite schema initialization"
```

Expected: commit succeeds.

## Task 3: Historical CSV Loader

**Files:**
- Create: `src/trading_learning/market_data/__init__.py`
- Create: `src/trading_learning/market_data/csv_loader.py`
- Create: `tests/fixtures/btcusdt_1h_sample.csv`
- Create: `tests/test_csv_loader.py`

- [ ] **Step 1: Create deterministic fixture**

Write `tests/fixtures/btcusdt_1h_sample.csv`:

```csv
opened_at,open,high,low,close,volume
2026-05-01T00:00:00+00:00,100,105,99,104,10
2026-05-01T01:00:00+00:00,104,108,103,107,12
2026-05-01T02:00:00+00:00,107,109,101,102,14
```

- [ ] **Step 2: Write failing loader test**

Write `tests/test_csv_loader.py`:

```python
from pathlib import Path

from trading_learning.market_data.csv_loader import load_candles_csv


def test_load_candles_csv_parses_rows():
    candles = load_candles_csv(
        Path("tests/fixtures/btcusdt_1h_sample.csv"),
        symbol="BTCUSDT",
    )

    assert len(candles) == 3
    assert candles[0].symbol == "BTCUSDT"
    assert candles[0].open == 100.0
    assert candles[1].close == 107.0
    assert candles[2].volume == 14.0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_csv_loader.py -v`

Expected: FAIL with `ModuleNotFoundError` for `trading_learning.market_data`.

- [ ] **Step 4: Implement CSV loader**

Write `src/trading_learning/market_data/csv_loader.py`:

```python
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from trading_learning.models import Candle


def load_candles_csv(path: Path, symbol: str) -> list[Candle]:
    candles: list[Candle] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            candles.append(
                Candle(
                    symbol=symbol,
                    opened_at=datetime.fromisoformat(row["opened_at"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )
    return candles
```

Create `src/trading_learning/market_data/__init__.py` as an empty file.

- [ ] **Step 5: Run loader test**

Run: `python -m pytest tests/test_csv_loader.py -v`

Expected: PASS.

- [ ] **Step 6: Commit loader**

Run:

```bash
git add src/trading_learning/market_data tests/fixtures tests/test_csv_loader.py
git commit -m "feat: load historical candles from csv"
```

Expected: commit succeeds.

## Task 4: Moving Average Strategy

**Files:**
- Create: `src/trading_learning/strategy/__init__.py`
- Create: `src/trading_learning/strategy/moving_average.py`
- Create: `tests/test_moving_average.py`

- [ ] **Step 1: Write failing signal test**

Write `tests/test_moving_average.py`:

```python
from datetime import datetime, timezone

from trading_learning.models import Candle, SignalAction
from trading_learning.strategy.moving_average import moving_average_crossover_signals


def candle(index: int, close: float) -> Candle:
    return Candle(
        symbol="BTCUSDT",
        opened_at=datetime(2026, 5, 1, index, tzinfo=timezone.utc),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1.0,
    )


def test_moving_average_crossover_emits_buy_then_sell():
    closes = [10, 10, 10, 11, 12, 13, 12, 11, 10]
    signals = moving_average_crossover_signals(
        [candle(i, value) for i, value in enumerate(closes)],
        short_window=2,
        long_window=3,
    )

    actions = [signal.action for signal in signals]
    assert SignalAction.BUY in actions
    assert SignalAction.SELL in actions
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_moving_average.py -v`

Expected: FAIL with `ModuleNotFoundError` for `trading_learning.strategy`.

- [ ] **Step 3: Implement moving average strategy**

Write `src/trading_learning/strategy/moving_average.py`:

```python
from __future__ import annotations

from trading_learning.models import Candle, Signal, SignalAction


def simple_average(values: list[float]) -> float:
    return sum(values) / len(values)


def moving_average_crossover_signals(
    candles: list[Candle],
    short_window: int,
    long_window: int,
) -> list[Signal]:
    if short_window <= 0 or long_window <= 0:
        raise ValueError("windows must be positive")
    if short_window >= long_window:
        raise ValueError("short_window must be lower than long_window")

    signals: list[Signal] = []
    previous_relation: int | None = None

    closes = [candle.close for candle in candles]
    for index in range(long_window - 1, len(candles)):
        short_ma = simple_average(closes[index - short_window + 1 : index + 1])
        long_ma = simple_average(closes[index - long_window + 1 : index + 1])
        relation = 1 if short_ma > long_ma else -1 if short_ma < long_ma else 0

        if previous_relation is not None:
            if previous_relation <= 0 and relation > 0:
                signals.append(
                    Signal(
                        symbol=candles[index].symbol,
                        timestamp=candles[index].opened_at,
                        action=SignalAction.BUY,
                        reason=f"short MA {short_window} crossed above long MA {long_window}",
                    )
                )
            elif previous_relation >= 0 and relation < 0:
                signals.append(
                    Signal(
                        symbol=candles[index].symbol,
                        timestamp=candles[index].opened_at,
                        action=SignalAction.SELL,
                        reason=f"short MA {short_window} crossed below long MA {long_window}",
                    )
                )

        previous_relation = relation

    return signals
```

Create `src/trading_learning/strategy/__init__.py` as an empty file.

- [ ] **Step 4: Run strategy test**

Run: `python -m pytest tests/test_moving_average.py -v`

Expected: PASS.

- [ ] **Step 5: Commit strategy**

Run:

```bash
git add src/trading_learning/strategy tests/test_moving_average.py
git commit -m "feat: add moving average crossover strategy"
```

Expected: commit succeeds.

## Task 5: Backtest Engine With Daily Trade Limit

**Files:**
- Create: `src/trading_learning/backtest/__init__.py`
- Create: `src/trading_learning/backtest/engine.py`
- Create: `tests/test_backtest_engine.py`

- [ ] **Step 1: Write failing backtest test**

Write `tests/test_backtest_engine.py`:

```python
from datetime import datetime, timezone

from trading_learning.backtest.engine import run_spot_backtest
from trading_learning.models import Signal, SignalAction


def test_backtest_enforces_daily_trade_limit():
    signals = [
        Signal("BTCUSDT", datetime(2026, 5, 1, hour, tzinfo=timezone.utc), SignalAction.BUY if hour % 2 == 0 else SignalAction.SELL, "test")
        for hour in range(8)
    ]
    prices = {
        signal.timestamp: 100.0 + index
        for index, signal in enumerate(signals)
    }

    result = run_spot_backtest(
        symbol="BTCUSDT",
        signals=signals,
        prices_by_timestamp=prices,
        starting_cash=1000.0,
        quote_amount_per_buy=100.0,
        fee_rate=0.001,
        daily_trade_limit=5,
    )

    assert result.trade_count == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_backtest_engine.py -v`

Expected: FAIL with `ModuleNotFoundError` for `trading_learning.backtest`.

- [ ] **Step 3: Implement deterministic backtest**

Write `src/trading_learning/backtest/engine.py`:

```python
from __future__ import annotations

from collections import defaultdict

from trading_learning.models import BacktestResult, Side, Signal, SignalAction, Trade


def run_spot_backtest(
    symbol: str,
    signals: list[Signal],
    prices_by_timestamp: dict,
    starting_cash: float,
    quote_amount_per_buy: float,
    fee_rate: float,
    daily_trade_limit: int,
) -> BacktestResult:
    cash = starting_cash
    position_quantity = 0.0
    trades: list[Trade] = []
    daily_counts: dict[str, int] = defaultdict(int)

    for signal in signals:
        day_key = signal.timestamp.date().isoformat()
        if daily_counts[day_key] >= daily_trade_limit:
            continue
        price = float(prices_by_timestamp[signal.timestamp])

        if signal.action == SignalAction.BUY and cash >= quote_amount_per_buy:
            fee = quote_amount_per_buy * fee_rate
            quantity = (quote_amount_per_buy - fee) / price
            cash -= quote_amount_per_buy
            position_quantity += quantity
            daily_counts[day_key] += 1
            trades.append(
                Trade(
                    external_id=f"backtest-{symbol}-{signal.timestamp.isoformat()}-buy",
                    symbol=symbol,
                    side=Side.BUY,
                    quantity=quantity,
                    price=price,
                    fee=fee,
                    timestamp=signal.timestamp,
                    reason=signal.reason,
                )
            )
        elif signal.action == SignalAction.SELL and position_quantity > 0:
            gross = position_quantity * price
            fee = gross * fee_rate
            cash += gross - fee
            quantity = position_quantity
            position_quantity = 0.0
            daily_counts[day_key] += 1
            trades.append(
                Trade(
                    external_id=f"backtest-{symbol}-{signal.timestamp.isoformat()}-sell",
                    symbol=symbol,
                    side=Side.SELL,
                    quantity=quantity,
                    price=price,
                    fee=fee,
                    timestamp=signal.timestamp,
                    reason=signal.reason,
                )
            )

    return BacktestResult(
        symbol=symbol,
        starting_cash=starting_cash,
        ending_cash=cash,
        position_quantity=position_quantity,
        trade_count=len(trades),
        trades=tuple(trades),
    )
```

Create `src/trading_learning/backtest/__init__.py` as an empty file.

- [ ] **Step 4: Run backtest test**

Run: `python -m pytest tests/test_backtest_engine.py -v`

Expected: PASS.

- [ ] **Step 5: Commit backtest engine**

Run:

```bash
git add src/trading_learning/backtest tests/test_backtest_engine.py
git commit -m "feat: add spot backtest engine"
```

Expected: commit succeeds.

## Task 6: Journal And Learning Repositories

**Files:**
- Create: `src/trading_learning/journal/__init__.py`
- Create: `src/trading_learning/journal/repository.py`
- Create: `src/trading_learning/learning/__init__.py`
- Create: `src/trading_learning/learning/repository.py`
- Modify: `tests/test_storage.py`

- [ ] **Step 1: Add repository persistence test**

Append to `tests/test_storage.py`:

```python
from trading_learning.journal.repository import save_daily_review
from trading_learning.learning.repository import save_knowledge_card, save_strategy_hypothesis


def test_repositories_store_review_and_learning_records(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    with connect(db_path) as conn:
        initialize_schema(conn)
        save_daily_review(
            conn,
            external_id="review-2026-05-01",
            review_date="2026-05-01",
            symbols_watched=["BTCUSDT"],
            trade_count=2,
            plan_followed=True,
            pnl=12.5,
            mistake_tags=["late_entry"],
            emotion_note="wanted to chase after a loss",
            lesson="wait for planned entries",
        )
        save_knowledge_card(
            conn,
            external_id="card-ma-lag",
            title="Moving average lag",
            category="technical_analysis",
            content="Moving averages confirm trends after price has already moved.",
        )
        save_strategy_hypothesis(
            conn,
            external_id="hypothesis-ma-cross",
            title="MA crossover continuation",
            statement="If short MA crosses above long MA, momentum may continue.",
        )

        review_count = conn.execute("select count(*) from daily_reviews").fetchone()[0]
        card_count = conn.execute("select count(*) from knowledge_cards").fetchone()[0]
        hypothesis_count = conn.execute("select count(*) from strategy_hypotheses").fetchone()[0]

    assert review_count == 1
    assert card_count == 1
    assert hypothesis_count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_storage.py -v`

Expected: FAIL with `ModuleNotFoundError` for `trading_learning.journal`.

- [ ] **Step 3: Implement journal repository**

Write `src/trading_learning/journal/repository.py`:

```python
from __future__ import annotations

import json
import sqlite3


def save_daily_review(
    conn: sqlite3.Connection,
    external_id: str,
    review_date: str,
    symbols_watched: list[str],
    trade_count: int,
    plan_followed: bool,
    pnl: float,
    mistake_tags: list[str],
    emotion_note: str,
    lesson: str,
) -> None:
    conn.execute(
        """
        insert into daily_reviews (
          external_id, review_date, symbols_watched, trade_count, plan_followed,
          pnl, mistake_tags, emotion_note, lesson
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            external_id,
            review_date,
            json.dumps(symbols_watched, ensure_ascii=False),
            trade_count,
            1 if plan_followed else 0,
            pnl,
            json.dumps(mistake_tags, ensure_ascii=False),
            emotion_note,
            lesson,
        ),
    )
    conn.commit()
```

Create `src/trading_learning/journal/__init__.py` as an empty file.

- [ ] **Step 4: Implement learning repository**

Write `src/trading_learning/learning/repository.py`:

```python
from __future__ import annotations

import sqlite3


def save_knowledge_card(
    conn: sqlite3.Connection,
    external_id: str,
    title: str,
    category: str,
    content: str,
) -> None:
    conn.execute(
        """
        insert into knowledge_cards (external_id, title, category, content)
        values (?, ?, ?, ?)
        """,
        (external_id, title, category, content),
    )
    conn.commit()


def save_strategy_hypothesis(
    conn: sqlite3.Connection,
    external_id: str,
    title: str,
    statement: str,
) -> None:
    conn.execute(
        """
        insert into strategy_hypotheses (external_id, title, statement)
        values (?, ?, ?)
        """,
        (external_id, title, statement),
    )
    conn.commit()
```

Create `src/trading_learning/learning/__init__.py` as an empty file.

- [ ] **Step 5: Run repository tests**

Run: `python -m pytest tests/test_storage.py -v`

Expected: PASS.

- [ ] **Step 6: Commit repositories**

Run:

```bash
git add src/trading_learning/journal src/trading_learning/learning tests/test_storage.py
git commit -m "feat: persist journal and learning records"
```

Expected: commit succeeds.

## Task 7: Local Codex Assistant Adapter

**Files:**
- Create: `src/trading_learning/ai_assistant/__init__.py`
- Create: `src/trading_learning/ai_assistant/local_codex.py`
- Create: `src/trading_learning/ai_assistant/tasks.py`
- Create: `tests/test_ai_assistant.py`

- [ ] **Step 1: Write failing adapter test**

Write `tests/test_ai_assistant.py`:

```python
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from trading_learning.ai_assistant.local_codex import LocalCodexClient


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        assert body["model"] == "test-model"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(
            json.dumps(
                {"choices": [{"message": {"content": "draft summary"}}]}
            ).encode("utf-8")
        )

    def log_message(self, format, *args):
        return


def test_local_codex_client_returns_text():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}/v1"
        client = LocalCodexClient(base_url=base_url, api_key="local-key", model="test-model")
        assert client.chat("system", "user") == "draft summary"
    finally:
        server.shutdown()
        thread.join()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ai_assistant.py -v`

Expected: FAIL with `ModuleNotFoundError` for `trading_learning.ai_assistant`.

- [ ] **Step 3: Implement local Codex client**

Write `src/trading_learning/ai_assistant/local_codex.py`:

```python
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class LocalCodexClient:
    base_url: str
    api_key: str
    model: str

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 1200,
        }
        request = urllib.request.Request(
            url=f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
```

Create `src/trading_learning/ai_assistant/__init__.py` as an empty file.

- [ ] **Step 4: Implement draft task storage**

Write `src/trading_learning/ai_assistant/tasks.py`:

```python
from __future__ import annotations

import sqlite3
from uuid import uuid4

from trading_learning.ai_assistant.local_codex import LocalCodexClient


REVIEW_SYSTEM_PROMPT = (
    "You are a trading learning assistant. Summarize reviews, ask learning questions, "
    "and never give buy or sell signals. Do not suggest changing live strategy parameters."
)


def create_daily_review_draft(
    conn: sqlite3.Connection,
    client: LocalCodexClient,
    source_external_id: str,
    review_text: str,
) -> str:
    content = client.chat(REVIEW_SYSTEM_PROMPT, review_text)
    external_id = f"ai-draft-{uuid4()}"
    conn.execute(
        """
        insert into ai_drafts (external_id, task_type, source_external_id, content, status)
        values (?, ?, ?, ?, 'draft')
        """,
        (external_id, "daily_review_summary", source_external_id, content),
    )
    conn.commit()
    return external_id
```

- [ ] **Step 5: Run adapter tests**

Run: `python -m pytest tests/test_ai_assistant.py -v`

Expected: PASS.

- [ ] **Step 6: Commit local AI adapter**

Run:

```bash
git add src/trading_learning/ai_assistant tests/test_ai_assistant.py
git commit -m "feat: add local codex draft assistant"
```

Expected: commit succeeds.

## Task 8: Export Package

**Files:**
- Create: `src/trading_learning/export_import/__init__.py`
- Create: `src/trading_learning/export_import/exporter.py`
- Create: `tests/test_exporter.py`

- [ ] **Step 1: Write failing export test**

Write `tests/test_exporter.py`:

```python
import zipfile

from trading_learning.export_import.exporter import export_zip
from trading_learning.journal.repository import save_daily_review
from trading_learning.storage.db import connect, initialize_schema


def test_export_zip_contains_manifest_and_jsonl(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    export_path = tmp_path / "export.zip"
    with connect(db_path) as conn:
        initialize_schema(conn)
        save_daily_review(
            conn,
            external_id="review-2026-05-01",
            review_date="2026-05-01",
            symbols_watched=["BTCUSDT"],
            trade_count=1,
            plan_followed=True,
            pnl=1.2,
            mistake_tags=[],
            emotion_note="calm",
            lesson="follow the plan",
        )
        export_zip(conn, export_path)

    with zipfile.ZipFile(export_path) as archive:
        names = set(archive.namelist())

    assert "manifest.json" in names
    assert "daily_reviews.jsonl" in names
    assert "markdown/daily_reviews.md" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_exporter.py -v`

Expected: FAIL with `ModuleNotFoundError` for `trading_learning.export_import`.

- [ ] **Step 3: Implement exporter**

Write `src/trading_learning/export_import/exporter.py`:

```python
from __future__ import annotations

import json
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def rows_as_dicts(conn: sqlite3.Connection, table: str) -> list[dict]:
    rows = conn.execute(f"select * from {table} order by id").fetchall()
    return [dict(row) for row in rows]


def export_zip(conn: sqlite3.Connection, export_path: Path) -> None:
    export_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1.0.0",
        "source_system": "trading_learning",
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    daily_reviews = rows_as_dicts(conn, "daily_reviews")
    knowledge_cards = rows_as_dicts(conn, "knowledge_cards")
    hypotheses = rows_as_dicts(conn, "strategy_hypotheses")
    ai_drafts = rows_as_dicts(conn, "ai_drafts")

    markdown_reviews = ["# Daily Reviews", ""]
    for review in daily_reviews:
        markdown_reviews.extend(
            [
                f"## {review['review_date']}",
                "",
                f"- Trade count: {review['trade_count']}",
                f"- PnL: {review['pnl']}",
                f"- Lesson: {review['lesson']}",
                "",
            ]
        )

    with zipfile.ZipFile(export_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("daily_reviews.jsonl", to_jsonl(daily_reviews))
        archive.writestr("knowledge_cards.jsonl", to_jsonl(knowledge_cards))
        archive.writestr("strategy_hypotheses.jsonl", to_jsonl(hypotheses))
        archive.writestr("ai_drafts.jsonl", to_jsonl(ai_drafts))
        archive.writestr("markdown/daily_reviews.md", "\n".join(markdown_reviews))


def to_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
```

Create `src/trading_learning/export_import/__init__.py` as an empty file.

- [ ] **Step 4: Run exporter test**

Run: `python -m pytest tests/test_exporter.py -v`

Expected: PASS.

- [ ] **Step 5: Commit exporter**

Run:

```bash
git add src/trading_learning/export_import tests/test_exporter.py
git commit -m "feat: export portable learning package"
```

Expected: commit succeeds.

## Task 9: CLI For The Local Loop

**Files:**
- Create: `src/trading_learning/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI smoke test**

Write `tests/test_cli.py`:

```python
from trading_learning.cli import build_parser


def test_cli_has_expected_commands():
    parser = build_parser()
    command_names = {
        action.dest
        for action in parser._subparsers._group_actions[0]._choices_actions
    }
    assert {"init-db", "backtest-ma", "export"}.issubset(command_names)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`

Expected: FAIL with `ModuleNotFoundError` for `trading_learning.cli`.

- [ ] **Step 3: Implement CLI parser and commands**

Write `src/trading_learning/cli.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path

from trading_learning.backtest.engine import run_spot_backtest
from trading_learning.config import load_config
from trading_learning.export_import.exporter import export_zip
from trading_learning.market_data.csv_loader import load_candles_csv
from trading_learning.storage.db import connect, initialize_schema
from trading_learning.strategy.moving_average import moving_average_crossover_signals


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trading-learning")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db")

    backtest = subparsers.add_parser("backtest-ma")
    backtest.add_argument("--csv", required=True)
    backtest.add_argument("--symbol", required=True)
    backtest.add_argument("--short-window", type=int, default=20)
    backtest.add_argument("--long-window", type=int, default=60)
    backtest.add_argument("--starting-cash", type=float, default=1000.0)
    backtest.add_argument("--quote-amount", type=float, default=100.0)
    backtest.add_argument("--fee-rate", type=float, default=0.001)
    backtest.add_argument("--daily-trade-limit", type=int, default=5)

    export = subparsers.add_parser("export")
    export.add_argument("--output", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config()

    with connect(config.db_path) as conn:
        initialize_schema(conn)

        if args.command == "init-db":
            print(f"initialized {config.db_path}")
            return 0

        if args.command == "backtest-ma":
            candles = load_candles_csv(Path(args.csv), args.symbol)
            signals = moving_average_crossover_signals(
                candles,
                short_window=args.short_window,
                long_window=args.long_window,
            )
            prices = {candle.opened_at: candle.close for candle in candles}
            result = run_spot_backtest(
                symbol=args.symbol,
                signals=signals,
                prices_by_timestamp=prices,
                starting_cash=args.starting_cash,
                quote_amount_per_buy=args.quote_amount,
                fee_rate=args.fee_rate,
                daily_trade_limit=args.daily_trade_limit,
            )
            print(f"symbol={result.symbol} trades={result.trade_count} ending_cash={result.ending_cash:.2f}")
            return 0

        if args.command == "export":
            export_zip(conn, Path(args.output))
            print(f"exported {args.output}")
            return 0

    parser.error(f"unknown command {args.command}")
    return 2
```

- [ ] **Step 4: Run CLI test**

Run: `python -m pytest tests/test_cli.py -v`

Expected: PASS.

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest -v`

Expected: all tests PASS.

- [ ] **Step 6: Commit CLI**

Run:

```bash
git add src/trading_learning/cli.py tests/test_cli.py
git commit -m "feat: add local trading learning cli"
```

Expected: commit succeeds.

## Task 10: Phase 1 Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write README usage**

Write `README.md`:

```markdown
# Trading Learning

Local low-frequency crypto trading learning system.

Phase 1 supports:

- SQLite local storage
- Historical CSV loading
- Moving-average backtests
- Daily review and learning records
- Local Codex-compatible draft assistant
- JSONL and Markdown ZIP export

Phase 1 does not place live orders.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Initialize Database

```powershell
trading-learning init-db
```

## Run Backtest

```powershell
trading-learning backtest-ma --csv tests/fixtures/btcusdt_1h_sample.csv --symbol BTCUSDT --short-window 2 --long-window 3
```

## Export Data

```powershell
trading-learning export --output exports/trading-learning-export.zip
```
```

- [ ] **Step 2: Run final tests**

Run: `python -m pytest -v`

Expected: all tests PASS.

- [ ] **Step 3: Run CLI smoke commands**

Run:

```bash
python -m trading_learning.cli init-db
python -m trading_learning.cli backtest-ma --csv tests/fixtures/btcusdt_1h_sample.csv --symbol BTCUSDT --short-window 2 --long-window 3
python -m trading_learning.cli export --output exports/trading-learning-export.zip
```

Expected:

```text
initialized data/local/trading_learning.sqlite3
symbol=BTCUSDT trades=...
exported exports/trading-learning-export.zip
```

- [ ] **Step 4: Inspect git status**

Run: `git status --short`

Expected: only intended files are modified or untracked before commit.

- [ ] **Step 5: Commit verification docs**

Run:

```bash
git add README.md
git commit -m "docs: document phase 1 local loop"
```

Expected: commit succeeds.

## Self-Review

- Spec coverage: Covers Phase 1 backtest, review, learning records, local Codex draft assistant, export package, and no-live-order boundary. Binance Spot Testnet and live spot are deliberately excluded from this plan because they are later milestones.
- Placeholder scan: The plan contains no unresolved markers or unspecified implementation steps.
- Type consistency: Shared names are consistent across tasks: `Candle`, `Signal`, `SignalAction`, `Trade`, `BacktestResult`, `LocalCodexClient`, `export_zip`, and `initialize_schema`.
