"""
Plaid API client module.

Centralizes Plaid connection setup and provides reusable methods for
common operations (creating sandbox tokens, exchanging tokens, fetching transactions).
"""
import time
from datetime import date, timedelta
from typing import List, Dict
import plaid
from plaid.api import plaid_api
from plaid.exceptions import ApiException
from plaid.model.products import Products
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

from config import Config
from logger import get_logger

log = get_logger(__name__)

class PlaidClient:
    """Wrapper around the Plaid API client with helper methods for common workflows."""

    # Plaid environment mapping
    ENV_MAP = {
        'sandbox': plaid.Environment.Sandbox,
        'production': plaid.Environment.Production,
    }

    # Default sandbox test institutions (different banks with different transaction patterns)
    SANDBOX_INSTITUTIONS = [
        'ins_109508',  # First Platypus Bank
        'ins_109509',  # First Gingham Credit Union
        'ins_109510',  # Tattersall Federal Credit Union
        'ins_109511',  # Tartan Bank
        'ins_109512',  # Houndstooth Bank
    ]

    DEFAULT_SANDBOX_INSTITUTION = 'ins_109508'

    
    def __init__(self, config: Config = None):
        self.config = config or Config.from_env()
        self.env = self.config.plaid_env

        configuration = plaid.Configuration(
            host=self.ENV_MAP[self.env],
            api_key={
                'clientId': self.config.plaid_client_id,
                'secret': self.config.plaid_secret,
            }
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
    
    def create_multiple_sandbox_tokens(self, institutions: list = None) -> List[Dict]:
        """
        Create access tokens for multiple sandbox institutions.
        Returns a list of dicts: [{'institution_id': ..., 'access_token': ...}, ...]
        """
        institutions = institutions or self.SANDBOX_INSTITUTIONS
        tokens = []
        for institution_id in institutions:
            try:
                token = self.create_sandbox_access_token(institution_id)
                tokens.append({
                    'institution_id': institution_id,
                    'access_token': token
                })
            except ApiException as e:
                log.warning(f"Skipping institution {institution_id}: {e}")
                continue
        return tokens

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