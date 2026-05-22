from __future__ import annotations

from typing import Any


def production_readiness_status() -> dict[str, Any]:
    checks = {
        "local_manual_approval": False,
        "risk_limits_configured": False,
        "kill_switch_reviewed": False,
        "real_order_tests_passed": False,
        "backup_recent": False,
    }
    missing = [name for name, passed in checks.items() if not passed]
    return {
        "ready": False,
        "real_trading_enabled": False,
        "kill_switch_active": True,
        "kill_switch": {
            "active": True,
            "mode": "locked",
            "message": "Kill switch is active; real trading routes are unavailable.",
        },
        "checks": checks,
        "missing": missing,
        "message": "Real trading is disabled. Complete the local production readiness gate before adding any real order path.",
    }
