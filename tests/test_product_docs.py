from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_final_product_operation_docs_exist_and_cover_core_entrypoints():
    docs = {
        "docs/operations/local-setup-zh.md": [
            "start-brain.ps1",
            "start-quant-runner.ps1",
            "start-local-workstation.ps1",
            "dashboard-serve",
        ],
        "docs/operations/server-setup-zh.md": [
            "bian-brain.service",
            "/feishu/events",
            "TRADING_LEARNING_RUNNER_TOKEN",
        ],
        "docs/operations/daily-use-zh.md": [
            "start-local-workstation.ps1",
            "/coach-next",
            "backup-db",
            "/real-dry-run-buy",
        ],
        "docs/operations/release-notes-zh.md": [
            "Phase 45",
            "Phase 50",
            "real trading",
            "239 passed",
        ],
    }

    for relative_path, expected_terms in docs.items():
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        for term in expected_terms:
            assert term in text
