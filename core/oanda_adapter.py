from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib import error, parse, request

from core.broker_adapter import BrokerAdapter, BrokerCredentials


class OandaAdapter(BrokerAdapter):
    def __init__(self, creds: BrokerCredentials):
        self.creds = creds
        base = "https://api-fxpractice.oanda.com"
        if (creds.environment or "").lower() == "live":
            base = "https://api-fxtrade.oanda.com"
        self.base_url = base

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.creds.api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=body, method=method, headers=self._headers())
        try:
            with request.urlopen(req, timeout=20) as res:
                text = res.read().decode("utf-8")
                return json.loads(text) if text else {}
        except error.HTTPError as e:
            raw = e.read().decode("utf-8") if e.fp else str(e)
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"error": raw}
            return {"error": parsed, "status_code": e.code}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def _to_oanda_symbol(symbol: str) -> str:
        s = symbol.replace("/", "").upper()
        if s == "GOLD":
            return "XAU_USD"
        if len(s) == 6:
            return f"{s[:3]}_{s[3:]}"
        return symbol

    def get_account(self) -> Dict[str, Any]:
        data = self._request("GET", f"/v3/accounts/{self.creds.account_id}/summary")
        return data.get("account", data)

    def get_positions(self) -> List[Dict[str, Any]]:
        data = self._request("GET", f"/v3/accounts/{self.creds.account_id}/openPositions")
        return data.get("positions", [])

    def get_prices(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        instruments = ",".join(self._to_oanda_symbol(s) for s in symbols)
        query = parse.urlencode({"instruments": instruments})
        data = self._request("GET", f"/v3/accounts/{self.creds.account_id}/pricing?{query}")
        out: Dict[str, Dict[str, float]] = {}
        for p in data.get("prices", []):
            bids = p.get("bids", [])
            asks = p.get("asks", [])
            if not bids or not asks:
                continue
            out[p.get("instrument", "")] = {
                "bid": float(bids[0].get("price", 0)),
                "ask": float(asks[0].get("price", 0)),
            }
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
        signed_units = abs(units) if side.lower() == "buy" else -abs(units)
        order: Dict[str, Any] = {
            "units": str(int(signed_units)),
            "instrument": self._to_oanda_symbol(symbol),
            "timeInForce": "FOK",
            "type": "MARKET",
            "positionFill": "DEFAULT",
            "clientExtensions": {"tag": client_tag},
        }
        if stop_loss:
            order["stopLossOnFill"] = {"price": str(stop_loss)}
        if take_profit:
            order["takeProfitOnFill"] = {"price": str(take_profit)}
        return self._request(
            "POST",
            f"/v3/accounts/{self.creds.account_id}/orders",
            {"order": order},
        )

    def close_position(self, instrument: str, side: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, str] = {}
        if side is None:
            payload = {"longUnits": "ALL", "shortUnits": "ALL"}
        elif side.lower() == "buy":
            payload = {"longUnits": "ALL"}
        else:
            payload = {"shortUnits": "ALL"}
        return self._request(
            "PUT",
            f"/v3/accounts/{self.creds.account_id}/positions/{self._to_oanda_symbol(instrument)}/close",
            payload,
        )
