"""
Snowflake client module.

Centralizes Snowflake connection setup and provides reusable methods for
common operations (executing queries, bulk inserts).

Uses key-pair authentication for programmatic access (production pattern).
"""

import json
from typing import List, Dict
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from config import Config
from logger import get_logger

log = get_logger(__name__)


class SnowflakeClient:
    """Wrapper around the Snowflake Python connector with helper methods."""

    def __init__(self, config: Config = None):
        self.config = config or Config.from_env()
        self.conn = None

    def _load_private_key(self) -> bytes:
        """Load and serialize the private key for Snowflake authentication."""
        with open(self.config.snowflake_private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )

        return private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def connect(self):
        """Open a connection to Snowflake using key-pair authentication."""
        self.conn = snowflake.connector.connect(
            account=self.config.snowflake_account,
            user=self.config.snowflake_user,
            private_key=self._load_private_key(),
            role=self.config.snowflake_role,
        )
        cursor = self.conn.cursor()
        try:
            cursor.execute(f"USE ROLE {self.config.snowflake_role}")
            cursor.execute(f"USE WAREHOUSE {self.config.snowflake_warehouse}")
            cursor.execute(f"USE DATABASE {self.config.snowflake_database}")
        finally:
            cursor.close()
        return self.conn

    def close(self):
        """Close the connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def execute(self, sql: str, params: dict = None):
        """Execute a SQL statement and return all rows."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, params or {})
            return cursor.fetchall()
        finally:
            cursor.close()

    def insert_transactions(
        self, schema: str, table: str, transactions: List[Dict]
    ) -> int:
        """
        Insert (merge) Plaid transactions into the target table.
        Idempotent — uses MERGE so re-runs don't create duplicates.
        Returns count of rows merged.
        """
        if not transactions:
            return 0

        cursor = self.conn.cursor()
        try:
            merge_sql = f"""
            MERGE INTO {schema}.{table} t
            USING (
                SELECT
                    %(transaction_id)s    AS transaction_id,
                    %(account_id)s        AS account_id,
                    %(item_id)s           AS item_id,
                    %(transaction_date)s  AS transaction_date,
                    %(authorized_date)s   AS authorized_date,
                    %(amount)s            AS amount,
                    %(iso_currency_code)s AS iso_currency_code,
                    %(merchant_name)s     AS merchant_name,
                    %(name)s              AS name,
                    %(pfc_primary)s       AS pfc_primary,
                    %(pfc_detailed)s      AS pfc_detailed,
                    %(payment_channel)s   AS payment_channel,
                    %(pending)s           AS pending,
                    PARSE_JSON(%(raw_payload)s) AS raw_payload
            ) s
            ON t.transaction_id = s.transaction_id
            WHEN MATCHED THEN UPDATE SET
                account_id = s.account_id,
                item_id = s.item_id,
                transaction_date = s.transaction_date,
                authorized_date = s.authorized_date,
                amount = s.amount,
                iso_currency_code = s.iso_currency_code,
                merchant_name = s.merchant_name,
                name = s.name,
                personal_finance_category_primary = s.pfc_primary,
                personal_finance_category_detailed = s.pfc_detailed,
                payment_channel = s.payment_channel,
                pending = s.pending,
                raw_payload = s.raw_payload,
                ingested_at = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT (
                transaction_id, account_id, item_id,
                transaction_date, authorized_date,
                amount, iso_currency_code, merchant_name, name,
                personal_finance_category_primary, personal_finance_category_detailed,
                payment_channel, pending, raw_payload
            ) VALUES (
                s.transaction_id, s.account_id, s.item_id,
                s.transaction_date, s.authorized_date,
                s.amount, s.iso_currency_code, s.merchant_name, s.name,
                s.pfc_primary, s.pfc_detailed,
                s.payment_channel, s.pending, s.raw_payload
            )
            """

            count = 0
            for tx in transactions:
                pfc = tx.get("personal_finance_category") or {}
                params = {
                    "transaction_id": tx["transaction_id"],
                    "account_id": tx["account_id"],
                    "item_id": tx.get("item_id"),
                    "transaction_date": tx["date"],
                    "authorized_date": tx.get("authorized_date"),
                    "amount": tx["amount"],
                    "iso_currency_code": tx.get("iso_currency_code"),
                    "merchant_name": tx.get("merchant_name"),
                    "name": tx.get("name"),
                    "pfc_primary": pfc.get("primary"),
                    "pfc_detailed": pfc.get("detailed"),
                    "payment_channel": tx.get("payment_channel"),
                    "pending": tx.get("pending"),
                    "raw_payload": json.dumps(tx, default=str),
                }
                cursor.execute(merge_sql, params)
                count += 1

            self.conn.commit()
            return count
        finally:
            cursor.close()
