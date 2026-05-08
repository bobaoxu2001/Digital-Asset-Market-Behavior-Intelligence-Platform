PY ?= python3.11

.PHONY: ingest features analysis test dashboard demo screenshots all clean

ingest:
	$(PY) -m src.ingest.market_data
	$(PY) -m src.ingest.sentiment_fng
	$(PY) -m src.ingest.defi_llama
	$(PY) -m src.ingest.onchain_blockchain
	$(PY) -m src.ingest.onchain_etherscan
	$(PY) -m src.ingest.macro_fred
	$(PY) -m src.ingest.events

features:
	$(PY) -m src.features.build_features

analysis:
	$(PY) -m src.analysis.event_study
	$(PY) -m src.analysis.lead_lag
	$(PY) -m src.analysis.regime_conditional
	$(PY) -m src.analysis.behavior_summary

test:
	$(PY) -m pytest tests/ -v

dashboard:
	$(PY) -m streamlit run dashboard/app.py

# Demo mode: copy bundled small parquet samples into data/processed and launch
# the dashboard. No API keys required, no ingestion run.
demo:
	mkdir -p data/processed
	cp data/sample/features_sample.parquet           data/processed/features.parquet
	cp data/sample/event_study_sample.parquet        data/processed/event_study.parquet
	cp data/sample/lead_lag_sample.parquet           data/processed/lead_lag.parquet
	cp data/sample/regime_conditional_sample.parquet data/processed/regime_conditional.parquet
	@echo "Sample data staged. Launching dashboard..."
	$(PY) -m streamlit run dashboard/app.py

# Regenerate the README's dashboard preview PNGs from data/processed/
screenshots:
	$(PY) scripts/generate_screenshots.py

all: ingest features analysis test
	@echo "Pipeline complete. Run 'make dashboard' to launch Streamlit."

clean:
	rm -rf data/raw/* data/processed/*
	find . -type d -name __pycache__ -exec rm -rf {} +
