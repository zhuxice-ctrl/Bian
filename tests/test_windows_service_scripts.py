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
    assert "GetEnvironmentVariable" in script
    assert "BINANCE_TESTNET_API_KEY" in script
    assert "BINANCE_TESTNET_API_SECRET" in script
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


def test_brain_chat_script_posts_commands_to_local_brain():
    script = _read_script("brain-chat.ps1")

    assert "Invoke-RestMethod" in script
    assert "http://127.0.0.1:8765/brain/command" in script
    assert "ConvertTo-Json" in script
    assert "/quit" in script


def test_restart_scripts_stop_listener_and_start_brain():
    stop_script = _read_script("stop-brain.ps1")
    restart_script = _read_script("restart-brain.ps1")

    assert "Get-NetTCPConnection" in stop_script
    assert "Stop-Process" in stop_script
    assert "start-brain.ps1" in restart_script
    assert "Start-Process" in restart_script
    assert "-WindowStyle Hidden" in restart_script
    assert "Invoke-RestMethod" in restart_script
    assert "/status" in restart_script


def test_feishu_event_smoke_script_posts_verification_and_message_events():
    script = _read_script("feishu-event-smoke.ps1")

    assert "http://127.0.0.1:8765/feishu/events" in script
    assert "url_verification" in script
    assert "im.message.receive_v1" in script
    assert "Invoke-RestMethod" in script
    assert "FEISHU_VERIFICATION_TOKEN" in script
    assert "FEISHU_ENCRYPT_KEY" in script
    assert "X-Lark-Signature" in script
    assert "FEISHU_VERIFICATION_TOKEN=" not in script


def test_set_feishu_env_script_prompts_for_secrets():
    script = _read_script("set-feishu-env.ps1")

    assert "FEISHU_VERIFICATION_TOKEN" in script
    assert "FEISHU_ENCRYPT_KEY" in script
    assert "FEISHU_USER_MAP" in script
    assert "FEISHU_APP_ID" in script
    assert "FEISHU_APP_SECRET" in script
    assert "Read-Host" in script
    assert "-AsSecureString" in script
    assert "SetEnvironmentVariable" in script
    assert "FEISHU_APP_SECRET=" not in script


def test_set_local_codex_env_script_prompts_for_secret():
    script = _read_script("set-local-codex-env.ps1")

    assert "Read-Host" in script
    assert "-AsSecureString" in script
    assert "LOCAL_CODEX_API_KEY" in script
    assert "LOCAL_CODEX_BASE_URL" in script
    assert "LOCAL_CODEX_MODEL" in script
    assert "SetEnvironmentVariable" in script
    assert "LOCAL_CODEX_API_KEY=" not in script


def test_start_quant_runner_script_uses_runner_token_without_literal_secret():
    script = _read_script("start-quant-runner.ps1")

    assert "trading-learning quant-runner" in script
    assert "TRADING_LEARNING_RUNNER_TOKEN" in script
    assert "GetEnvironmentVariable" in script
    assert "--server-url" in script
    assert "--runner-id" in script
    assert "TRADING_LEARNING_RUNNER_TOKEN=" not in script


def test_start_local_workstation_script_starts_daily_services_without_secrets():
    script = _read_script("start-local-workstation.ps1")

    assert "start-brain.ps1" in script
    assert "start-quant-runner.ps1" in script
    assert "trading-learning dashboard-serve" in script
    assert "trading-learning health-check" in script
    assert "http://127.0.0.1:8780/" in script
    assert "Start-Process" in script
    assert "-WindowStyle Hidden" in script
    assert "TRADING_LEARNING_RUNNER_TOKEN=" not in script
    assert "LOCAL_CODEX_API_KEY=" not in script


def test_connect_server_llm_script_uses_ssh_reverse_tunnel():
    script = _read_script("connect-server-llm.ps1")

    assert "ssh" in script
    assert "-R" in script
    assert "127.0.0.1:61771:127.0.0.1:61771" in script
    assert "bian_server_codex_ed25519" in script
    assert "ubuntu@152.136.204.41" in script
    assert "LOCAL_CODEX_API_KEY=" not in script


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
    assert "FEISHU_APP_SECRET=" not in combined
    assert "TRADING_LEARNING_RUNNER_TOKEN=" not in combined
