"""
Configuration validation.

Validates required environment variables at startup and exposes them as a
typed Config object. Fails fast with clear error messages when misconfigured.
"""
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Validated configuration loaded from environment variables."""

    # Plaid
    plaid_client_id: str
    plaid_secret: str
    plaid_env: str

    # Snowflake
    snowflake_account: str
    snowflake_user: str
    snowflake_private_key_path: Path
    snowflake_database: str
    snowflake_warehouse: str
    snowflake_role: str

    @classmethod
    def from_env(cls) -> 'Config':
        """Build Config from environment variables, validating each one."""
        errors = []

        # Required Plaid vars
        plaid_client_id = os.getenv('PLAID_CLIENT_ID')
        if not plaid_client_id:
            errors.append("PLAID_CLIENT_ID is required")

        plaid_secret = os.getenv('PLAID_SECRET')
        if not plaid_secret:
            errors.append("PLAID_SECRET is required")

        plaid_env = os.getenv('PLAID_ENV', 'sandbox')
        if plaid_env not in ('sandbox', 'production'):
            errors.append(f"PLAID_ENV must be 'sandbox' or 'production', got '{plaid_env}'")

        # Required Snowflake vars
        snowflake_account = os.getenv('SNOWFLAKE_ACCOUNT')
        if not snowflake_account:
            errors.append("SNOWFLAKE_ACCOUNT is required")

        snowflake_user = os.getenv('SNOWFLAKE_USER')
        if not snowflake_user:
            errors.append("SNOWFLAKE_USER is required")

        # Validate the private key path exists and is readable
        key_path_str = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH')
        if not key_path_str:
            errors.append("SNOWFLAKE_PRIVATE_KEY_PATH is required")
            snowflake_private_key_path = None
        else:
            snowflake_private_key_path = Path(key_path_str).expanduser()
            if not snowflake_private_key_path.exists():
                errors.append(
                    f"SNOWFLAKE_PRIVATE_KEY_PATH points to a file that doesn't exist: "
                    f"{snowflake_private_key_path}"
                )
            elif not snowflake_private_key_path.is_file():
                errors.append(
                    f"SNOWFLAKE_PRIVATE_KEY_PATH is not a file: {snowflake_private_key_path}"
                )
            elif not os.access(snowflake_private_key_path, os.R_OK):
                errors.append(
                    f"SNOWFLAKE_PRIVATE_KEY_PATH is not readable: {snowflake_private_key_path}"
                )

        # Optional Snowflake vars with defaults
        snowflake_database = os.getenv('SNOWFLAKE_DATABASE', 'PERSONAL_FINANCE')
        snowflake_warehouse = os.getenv('SNOWFLAKE_WAREHOUSE', 'FINANCE_WH')
        snowflake_role = os.getenv('SNOWFLAKE_ROLE', 'TRANSFORMER')

        if errors:
            error_msg = "Configuration validation failed:\n  - " + "\n  - ".join(errors)
            raise ValueError(error_msg)

        return cls(
            plaid_client_id=plaid_client_id,
            plaid_secret=plaid_secret,
            plaid_env=plaid_env,
            snowflake_account=snowflake_account,
            snowflake_user=snowflake_user,
            snowflake_private_key_path=snowflake_private_key_path,
            snowflake_database=snowflake_database,
            snowflake_warehouse=snowflake_warehouse,
            snowflake_role=snowflake_role,
        )