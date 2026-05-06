import os
from dotenv import load_dotenv
import plaid
from plaid.api import plaid_api
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

load_dotenv()

configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': os.getenv('PLAID_CLIENT_ID'),
        'secret': os.getenv('PLAID_SECRET'),
    }
)
api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

# Step 1: Create a sandbox public token (simulates a user logging into a bank)
public_token_request = SandboxPublicTokenCreateRequest(
    institution_id='ins_109508',  # First Platypus Bank — Plaid's test institution
    initial_products=[Products('transactions')]
)
public_token_response = client.sandbox_public_token_create(public_token_request)
public_token = public_token_response['public_token']
print(f"Got public token: {public_token[:20]}...")

# Step 2: Exchange the public token for an access token
exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
exchange_response = client.item_public_token_exchange(exchange_request)
access_token = exchange_response['access_token']
print(f"Got access token: {access_token[:20]}...")
print("\nPlaid connection successful!")