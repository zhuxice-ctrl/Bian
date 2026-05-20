import hashlib
import hmac
import json
from urllib.parse import parse_qs, urlencode, urlparse

import pytest

from trading_learning.execution.binance_spot_testnet import BinanceSpotTestnetClient


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.body


def fixed_time_ms():
    return 1777593600000


def make_client(urlopen):
    return BinanceSpotTestnetClient(
        api_key="synthetic-header-value",
        api_secret="synthetic-signing-secret",
        urlopen=urlopen,
        time_ms=fixed_time_ms,
    )


def query_params(full_url):
    return parse_qs(urlparse(full_url).query, keep_blank_values=True)


def first_values(params):
    return {key: values[0] for key, values in params.items()}


def test_signature_is_deterministic_with_fixed_time_and_secret():
    captured = []

    def fake_urlopen(request, timeout):
        captured.append(request.full_url)
        return FakeResponse(b"{}")

    make_client(fake_urlopen).account()

    params = first_values(query_params(captured[0]))
    signature = params.pop("signature")
    expected = hmac.new(
        b"synthetic-signing-secret",
        urlencode(params).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    assert signature == expected


def test_account_sends_signed_get_request_with_api_key_header():
    captured = []

    def fake_urlopen(request, timeout):
        captured.append(request)
        return FakeResponse(json.dumps({"canTrade": True}).encode("utf-8"))

    result = make_client(fake_urlopen).account()

    request = captured[0]
    parsed = urlparse(request.full_url)
    params = query_params(request.full_url)
    assert result == {"canTrade": True}
    assert request.get_method() == "GET"
    assert parsed.scheme == "https"
    assert parsed.netloc == "testnet.binance.vision"
    assert parsed.path == "/api/v3/account"
    assert params["timestamp"] == [str(fixed_time_ms())]
    assert "signature" in params
    assert request.get_header("X-mbx-apikey") == "synthetic-header-value"


def test_test_order_posts_market_quote_order_to_order_test_endpoint():
    captured = []

    def fake_urlopen(request, timeout):
        captured.append(request)
        return FakeResponse(b"{}")

    result = make_client(fake_urlopen).test_order(
        symbol="BTCUSDT",
        side="BUY",
        order_type="MARKET",
        quote_order_qty="100.00",
    )

    request = captured[0]
    params = query_params(request.full_url)
    assert result == {}
    assert request.get_method() == "POST"
    assert urlparse(request.full_url).path == "/api/v3/order/test"
    assert params["symbol"] == ["BTCUSDT"]
    assert params["side"] == ["BUY"]
    assert params["type"] == ["MARKET"]
    assert params["quoteOrderQty"] == ["100.00"]
    assert "signature" in params


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "symbol": "BTCUSDT",
                "side": "HOLD",
                "order_type": "MARKET",
                "quantity": "0.01",
            },
            "side",
        ),
        (
            {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "STOP",
                "quantity": "0.01",
            },
            "order_type",
        ),
        (
            {"symbol": "BTCUSDT", "side": "BUY", "order_type": "MARKET"},
            "quantity",
        ),
        (
            {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "LIMIT",
                "quantity": "0.01",
                "price": "100.00",
            },
            "time_in_force",
        ),
        (
            {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "LIMIT",
                "quote_order_qty": "100.00",
                "price": "100.00",
                "time_in_force": "GTC",
            },
            "quantity",
        ),
    ],
)
def test_invalid_order_inputs_raise_value_error_before_urlopen_is_called(
    kwargs, message
):
    def fake_urlopen(request, timeout):
        raise AssertionError("urlopen should not be called")

    with pytest.raises(ValueError, match=message):
        make_client(fake_urlopen).create_order(**kwargs)


def test_empty_response_body_returns_empty_dict():
    def fake_urlopen(request, timeout):
        return FakeResponse(b"")

    assert make_client(fake_urlopen).account() == {}
