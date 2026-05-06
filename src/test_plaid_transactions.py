import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import plaid
from plaid.api import plaid_api
from plaid.model.products import Products
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

load_dotenv()

configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': os.getenv('PLAID_CLIENT_ID'),
        'secret': os.getenv('PLAID_SECRET'),
    }
)
client = plaid_api.PlaidApi(plaid.ApiClient(configuration))

# Create a fresh sandbox token + access token
public_token_response = client.sandbox_public_token_create(
    SandboxPublicTokenCreateRequest(
        institution_id='ins_109508',
        initial_products=[Products('transactions')]
    )
)
access_token = client.item_public_token_exchange(
    ItemPublicTokenExchangeRequest(public_token=public_token_response['public_token'])
)['access_token']

print("Waiting for transactions to provision...")
time.sleep(3)

# Pull last 90 days of transactions
end_date = datetime.now().date()
start_date = end_date - timedelta(days=90)

request = TransactionsGetRequest(
    access_token=access_token,
    start_date=start_date,
    end_date=end_date,
    options=TransactionsGetRequestOptions(count=10)
)
response = client.transactions_get(request)

transactions = response['transactions']
print(f"Pulled {len(transactions)} transactions (showing first 10):\n")

for tx in transactions:
    print(f"{tx['date']} | ${tx['amount']:>8.2f} | {tx['name'][:40]:<40} | {tx.get('personal_finance_category', {}).get('primary', 'UNCATEGORIZED')}")