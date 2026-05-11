"""
Integration tests for the full Plaid → Snowflake pipeline.

These tests actually hit the Plaid sandbox API and a test Snowflake schema.
They are slower than unit tests and require working credentials.

Run only with: pytest tests/test_integration.py -v -m integration
Or skip with:  pytest tests/ -v -m "not integration"
"""

import os
import sys
import pytest
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import Config
from plaid_client import PlaidClient
from snowflake_client import SnowflakeClient


# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def config():
    """Real config loaded from .env (requires valid credentials)."""
    return Config.from_env()


@pytest.fixture(scope="module")
def plaid_client(config):
    return PlaidClient(config=config)


@pytest.fixture
def snowflake_client(config):
    """Yield a connected SnowflakeClient and ensure cleanup."""
    with SnowflakeClient(config=config) as client:
        yield client


@pytest.fixture
def test_run_id():
    """Unique ID for this test run so transactions don't collide across runs."""
    return f"it_{uuid.uuid4().hex[:4]}"  # was itest_xxxxxxxx, now it_xxxx


def test_plaid_can_create_sandbox_token(plaid_client):
    """We can actually create a sandbox access token from Plaid."""
    token = plaid_client.create_sandbox_access_token()
    assert token.startswith("access-sandbox-")


def test_plaid_can_fetch_transactions(plaid_client):
    """We can pull real (synthetic) transactions from Plaid sandbox."""
    token = plaid_client.create_sandbox_access_token()
    transactions = plaid_client.get_transactions(token, days_back=30)
    assert isinstance(transactions, list)
    assert len(transactions) > 0

    # Verify expected structure
    tx = transactions[0]
    assert "transaction_id" in tx
    assert "amount" in tx
    assert "date" in tx


def test_snowflake_can_connect(snowflake_client):
    """We can connect to Snowflake and run a basic query."""
    result = snowflake_client.execute("SELECT CURRENT_USER()")
    assert result[0][0] is not None


def test_snowflake_test_schema_exists(snowflake_client):
    """The RAW_TEST schema must exist before integration tests can run."""
    result = snowflake_client.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.SCHEMATA
        WHERE SCHEMA_NAME = 'RAW_TEST'
    """
    )
    assert result[0][0] == 1


def test_full_pipeline_end_to_end(plaid_client, snowflake_client, test_run_id):
    """
    Full pipeline: pull from Plaid → write to RAW_TEST.PLAID_TRANSACTIONS → verify rows landed.
    Cleans up after itself.
    """
    # 1. Pull transactions from Plaid
    token = plaid_client.create_sandbox_access_token()
    transactions = plaid_client.get_transactions(token, days_back=30)
    assert len(transactions) > 0

    # 2. Tag each transaction with our test run ID so we can clean up later
    for tx in transactions:
        tx["_test_run_id"] = test_run_id
        # Override transaction_id to avoid collisions with real ingestion data
        tx["transaction_id"] = f"{test_run_id}_{tx['transaction_id']}"

    # 3. Insert into test schema
    merged = snowflake_client.insert_transactions(
        schema="RAW_TEST", table="PLAID_TRANSACTIONS", transactions=transactions
    )
    assert merged == len(transactions)

    # 4. Verify rows landed correctly
    result = snowflake_client.execute(
        f"""
        SELECT COUNT(*)
        FROM RAW_TEST.PLAID_TRANSACTIONS
        WHERE TRANSACTION_ID LIKE '{test_run_id}_%'
    """
    )
    assert result[0][0] == len(transactions)

    # 5. Verify non-null critical fields
    result = snowflake_client.execute(
        f"""
        SELECT COUNT(*)
        FROM RAW_TEST.PLAID_TRANSACTIONS
        WHERE TRANSACTION_ID LIKE '{test_run_id}_%'
          AND (ACCOUNT_ID IS NULL OR TRANSACTION_DATE IS NULL OR AMOUNT IS NULL)
    """
    )
    assert result[0][0] == 0, "Found rows with NULL critical fields"

    # 6. Cleanup — delete the test rows
    snowflake_client.execute(
        f"""
        DELETE FROM RAW_TEST.PLAID_TRANSACTIONS
        WHERE TRANSACTION_ID LIKE '{test_run_id}_%'
    """
    )
