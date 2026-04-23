from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib import error, parse, request

from core.broker_adapter import BrokerAdapter, BrokerCredentials


class FxcmAdapter(BrokerAdapter):
    def __init__(self, creds: BrokerCredentials):
        self.creds = creds
        env = (creds.environment or "demo").lower()
        self.base_url = "https://api-demo.fxcm.com"
        if env == "live":
            self.base_url = "https://api.fxcm.com"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.creds.api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def _request(self, method: str, path: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        body = None
        if data is not None:
            body = parse.urlencode(data).encode("utf-8")
        req = request.Request(f"{self.base_url}{path}", data=body, method=method, headers=self._headers())
        try:
            with request.urlopen(req, timeout=20) as res:
                text = res.read().decode("utf-8")
                return json.loads(text) if text else {}
        except error.HTTPError as e:
            raw = e.read().decode("utf-8") if e.fp else str(e)
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {"error": raw}
            return {"error": payload, "status_code": e.code}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def _to_fxcm_symbol(symbol: str) -> str:
        s = symbol.replace("/", "").upper()
        if s == "GOLD":
            return "XAU/USD"
        if len(s) == 6:
            return f"{s[:3]}/{s[3:]}"
        return symbol

    def _get_model(self, models: str) -> Dict[str, Any]:
        return self._request("POST", "/trading/get_model", {"models": models})

    def get_account(self) -> Dict[str, Any]:
        res = self._get_model("Account")
        data = res.get("accounts") or res.get("data") or []
        if isinstance(data, list) and data:
            return data[0]
        return res

    def get_positions(self) -> List[Dict[str, Any]]:
        res = self._get_model("OpenPosition")
        data = res.get("open_positions") or res.get("data") or []
        return data if isinstance(data, list) else []

    def get_prices(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        # FXCM REST exposes offers through model snapshots.
        res = self._get_model("Offer")
        offers = res.get("offers") or res.get("data") or []
        wanted = {self._to_fxcm_symbol(s) for s in symbols}
        out: Dict[str, Dict[str, float]] = {}
        if isinstance(offers, list):
            for item in offers:
                name = item.get("currency") or item.get("symbol")
                if name in wanted:
                    bid = float(item.get("bid", 0))
                    ask = float(item.get("ask", 0))
                    out[name] = {"bid": bid, "ask": ask}
        return out

    def open_market_order(
        self,
        symbol: str,
        side: str,
        units: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        client_tag: str = "Qbit",
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "symbol": self._to_fxcm_symbol(symbol),
            "is_buy": "true" if side.lower() == "buy" else "false",
            "amount": int(units),
            "time_in_force": "GTC",
            "order_type": "AtMarket",
            "account_id": self.creds.account_id,
            "custom_id": client_tag,
        }
        if stop_loss is not None:
            payload["stop"] = stop_loss
        if take_profit is not None:
            payload["limit"] = take_profit
        return self._request("POST", "/trading/open_trade", payload)

    def close_position(self, instrument: str, side: Optional[str] = None) -> Dict[str, Any]:
        # FXCM closes by trade_id; resolve open positions then close matching rows.
        positions = self.get_positions()
        symbol = self._to_fxcm_symbol(instrument)
        closed = 0
        for p in positions:
            if p.get("currency") != symbol and p.get("symbol") != symbol:
                continue
            is_buy = bool(p.get("is_buy", True))
            if side and side.lower() == "buy" and not is_buy:
                continue
            if side and side.lower() == "sell" and is_buy:
                continue
            trade_id = p.get("trade_id") or p.get("tradeId")
            amount = p.get("amountK") or p.get("amount") or 0
            if not trade_id:
                continue
            res = self._request(
                "POST",
                "/trading/close_trade",
                {"trade_id": trade_id, "amount": int(amount)},
            )
            if not res.get("error"):
                closed += 1
        return {"closed": closed}
