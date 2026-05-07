"""
Ingest Plaid transactions from multiple sandbox institutions into Snowflake RAW schema.
"""
import argparse
from logger import get_logger
from plaid_client import PlaidClient
from snowflake_client import SnowflakeClient

log = get_logger(__name__)


def main(days_back: int = 90):
    log.info(f"Pulling last {days_back} days of transactions from Plaid (multiple institutions)")
    plaid = PlaidClient()

    tokens = plaid.create_multiple_sandbox_tokens()
    log.info(f"Got tokens for {len(tokens)} institutions")

    all_transactions = []
    for t in tokens:
        log.info(f"Fetching from {t['institution_id']}")
        transactions = plaid.get_transactions(t['access_token'], days_back=days_back)
        for tx in transactions:
            tx['_institution_id'] = t['institution_id']
        all_transactions.extend(transactions)
        log.info(f"  Pulled {len(transactions)} transactions from {t['institution_id']}")

    log.info(f"Total: {len(all_transactions)} transactions across {len(tokens)} institutions")

    log.info("Writing to Snowflake")
    with SnowflakeClient() as snow:
        merged = snow.insert_transactions(
            schema='RAW',
            table='PLAID_TRANSACTIONS',
            transactions=all_transactions
        )
        log.info(f"Merged {merged} rows into RAW.PLAID_TRANSACTIONS")

        result = snow.execute("SELECT COUNT(*) FROM RAW.PLAID_TRANSACTIONS")
        log.info(f"Total rows in RAW.PLAID_TRANSACTIONS: {result[0][0]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=90, help='Days of transactions to pull')
    args = parser.parse_args()
    main(days_back=args.days)