"""Quick smoke test for the PlaidClient module."""
from plaid_client import PlaidClient


def main():
    client = PlaidClient()
    print(f"Initialized PlaidClient in {client.env} mode")

    access_token = client.create_sandbox_access_token()
    print(f"Got access token: {access_token[:20]}...")

    transactions = client.get_transactions(access_token, days_back=90)
    print(f"\nPulled {len(transactions)} transactions (showing first 10):\n")

    for tx in transactions[:10]:
        category = tx.get('personal_finance_category', {}).get('primary', 'UNCATEGORIZED')
        print(f"{tx['date']} | ${tx['amount']:>8.2f} | {tx['name'][:40]:<40} | {category}")


if __name__ == "__main__":
    main()