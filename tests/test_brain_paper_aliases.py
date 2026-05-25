from trading_learning.brain.command_aliases import normalize_brain_command


def _u(value: str) -> str:
    return value.encode("ascii").decode("unicode_escape")


def test_paper_chinese_aliases_route_to_commands():
    assert normalize_brain_command(_u(r"\u7b56\u7565\u72b6\u6001")) == "/paper-status"
    assert normalize_brain_command(_u(r"\u7eb8\u76d8\u72b6\u6001")) == "/paper-status"
    assert normalize_brain_command(_u(r"\u6bcf\u65e5\u66f4\u65b0")) == "/paper-update"
    assert normalize_brain_command(_u(r"\u66f4\u65b0\u7b56\u7565")) == "/paper-update"
    assert normalize_brain_command(_u(r"\u7b56\u7565\u5386\u53f2")) == "/paper-history days=7"
