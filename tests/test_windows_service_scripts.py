from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_script(name: str) -> str:
    return (ROOT / "scripts" / name).read_text(encoding="utf-8")


def test_start_brain_script_runs_local_brain_with_logs():
    script = _read_script("start-brain.ps1")

    assert "trading-learning brain-serve" in script
    assert '[string]$HostAddress = "127.0.0.1"' in script
    assert "[int]$Port = 8765" in script
    assert "--host $HostAddress" in script
    assert "--port $Port" in script
    assert "logs" in script
    assert "BINANCE_TESTNET_API_KEY=" not in script
    assert "BINANCE_TESTNET_API_SECRET=" not in script


def test_register_brain_task_script_registers_logon_task():
    script = _read_script("register-brain-task.ps1")

    assert "TradingLearningBrain" in script
    assert "Register-ScheduledTask" in script
    assert "New-ScheduledTaskTrigger -AtLogOn" in script
    assert "start-brain.ps1" in script


def test_unregister_brain_task_script_removes_task():
    script = _read_script("unregister-brain-task.ps1")

    assert "TradingLearningBrain" in script
    assert "Unregister-ScheduledTask" in script
    assert "-Confirm:$false" in script


def test_startup_shortcut_scripts_use_current_user_startup_folder():
    install_script = _read_script("install-brain-startup-shortcut.ps1")
    uninstall_script = _read_script("uninstall-brain-startup-shortcut.ps1")

    assert "TradingLearningBrain.lnk" in install_script
    assert "WScript.Shell" in install_script
    assert "Startup" in install_script
    assert "start-brain.ps1" in install_script
    assert "TradingLearningBrain.lnk" in uninstall_script
    assert "Remove-Item" in uninstall_script


def test_service_scripts_do_not_contain_known_secret_values():
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "scripts").glob("*.ps1")
    )

    assert "BINANCE_TESTNET_API_KEY=" not in combined
    assert "BINANCE_TESTNET_API_SECRET=" not in combined
    assert "LOCAL_CODEX_API_KEY=" not in combined
    assert "FEISHU_VERIFICATION_TOKEN=" not in combined
    assert "FEISHU_ENCRYPT_KEY=" not in combined
