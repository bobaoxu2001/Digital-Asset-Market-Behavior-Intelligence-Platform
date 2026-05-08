# Deployment Guide

This document describes how to deploy the dashboard to Streamlit Community Cloud and how to operate the platform in local, demo, and production modes.

---

## Local Modes

### Full mode

Runs the full ingestion pipeline, builds features and analysis tables, and launches the dashboard from live processed data.

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill COINGECKO_API_KEY, ETHERSCAN_API_KEY, FRED_API_KEY in .env
make ingest && make features && make analysis
make dashboard
```

### Demo mode

Copies a small bundled sample of parquet files into `data/processed/` and launches the dashboard. Requires no API keys and no network access.

```bash
make demo
```

This is the recommended path for a quick walkthrough or for verifying that the project runs end-to-end on a fresh machine.

---

## Streamlit Community Cloud Deployment

The dashboard is structured so that no code changes are required to deploy it on Streamlit Community Cloud.

### Steps

1. Push the repository to GitHub (already done at `https://github.com/bobaoxu2001/Digital-Asset-Market-Behavior-Intelligence-Platform`).
2. In Streamlit Community Cloud, click **New app** and select the repository and the `main` branch.
3. Set the **Main file path** to:
   ```
   dashboard/app.py
   ```
4. Set the **Python version** to `3.11`.
5. Open the app's **Secrets** management panel and add:
   ```toml
   COINGECKO_API_KEY = "your-key"
   ETHERSCAN_API_KEY = "your-key"
   FRED_API_KEY      = "your-key"
   ```
   The application reads these via `python-dotenv` plus `os.getenv`. Streamlit Cloud injects secrets as environment variables, so no code changes are needed.
6. Click **Deploy**.

### Provisioning processed data on the deployed instance

Streamlit Cloud does not run `make ingest` automatically. There are three operational options, listed in order of preference:

- **Bundled sample mode (recommended for demos):** the `data/sample/*.parquet` files are tracked in the repo. Add a startup hook in `dashboard/app.py` (or a small `prestart.py`) that copies the sample files to `data/processed/` if no processed data exists. The repository already includes a `make demo` target that performs this copy locally; the same logic can be run on Cloud start.
- **Scheduled refresh:** add a GitHub Action that runs the ingestion pipeline on a cron schedule, commits the small daily processed parquets to a separate `data-cache` branch, and have the deployed app pull from that branch.
- **External storage:** push processed parquet to S3 / GCS and have the dashboard read from object storage at startup. Add the credentials as additional Streamlit secrets.

### Security

- `.env` is local only. It is listed in `.gitignore` and must never be committed.
- API keys live exclusively in `.env` (local) or Streamlit secrets (cloud). They are never logged. The HTTP cache layer redacts query parameters that look like keys before logging.
- The CI workflow includes a guard step that fails the build if `.env` is ever committed or if known key fragments leak into tracked files.

---

## Running the dashboard headlessly

For containerized deployments or self-hosted servers:

```bash
streamlit run dashboard/app.py \
  --server.headless true \
  --server.port 8501 \
  --server.address 0.0.0.0
```

The dashboard reads only from `data/processed/*.parquet` at runtime; it never calls APIs live. This makes it safe to expose behind a reverse proxy without giving the dashboard process outbound network access.
