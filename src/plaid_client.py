"""
Plaid API client module.

Centralizes Plaid connection setup and provides reusable methods for
common operations (creating sandbox tokens, exchanging tokens, fetching transactions).
"""
import os
import time
from datetime import date, timedelta
from typing import List, Dict
from dotenv import load_dotenv
import plaid
from plaid.api import plaid_api
from plaid.exceptions import ApiException
from plaid.model.products import Products
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

load_dotenv()


class PlaidClient:
    """Wrapper around the Plaid API client with helper methods for common workflows."""

    # Plaid environment mapping
    ENV_MAP = {
        'sandbox': plaid.Environment.Sandbox,
        'production': plaid.Environment.Production,
    }

    # Default sandbox test institution (First Platypus Bank)
    DEFAULT_SANDBOX_INSTITUTION = 'ins_109508'

    def __init__(self):
        self.client_id = os.getenv('PLAID_CLIENT_ID')
        self.secret = os.getenv('PLAID_SECRET')
        self.env = os.getenv('PLAID_ENV', 'sandbox')

        if not self.client_id or not self.secret:
            raise ValueError("PLAID_CLIENT_ID and PLAID_SECRET must be set in .env")

        if self.env not in self.ENV_MAP:
            raise ValueError(f"PLAID_ENV must be one of {list(self.ENV_MAP.keys())}")

        configuration = plaid.Configuration(
            host=self.ENV_MAP[self.env],
            api_key={'clientId': self.client_id, 'secret': self.secret}
        )
        self.client = plaid_api.PlaidApi(plaid.ApiClient(configuration))

    def create_sandbox_access_token(self, institution_id: str = None) -> str:
        """Create a sandbox public token and exchange it for an access token."""
        if self.env != 'sandbox':
            raise RuntimeError("create_sandbox_access_token only valid in sandbox environment")

        institution_id = institution_id or self.DEFAULT_SANDBOX_INSTITUTION

        public_token_response = self.client.sandbox_public_token_create(
            SandboxPublicTokenCreateRequest(
                institution_id=institution_id,
                initial_products=[Products('transactions')]
            )
        )
        access_token = self.client.item_public_token_exchange(
            ItemPublicTokenExchangeRequest(public_token=public_token_response['public_token'])
        )['access_token']

        return access_token

    def get_transactions(
        self,
        access_token: str,
        days_back: int = 90,
        max_retries: int = 10,
        retry_delay: int = 2
    ) -> List[Dict]:
        """
        Fetch transactions for the past N days, with retry logic for PRODUCT_NOT_READY.

        Returns a list of transaction dicts.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        all_transactions = []
        offset = 0
        page_size = 500

        while True:
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date,
                end_date=end_date,
                options=TransactionsGetRequestOptions(count=page_size, offset=offset)
            )

            response = None
            for attempt in range(max_retries):
                try:
                    response = self.client.transactions_get(request)
                    break
                except ApiException as e:
                    if 'PRODUCT_NOT_READY' in str(e) and attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    else:
                        raise

            transactions = response['transactions']
            all_transactions.extend(transactions)

            # Stop when we've fetched all available transactions
            if len(all_transactions) >= response['total_transactions']:
                break

            offset += page_size

        return all_transactions