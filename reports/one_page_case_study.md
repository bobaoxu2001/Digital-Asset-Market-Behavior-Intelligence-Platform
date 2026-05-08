# Digital Asset Market Behavior Intelligence Platform

*A research platform for digital-asset markets covering regimes, events, sentiment, liquidity, and on-chain activity.*

**Author:** Xu Ao &nbsp;|&nbsp; **Coverage:** BTC, ETH, SOL, plus a six-token DeFi basket; daily; 2023-01-01 to today
**Repository:** [github.com/bobaoxu2001/Digital-Asset-Market-Behavior-Intelligence-Platform](https://github.com/bobaoxu2001/Digital-Asset-Market-Behavior-Intelligence-Platform)
**Live dashboard:** local — `make dashboard` &nbsp;|&nbsp; **Demo mode:** `make demo`

---

### Problem

Existing crypto research tooling tends to fall into two categories: short-horizon price-prediction models built on one or two signals, and single-source dashboards that present price, sentiment, or on-chain activity in isolation. Neither maps cleanly to the strategy analyst's actual workflow, which requires explaining market behavior, ranking event sensitivity, identifying regime transitions, and producing written research across multiple coupled data sources.

### What It Is

A reproducible end-to-end platform that fuses six data domains into a single feature table, classifies each (date, asset) day into one of seven interpretable behavior regimes, runs a formal event study over a curated calendar, and surfaces results through a six-page Streamlit dashboard and a written research memo.

### Data Sources

All sources are free-tier and all have documented fallbacks.

| Domain | Primary | Fallback |
|---|---|---|
| Price, volume, market cap | yfinance and CoinGecko Demo | each fills the other's gaps |
| Sentiment | Alternative.me Fear & Greed Index | synthetic series if API unavailable |
| DeFi liquidity and TVL | DeFiLlama (chains, protocols, stablecoins) | — |
| BTC on-chain | Blockchain.com Charts | — |
| ETH on-chain | Etherscan stats | DeFiLlama TVL flux proxy (documented) |
| Macro | FRED (VIX, DGS10, DXY proxy, SP500) | yfinance equivalents |
| Events | Curated CSV, 46 events, 2023-Q1 to today | — |

### Methodology

- Approximately fifty daily features per (date, asset): returns, realized volatility, volume z-score, drawdown, sentiment z-score and shifts, TVL changes, composite liquidity-stress score, on-chain activity index, macro layer, event flag / severity / days-since / days-to.
- Rule-based regime classifier with explicit precedence: Event-driven → Liquidity Stress → Risk-off → On-chain Activity Spike → Momentum → Calm → Neutral.
- Event study: per (event, asset) — `t-1 → t+1`, `t → t+3`, `t → t+7` cumulative log returns; pre / post realized volatility and average volume; sentiment shift; TVL and on-chain reaction; composite impact score.
- Lead-lag: cross-correlation of `Δsentiment_t` against `return_{t+k}` for `k ∈ [-7, +7]`.
- Look-ahead control: every rolling feature is trailing-only; regime labels at time *t* use only features known by end of day *t*.

### Key Findings

| # | Finding | Implication |
|---|---|---|
| 1 | Sentiment lags price by approximately one day across all nine assets — peak |corr| at lag = −1 (BTC +0.65, ETH +0.55, SOL +0.49). | Treat Fear & Greed as a confirming indicator rather than a forward-looking signal. |
| 2 | Protocol upgrades and exchange events are associated with the largest mean event impact (1.44 and 0.86 respectively); ETF events showed lower average short-window impact, likely because major approval expectations were partially priced in before the event date. | Distinguish anticipated catalysts from genuine surprise events when interpreting market reactions. |
| 3 | Regime labels separate behavior in the sample: *Calm* days showed negative average performance; *Momentum* and *Event-driven* days produced the bulk of upside. | Regime label is a useful conditioning variable for any strategy overlay. |
| 4 | Joint occurrence of liquidity stress and abnormal on-chain activity coincided with the largest sample drawdowns (March 2023 SVB and USDC depeg week, August 2024 yen-carry unwind). | Monitor as a potential risk-management signal. |

### Strategy Implications

1. Use Fear & Greed inside the regime engine rather than as a stand-alone directional signal.
2. Differentiate scheduled, well-anticipated events (FOMC, CPI, ETF launches) from less-anticipated events (protocol upgrades, exchange incidents) when sizing event-driven exposure.
3. DeFi tokens (UNI, AAVE, LDO, MKR, CRV) showed systematically larger event-window moves than majors and are candidates for higher-beta event expressions when conviction is high.
4. Treat the joint signal of liquidity stress and abnormal on-chain activity as a risk configuration to monitor or hedge.

### Why This Matters for Digital Asset Research Teams

- Multi-modal rather than single-source. Replicates how a research analyst combines price, sentiment, liquidity, on-chain, and event data.
- Interpretable rather than black-box. Every regime label is auditable; every event ranking is a transparent formula a portfolio manager can disagree with.
- Defensible under scrutiny. Look-ahead bias is controlled, limitations are documented, and fallback paths are declared up front.
- Reproducible end-to-end. `make ingest && make features && make analysis && make dashboard` on a fresh clone, in under two minutes.

### Tech Stack

Python 3.11, pandas, numpy, scipy, plotly, streamlit, pyarrow, yfinance, requests, pyyaml, python-dotenv, pytest, GitHub Actions CI. Data: DeFiLlama, CoinGecko, FRED, Blockchain.com Charts, Etherscan, GDELT 2.0.

---

> Export to PDF: `pandoc reports/one_page_case_study.md -o reports/one_page_case_study.pdf` (requires `pandoc` plus a LaTeX engine such as `tectonic` or `xelatex`).
