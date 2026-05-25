from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from trading_learning.paper_trading import daily_runner


def missing_status_message(state_dir: str | Path) -> str:
    return (
        "Paper trading data is not ready. Run the paper trading backfill first, "
        f"then check {Path(state_dir) / daily_runner.STATE_FILE}."
    )


def load_status_payload(
    *,
    state_dir: str | Path = daily_runner.DEFAULT_STATE_DIR,
) -> dict[str, Any]:
    history = load_history_frame(state_dir=state_dir)
    if history.empty:
        return _empty_status("not_found", missing_status_message(state_dir))
    latest = history.iloc[-1]
    signals = load_latest_signals(state_dir=state_dir)
    config = load_paper_config(state_dir=state_dir)
    capital = _capital(config, latest)
    cumulative_pnl = _float(latest.get("cum_pnl"))
    equity = _float(latest.get("equity"))
    return {
        "status": "ok",
        "date": str(latest.get("date", "")),
        "equity": equity,
        "cumulative_pnl": cumulative_pnl,
        "cumulative_return_pct": _pct(cumulative_pnl / capital if capital else 0.0),
        "daily_pnl": _pct(_float(latest.get("daily_pnl"))),
        "target_position": _float(latest.get("target_pos")),
        "signals": {
            "trend_fast": _signal_value(signals, latest, "sig_trend_fast", "sig_fast"),
            "momentum": _signal_value(signals, latest, "sig_momentum", "sig_mom"),
            "mean_rev": _signal_value(signals, latest, "sig_mean_rev", "sig_mr"),
            "vol_regime": _signal_value(signals, latest, "sig_vol_regime", "sig_vol"),
            "combined": _signal_value(signals, latest, "combined_forecast", "combined"),
        },
        "fdm": _signal_value(signals, latest, "fdm", "fdm"),
        "config": {
            "capital": capital,
            "vol_target": _float(config.get("target_vol")),
            "cost_per_rt": _float(config.get("cost_per_round_trip")),
        },
    }


def load_history_payload(
    *,
    state_dir: str | Path = daily_runner.DEFAULT_STATE_DIR,
    days: int = 7,
) -> dict[str, Any]:
    history = load_history_frame(state_dir=state_dir)
    if history.empty:
        return {"status": "ok", "history": []}
    clean_days = max(1, int(days))
    rows = history.tail(clean_days)
    return {
        "status": "ok",
        "history": [_history_row(row) for _, row in rows.iterrows()],
    }


def load_equity_curve_payload(
    *,
    state_dir: str | Path = daily_runner.DEFAULT_STATE_DIR,
    price_csv: str | Path = daily_runner.DEFAULT_PRICE_CSV,
) -> dict[str, Any]:
    history = load_history_frame(state_dir=state_dir)
    if history.empty:
        return {"status": "ok", "equity_curve": []}
    config = load_paper_config(state_dir=state_dir)
    capital = _capital(config, history.iloc[-1])
    benchmark_by_date = _benchmark_equity_by_date(price_csv=price_csv, capital=capital)
    return {
        "status": "ok",
        "equity_curve": [
            {
                "date": str(row["date"]),
                "equity": _float(row["equity"]),
                "benchmark_equity": benchmark_by_date.get(str(row["date"])),
            }
            for _, row in history.iterrows()
        ],
    }


def format_status_message(payload: dict[str, Any]) -> str:
    if payload.get("status") != "ok":
        return str(payload.get("message", "Paper trading data is not ready."))
    signals = payload["signals"]
    direction = _position_label(float(payload["target_position"]))
    return "\n".join(
        [
            "\U0001f4ca Bian v1 Paper Trading",
            f"\u65e5\u671f: {payload['date']}",
            (
                f"\u6743\u76ca: {_format_number(payload['equity'])} "
                f"({_format_signed_pct(payload['cumulative_return_pct'])})"
            ),
            f"\u4eca\u65e5 PnL: {_format_signed_pct(payload['daily_pnl'])}",
            f"\u76ee\u6807\u4ed3\u4f4d: {payload['target_position']:.3f} ({direction})",
            (
                "\u4fe1\u53f7: "
                f"FAST={signals['trend_fast']:.2f} "
                f"MOM={signals['momentum']:.2f} "
                f"MR={signals['mean_rev']:.2f} "
                f"VOL={signals['vol_regime']:.2f}"
            ),
            f"Combined: {signals['combined']:.2f} (FDM={payload['fdm']:.2f})",
        ]
    )


def format_history_message(payload: dict[str, Any]) -> str:
    history = payload.get("history", [])
    if not history:
        return missing_status_message(daily_runner.DEFAULT_STATE_DIR)
    lines = ["\U0001f4c8 Bian v1 Paper History", "\u65e5\u671f | PnL | \u76ee\u6807\u4ed3\u4f4d | Combined"]
    for row in history:
        lines.append(
            f"{row['date']} | {_format_signed_pct(row['daily_pnl'])} | "
            f"{row['target_position']:.3f} | {row['signals']['combined']:.2f}"
        )
    return "\n".join(lines)


def load_history_frame(*, state_dir: str | Path) -> pd.DataFrame:
    state_path = Path(state_dir) / daily_runner.STATE_FILE
    if not state_path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(state_path)
    if frame.empty:
        return pd.DataFrame()
    return frame.sort_values("date").reset_index(drop=True)


def load_latest_signals(*, state_dir: str | Path) -> dict[str, Any]:
    path = Path(state_dir) / daily_runner.SIGNALS_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_paper_config(*, state_dir: str | Path) -> dict[str, Any]:
    path = Path(state_dir) / daily_runner.CONFIG_FILE
    if not path.exists():
        return {
            "capital": float(daily_runner.DEFAULT_CAPITAL),
            "target_vol": float(daily_runner.DEFAULT_TARGET_VOL),
            "cost_per_round_trip": float(daily_runner.DEFAULT_COST_PER_RT),
        }
    return json.loads(path.read_text(encoding="utf-8"))


def _history_row(row: pd.Series) -> dict[str, Any]:
    return {
        "date": str(row.get("date", "")),
        "equity": _float(row.get("equity")),
        "daily_pnl": _pct(_float(row.get("daily_pnl"))),
        "target_position": _float(row.get("target_pos")),
        "signals": {
            "trend_fast": _float(row.get("sig_fast")),
            "momentum": _float(row.get("sig_mom")),
            "mean_rev": _float(row.get("sig_mr")),
            "vol_regime": _float(row.get("sig_vol")),
            "combined": _float(row.get("combined")),
        },
    }


def _benchmark_equity_by_date(*, price_csv: str | Path, capital: float) -> dict[str, float]:
    path = Path(price_csv)
    if not path.exists():
        return {}
    frame = pd.read_csv(path)
    if frame.empty or "close" not in frame:
        return {}
    timestamp_column = "opened_at" if "opened_at" in frame.columns else "timestamp"
    frame["date"] = pd.to_datetime(frame[timestamp_column], utc=True).dt.date.astype(str)
    frame["close"] = frame["close"].astype(float)
    frame = frame.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    first_close = float(frame["close"].iloc[0])
    if first_close == 0.0:
        return {}
    return {
        str(row["date"]): float(capital * (float(row["close"]) / first_close))
        for _, row in frame.iterrows()
    }


def _empty_status(status: str, message: str) -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "date": "",
        "equity": 0.0,
        "cumulative_pnl": 0.0,
        "cumulative_return_pct": 0.0,
        "daily_pnl": 0.0,
        "target_position": 0.0,
        "signals": {
            "trend_fast": 0.0,
            "momentum": 0.0,
            "mean_rev": 0.0,
            "vol_regime": 0.0,
            "combined": 0.0,
        },
        "fdm": 0.0,
        "config": {
            "capital": float(daily_runner.DEFAULT_CAPITAL),
            "vol_target": float(daily_runner.DEFAULT_TARGET_VOL),
            "cost_per_rt": float(daily_runner.DEFAULT_COST_PER_RT),
        },
    }


def _signal_value(signals: dict[str, Any], row: pd.Series, signal_key: str, row_key: str) -> float:
    if signal_key in signals:
        return _float(signals[signal_key])
    return _float(row.get(row_key))


def _capital(config: dict[str, Any], latest: pd.Series) -> float:
    if "capital" in config:
        return _float(config["capital"])
    return _float(latest.get("equity")) - _float(latest.get("cum_pnl"))


def _float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    if pd.isna(result):
        return 0.0
    return result


def _pct(value: float) -> float:
    return round(float(value) * 100.0, 2)


def _format_number(value: float) -> str:
    return f"{float(value):,.2f}"


def _format_signed_pct(value: float) -> str:
    return f"{float(value):+.2f}%"


def _position_label(value: float) -> str:
    if value >= 0.2:
        return "\u591a"
    if value > 0.0:
        return "\u5fae\u591a"
    if value <= -0.2:
        return "\u7a7a"
    if value < 0.0:
        return "\u5fae\u7a7a"
    return "\u7a7a\u4ed3"
