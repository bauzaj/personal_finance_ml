"""
Ingest Plaid transactions into Snowflake RAW schema.

Pulls transactions from Plaid (sandbox) and writes them to PERSONAL_FINANCE.RAW.PLAID_TRANSACTIONS
using an idempotent MERGE so re-runs don't create duplicates.
"""
import argparse
from plaid_client import PlaidClient
from snowflake_client import SnowflakeClient


def main(days_back: int = 90):
    print(f"Pulling last {days_back} days of transactions from Plaid...")
    plaid = PlaidClient()
    access_token = plaid.create_sandbox_access_token()
    transactions = plaid.get_transactions(access_token, days_back=days_back)
    print(f"Pulled {len(transactions)} transactions from Plaid")

    print("Writing to Snowflake...")
    with SnowflakeClient() as snow:
        merged = snow.insert_transactions(
            schema='RAW',
            table='PLAID_TRANSACTIONS',
            transactions=transactions
        )
        print(f"Merged {merged} rows into RAW.PLAID_TRANSACTIONS")

        # Verify the writes
        result = snow.execute("SELECT COUNT(*) FROM RAW.PLAID_TRANSACTIONS")
        print(f"Total rows in RAW.PLAID_TRANSACTIONS: {result[0][0]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=90, help='Days of transactions to pull')
    args = parser.parse_args()
    main(days_back=args.days)