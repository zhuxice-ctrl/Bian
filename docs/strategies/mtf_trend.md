# MTF Trend

MTF Trend is the first research strategy built on the falsifiable workflow.

## Phase Ladder

| Phase | Hypothesis | Added Variable |
|---|---|---|
| 6.1 | H-100 | 1h MA baseline |
| 6.2 | H-101 | EMA200 trend filter |
| 6.3 | H-102 | ATR position sizing |
| 6.4 | H-103 | 15m pullback entry |
| 6.5 | H-104 | 5m trigger confirmation |
| 6.6 | H-105 | ATR dynamic stop/take-profit |

## Corrected Local Result

This run corrects the old `trade_count` bug: OOS bar count is no longer treated as trade count. It also applies the market cost model `fee=0.0008`, `slippage=0.0005`, and `latency=0.0002`.

| Phase | OOS Sharpe | Max DD | Trades | Bars | Deferred Windows | Decision |
|---|---:|---:|---:|---:|---:|---|
| H-100 | -0.82987 | -0.10001 | 28 | 582 | 0 | kept |
| H-101 | 0.00000 | 0.00000 | 0 | 582 | 0 | rejected |
| H-102 | 0.00000 | 0.00000 | 0 | 582 | 0 | inconclusive |
| H-103 | 0.00000 | 0.00000 | 0 | 582 | 4 | deferred |
| H-104 | 0.00000 | 0.00000 | 0 | 582 | 6 | deferred |
| H-105 | 0.00000 | 0.00000 | 0 | 582 | 6 | deferred |

The next research improvement is data coverage: refresh enough synchronized 1h/15m/5m history so H-103 through H-105 can leave `deferred` and become real tests.
