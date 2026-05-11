"""Unit tests for PlaidClient."""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Make src importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from plaid.exceptions import ApiException
from config import Config


@pytest.fixture
def fake_config():
    """Return a Config object with fake credentials for testing."""
    return Config(
        plaid_client_id='fake_client_id',
        plaid_secret='fake_secret',
        plaid_env='sandbox',
        snowflake_account='fake_account',
        snowflake_user='fake_user',
        snowflake_private_key_path='/tmp/fake_key.p8',
        snowflake_database='FAKE_DB',
        snowflake_warehouse='FAKE_WH',
        snowflake_role='FAKE_ROLE',
    )


@pytest.fixture
def plaid_client(fake_config):
    """Return a PlaidClient with a mocked underlying API client."""
    from plaid_client import PlaidClient
    client = PlaidClient(config=fake_config)
    client.client = MagicMock()
    return client


class TestPlaidClient:
    def test_init_requires_valid_env(self, fake_config):
        """Config with invalid env should raise at config level."""
        from plaid_client import PlaidClient
        fake_config.plaid_env = 'invalid'
        with pytest.raises(KeyError):
            PlaidClient(config=fake_config)

    def test_create_sandbox_access_token_returns_token(self, plaid_client):
        """create_sandbox_access_token exchanges public token for access token."""
        plaid_client.client.sandbox_public_token_create.return_value = {
            'public_token': 'public-sandbox-fake'
        }
        plaid_client.client.item_public_token_exchange.return_value = {
            'access_token': 'access-sandbox-fake'
        }

        token = plaid_client.create_sandbox_access_token()

        assert token == 'access-sandbox-fake'
        plaid_client.client.sandbox_public_token_create.assert_called_once()
        plaid_client.client.item_public_token_exchange.assert_called_once()

    def test_create_sandbox_token_rejects_production_env(self, fake_config):
        """Calling create_sandbox_access_token in production env should raise."""
        from plaid_client import PlaidClient
        fake_config.plaid_env = 'production'
        client = PlaidClient(config=fake_config)
        with pytest.raises(RuntimeError, match='sandbox'):
            client.create_sandbox_access_token()

    def test_create_multiple_sandbox_tokens_returns_all_successful(self, plaid_client):
        """create_multiple_sandbox_tokens returns one entry per successful institution."""
        plaid_client.client.sandbox_public_token_create.return_value = {
            'public_token': 'public-sandbox-fake'
        }
        plaid_client.client.item_public_token_exchange.return_value = {
            'access_token': 'access-sandbox-fake'
        }

        tokens = plaid_client.create_multiple_sandbox_tokens(
            institutions=['ins_109508', 'ins_109509']
        )

        assert len(tokens) == 2
        assert tokens[0]['institution_id'] == 'ins_109508'
        assert tokens[0]['access_token'] == 'access-sandbox-fake'

    def test_create_multiple_sandbox_tokens_skips_failures(self, plaid_client):
        """A failed institution shouldn't stop the rest from succeeding."""
        # First call fails, second succeeds
        plaid_client.client.sandbox_public_token_create.side_effect = [
            ApiException(status=400, reason='Bad institution'),
            {'public_token': 'public-sandbox-fake'},
        ]
        plaid_client.client.item_public_token_exchange.return_value = {
            'access_token': 'access-sandbox-fake'
        }

        tokens = plaid_client.create_multiple_sandbox_tokens(
            institutions=['ins_bad', 'ins_good']
        )

        assert len(tokens) == 1
        assert tokens[0]['institution_id'] == 'ins_good'

    def test_get_transactions_returns_list(self, plaid_client):
        """get_transactions returns a flat list of transactions."""
        fake_response = {
            'transactions': [
                {'transaction_id': 'tx_1', 'amount': 10.0, 'date': '2026-01-01'},
                {'transaction_id': 'tx_2', 'amount': 20.0, 'date': '2026-01-02'},
            ],
            'total_transactions': 2,
        }
        plaid_client.client.transactions_get.return_value = fake_response

        result = plaid_client.get_transactions(access_token='fake_token')

        assert len(result) == 2
        assert result[0]['transaction_id'] == 'tx_1'

    def test_get_transactions_handles_pagination(self, plaid_client):
        """get_transactions paginates when there are more than 500 transactions."""
        # Simulate 750 total transactions across 2 pages
        page1 = {'transactions': [{'transaction_id': f'tx_{i}'} for i in range(500)],
                 'total_transactions': 750}
        page2 = {'transactions': [{'transaction_id': f'tx_{i}'} for i in range(500, 750)],
                 'total_transactions': 750}
        plaid_client.client.transactions_get.side_effect = [page1, page2]

        result = plaid_client.get_transactions(access_token='fake_token')

        assert len(result) == 750
        assert plaid_client.client.transactions_get.call_count == 2

    def test_get_transactions_retries_on_product_not_ready(self, plaid_client):
        """PRODUCT_NOT_READY should trigger retry, eventually succeeding."""
        not_ready = ApiException(status=400, reason='Bad Request')
        not_ready.body = '{"error_code": "PRODUCT_NOT_READY"}'

        success_response = {
            'transactions': [{'transaction_id': 'tx_1'}],
            'total_transactions': 1,
        }
        plaid_client.client.transactions_get.side_effect = [not_ready, success_response]

        with patch('plaid_client.time.sleep'):  # skip the actual delay
            result = plaid_client.get_transactions(
                access_token='fake_token',
                retry_delay=0,
            )

        assert len(result) == 1
        assert plaid_client.client.transactions_get.call_count == 2