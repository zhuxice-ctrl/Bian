from __future__ import annotations

import re


def _u(value: str) -> str:
    return value.encode("ascii").decode("unicode_escape")


_KEY_ALIASES = {
    _u(r"\u65e5\u671f"): "date",
    _u(r"\u5e01\u79cd"): "symbols",
    _u(r"\u4ea4\u6613\u5bf9"): "symbols",
    _u(r"\u6700\u5927\u4ea4\u6613"): "max_trades",
    _u(r"\u6700\u5927\u4ea4\u6613\u6570"): "max_trades",
    _u(r"\u65b9\u5411"): "bias",
    _u(r"\u6761\u4ef6"): "conditions",
    _u(r"\u7981\u6b62"): "forbidden",
    _u(r"\u8ba1\u5212"): "plan",
    _u(r"\u5f62\u6001"): "setup",
    _u(r"\u8bbe\u7f6e"): "setup",
    _u(r"\u98ce\u9669"): "risk",
    _u(r"\u60c5\u7eea"): "emotion",
    _u(r"\u4ea4\u6613"): "trades",
    _u(r"\u4ea4\u6613\u6570"): "trades",
    _u(r"\u9075\u5b88\u8ba1\u5212"): "plan",
    _u(r"\u76c8\u4e8f"): "pnl",
    _u(r"\u6807\u7b7e"): "tags",
    _u(r"\u6559\u8bad"): "lesson",
    _u(r"\u7b14\u8bb0"): "note",
    _u(r"\u5b9e\u9a8c"): "experiment",
    _u(r"\u6570\u91cf"): "limit",
    _u(r"\u5468\u671f"): "interval",
    _u(r"\u77ed\u7ebf"): "short",
    _u(r"\u957f\u7ebf"): "long",
    _u(r"\u6587\u4ef6"): "csv",
    _u(r"\u6807\u9898"): "title",
    _u(r"\u9884\u6d4b"): "predicted",
    _u(r"\u63cf\u8ff0"): "description",
    _u(r"\u7236\u7248\u672c"): "parent_iteration",
    _u(r"\u53d8\u66f4"): "change_summary",
    _u(r"\u89c4\u5219"): "decision_rule",
    _u(r"\u5047\u8bbe"): "hypothesis",
    _u(r"\u51b3\u7b56"): "decision",
    _u(r"\u5b9e\u9645"): "actual",
    _u(r"\u7406\u7531"): "reason",
}

_YES_VALUES = {_u(r"\u662f"), _u(r"\u5bf9"), _u(r"\u597d"), _u(r"\u901a\u8fc7"), "yes", "true", "1", "ok"}
_NO_VALUES = {_u(r"\u5426"), _u(r"\u4e0d"), _u(r"\u4e0d\u662f"), "no", "false", "0"}

_STATUS_ALIASES = {_u(r"\u72b6\u6001"), _u(r"\u67e5\u770b\u72b6\u6001"), _u(r"\u7cfb\u7edf\u72b6\u6001"), _u(r"\u8111\u72b6\u6001")}
_LLM_STATUS_ALIASES = {
    _u(r"\u68c0\u67e5\u94fe\u63a5"),
    _u(r"\u68c0\u67e5LLM\u8fde\u63a5"),
    _u(r"\u68c0\u67e5llm\u8fde\u63a5"),
    _u(r"\u7535\u8111\u72b6\u6001"),
}
_PLAN_STATUS_ALIASES = {_u(r"\u8ba1\u5212\u72b6\u6001"), _u(r"\u4eca\u65e5\u8ba1\u5212"), _u(r"\u67e5\u770b\u8ba1\u5212")}
_REVIEW_SUMMARY_ALIASES = {_u(r"\u6700\u8fd1\u590d\u76d8"), _u(r"\u590d\u76d8\u6458\u8981"), _u(r"\u67e5\u770b\u590d\u76d8"), _u(r"\u590d\u76d8\u603b\u7ed3")}
_EXPERIMENT_SUMMARY_ALIASES = {_u(r"\u6700\u8fd1\u5b9e\u9a8c"), _u(r"\u5b9e\u9a8c\u603b\u7ed3"), _u(r"\u56de\u6d4b\u603b\u7ed3"), _u(r"\u6700\u8fd1\u56de\u6d4b")}
_LEARNING_ALIASES = {_u(r"\u4eca\u5929\u5b66\u4ec0\u4e48"), _u(r"\u4eca\u65e5\u5b66\u4e60"), _u(r"\u5b66\u4e60\u5efa\u8bae"), _u(r"\u4e0b\u4e00\u6b65\u5b66\u4e60")}
_LEARNING_QUEUE_ALIASES = {_u(r"\u5b66\u4e60\u961f\u5217"), _u(r"\u590d\u4e60\u961f\u5217"), _u(r"\u4eca\u5929\u590d\u4e60\u4ec0\u4e48")}
_TASK_STATUS_ALIASES = {_u(r"\u4efb\u52a1\u72b6\u6001"), _u(r"\u8fdc\u7a0b\u4efb\u52a1"), _u(r"\u67e5\u770b\u4efb\u52a1")}
_COACH_DAILY_ALIASES = {_u(r"\u4eca\u65e5\u6559\u7ec3"), _u(r"\u6559\u7ec3\u8ba1\u5212"), _u(r"\u4eca\u5929\u505a\u4ec0\u4e48")}
_RUN_SUGGESTED_ALIASES = {_u(r"\u6267\u884c\u5efa\u8bae"), _u(r"\u8fd0\u884c\u5efa\u8bae"), _u(r"\u6267\u884c\u63a8\u8350")}

_SET_PLAN = _u(r"\u8bbe\u7f6e\u8ba1\u5212")
_PLAN_STATUS = _u(r"\u8ba1\u5212\u72b6\u6001")
_PRE_TRADE_CHECK = _u(r"\u4ea4\u6613\u524d\u68c0\u67e5")
_ADD_REVIEW = _u(r"\u6dfb\u52a0\u590d\u76d8")
_DOWNLOAD_HISTORY = _u(r"\u4e0b\u8f7d\u5386\u53f2")
_MA_BACKTEST = _u(r"\u5747\u7ebf\u56de\u6d4b")
_REMOTE_MA_BACKTEST = _u(r"\u8fdc\u7a0b\u56de\u6d4b")
_REMOTE_MARKET_REFRESH = _u(r"\u8fdc\u7a0b\u5237\u65b0\u6570\u636e")
_COMMIT_EXPERIMENT_REVIEW = _u(r"\u6c89\u6dc0\u5b9e\u9a8c\u590d\u76d8")
_TESTNET_BUY = _u(r"\u6d4b\u8bd5\u7f51\u4e70\u5165")
_TEST_BUY = _u(r"\u6d4b\u8bd5\u4e70\u5165")
_RESEARCH_HYPOTHESIS = _u(r"\u7814\u7a76\u5047\u8bbe")
_RESEARCH_DECISION = _u(r"\u7814\u7a76\u51b3\u7b56")
_RESEARCH_STATUS = _u(r"\u7814\u7a76\u72b6\u6001")
_RESEARCH_BASELINE = _u(r"\u7814\u7a76\u57fa\u7ebf")
_RESEARCH_TEST = _u(r"\u7814\u7a76\u6d4b\u8bd5")
_RESEARCH_ABLATION = _u(r"\u7814\u7a76\u5bf9\u6bd4")


def normalize_brain_command(text: str) -> str:
    command = text.strip()
    if not command or command.startswith("/"):
        return command

    compact = re.sub(r"\s+", "", command)
    if compact in _STATUS_ALIASES:
        return "/status"
    if compact in _LLM_STATUS_ALIASES:
        return "/llm-status"
    if compact in _PLAN_STATUS_ALIASES:
        return "/plan-status"
    if compact in _REVIEW_SUMMARY_ALIASES:
        return "/review-summary limit=5"
    if compact in _EXPERIMENT_SUMMARY_ALIASES:
        return "/experiment-summary limit=5"
    if compact in _LEARNING_ALIASES:
        return "/learning-next"
    if compact in _LEARNING_QUEUE_ALIASES:
        return "/learning-queue"
    if compact in _TASK_STATUS_ALIASES:
        return "/task-status limit=5"
    if compact in _COACH_DAILY_ALIASES:
        return "/coach-daily"
    if compact in _RUN_SUGGESTED_ALIASES:
        return "/run suggested"
    if compact == _RESEARCH_STATUS:
        return "/research-status"
    if compact == _RESEARCH_BASELINE:
        return "/research-baseline"
    if compact == _RESEARCH_ABLATION:
        return "/research-ablation"

    confirm = re.fullmatch(_u(r"\u786e\u8ba4") + r"[-\s]*([A-Za-z0-9]+)", command)
    if confirm:
        return f"/confirm {confirm.group(1)}"

    buy = re.fullmatch(
        rf"(?:{_TESTNET_BUY}|{_TEST_BUY})\s+([A-Za-z0-9]+)\s+([0-9]+(?:\.[0-9]+)?)(?:U|USDT)?",
        command,
    )
    if buy:
        return f"/testnet-create-buy {buy.group(1).upper()} {buy.group(2)}"

    if command.startswith(_SET_PLAN + " "):
        return _rewrite_keyed_command("/plan-set", command.removeprefix(_SET_PLAN + " "))
    if command.startswith(_PLAN_STATUS + " "):
        return _rewrite_keyed_command("/plan-status", command.removeprefix(_PLAN_STATUS + " "))
    if command.startswith(_PRE_TRADE_CHECK + " "):
        return _rewrite_keyed_command("/checklist", command.removeprefix(_PRE_TRADE_CHECK + " "))
    if command.startswith(_ADD_REVIEW + " "):
        return _rewrite_keyed_command("/review-add", command.removeprefix(_ADD_REVIEW + " "))
    if command.startswith(_DOWNLOAD_HISTORY + " "):
        return _rewrite_keyed_command("/history-download", command.removeprefix(_DOWNLOAD_HISTORY + " "))
    if command.startswith(_MA_BACKTEST + " "):
        return _rewrite_keyed_command("/backtest-ma", command.removeprefix(_MA_BACKTEST + " "))
    if command.startswith(_REMOTE_MA_BACKTEST + " "):
        return _rewrite_keyed_command("/queue-backtest-ma", command.removeprefix(_REMOTE_MA_BACKTEST + " "))
    if command.startswith(_REMOTE_MARKET_REFRESH + " "):
        return _rewrite_keyed_command("/queue-market-refresh", command.removeprefix(_REMOTE_MARKET_REFRESH + " "))
    if command.startswith(_COMMIT_EXPERIMENT_REVIEW + " "):
        return _rewrite_keyed_command(
            "/experiment-review-commit",
            command.removeprefix(_COMMIT_EXPERIMENT_REVIEW + " "),
        )
    if command.startswith(_RESEARCH_HYPOTHESIS + " "):
        return _rewrite_keyed_command("/hypothesis-create", command.removeprefix(_RESEARCH_HYPOTHESIS + " "))
    if command.startswith(_RESEARCH_DECISION + " "):
        return _rewrite_keyed_command("/hypothesis-resolve", command.removeprefix(_RESEARCH_DECISION + " "))
    if command.startswith(_RESEARCH_BASELINE + " "):
        return _rewrite_keyed_command("/research-baseline", command.removeprefix(_RESEARCH_BASELINE + " "))
    if command.startswith(_RESEARCH_TEST + " "):
        return _rewrite_keyed_command("/research-test", command.removeprefix(_RESEARCH_TEST + " "))
    if command.startswith(_RESEARCH_ABLATION + " "):
        return _rewrite_keyed_command("/research-ablation", command.removeprefix(_RESEARCH_ABLATION + " "))

    return command


def _rewrite_keyed_command(prefix: str, body: str) -> str:
    fields = []
    for part in body.split():
        key, separator, value = part.partition("=")
        if not separator or not key:
            continue
        normalized_key = _KEY_ALIASES.get(key, key)
        if prefix in {"/checklist", "/history-download", "/backtest-ma", "/queue-backtest-ma"} and normalized_key == "symbols":
            normalized_key = "symbol"
        if prefix == "/queue-market-refresh" and normalized_key == "interval":
            normalized_key = "intervals"
        if prefix == "/history-download" and normalized_key == "csv":
            normalized_key = "output"
        normalized_value = _normalize_value(normalized_key, value)
        fields.append(f"{normalized_key}={normalized_value}")
    return " ".join([prefix, *fields]).strip()


def _normalize_value(key: str, value: str) -> str:
    if key not in {"plan", "setup", "risk"}:
        return value.strip().removesuffix("U")
    if value in _YES_VALUES:
        return "yes"
    if value in _NO_VALUES:
        return "no"
    return value.strip().removesuffix("U")
