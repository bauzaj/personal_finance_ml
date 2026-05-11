"""Unit tests for SnowflakeClient."""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import Config


@pytest.fixture
def fake_config(tmp_path):
    """Return a Config object with a real temp file as the private key path."""
    fake_key = tmp_path / "fake_key.p8"
    fake_key.write_bytes(b"fake_key_content")
    return Config(
        plaid_client_id='fake_client_id',
        plaid_secret='fake_secret',
        plaid_env='sandbox',
        snowflake_account='fake_account',
        snowflake_user='fake_user',
        snowflake_private_key_path=fake_key,
        snowflake_database='FAKE_DB',
        snowflake_warehouse='FAKE_WH',
        snowflake_role='FAKE_ROLE',
    )


@pytest.fixture
def snowflake_client(fake_config):
    """Return a SnowflakeClient with mocked connection internals."""
    from snowflake_client import SnowflakeClient
    client = SnowflakeClient(config=fake_config)
    return client


class TestSnowflakeClient:
    def test_init_stores_config(self, snowflake_client, fake_config):
        """SnowflakeClient stores the passed config."""
        assert snowflake_client.config is fake_config
        assert snowflake_client.conn is None

    @patch('snowflake_client.snowflake.connector.connect')
    @patch('snowflake_client.SnowflakeClient._load_private_key')
    def test_connect_uses_key_pair_auth(self, mock_load_key, mock_connect, snowflake_client):
        """connect() calls snowflake.connector.connect with private_key, not password."""
        mock_load_key.return_value = b'fake_der_key'
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        snowflake_client.connect()

        mock_connect.assert_called_once()
        call_kwargs = mock_connect.call_args.kwargs
        assert call_kwargs['account'] == 'fake_account'
        assert call_kwargs['user'] == 'fake_user'
        assert call_kwargs['private_key'] == b'fake_der_key'
        assert 'password' not in call_kwargs

    @patch('snowflake_client.snowflake.connector.connect')
    @patch('snowflake_client.SnowflakeClient._load_private_key')
    def test_connect_sets_session_context(self, mock_load_key, mock_connect, snowflake_client):
        """connect() runs USE ROLE / WAREHOUSE / DATABASE after auth."""
        mock_load_key.return_value = b'fake_der_key'
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        snowflake_client.connect()

        executed_sql = [call.args[0] for call in mock_cursor.execute.call_args_list]
        assert 'USE ROLE FAKE_ROLE' in executed_sql
        assert 'USE WAREHOUSE FAKE_WH' in executed_sql
        assert 'USE DATABASE FAKE_DB' in executed_sql

    def test_close_closes_connection(self, snowflake_client):
        """close() calls .close() on the underlying connection."""
        snowflake_client.conn = MagicMock()
        snowflake_client.close()
        snowflake_client.conn = MagicMock()  # reassign because close() sets to None
        # Test the actual close behavior
        conn_before = snowflake_client.conn
        snowflake_client.close()
        conn_before.close.assert_called_once()
        assert snowflake_client.conn is None

    def test_close_is_safe_when_no_connection(self, snowflake_client):
        """close() does nothing if conn is None — should not raise."""
        snowflake_client.conn = None
        snowflake_client.close()  # should not raise

    def test_insert_transactions_returns_zero_for_empty(self, snowflake_client):
        """Empty transactions list should return 0 and skip the cursor entirely."""
        snowflake_client.conn = MagicMock()
        result = snowflake_client.insert_transactions(
            schema='RAW',
            table='PLAID_TRANSACTIONS',
            transactions=[]
        )
        assert result == 0

    def test_insert_transactions_merges_each_row(self, snowflake_client):
        """Each transaction should result in one MERGE execution."""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        snowflake_client.conn = mock_conn

        transactions = [
            {
                'transaction_id': 'tx_1',
                'account_id': 'acc_1',
                'date': '2026-01-01',
                'amount': 10.0,
            },
            {
                'transaction_id': 'tx_2',
                'account_id': 'acc_1',
                'date': '2026-01-02',
                'amount': 20.0,
            },
        ]

        count = snowflake_client.insert_transactions(
            schema='RAW',
            table='PLAID_TRANSACTIONS',
            transactions=transactions
        )

        assert count == 2
        assert mock_cursor.execute.call_count == 2
        mock_conn.commit.assert_called_once()

    def test_insert_transactions_handles_missing_optional_fields(self, snowflake_client):
        """Transactions missing optional fields (item_id, pfc) should still merge cleanly."""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        snowflake_client.conn = mock_conn

        # Minimal transaction — only required fields
        transactions = [{
            'transaction_id': 'tx_1',
            'account_id': 'acc_1',
            'date': '2026-01-01',
            'amount': 10.0,
        }]

        count = snowflake_client.insert_transactions(
            schema='RAW',
            table='PLAID_TRANSACTIONS',
            transactions=transactions
        )

        assert count == 1
        # Verify the params passed had None for missing fields
        params = mock_cursor.execute.call_args.args[1]
        assert params['item_id'] is None
        assert params['pfc_primary'] is None

    def test_context_manager_opens_and_closes(self, snowflake_client):
        """Using SnowflakeClient as a context manager opens on enter, closes on exit."""
        with patch.object(snowflake_client, 'connect') as mock_connect, \
             patch.object(snowflake_client, 'close') as mock_close:
            with snowflake_client:
                pass
            mock_connect.assert_called_once()
            mock_close.assert_called_once()

    def test_execute_returns_query_results(self, snowflake_client):
        """execute() returns the cursor's fetchall() result."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [('row1',), ('row2',)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        snowflake_client.conn = mock_conn

        result = snowflake_client.execute("SELECT * FROM table")

        assert result == [('row1',), ('row2',)]
        mock_cursor.execute.assert_called_once_with("SELECT * FROM table", {})