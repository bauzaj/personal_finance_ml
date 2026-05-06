# Personal Finance ML Dashboard

A personal finance dashboard that ingests transaction data via the Plaid API, applies machine learning to categorize transactions, detect subscriptions, and forecast spending. Built as a learning project to deepen ML/AI application skills while building something genuinely useful.

---

## Architecture

```
Plaid API → Python Ingest Layer → Snowflake RAW
                                       ↓
                                 Snowflake STAGING (normalized)
                                       ↓
                                 ML Models (categorization, forecasting, subscription detection)
                                       ↓
                                 Snowflake ANALYTICS
                                       ↓
                                 Streamlit Dashboard
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data Source | Plaid API (sandbox mode) |
| Warehouse | Snowflake |
| ML | scikit-learn, Prophet |
| Dashboard | Streamlit |
| Data Processing | Pandas |
| Language | Python 3.11 |

---

## Project Phases

1. **Phase 1**: Plaid sandbox integration — auth flow, transaction pull, RAW schema load
2. **Phase 2**: Auto-categorization model — multi-class classifier
3. **Phase 3**: Subscription detection — recurring charge identification
4. **Phase 4**: Spending forecast — time series model
5. **Phase 5**: Savings rate tracker — goals and progress visualization
6. **Phase 6**: Dashboard polish — combined Streamlit UI

Currently working on **Phase 1**.

---

## Project Structure

    personal_finance_ml/
    ├── src/                  # Python source code
    ├── data/
    │   ├── raw/              # API response cache (gitignored)
    │   └── processed/        # Cleaned data (gitignored)
    ├── models/               # Trained model artifacts (gitignored)
    ├── notebooks/            # Jupyter exploration
    ├── snowflake/            # Snowflake DDL scripts
    ├── tests/                # Unit tests
    ├── requirements.txt
    ├── .env.example
    └── CLAUDE.md             # Claude Code project context

---

## Getting Started

### Prerequisites
- Python 3.11+
- Snowflake account
- Plaid developer account (sandbox mode is free)

### 1. Clone and set up environment

```bash
git clone https://github.com/bauzaj/personal_finance_ml.git
cd personal_finance_ml
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
# Fill in Plaid and Snowflake credentials in .env
```

### 3. Set up Snowflake

Run the DDL script in `snowflake/setup.sql` against your Snowflake account. Replace `<YOUR_SNOWFLAKE_USERNAME>` with your actual username before running.

### 4. Verify Plaid connection

```bash
python src/test_plaid_connection.py
python src/test_plaid_transactions.py
```

You should see synthetic transactions printed if everything is configured correctly.

---

## Snowflake Schema

- **PERSONAL_FINANCE.RAW** — raw Plaid API responses
- **PERSONAL_FINANCE.STAGING** — normalized transactions, common schema
- **PERSONAL_FINANCE.ANALYTICS** — ML outputs: categorized transactions, subscriptions, forecasts

Access controlled via `TRANSFORMER` role. Warehouse: `FINANCE_WH` (XSMALL, auto-suspend 60s).

---

## Security Principles

This project handles personal financial data and follows security best practices throughout.

### API Credentials
- **Plaid credentials in `.env` only** — never hardcoded, never committed
- **Sandbox mode by default** — production access requires explicit opt-in
- **No long-lived access tokens in logs** — sanitize all log output

### Data Handling
- **API responses cached locally only** — `data/raw/` is gitignored entirely
- **No personal financial data in version control** — only synthetic Plaid sandbox data is used during development
- **Local ML processing** — models trained on local or warehoused data, never sent to external ML services

### Snowflake Credentials
- **Credentials in `.env` only** — never hardcoded
- Snowflake user scoped to `PERSONAL_FINANCE` database with minimum required permissions
- Pinned dependency versions in `requirements.txt` for reproducibility

### Repository Hygiene
- `.gitignore` covers: `data/raw/`, `data/processed/`, `.env`, `*.csv`, `models/*.joblib`, `__pycache__/`, `.ipynb_checkpoints/`, `*.log`
- Pre-commit hook recommended for secret detection (`gitleaks`)

---

## Why Plaid (Sandbox First)?

Plaid is the industry-standard API for personal finance applications — used by Venmo, Robinhood, and most fintech apps. Building against it provides realistic enterprise-style API integration experience, including:

- OAuth-style token exchange flow
- Asynchronous product readiness handling
- Webhook-driven update patterns

Sandbox mode provides synthetic but realistic transaction data, allowing the entire pipeline to be developed without ever touching real bank accounts.

---

## Background

Multi-week portfolio project focused on end-to-end ML application development. Builds on streaming pipeline experience (see [fraud_detection](https://github.com/bauzaj/fraud_detection)) by adding batch ingestion, multi-class ML, time series forecasting, and a complete cloud data warehouse layer.