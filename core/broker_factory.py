from __future__ import annotations

import os
from typing import Any, Dict

from core.broker_adapter import BrokerCredentials
from core.database_client import db_client
from core.fxcm_adapter import FxcmAdapter
from core.mt5_adapter import MT5Adapter
from core.oanda_adapter import OandaAdapter


def _from_env_fxcm() -> BrokerCredentials:
    return BrokerCredentials(
        provider="fxcm",
        account_id=os.getenv("FXCM_ACCOUNT_ID", "") or os.getenv("FXCM_LOGIN", ""),
        api_key=os.getenv("FXCM_API_TOKEN", "") or os.getenv("FXCM_PASSWORD", ""),
        environment=os.getenv("FXCM_ENV", "demo"),
    )


def _from_env_oanda() -> BrokerCredentials:
    return BrokerCredentials(
        provider="oanda",
        account_id=os.getenv("OANDA_ACCOUNT_ID", ""),
        api_key=os.getenv("OANDA_API_KEY", ""),
        environment=os.getenv("OANDA_ENV", "practice"),
    )


def get_broker_for_account(account_id: str, mt5_manager):
    record: Dict[str, Any] = db_client.get_broker_connection(account_id)
    provider = (record.get("provider") or os.getenv("BROKER_PROVIDER", "fxcm")).lower()
    if provider == "fxcm":
        creds = BrokerCredentials(
            provider="fxcm",
            account_id=record.get("broker_account_id") or os.getenv("FXCM_ACCOUNT_ID", "") or os.getenv("FXCM_LOGIN", ""),
            api_key=record.get("api_key_plain") or os.getenv("FXCM_API_TOKEN", "") or os.getenv("FXCM_PASSWORD", ""),
            environment=record.get("environment") or os.getenv("FXCM_ENV", "demo"),
        )
        if not creds.account_id or not creds.api_key:
            creds = _from_env_fxcm()
        return FxcmAdapter(creds)
    if provider == "oanda":
        creds = BrokerCredentials(
            provider="oanda",
            account_id=record.get("broker_account_id") or os.getenv("OANDA_ACCOUNT_ID", ""),
            api_key=record.get("api_key_plain") or os.getenv("OANDA_API_KEY", ""),
            environment=record.get("environment") or os.getenv("OANDA_ENV", "practice"),
        )
        if not creds.account_id or not creds.api_key:
            creds = _from_env_oanda()
        return OandaAdapter(creds)
    return MT5Adapter(mt5_manager)
