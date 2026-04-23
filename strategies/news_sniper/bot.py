import logging
import json
import datetime
import requests
import MetaTrader5 as mt5
from strategies.smart_scalper.guards import TradingGuards
from core.decision_journal import DecisionJournal
from brain.snapshot_manager import SnapshotManager

logger = logging.getLogger("NewsSniper")

SNIPER_MAGIC = 999999

# ─────────────────────────────────────────────────────────────────
# Sniper 2.0: Country → Symbol mapping + Trade Direction Logic
# ─────────────────────────────────────────────────────────────────
# When USD data beats expectations → USD strengthens → Sell EURUSD/GBPUSD, Buy USDJPY/USDCAD
USD_STRONG_ACTION = {
    "EURUSD": "sell", "GBPUSD": "sell", "AUDUSD": "sell",
    "NZDUSD": "sell", "GOLD": "sell", "USDJPY": "buy",
    "USDCAD": "buy",  "USDCHF": "buy"
}
USD_WEAK_ACTION = {k: ("buy" if v == "sell" else "sell") for k, v in USD_STRONG_ACTION.items()}

COUNTRY_TO_SYMBOLS = {
    "USD": ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "GOLD"],
    "EUR": ["EURUSD"],
    "GBP": ["GBPUSD"],
    "JPY": ["USDJPY"],
    "CAD": ["USDCAD"],
    "AUD": ["AUDUSD"],
    "NZD": ["NZDUSD"],
    "CHF": ["USDCHF"],
}


class NewsSniper:
    def __init__(self, mt5_manager):
        self.mt = mt5_manager
        self.symbols = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "USDCAD", "AUDUSD", "NZDUSD"]
        self.magic_number = SNIPER_MAGIC
        self._armed_events = set()   # Track events already handled

    def load_sniper_config(self):
        try:
            with open("config_sniper.json", "r") as f:
                return json.load(f)
        except:
            return {"distance": 100, "lot": 0.05, "is_armed": True, "deviation_threshold": 0.1}

    # ─────────────────────────────────────────────────────────────────
    # PHASE 3: Data-Driven Intelligence (Actual vs Expected)
    # ─────────────────────────────────────────────────────────────────

    def scan_for_events(self):
        """
        Sniper 2.0: Reads upcoming High Impact events.
        For events that have just released, compares Actual vs Expected.
        If surprise is significant, fires a directional trade immediately.
        """
        cfg = self.load_sniper_config()
        if not cfg.get("is_armed", True):
            return

        news = TradingGuards.get_upcoming_news()
        now = datetime.datetime.now()

        for event in news:
            if event.get("impact") != "High":
                continue

            # Parse event time
            try:
                event_time = datetime.datetime.strptime(event["time"], "%I:%M %p").replace(
                    year=now.year, month=now.month, day=now.day
                )
            except Exception:
                continue

            diff_seconds = (event_time - now).total_seconds()
            event_id = f"{event['title']}_{event['time']}"

            # ── T-60s: Legacy Straddle (optional backup) ─────────────
            if 0 < diff_seconds <= 60 and event_id not in self._armed_events:
                logger.info(f"🧨 SNIPER: '{event['title']}' in {int(diff_seconds)}s — Standby mode only.")
                # No blind straddle in 2.0: we wait for actual data instead
                self._armed_events.add(event_id)

            # ── T+0 to T+120s: React to actual data ──────────────────
            elif -120 <= diff_seconds <= 0:
                react_id = f"react_{event_id}"
                if react_id not in self._armed_events:
                    logger.info(f"🎯 SNIPER: '{event['title']}' just released! Checking actual data...")
                    self._armed_events.add(react_id)
                    self._react_to_release(event, cfg)

    def _react_to_release(self, event: dict, cfg: dict):
        """
        Fetches the actual number from ForexFactory RSS (or fallback to
        the event 'actual' field if the guard already parsed it) and
        decides the trade direction based on the surprise delta.
        """
        actual   = event.get("actual")    # Parsed from feed if available
        forecast = event.get("forecast")  # Expected consensus

        threshold = float(cfg.get("deviation_threshold", 0.1))

        # If feed doesn't provide actual/forecast numbers, fall back to
        # Gemini-based directional inference (available via state)
        if actual is None or forecast is None:
            DecisionJournal.log("NEWS", "Sniper", "SKIP", f"Missing data for {event['title']}")
            logger.warning(f"⚠️ SNIPER: No actual/forecast for '{event['title']}'. Skipping data-driven entry.")
            return

        try:
            actual   = float(str(actual).replace("%", "").replace("K", "000").strip())
            forecast = float(str(forecast).replace("%", "").replace("K", "000").strip())
        except Exception:
            logger.warning(f"⚠️ SNIPER: Could not parse numbers for '{event['title']}'.")
            return

        delta = actual - forecast
        logger.info(f"📊 SNIPER Data: Actual={actual}, Forecast={forecast}, Delta={delta:+.3f}, Threshold={threshold}")

        if abs(delta) < threshold:
            DecisionJournal.log(country, "Sniper", "SKIP", f"Delta {delta:.3f} < Threshold {threshold}")
            logger.info("📊 SNIPER: Surprise too small. No trade fired.")
            return

        country = event.get("country", "")
        impacted_symbols = COUNTRY_TO_SYMBOLS.get(country, [])

        if not impacted_symbols:
            return

        # Determine direction: positive delta = stronger than expected
        if country == "USD":
            action_map = USD_STRONG_ACTION if delta > 0 else USD_WEAK_ACTION
        else:
            # Non-USD: positive delta strengthens that currency
            # → if the pair is XXX/USD, positive delta = BUY the pair
            # → if the pair is USD/XXX, positive delta = SELL the pair
            action_map = {}
            for sym in impacted_symbols:
                if sym.startswith(country):        # e.g. EURUSD starts with EUR
                    action_map[sym] = "buy" if delta > 0 else "sell"
                elif sym.endswith(country):        # e.g. USDCAD ends with CAD
                    action_map[sym] = "sell" if delta > 0 else "buy"

        for sym in impacted_symbols:
            direction = action_map.get(sym)
            if direction:
                logger.info(f"🚀 SNIPER FIRE: {direction.upper()} {sym} | Delta: {delta:+.3f}")
                if self._fire_market_order(sym, direction, cfg):
                    DecisionJournal.log(sym, "Sniper", "ENTRY", f"News Release Surprise {delta:+.3f}", {"delta": delta, "event": event["title"]})
                else:
                    logger.critical(f"❌ SNIPER EXECUTION FAILURE on {sym}")
                    SnapshotManager.capture_full_state()

    def _fire_market_order(self, symbol: str, direction: str, cfg: dict):
        """Fires an immediate market order using the robust MT5Manager layer."""
        try:
            lot = float(cfg.get("lot", 0.05))
            
            # Use points from config or default news sniper targets
            sl_pts = 250
            tp_pts = 750
            
            res = self.mt.execute_trade(
                symbol, 
                direction, 
                lot, 
                sl_pts, 
                tp_pts, 
                magic=self.magic_number,
                comment="Sniper v5.0 Robust"
            )
            
            if res:
                logger.info(f"✅ SNIPER: {direction.upper()} {symbol} executed successfully.")
                return True
            return False
        except Exception as e:
            logger.critical(f"💥 Critical Failure in Sniper Order: {e}")
            SnapshotManager.capture_full_state()
            return False

    # ─────────────────────────────────────────────────────────────────
    # Volatility Gap Monitor (Non-calendar shock detection)
    # ─────────────────────────────────────────────────────────────────

    def monitor_gaps(self):
        """
        🚨 Aggressive Volatility Hunter (v4.5)
        Detects sudden price spikes (400+ points in 1 candle) and fires momentum trades.
        """
        cfg = self.load_sniper_config()
        if not cfg.get("is_armed", True):
            return

        for sym in self.symbols:
            rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 2)
            if rates is None or len(rates) < 2:
                continue

            movement_raw = rates[1]["close"] - rates[1]["open"]
            movement_pts = abs(movement_raw)
            point = mt5.symbol_info(sym).point if mt5.symbol_info(sym) else 0.00001

            threshold = 400 * point
            # For GOLD, spikes are larger, so we adjust
            if "GOLD" in sym: threshold = 1500 * point # 15.00 USD surge

            if movement_pts > threshold:
                direction = "buy" if movement_raw > 0 else "sell"
                logger.warning(f"⚡ VOLATILITY SPIKE DETECTED on {sym}: {movement_pts/point:.0f} pts. Firing Aggressive Sniper...")
                
                # Double check for existing sniper trade to prevent spam
                existing = mt5.positions_get(symbol=sym)
                if existing and any(p.magic == SNIPER_MAGIC for p in existing):
                    continue

                DecisionJournal.log(sym, "Sniper", "ENTRY", f"V-Spike Hunter: {movement_pts/point:.0f} pts")
                self._fire_market_order(sym, direction, cfg)
