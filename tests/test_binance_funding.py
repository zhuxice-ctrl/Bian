from unittest.mock import Mock, patch

import pandas as pd

from trading_learning.market_data.binance_funding import (
    aggregate_daily_funding,
    calculate_funding_pnl,
    fetch_funding_rate,
)


def _mock_response(payload: object) -> Mock:
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_fetch_funding_rate_returns_expected_dataframe():
    response = _mock_response(
        [
            {
                "symbol": "BTCUSDT",
                "fundingTime": 1777593600000,
                "fundingRate": "0.00010000",
                "markPrice": "100.50",
            }
        ]
    )

    with patch("trading_learning.market_data.binance_funding.requests.get", return_value=response) as get:
        frame = fetch_funding_rate(
            symbol="btcusdt",
            start_ms=1777593600000,
            end_ms=1777680000000,
            limit=1,
        )

    assert list(frame.columns) == ["timestamp", "funding_rate"]
    assert frame.loc[0, "timestamp"] == pd.Timestamp("2026-05-01T00:00:00Z")
    assert frame.loc[0, "funding_rate"] == 0.0001
    get.assert_called_once_with(
        "https://fapi.binance.com/fapi/v1/fundingRate",
        params={
            "symbol": "BTCUSDT",
            "limit": 1,
            "startTime": 1777593600000,
            "endTime": 1777680000000,
        },
        timeout=30,
    )


def test_aggregate_daily_funding_sums_three_8h_rows():
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-05-01T00:00:00Z",
                    "2026-05-01T08:00:00Z",
                    "2026-05-01T16:00:00Z",
                ],
                utc=True,
            ),
            "funding_rate": [0.0001, -0.00002, 0.00003],
        }
    )

    daily = aggregate_daily_funding(frame)

    assert daily.index.tolist() == [pd.Timestamp("2026-05-01T00:00:00Z")]
    assert daily.loc[pd.Timestamp("2026-05-01T00:00:00Z")] == 0.00011


def test_calculate_funding_pnl_long_positive_funding_is_negative_pnl():
    positions = pd.Series([1.0], index=pd.to_datetime(["2026-05-01"], utc=True))
    daily_funding = pd.Series([0.0002], index=pd.to_datetime(["2026-05-01"], utc=True))

    funding_pnl = calculate_funding_pnl(positions, daily_funding)

    assert funding_pnl.loc[pd.Timestamp("2026-05-01T00:00:00Z")] == -0.0002


def test_calculate_funding_pnl_short_positive_funding_is_positive_pnl():
    positions = pd.Series([-1.0], index=pd.to_datetime(["2026-05-01"], utc=True))
    daily_funding = pd.Series([0.0002], index=pd.to_datetime(["2026-05-01"], utc=True))

    funding_pnl = calculate_funding_pnl(positions, daily_funding)

    assert funding_pnl.loc[pd.Timestamp("2026-05-01T00:00:00Z")] == 0.0002
