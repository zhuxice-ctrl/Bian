import json

from trading_learning.paper_push import send_paper_summary_if_enabled


class FakeMessenger:
    calls = []

    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret

    def send_text(self, chat_id, text):
        self.calls.append((self.app_id, self.app_secret, chat_id, text))
        return {"message_id": "msg-1"}


def _write_state(state_dir, *, enabled):
    state_dir.mkdir(parents=True)
    (state_dir / "portfolio_state.csv").write_text(
        "date,price,sig_fast,sig_mom,sig_mr,sig_vol,combined,fdm,inst_vol,target_pos,current_pos,change,cost,daily_pnl,cum_pnl,equity\n"
        "2026-05-25,77728.79,0.12,-0.35,1.20,-0.88,0.02,2.753598,0.346,0.032,0.031,0.001,0.0001,0.0059,12851.89,112851.89\n",
        encoding="utf-8",
    )
    (state_dir / "latest_signals.json").write_text(
        json.dumps(
            {
                "date": "2026-05-25",
                "sig_trend_fast": 0.12,
                "sig_momentum": -0.35,
                "sig_mean_rev": 1.2,
                "sig_vol_regime": -0.88,
                "combined_forecast": 0.02,
                "fdm": 2.753598,
            }
        ),
        encoding="utf-8",
    )
    (state_dir / "config.json").write_text(
        json.dumps(
            {
                "capital": 100000,
                "target_vol": 0.2,
                "cost_per_round_trip": 0.002,
                "feishu_push_enabled": enabled,
                "feishu_push_chat_id": "chat-1",
            }
        ),
        encoding="utf-8",
    )


def test_disabled_feishu_push_does_not_call_messenger(tmp_path, monkeypatch):
    state_dir = tmp_path / "paper"
    _write_state(state_dir, enabled=False)
    FakeMessenger.calls = []
    monkeypatch.setenv("FEISHU_APP_ID", "app-1")
    monkeypatch.setenv("FEISHU_APP_SECRET", "secret-1")

    result = send_paper_summary_if_enabled(state_dir=state_dir, messenger_cls=FakeMessenger)

    assert result == {"status": "disabled"}
    assert FakeMessenger.calls == []


def test_enabled_feishu_push_sends_formatted_summary(tmp_path, monkeypatch):
    state_dir = tmp_path / "paper"
    _write_state(state_dir, enabled=True)
    FakeMessenger.calls = []
    monkeypatch.setenv("FEISHU_APP_ID", "app-1")
    monkeypatch.setenv("FEISHU_APP_SECRET", "secret-1")

    result = send_paper_summary_if_enabled(state_dir=state_dir, messenger_cls=FakeMessenger)

    assert result == {"status": "sent", "message_id": "msg-1"}
    assert FakeMessenger.calls[0][0:3] == ("app-1", "secret-1", "chat-1")
    assert "Bian v1 Paper Trading" in FakeMessenger.calls[0][3]
    assert "权益: 112,851.89 (+12.85%)" in FakeMessenger.calls[0][3]
