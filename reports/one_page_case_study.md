# Digital Asset Market Behavior Intelligence Platform
### *A behavior-explanation platform for crypto markets — regimes, events, sentiment, liquidity, on-chain.*

**Author:** Xu Ao &nbsp;|&nbsp; **Coverage:** BTC, ETH, SOL + 6-token DeFi basket, daily, 2023-01-01 → today
**Repo:** [github.com/bobaoxu2001/Digital-Asset-Market-Behavior-Intelligence-Platform](https://github.com/bobaoxu2001/Digital-Asset-Market-Behavior-Intelligence-Platform)
**Live dashboard:** local — `make dashboard` &nbsp;|&nbsp; **Demo mode:** `make demo`

---

### 🎯 Problem

Most crypto research tools either (a) predict next-day price using one or two signals, or (b) display single-source dashboards (price-only, sentiment-only). Neither is what a **digital-asset strategy analyst** actually needs. The analyst's job is to **explain** market behavior, **rank** event sensitivities, **detect** regime shifts, and **produce** strategy-relevant memos — across multiple coupled data sources.

### 🛠️ What it is

A reproducible end-to-end platform that fuses six data domains into a single feature table, classifies each (date, asset) day into one of seven interpretable behavior regimes, runs a formal event study over a curated calendar, and surfaces all of it through a polished six-page Streamlit dashboard plus a written research memo.

### 🗂️ Data sources (all free-tier; all with documented fallbacks)

| Domain | Primary | Fallback |
|---|---|---|
| Price / volume / market cap | yfinance + CoinGecko Demo | each fills the other's gaps |
| Sentiment | Alternative.me Fear & Greed | synthetic series if API down |
| DeFi liquidity / TVL | DeFiLlama (chains, protocols, stablecoins) | — |
| BTC on-chain | Blockchain.com Charts | — |
| ETH on-chain | Etherscan stats | DeFiLlama TVL flux proxy *(documented)* |
| Macro | FRED (VIX, DGS10, DXY proxy, SP500) | yfinance equivalents |
| Events | Curated CSV — 46 real events, 2023-Q1 → today | — |

### 🔬 Methodology

- ~50 daily features per (date, asset): returns, realized vol, volume z-score, drawdown, sentiment z-score & shifts, TVL changes, composite **liquidity stress score**, **on-chain activity index**, macro layer, event flag/severity/days-since-or-to.
- **Rule-based regime classifier** with explicit precedence: Event-driven → Liquidity Stress → Risk-off → On-chain Activity Spike → Momentum → Calm → Neutral.
- **Event study**: per (event, asset) — `t-1→t+1`, `t→t+3`, `t→t+7` cumulative log returns; pre/post realized vol & volume; sentiment shift; TVL & on-chain reaction; composite impact score.
- **Lead-lag**: cross-correlation of `Δsentiment_t` vs `return_{t+k}` for `k ∈ [-7, +7]`.
- **Look-ahead control**: every rolling feature is trailing-only; regime labels at time *t* use only features known by end-of-day *t*.

### 🏆 Key findings

| # | Finding | Implication |
|---|---|---|
| 1 | **Sentiment lags price by 1 day** universally — peak corr at lag = −1 for all 9 assets (BTC +0.65, ETH +0.55, SOL +0.49). | Treat F&G as a *confirming* indicator, not an alpha. |
| 2 | **Protocol Upgrades and Exchange events** generate the largest impact (mean impact 1.44 and 0.86); ETFs rank lowest (0.22) — already priced in. | Pre-position around tech catalysts; fade hype around scheduled macro / ETF flows. |
| 3 | **Regime labels separate behavior** — *Calm* days quietly drift negative; *Momentum* / *Event-driven* days carry the upside. | Regime label is a useful conditioning variable for any strategy overlay. |
| 4 | **Liquidity stress + abnormal on-chain activity** coincided with the worst drawdowns (March 2023 SVB / USDC depeg, August 2024 yen carry unwind). | Joint occurrence is a hedge / fade trigger. |

### 💼 Strategy implications

1. **Don't trade Fear & Greed directionally.** Use it inside the regime engine, not as a forward signal.
2. **Pre-position around Protocol Upgrades and Exchange events**, not ETFs or CPI prints.
3. **DeFi tokens (UNI, AAVE, LDO, MKR, CRV) amplify event-driven moves** — higher-beta event expressions when conviction is high.
4. **Liquidity stress + on-chain abnormal activity = fade or hedge.**

### 📌 Why this matters for digital asset research teams

- **Multi-modal**, not single-source. Replicates how a real analyst combines price, sentiment, liquidity, on-chain, and event data.
- **Interpretable**, not black-box. Every regime label is auditable; every event ranking has a formula a PM can disagree with.
- **Defensible under interview pressure.** Look-ahead bias controlled; limitations documented; fallback paths declared up front.
- **Reproducible end-to-end.** `make ingest && make features && make analysis && make dashboard` on a fresh clone, in under 2 minutes.

### 🧰 Tech stack

Python 3.11 · pandas · numpy · scipy · plotly · streamlit · pyarrow · yfinance · requests · pyyaml · dotenv · pytest · GitHub Actions CI · DeFiLlama · CoinGecko · FRED · Blockchain.com Charts · Etherscan · GDELT 2.0.

---

> **Export to PDF:** `pandoc reports/one_page_case_study.md -o reports/one_page_case_study.pdf` (requires `pandoc` + a LaTeX engine, e.g. `tectonic` or `xelatex`).
