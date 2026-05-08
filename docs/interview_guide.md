# Interview Guide — Digital Asset Market Behavior Intelligence Platform

A working script for using this project in a Digital Asset Market Behavior & Strategy Analyst interview. Written in natural spoken English so the phrasing transfers directly to the conversation.

---

## 30-second pitch

> I built a research platform that explains how and why crypto markets move. It pulls daily data on price, sentiment, DeFi liquidity, on-chain activity, macro context, and a curated event calendar, fuses it into about fifty features, and classifies every trading day into one of seven interpretable behavior regimes. On top of that I run a formal event study and a sentiment-price lead-lag analysis. The output is a six-page Streamlit dashboard and a written research memo with strategy implications. The point is to do the analyst's job, which is explaining behavior, not predicting next-day price.

## 90-second pitch

> Most crypto portfolio projects predict next-day BTC price using a couple of signals. I deliberately did the opposite, because the strategy analyst's job is not next-day forecasting. It is explaining market behavior, ranking event sensitivity, and producing research that a portfolio manager can actually read.
>
> The platform covers BTC, ETH, SOL, plus a six-token DeFi basket, daily, from January 2023 to today. It pulls market data from yfinance and CoinGecko, sentiment from the Fear & Greed Index, DeFi liquidity from DeFiLlama, BTC on-chain from Blockchain.com, ETH on-chain from Etherscan with a documented free-tier proxy, macro from FRED, and a curated calendar of forty-six real events spanning FOMC, CPI, ETFs, regulation, exchanges, exploits, protocol upgrades, and macro shocks. From those, I engineer about fifty features and classify each day into one of seven regimes — Calm, Momentum, Risk-off, Liquidity Stress, Event-driven, On-chain Activity Spike, or Neutral — using explicit rules with a defined precedence.
>
> Three findings stood out. First, sentiment lags price by approximately one day across all nine tracked assets. Fear & Greed is best treated as a confirming indicator. Second, protocol upgrades and exchange events are associated with the largest short-window reactions, while ETF and CPI events show lower average impact, consistent with substantial pre-event pricing. Third, regime labels carry economically meaningful information about subsequent realized returns.
>
> The deliverables are a six-page Streamlit dashboard, a written research memo, and a one-page case study. Every method is interpretable, every API has a documented fallback, and the dashboard runs end-to-end from parquet without ever calling an API live.

## STAR-format answer

**Situation:** I was preparing for a Digital Asset Market Behavior & Strategy Analyst role and wanted a portfolio piece that demonstrated research thinking, not just an ML notebook.

**Task:** Build something that mirrors what an analyst at a crypto-focused fund would actually produce — interpretable behavior regimes, event-reaction studies, sentiment dynamics, liquidity and on-chain signals — and present it as if it were a real internal research product.

**Action:** Designed a multi-source pipeline across price, sentiment, DeFi liquidity, on-chain activity, macro, and curated events. Implemented modular ingestion with graceful fallbacks, about fifty engineered features, a rule-based regime classifier with explicit precedence, a formal event study, and a sentiment-price lead-lag analysis. Built a six-page Streamlit dashboard for interactive exploration, wrote a research memo with real numbers from the analysis, added GitHub Actions CI with a secret-scan guard, and produced a one-page case study.

**Result:** A reproducible end-to-end research product. The dashboard runs in under two minutes from a fresh clone, every output is interpretable, and the methodology is defensible — for example, sentiment lags price by approximately one day across all nine assets, which I treat as a finding rather than a problem and use to argue for using Fear & Greed as a confirming indicator.

---

## How to explain why there is no accuracy or F1 score

> The project is not a classifier of a labeled outcome, so accuracy and F1 are the wrong metrics. The regime classifier assigns interpretive labels using transparent rules; there is no ground-truth regime to score against. The event study reports descriptive statistics — cumulative returns, volatility ratios, sentiment shifts — over windows around real events. The lead-lag analysis is a cross-correlation, which is reported as a correlation coefficient with a sample size, not as a prediction-quality metric. If the role required a predictive model, I would add an out-of-sample evaluation harness; for behavior research, the right diagnostics are economic separation between regimes and event-window statistics, both of which are in the memo.

## How to explain the event study

> For each event in the curated calendar I compute three metrics around the event date: cumulative log return from t−1 to t+1, t to t+3, and t to t+7; the ratio of post-event to pre-event five-day realized volatility; and the change in mean trading volume across the same windows. I also track changes in sentiment, total DeFi TVL, and the on-chain activity index across pre- and post-event windows. The composite impact score is the absolute t-to-t+7 return plus the excess of the volatility ratio above one. Events are then ranked overall and grouped by event type and by asset. The output is a descriptive picture of how the market reacted around different categories of events, not a causal estimate.

## How to explain lead-lag without implying look-ahead bias

> The lead-lag analysis is a sample cross-correlation between the daily change in Fear & Greed and the asset's daily return, evaluated at lags from minus seven to plus seven days. A lag of minus one means that the change in sentiment at time t is most correlated with the asset return that was realized about one day earlier. In other words, sentiment is reacting to recent realized price action; it is not predicting forward returns. This is consistent with how the Fear & Greed Index is constructed — it weights recent price action heavily — so the finding is descriptive, not a sign that the model is leaking future information. Every rolling feature in the platform is trailing-only, and regime labels at time t use only features known by end of day t.

## How to explain "priced in"

> When I say an event was partially priced in, I mean that market participants had time to update positioning before the event date. ETF approvals, for example, were anticipated for weeks; by the time the formal approval landed, much of the directional move had already happened. That shows up in the data as smaller short-window post-event impact relative to pre-event drift. It does not mean ETF approvals are unimportant — it means the measured event-window surprise was smaller because the information had been absorbed gradually. By contrast, exchange exploits and protocol upgrades that did not have a fixed pre-announced surprise schedule produced larger reactions in the same metric.

## How to explain limitations honestly

> Three limitations are worth flagging up front. First, ETH on-chain data uses a DeFiLlama-derived TVL flux proxy because the Etherscan free-tier stats endpoints are Pro-only. The activity direction is informative; the absolute units are not native transaction counts. A Pro Etherscan key would replace the proxy in one module without other code changes. Second, sentiment is a single proxy — Fear & Greed — which heavily weights recent price action, so the lead-lag finding describes that proxy and not sentiment in general. Tweet-level sentiment is no longer free since the X / Twitter API changes. Third, the regime-conditional return statistics include some labels with small sample counts; I treat them as illustrative of separation between regimes, not as a tradable backtest. Each of these is documented in the README and the memo.

---

## Ten likely interview questions and strong answers

**1. Why didn't you build a price-prediction model?**

> Because the role is research and strategy, not high-frequency alpha. A price model on free daily data without microstructure would either overfit or be mediocre, and either way it would not tell a strategy team why the market moved. Regimes and event studies are interpretable and consumable, which is what a portfolio manager actually needs.

**2. Why rules instead of a hidden Markov model or clustering?**

> Auditability. With about 1,200 daily observations and seven regimes, an HMM is fragile and the labels are not stable across re-fits. Rules are defensible — a portfolio manager can read the threshold and disagree. The framework supports swapping in a probabilistic model later, seeded with the rule labels as priors, which is in the future-work list.

**3. How do you avoid look-ahead bias?**

> Every rolling feature is trailing-only — the z-score at time t uses the window ending at t minus one. Regime labels at time t use only features known by end of day t. The event study computes returns and volatility ratios in calendar time around the event date and never re-baselines. Tests in `tests/test_features.py` include a no-look-ahead check that shifts inputs and confirms the feature does not change.

**4. Total Value Locked is denominated in dollars — won't it just track price?**

> Yes, partially, and the memo flags this. A ten-percent TVL drop with a ten-percent ETH drop is mostly mechanical. I report TVL changes alongside the relevant token's price change so a reader can distinguish mechanical from net-flow moves. For a production version I would compute token-denominated TVL per protocol, which removes the price contamination entirely. That is the standard upgrade path.

**5. Sentiment lags price — so what?**

> It is a useful constraint. It means Fear & Greed should not be used as a forward signal in isolation, which is how a lot of retail-facing tools use it. It can still be a useful conditioning variable — for example, a Risk-off regime is more reliably labeled when drawdown is severe and sentiment is also in the Fear or Extreme Fear zone. So the practical implication is that sentiment confirms a state rather than predicts the next state, and the regime engine is built on that distinction.

**6. ETF events score lowest in the impact ranking — does that mean they don't matter?**

> No. It means the measured event-window reaction was smaller, likely because major ETF events were anticipated for weeks. Many ETF events drove sustained multi-week trends rather than concentrated single-day reactions. So the right reading is "smaller event-window surprise," not "less important." The composite impact score captures short-window response, which is the metric that reveals how much information was actually new on the event date.

**7. What would you do differently with a paid data stack?**

> Three things in priority order. Funding-rate dispersion across major centralized exchanges as a forward-looking liquidity-stress feature. Deribit DVOL and 25-delta skew as a forward-looking implied-volatility layer. Glassnode or CryptoQuant Pro for native exchange netflow, which would let me split the On-chain Activity Spike regime into Accumulation and Distribution. The platform is structured so each of these slots into existing modules without rewrites.

**8. How is the impact score weighted, and why that formula?**

> The composite impact score is the absolute cumulative log return from t to t+7 plus the excess of the post-over-pre five-day realized-volatility ratio above one. The first term captures directional move, the second captures volatility expansion. Both are non-negative and roughly comparable in scale across events, so the sum is a reasonable single ranking. I deliberately did not weight by curated severity, so the ranking is robust to subjectivity in the severity rubric.

**9. Can this run in production?**

> The architecture is production-ready in shape but not yet hardened. Ingestion is modular with retries, caching, and graceful fallbacks. The dashboard reads only parquet — it never calls APIs live — which makes it safe to deploy behind a reverse proxy. CI runs pytest plus a dashboard import smoke test on every push and includes a secret-scan guard. To go to real production I would add scheduled refresh via GitHub Actions or a small worker, externalize processed data to object storage, and add observability around the ingest layer.

**10. What is the most defensible single number in the project?**

> The lead-lag correlation between daily change in Fear & Greed and BTC return at lag minus one — about plus zero point six five over roughly 1,200 daily observations. The construction is simple, the sign is the right way around for a sentiment proxy that weights recent price, and the magnitude is large enough to be operationally relevant. That single number anchors the rule that Fear & Greed is a confirming indicator rather than a forward signal, and that rule cascades into the regime classifier.
