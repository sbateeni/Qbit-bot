from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.broker_adapter import BrokerAdapter
from core.mt5_proxy import mt5


class MT5Adapter(BrokerAdapter):
    def __init__(self, mt5_manager):
        self.mt5_manager = mt5_manager

    def get_account(self) -> Dict[str, Any]:
        self.mt5_manager.keep_alive()
        acc = mt5.account_info()
        if not acc:
            return {}
        mode = "Real" if acc.trade_mode in [mt5.ACCOUNT_TRADE_MODE_REAL, mt5.ACCOUNT_TRADE_MODE_CONTEST] else "Demo"
        return {
            "balance": acc.balance,
            "equity": acc.equity,
            "currency": acc.currency,
            "mode": mode,
            "name": acc.name,
            "server": acc.server,
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        self.mt5_manager.keep_alive()
        positions = mt5.positions_get()
        if not positions:
            return []
        return [
            {
                "ticket": p.ticket,
                "symbol": p.symbol,
                "volume": p.volume,
                "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                "open_price": p.price_open,
                "current_price": p.price_current,
                "profit": p.profit,
                "magic": p.magic,
            }
            for p in positions
        ]

    def get_prices(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        out: Dict[str, Dict[str, float]] = {}
        for sym in symbols:
            tick = mt5.symbol_info_tick(sym)
            if tick:
                out[sym] = {"bid": tick.bid, "ask": tick.ask}
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
        order_type = "buy" if side.lower() == "buy" else "sell"
        result = self.mt5_manager.open_order(
            symbol=symbol,
            order_type=order_type,
            volume=units,
            stop_loss=stop_loss or 0.0,
            take_profit=take_profit or 0.0,
            comment=client_tag,
        )
        return {"ok": bool(result), "result": str(result)}

    def close_position(self, instrument: str, side: Optional[str] = None) -> Dict[str, Any]:
        positions = mt5.positions_get(symbol=instrument) or []
        closed = 0
        for p in positions:
            if side and side.lower() == "buy" and p.type != mt5.ORDER_TYPE_BUY:
                continue
            if side and side.lower() == "sell" and p.type != mt5.ORDER_TYPE_SELL:
                continue
            if self.mt5_manager.close_position(p.ticket):
                closed += 1
        return {"closed": closed}
