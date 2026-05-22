# MTF Trend

MTF Trend is the first research strategy built on the new falsifiable workflow.

## Phase Ladder

| Phase | Hypothesis | Added Variable |
|---|---|---|
| 6.1 | H-100 | 1h MA baseline |
| 6.2 | H-101 | EMA200 trend filter |
| 6.3 | H-102 | ATR position sizing |
| 6.4 | H-103 | 15m pullback entry |
| 6.5 | H-104 | 5m trigger confirmation |
| 6.6 | H-105 | ATR dynamic stop/take-profit |

## Current Local Result

The local BTCUSDT 1h cache is short, so this is a research smoke run rather than a production-grade conclusion.

| Phase | OOS Sharpe | Max DD | OOS Count | Decision |
|---|---:|---:|---:|---|
| H-100 | 0.16699 | -0.04791 | 582 | kept |
| H-101 | 0.00000 | 0.00000 | 582 | risk_reduction_kept |
| H-102 | 0.00000 | 0.00000 | 582 | inconclusive |
| H-103 | 0.00000 | 0.00000 | 582 | inconclusive |
| H-104 | 0.00000 | 0.00000 | 582 | inconclusive |
| H-105 | 0.00000 | 0.00000 | 582 | inconclusive |

The next research improvement is to make the walk-forward runner consume synchronized 1h/15m/5m frames and simulate stop/take-profit exits candle by candle.
