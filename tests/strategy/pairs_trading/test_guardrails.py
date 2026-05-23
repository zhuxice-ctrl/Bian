from trading_learning.research.guardrails import PairsGuardrails


def test_pairs_guardrails_defer_when_cointegration_or_half_life_fails():
    weak = PairsGuardrails.validate_training({"coint_p": 0.2, "half_life": 50})
    slow = PairsGuardrails.validate_training({"coint_p": 0.01, "half_life": 600})
    ok = PairsGuardrails.validate_training({"coint_p": 0.01, "half_life": 80})

    assert weak["decision"] == "deferred"
    assert slow["decision"] == "deferred"
    assert ok["decision"] == "enabled"
