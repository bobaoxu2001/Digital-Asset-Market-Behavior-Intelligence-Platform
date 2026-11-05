"""Shared dashboard layout and narrative components."""
from __future__ import annotations

from typing import Iterable

import streamlit as st


def apply_institutional_theme() -> None:
    """Apply light CSS polish for a research-terminal look."""
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2.2rem;
            padding-bottom: 3rem;
            max-width: 1480px;
        }
        .stApp {
            background:
                radial-gradient(circle at 20% 0%, rgba(43, 91, 157, 0.16), transparent 28rem),
                linear-gradient(180deg, #0b0f17 0%, #111827 42%, #0b0f17 100%);
        }
        div[data-testid="stMetric"] {
            background: rgba(15, 23, 42, 0.78);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 8px;
            padding: 0.8rem 0.95rem;
            min-height: 104px;
        }
        div[data-testid="stMetricLabel"] p {
            color: #a8b3c7;
            font-size: 0.78rem;
        }
        div[data-testid="stMetricValue"] {
            color: #f8fafc;
        }
        .research-kicker {
            color: #eab308;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }
        .research-title {
            color: #f8fafc;
            font-size: clamp(2rem, 4vw, 3.4rem);
            line-height: 1.02;
            font-weight: 760;
            margin: 0;
        }
        .research-subtitle {
            color: #cbd5e1;
            font-size: 1.02rem;
            line-height: 1.55;
            max-width: 980px;
            margin-top: 0.8rem;
            margin-bottom: 1.2rem;
        }
        .takeaway {
            border: 1px solid rgba(234, 179, 8, 0.35);
            border-left: 4px solid #eab308;
            border-radius: 8px;
            background: rgba(15, 23, 42, 0.86);
            padding: 1rem 1.1rem;
            margin: 1rem 0 1.25rem;
        }
        .takeaway h3 {
            margin: 0 0 0.65rem;
            color: #f8fafc;
            font-size: 1.05rem;
        }
        .takeaway-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.8rem;
        }
        .takeaway-label {
            color: #eab308;
            font-size: 0.73rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.25rem;
        }
        .takeaway p {
            color: #dbe4f0;
            margin: 0;
            line-height: 1.48;
        }
        .takeaway-caveat {
            color: #a8b3c7;
            border-top: 1px solid rgba(148, 163, 184, 0.2);
            margin-top: 0.8rem;
            padding-top: 0.65rem;
            font-size: 0.88rem;
        }
        .demo-flow {
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 8px;
            background: rgba(2, 6, 23, 0.55);
            padding: 1rem 1.1rem;
        }
        .demo-flow h3 {
            margin-top: 0;
            color: #f8fafc;
        }
        .demo-flow li {
            margin-bottom: 0.35rem;
        }
        @media (max-width: 900px) {
            .takeaway-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str, kicker: str = "Digital asset behavior terminal") -> None:
    st.markdown(
        f"""
        <div class="research-kicker">{kicker}</div>
        <h1 class="research-title">{title}</h1>
        <div class="research-subtitle">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_context(title: str, bullets: Iterable[str]) -> None:
    with st.sidebar:
        st.markdown(f"### {title}")
        for bullet in bullets:
            st.caption(bullet)


def render_analyst_takeaway(
    what_happened: str,
    why_it_matters: str,
    monitor_next: str,
    caveat: str | None = "Observed relationships and short-window reactions are descriptive, not causal claims or trading advice.",
) -> None:
    caveat_html = f'<div class="takeaway-caveat">{caveat}</div>' if caveat else ""
    st.markdown(
        f"""
        <div class="takeaway">
          <h3>Analyst Takeaway</h3>
          <div class="takeaway-grid">
            <div>
              <div class="takeaway-label">What happened</div>
              <p>{what_happened}</p>
            </div>
            <div>
              <div class="takeaway-label">Why it matters</div>
              <p>{why_it_matters}</p>
            </div>
            <div>
              <div class="takeaway-label">What to monitor next</div>
              <p>{monitor_next}</p>
            </div>
          </div>
          {caveat_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_demo_flow() -> None:
    st.markdown(
        """
        <div class="demo-flow">
          <h3>How to demo this project in an interview</h3>
          <ol>
            <li><strong>Start here:</strong> show the cross-asset regime snapshot, drawdown, breadth, and sample-data disclosure.</li>
            <li><strong>Go to Strategy Insights:</strong> explain event impact, DeFi beta, and the non-causal interpretation.</li>
            <li><strong>Open Sentiment & Event Reaction:</strong> show why Fear & Greed is a confirmation signal, not a forward signal.</li>
            <li><strong>Close on limitations:</strong> point out free-tier on-chain constraints and the clean upgrade path.</li>
          </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )
