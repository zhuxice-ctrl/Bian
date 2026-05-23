from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from trading_learning.backtest.walk_forward import WalkForwardConfig, run_walk_forward
from trading_learning.research.significance import is_strategy_better_than_baseline


@dataclass(frozen=True)
class AblationRun:
    name: str
    strategy_factory: Callable
    description: str


def run_ablation_study(
    runs: list[AblationRun],
    df: pd.DataFrame,
    wf_config: WalkForwardConfig,
    *,
    report_dir: Path | str = "exports",
) -> dict[str, Any]:
    if not runs:
        raise ValueError("at least one ablation run is required")
    results: list[dict[str, Any]] = []
    baseline_returns = None
    for run in runs:
        wf_result = run_walk_forward(run.strategy_factory, df, wf_config)
        vs_first = None
        if baseline_returns is None:
            baseline_returns = wf_result.oos_returns
        else:
            verdict = is_strategy_better_than_baseline(wf_result.oos_returns, baseline_returns)
            vs_first = {
                "sharpe_diff": verdict["metrics"]["diff"],
                "verdict": verdict["verdict"],
                "p_value": verdict["metrics"]["p_value"],
            }
        results.append({"name": run.name, "description": run.description, "wf_result": wf_result, "vs_first": vs_first})
    report_path = _write_report(results, wf_config, Path(report_dir))
    return {"runs": results, "report_path": str(report_path)}


def _write_report(results: list[dict[str, Any]], config: WalkForwardConfig, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"ablation-{datetime.now(timezone.utc).date().isoformat()}.md"
    lines = [
        f"# Ablation Study · {datetime.now(timezone.utc).date().isoformat()}",
        "",
        "## Setup",
        f"- Walk-forward: {config.train_window_days}d train / {config.test_window_days}d test / {config.purge_days}d purge",
        "",
        "## Results",
        "",
        "| Variant | OOS Sharpe | Max DD | Trade Count | vs Baseline | Verdict |",
        "|---|---:|---:|---:|---|---|",
    ]
    for item in results:
        metrics = item["wf_result"].aggregate_metrics
        vs_first = item["vs_first"]
        if vs_first is None:
            comparison = "-"
            verdict = "-"
        else:
            comparison = f"{vs_first['sharpe_diff']:.4f} (p={vs_first['p_value']:.4f})"
            verdict = vs_first["verdict"]
        lines.append(
            f"| {item['name']} | {metrics.get('oos_sharpe', 0):.4f} | {metrics.get('max_drawdown', 0):.4f} | "
            f"{metrics.get('oos_trade_count', 0)} | {comparison} | {verdict} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
