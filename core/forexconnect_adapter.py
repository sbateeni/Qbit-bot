from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from core.broker_adapter import BrokerAdapter, BrokerCredentials


class ForexConnectAdapter(BrokerAdapter):
    """
    FXCM integration through ForexConnect (login/password flow).
    account_id => Trading Station login
    api_key => Trading Station password (legacy field name compatibility)
    """

    def __init__(self, creds: BrokerCredentials):
        self.creds = creds
        self.connection = "Demo" if (creds.environment or "demo").lower() == "demo" else "Real"
        self.host_url = os.getenv("FXCM_HOST_URL", "https://www.fxcorporate.com/Hosts.jsp")
        self._sdk = None

    def _load_sdk(self):
        if self._sdk is not None:
            return self._sdk
        try:
            import forexconnect  # type: ignore
            self._sdk = forexconnect
        except Exception:
            self._sdk = False
        return self._sdk

    def _sdk_missing(self) -> Dict[str, Any]:
        return {
            "error": "ForexConnect SDK is not installed on this runtime",
            "hint": "Install forexconnect package and FXCM dependencies on worker/runtime",
        }

    def get_account(self) -> Dict[str, Any]:
        sdk = self._load_sdk()
        if sdk is False:
            return self._sdk_missing()
        # Placeholder login check for environments where SDK exists.
        # Full table/session implementation can be added progressively.
        if not self.creds.account_id or not self.creds.api_key:
            return {"error": "Missing FXCM login/password"}
        return {
            "provider": "fxcm-forexconnect",
            "login": self.creds.account_id,
            "connection": self.connection,
            "host_url": self.host_url,
            "status": "credentials_loaded",
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        return []

    def get_prices(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        return {s: {"bid": 0.0, "ask": 0.0} for s in symbols}

    def open_market_order(
        self,
        symbol: str,
        side: str,
        units: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        client_tag: str = "Qbit",
    ) -> Dict[str, Any]:
        return {
            "error": "ForexConnect execution flow pending final account binding",
            "symbol": symbol,
            "side": side,
            "units": units,
        }

    def close_position(self, instrument: str, side: Optional[str] = None) -> Dict[str, Any]:
        return {"error": "ForexConnect close flow pending final account binding", "instrument": instrument}
