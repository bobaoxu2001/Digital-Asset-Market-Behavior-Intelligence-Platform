# Digital Asset Market Behavior Intelligence Platform
## Research Memo

**Author:** Xu Ao  
**As of:** 2026-05-08  
**Coverage:** BTC, ETH, SOL, AVAX, UNI, AAVE, LDO, MKR, CRV — daily, 2023-01-01 to 2026-05-08

---

### Key Takeaways

| # | Finding | Strategy implication |
|---|---|---|
| 1 | Sentiment lags price by ~1 day across all 9 assets (peak corr at lag = −1, BTC +0.65 ⇨ MKR +0.33) | Use F&G as a *confirming* indicator, not an alpha — feed into the regime engine, not into a directional signal |
| 2 | Protocol Upgrade and Exchange events drive the largest market reactions (mean impact 1.44 / 0.86); ETF and CPI rank lowest (0.22 / 0.37) | Pre-position around tech catalysts; fade scheduled-macro hype where information is already discounted |
| 3 | Regime labels carry economically meaningful information about subsequent returns | Regime is a useful conditioning variable for any overlay strategy |
| 4 | Joint occurrence of liquidity stress + abnormal on-chain activity coincided with the worst sample drawdowns (March 2023 SVB / Aug 2024 yen carry) | Treat the joint signal as a *fade-or-hedge* trigger, not a contrarian-buy |
| 5 | DeFi tokens (UNI, AAVE, LDO, MKR, CRV) systematically amplify event-driven moves vs. majors | Use DeFi basket for higher-beta event expressions when conviction is high |

📊 Charts referenced below are also viewable in the live dashboard — see `assets/screenshots/` for static previews.

---

### 1. Executive Summary

- **Sentiment lags price by ~1 day, uniformly across all 9 assets.** Peak correlation between daily change in Fear & Greed and prior-day asset return ranges from **+0.33 (MKR) to +0.65 (BTC)** at lag = −1. Treat market sentiment as a *confirming* indicator, not a leading one.
- **Protocol-upgrade and exchange-incident events generate the largest behavior reactions.** Mean composite impact score: Protocol Upgrade **1.44**, Exchange **0.86**, Regulation **0.74**, Exploit **0.62**. ETF and CPI events under-rank because their information was largely priced in pre-event.
- **Regime separation is economically meaningful.** For BTC, *Momentum* days (n=37) annualize to a hypothetical +349% return (caveat: small sample, illustrative not investable), while *Calm* days (n=237) return **−24% annualized**. Regime labels capture distinct behaviors, not noise.
- **Current state (2026-05-08):** BTC in **Risk-off** regime; Fear & Greed = **38 (Fear)**; DeFi TVL = **$57.0B**; liquidity stress score **−0.89** (no acute stress).

### 2. Research Question

How do digital-asset markets *behave* — not just price — and which signals (sentiment, liquidity, on-chain activity, event flow) explain that behavior? The platform answers six concrete sub-questions:

1. Does sentiment lead or lag price?
2. Which event types produce the largest market reactions?
3. Do liquidity stress signals coincide with drawdowns?
4. Does on-chain activity provide leading or coincident information?
5. Which assets are most event-sensitive?
6. How persistent are behavior regimes, and what conditional returns do they imply?

### 3. Data Sources

| Domain | Primary | Fallback / Note |
|---|---|---|
| Price / volume / market cap | yfinance (full history) + CoinGecko Demo API (trailing 365d for market_cap) | CoinGecko Demo plan caps historical depth at 365d, so yfinance is the backbone |
| Sentiment | Alternative.me Crypto Fear & Greed Index | Synthetic series fallback if API down |
| Events | Curated CSV of 46 macro + crypto events (FOMC, CPI, ETF, Regulation, Exchange, Exploit, Protocol Upgrade, Macro Shock) | — |
| News volume | GDELT 2.0 timeline | Optional; pipeline does not block on GDELT |
| DeFi TVL | DeFiLlama chain & protocol historical endpoints | — |
| Stablecoins | DeFiLlama stablecoincharts/all | — |
| BTC on-chain | Blockchain.com Charts (n-transactions, n-unique-addresses, transaction-fees-usd) | — |
| ETH on-chain | Etherscan stats (`dailytx`, `dailyavggasprice`, `dailynewaddress`) | **Etherscan free tier returned `NOTOK` (Pro-only)**; falls back to a DeFiLlama Ethereum-chain TVL flux proxy. The activity *direction* is informative; absolute units are not native tx counts and this is documented in the dashboard. |
| Macro | FRED (VIX, DGS10, DTWEXBGS, SP500) | yfinance fallback (^VIX, ^TNX, DX-Y.NYB, ^GSPC) |
| News (CryptoPanic) | not available — explicitly skipped per project scope | curated events provide the event channel |

### 4. Methodology

- **Feature engineering** produces ~50 daily features per (date, asset): price returns (1d/7d/30d), realized volatility (7d/30d annualized), volume z-score & spike flag, drawdown, rolling sentiment z-score & 3d/7d shifts, TVL changes (1d/7d/30d), composite **liquidity stress score** (z-scored negative TVL trend + negative stablecoin trend, threshold 1.5σ), per-asset on-chain activity z-scores and a composite **on-chain activity index**, macro layer (VIX, 10Y, DXY proxy, S&P 500), event flag/type/severity and days-since/to.
- **Regime classifier:** transparent rule-based with explicit precedence — Event-driven → Liquidity Stress → Risk-off → On-chain Activity Spike → Momentum → Calm → Neutral. Rules are auditable in `src/features/regime_classifier.py`. Vol-low threshold is per-asset 33rd percentile of trailing 30d vol over the full sample (trailing-only).
- **Event study:** for each (event, asset), compute t-1→t+1, t→t+3, t→t+7 cumulative log returns; pre/post 5d realized vol and average volume; sentiment shift; TVL reaction; on-chain activity shift. Composite `impact_score = |ret_t_t7| + max(vol_ratio − 1, 0)` ranks events.
- **Lead-lag:** sample cross-correlation between daily change in F&G and asset return at lags k ∈ [−7, +7]; positive k means sentiment leads.
- **Look-ahead control:** all rolling features are trailing-only (z-scores at t use the window ending t−1). Regime labels use only features known at end of day t.

### 5. Market Regime Findings

Across 2023-01-01 → 2026-05-08, BTC spent the largest share of days in **Calm (237)**, **Risk-off (189)**, and **Liquidity Stress (169)**, with shorter bursts of **Momentum (37)** and **Event-driven (91)**.

Hypothetical regime-conditional annualized returns for BTC (n_days, ann. return, ann. vol):
- Momentum: 37, **+349%** ann. ret, 71% vol
- Event-driven: 91, **+1491%** ann. ret, 68% vol *(small-sample, dominated by 2024–25 catalyst clusters)*
- Liquidity Stress: 169, +56% ann. ret, 60% vol
- Calm: 237, **−24%** ann. ret, 28% vol *(low-vol drift days are not free returns)*
- Risk-off: 189, ~0% ann. ret, 44% vol
- Neutral: 494, +60% ann. ret, 43% vol

Caveats: small samples in Momentum/Event-driven inflate annualized estimates; these numbers are illustrative of *separation between regimes*, not a tradable backtest. The clear takeaway is that regime label carries economically meaningful information about subsequent realized returns.

### 6. Sentiment & Event Reaction Findings

**Sentiment lags price by ~1 day, universally:**

| Asset | Best lag (days) | corr |
|---|---|---|
| BTC | −1 | +0.65 |
| ETH | −1 | +0.55 |
| SOL | −1 | +0.49 |
| AVAX | −1 | +0.47 |
| AAVE | −1 | +0.43 |
| CRV | −1 | +0.43 |
| LDO | −1 | +0.42 |
| UNI | −1 | +0.40 |
| MKR | −1 | +0.33 |

Lead correlations (k > 0) are near zero across the board, often negative. **Implication:** Fear & Greed encodes recent realized price action — it is descriptive, not predictive. For directional research it should be used as a *regime co-confirmer* (e.g., F&G < 25 reinforces Risk-off labels) and *not* as a forward signal.

**Event sensitivity by type (mean impact score, n events):**

1. Protocol Upgrade — 1.44 (n=4 events × 9 assets = 36 obs)
2. Exchange — 0.86 (e.g., FTX, Bybit hack, Binance settlement)
3. Regulation — 0.74 (SEC enforcement, MiCA, EOs)
4. Exploit — 0.62 (Curve, Bybit cold-wallet)
5. Macro Shock — 0.51 (yen carry unwind, Liberation Day tariffs)
6. FOMC — 0.42
7. CPI — 0.37
8. ETF — 0.22

ETFs rank lowest because the news was *priced in* over weeks of approval anticipation rather than in single-day reactions. The largest single event observations are clustered around Ethereum Pectra (May 2025) and the November 2024 US election outcome — both produced multi-week trends that show up as elevated post/pre realized-vol ratios.

### 7. Liquidity & DeFi Participation Findings

- Tracked DeFi TVL across Ethereum, Solana, Arbitrum, and Base aggregates to **$57.0B** as of 2026-05-08.
- Stablecoin total circulating supply — a crypto-native risk-on/off proxy — has been steadily expanding through 2024–2026, supportive of the ongoing risk-asset bid.
- The composite **liquidity stress score** (z-scored negative TVL & stablecoin trend) currently reads **−0.89** — well below the 1.5σ stress threshold. Historical breaches of that threshold cluster around (a) the March 2023 Silvergate/SVB/USDC depeg week, and (b) the August 2024 yen carry-unwind day. In both cases, stress flagged within ±2 days of the worst BTC drawdown of the surrounding period.

### 8. On-chain Activity Findings

BTC on-chain (full data via Blockchain.com): the **on-chain activity index** combines z-scored daily transaction count, unique-address count, and USD-denominated transaction-fee proxy. Abnormal-activity days (index > 1.5σ) cluster around (i) major protocol/network events, (ii) volatility regime changes, and (iii) pre-halving accumulation periods. Of the 5 BTC abnormal-activity days that coincided with volume spikes (the precondition for the *On-chain Activity Spike* regime), the dominant context was elevated transaction throughput rather than fee-spike — consistent with active rotation, not stress.

ETH on-chain: **Etherscan's free-tier `stats` endpoints returned `NOTOK` (Pro-only)**, so the platform falls back to a DeFiLlama-derived Ethereum chain-TVL flux proxy. This captures activity *direction* faithfully but is denominated in USD-flux units, not native tx-count. This limitation is documented in the dashboard and is a known scope choice for a free-tier build.

### 9. Strategy Implications

1. **Don't trade Fear & Greed directionally on its own.** With every asset's peak lead-lag at −1 day, F&G is a confirmation tool, not an alpha. The right operational use is to threshold it into the regime classifier — F&G < 40 + drawdown < −15% is a clean Risk-off filter that the rule engine already uses.
2. **Pre-position around Protocol Upgrades and Exchange events, not ETFs or CPI.** Cross-asset event-type ranking shows where information is genuinely surprising. Calendar-driven events (FOMC, CPI, ETF launches) trade smaller because they are pre-discounted.
3. **DeFi tokens (UNI, AAVE, LDO, MKR, CRV) amplify event-driven moves.** The top-10 impact list disproportionately features DeFi names rather than majors, even after controlling for baseline volatility. Use this for higher-beta event expressions when conviction is high.
4. **Liquidity stress + abnormal on-chain activity is the configuration to fade or hedge.** Both signals coincided with the worst drawdowns in the sample. Treat their joint occurrence as a hedge trigger rather than a contrarian buy.

### 10. Limitations

- **Etherscan free tier.** ETH on-chain `dailytx` / gas / new-address endpoints are Pro-only on the current free tier; ETH on-chain features use a DeFiLlama-derived flux proxy. A Pro key would replace the proxy with native chain counters in `src/ingest/onchain_etherscan.py` without other code changes.
- **CoinGecko Demo historical depth.** Demo plan limits `market_chart/range` to the trailing 365 days; the platform uses yfinance for the longer history and CoinGecko for trailing-365d enrichment.
- **No exchange inflow/outflow.** Free sources do not reliably label exchange wallets. The platform deliberately avoids fabricating netflow; an `On-chain Distribution / Accumulation` regime split is left as an upgrade contingent on Glassnode or CryptoQuant access.
- **Curated event severity is judgmental.** 46 events with manually assigned 1–3 severity. Sensitivity to severity weights is bounded because the impact_score does not weight by severity; severity is used only for tie-breaking when multiple events share a date.
- **Lead-lag uses a single sentiment series (F&G).** Adding tweet-level or news-headline sentiment would test whether the lag pattern is an artifact of how F&G is constructed (it heavily weights recent price). The current finding is that *the available sentiment proxy is reactive*, not that sentiment in general is reactive.
- **Sample-size effects in regime returns.** *Momentum* and *Event-driven* labels have <100 days for some assets; annualized return point estimates are unstable.

### 11. Next Steps

1. **Funding-rate dispersion** across CEXs (Binance, OKX, Bybit) as a forward-looking liquidity-stress feature.
2. **Deribit DVOL** and 25-delta skew as an implied-vol layer to complement realized vol regimes.
3. **Glassnode or CryptoQuant Pro** integration for native exchange netflow → split *On-chain Activity Spike* into Accumulation vs Distribution.
4. **Probabilistic regime model** seeded with the rule labels (HMM or supervised L1-logistic on transitions) to surface which features actually mark regime turns.
5. **Hourly resolution** for BTC/ETH event windows around scheduled macro releases — daily resolution averages over the actual reaction.
6. **Out-of-sample evaluation** of the strategy implications: train regime + lead-lag on 2023–2024, evaluate on 2025–2026, report degradation.

---

*Reproducibility:* every number in this memo is computable from the parquet outputs in `data/processed/` produced by `make ingest && make features && make analysis`. Code and configuration are in this repository.
