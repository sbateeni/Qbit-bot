import datetime
import json
import logging
import os
import MetaTrader5 as mt5
import pandas as pd

logger = logging.getLogger("RiskManager")

BOT_MAGICS = frozenset({123456, 777777, 999999})

# Correlation threshold above which we consider two pairs as "too correlated"
CORRELATION_BLOCK_THRESHOLD = 0.75

# Known static direction map: +1 = moves WITH USD strength, -1 = moves AGAINST USD strength
USD_DIRECTION_MAP = {
    "EURUSD": -1,
    "GBPUSD": -1,
    "AUDUSD": -1,
    "NZDUSD": -1,
    "GOLD": -1,
    "XAUUSD": -1,
    "USDJPY": +1,
    "USDCAD": +1,
    "USDCHF": +1,
}


def _load_risk_block() -> dict:
    defaults = {
        "max_account_positions": 10,
        "max_same_usd_direction": 4,
        "hourly_panic_bot_deals_only": True,
        "hourly_panic_include_commission": True,
    }
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            r = cfg.get("risk")
            if isinstance(r, dict):
                defaults.update({k: v for k, v in r.items() if k in defaults or k in (
                    "max_account_positions", "max_same_usd_direction",
                    "hourly_panic_bot_deals_only", "hourly_panic_include_commission",
                    "hourly_panic_magics",
                )})
    except Exception as e:
        logger.debug("risk config load: %s", e)
    return defaults


class RiskManager:
    """
    Correlation guard, portfolio exposure, and hard risk stops.
    """

    def __init__(self, mt5_manager):
        self.mt = mt5_manager
        self._price_cache = {}
        self._risk = _load_risk_block()

    def reload_settings(self):
        self._risk = _load_risk_block()

    def is_trade_allowed(self, symbol: str, order_type: str) -> bool:
        """
        Caps total open positions and stacked USD directional exposure.
        Tuned for multi-strategy accounts (scalper + swing + sniper).
        """
        self.reload_settings()
        open_positions = list(mt5.positions_get() or [])
        max_pos = int(self._risk.get("max_account_positions", 10))
        if len(open_positions) >= max_pos:
            logger.warning("⛔ [RISK] Max account positions (%s) reached.", max_pos)
            return False

        new_usd_bias = self._get_usd_bias(symbol, order_type)
        if new_usd_bias == 0:
            return True

        max_same = int(self._risk.get("max_same_usd_direction", 4))
        same = 0
        for pos in open_positions:
            existing_bias = self._get_usd_bias(
                pos.symbol, "buy" if pos.type == mt5.ORDER_TYPE_BUY else "sell"
            )
            if existing_bias != 0 and existing_bias == new_usd_bias:
                same += 1
        if same >= max_same:
            logger.warning(
                "⛔ [RISK] USD directional stack full (%s/%s). Blocked %s.",
                same,
                max_same,
                symbol,
            )
            return False

        return True

    def check_hourly_panic(self, max_loss_usd=25.0):
        """Halts system if realized+swap loss in the last hour exceeds threshold."""
        self.reload_settings()
        import api.state

        from_date = datetime.datetime.now() - datetime.timedelta(hours=1)
        to_date = datetime.datetime.now()
        try:
            mt5.history_select(from_date, to_date)
        except Exception as e:
            logger.debug("history_select: %s", e)

        deals = mt5.history_deals_get(from_date, to_date) or []
        bot_only = bool(self._risk.get("hourly_panic_bot_deals_only", True))
        use_comm = bool(self._risk.get("hourly_panic_include_commission", True))
        magics_cfg = self._risk.get("hourly_panic_magics")
        if isinstance(magics_cfg, list) and len(magics_cfg) > 0:
            allowed_magics = frozenset(int(x) for x in magics_cfg)
        else:
            allowed_magics = BOT_MAGICS

        total = 0.0
        for d in deals:
            if getattr(d, "entry", None) != mt5.DEAL_ENTRY_OUT:
                continue
            net = float(getattr(d, "profit", 0.0))
            if use_comm:
                net += float(getattr(d, "commission", 0.0) or 0.0)
                net += float(getattr(d, "swap", 0.0) or 0.0)
            if net >= 0:
                continue
            if bot_only and int(getattr(d, "magic", 0)) not in allowed_magics:
                continue
            total += net

        if abs(total) < max_loss_usd:
            return True

        # Already locked: do not spam logs or re-flatten every tick
        if not getattr(api.state, "trading_enabled", True):
            return False

        logger.critical(
            "🚨 [HOURLY PANIC] Net loss $%.2f in 1h (limit %.2f). Locking system.",
            abs(total),
            max_loss_usd,
        )
        self.flatten_all_positions()
        api.state.trading_enabled = False
        return False

    def get_portfolio_usd_bias(self) -> dict:
        open_positions = mt5.positions_get()
        if not open_positions:
            return {"long_usd": 0, "short_usd": 0, "neutral": 0}

        long_usd = short_usd = neutral = 0
        for pos in open_positions:
            pos_type = "buy" if pos.type == mt5.ORDER_TYPE_BUY else "sell"
            bias = self._get_usd_bias(pos.symbol, pos_type)
            if bias == +1:
                long_usd += 1
            elif bias == -1:
                short_usd += 1
            else:
                neutral += 1

        return {"long_usd": long_usd, "short_usd": short_usd, "neutral": neutral}

    def check_global_drawdown(self, max_drawdown_percent=5.0, session_equity_peak: float | None = None):
        """
        Returns True if the account is SAFE.
        If session_equity_peak is provided, drawdown is measured from that peak (open + closed risk).
        """
        self.reload_settings()
        acc = mt5.account_info()
        if not acc:
            return True

        if session_equity_peak and session_equity_peak > 0:
            drawdown_pct = ((session_equity_peak - acc.equity) / session_equity_peak) * 100.0
        else:
            balance = acc.balance
            equity = acc.equity
            drawdown_usd = balance - equity
            drawdown_pct = (drawdown_usd / balance) * 100 if balance > 0 else 0

        if drawdown_pct < max_drawdown_percent:
            return True

        import api.state

        if not getattr(api.state, "trading_enabled", True):
            return False

        logger.critical(
            "🚨 [EQUITY GUARDIAN] Drawdown %.2f%% (limit %.2f%%). Flattening.",
            drawdown_pct,
            max_drawdown_percent,
        )
        self.flatten_all_positions()
        api.state.trading_enabled = False
        return False

    def flatten_all_positions(self):
        positions = mt5.positions_get()
        if not positions:
            return

        logger.warning("💥 [FLATTEN] Closing %s positions (risk stop).", len(positions))
        for pos in positions:
            self.mt.close_position(pos.ticket)

        try:
            import api.state

            acc = mt5.account_info()
            if acc:
                api.state.equity_peak_session = float(acc.equity)
        except Exception:
            pass

    def get_live_correlations(self, symbols: list, mt5_manager, timeframe=mt5.TIMEFRAME_H1, count: int = 50) -> pd.DataFrame:
        closes = {}
        for sym in symbols:
            df = mt5_manager.get_market_data(sym, timeframe, count)
            if df is not None and not df.empty:
                closes[sym] = df["close"].values[-count:]

        if len(closes) < 2:
            return pd.DataFrame()

        min_len = min(len(v) for v in closes.values())
        aligned = {k: v[-min_len:] for k, v in closes.items()}
        df = pd.DataFrame(aligned)
        return df.corr()

    def _get_usd_bias(self, symbol: str, order_type: str) -> int:
        direction_map_val = USD_DIRECTION_MAP.get(symbol.upper().replace("/", ""), 0)
        if direction_map_val == 0:
            return 0

        order_mult = +1 if order_type.lower() == "buy" else -1
        return direction_map_val * order_mult
