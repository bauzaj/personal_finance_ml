# Personal Finance ML Dashboard

## Project Overview
Personal finance dashboard that ingests transaction data via the Plaid API, applies ML to categorize transactions, detect subscriptions, and forecast spending.

## Goal
Multi-week learning project to deepen ML/AI application skills while building something genuinely useful for personal finance management. Emphasis on enterprise-realistic patterns: API integration, secure credential handling, cloud warehousing.

## Stack
- **Language**: Python 3.11
- **API**: Plaid (sandbox mode initially)
- **ML**: scikit-learn (categorization), Prophet or ARIMA (forecasting)
- **Warehouse**: Snowflake (PERSONAL_FINANCE database)
- **Dashboard**: Streamlit
- **Data Processing**: Pandas
- **Local Development**: macOS

## Data Sources
Plaid API — provides transaction history, account balances, and category metadata. Sandbox mode used during development with synthetic test institutions. Production mode (optional later) connects to real accounts via Plaid Link.

## Architecture
Plaid API → Python ingest layer → Snowflake RAW → ML models → Snowflake ANALYTICS → Streamlit dashboard

## Snowflake Schema (planned)
- **PERSONAL_FINANCE** database
  - **RAW** schema — raw Plaid API responses per account
  - **STAGING** schema — normalized transactions, common schema
  - **ANALYTICS** schema — categorized transactions, subscriptions, forecasts

## Project Phases
1. **Phase 1**: Plaid sandbox integration — auth flow, transaction pull, RAW schema load
2. **Phase 2**: Auto-categorization model — multi-class classifier
3. **Phase 3**: Subscription detection — recurring charge identification
4. **Phase 4**: Spending forecast — time series model
5. **Phase 5**: Savings rate tracker — goals and progress
6. **Phase 6**: Dashboard polish — combined UI

## Project Structure

    personal_finance_ml/
    ├── src/                  # Python code
    ├── data/
    │   ├── raw/              # API response cache (gitignored)
    │   └── processed/        # Cleaned data
    ├── models/               # Trained model artifacts
    ├── notebooks/            # Jupyter exploration
    ├── tests/                # Unit tests
    ├── requirements.txt
    ├── .env.example
    └── CLAUDE.md

## Environment Variables (see .env.example)
- `PLAID_CLIENT_ID`
- `PLAID_SECRET`
- `PLAID_ENV` — sandbox / development / production
- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER`
- `SNOWFLAKE_PASSWORD`
- `SNOWFLAKE_DATABASE=PERSONAL_FINANCE`
- `SNOWFLAKE_WAREHOUSE`

## Security Principles

### API Credentials
- **Plaid credentials in `.env` only** — never hardcoded, never committed
- **Sandbox mode by default** — production mode requires explicit opt-in via `PLAID_ENV` variable
- **Access tokens encrypted at rest** when stored in Snowflake (use Snowflake's encryption features)
- **No long-lived access tokens in logs** — sanitize all log output

### Data Handling
- **API responses cached locally only** — `data/raw/` gitignored entirely
- **No personal financial data committed** — all real transaction data stays local or in Snowflake
- **Sample/synthetic data only in version control** — Plaid sandbox provides realistic but fake data
- **Local ML processing** — models trained on local or warehoused data, no data sent to external ML services

### Snowflake Credentials
- **Credentials in `.env` only** — never hardcoded
- Use Snowflake key-pair authentication over passwords where possible
- Snowflake user scoped to `PERSONAL_FINANCE` database with minimum required permissions
- Network policies restrict Snowflake access to known IPs where feasible

### Dependencies
- Pin all dependencies in `requirements.txt` to prevent supply chain risks
- Periodically audit with `pip-audit`
- No unnecessary packages — minimal attack surface

### Repository Hygiene
- `.gitignore` covers: `data/raw/`, `.env`, `*.csv`, `models/*.joblib`, `__pycache__/`, `.ipynb_checkpoints/`, `*.log`
- No screenshots or notebook outputs containing real financial data
- Pre-commit hook to prevent accidental secret commits (consider `gitleaks`)

### Plaid-Specific Security
- **Never log access tokens or item IDs** — these grant API access to accounts
- **Use Plaid Link for token exchange** — never handle raw bank credentials
- **Rotate access tokens** if compromise suspected via Plaid dashboard
- **Webhook signatures verified** if implementing webhook handlers later

## Current Status
Project scaffolded. Setting up Snowflake schema and Plaid sandbox integration next.