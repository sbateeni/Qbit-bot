import logging
import json
import datetime
import MetaTrader5 as mt5
from .guards import SwingGuards
from core.telegram_notifier import TelegramNotifier
from core.decision_journal import DecisionJournal
from brain.snapshot_manager import SnapshotManager

logger = logging.getLogger("SwingInvestor")

SCALPER_MAGIC = 123456
SWING_MAGIC   = 777777

class SwingInvestor:
    def __init__(self, mt5_manager, symbol):
        self.mt = mt5_manager
        self.symbol = symbol
        self.magic_number = SWING_MAGIC
        self.telegram = TelegramNotifier()

        info = mt5.symbol_info(symbol)
        self.point = info.point if info else 0.0001
        self.digits = info.digits if info else 5

    def get_market_intel(self):
        try:
            with open("logs/market_intel.json", "r") as f:
                data = json.load(f)
                # If JSON is a list, find matching pair. If single object, check pair.
                if isinstance(data, list):
                    for item in data:
                        pair = item.get("pair", "").replace("/", "").upper() # e.g. EUR/USD -> EURUSD
                        if pair == self.symbol.upper(): return item
                else:
                    pair = data.get("pair", "").replace("/", "").upper()
                    if pair == self.symbol.upper(): return data
            return None
        except:
            return None

    def load_swing_config(self):
        """Load user-configured swing settings from config_swing.json (written by dashboard)."""
        try:
            with open("config_swing.json", "r") as f:
                cfg = json.load(f)
            return {
                "tp_points":      int(cfg.get("tp_points", 1500)),
                "sl_points":      int(cfg.get("sl_points", 500)),
                "min_confidence": int(cfg.get("min_confidence", 80)),
                "max_trades":     int(cfg.get("max_trades", 1)),
                "target_profit_usd": float(cfg.get("target_profit_usd", 2.0))
            }
        except:
            return {"tp_points": 1500, "sl_points": 500, "min_confidence": 80, "max_trades": 1}

    def calculate_swing_lot(self, confidence=80):
        """Dynamic Lot Sizing based on Gemini Confidence."""
        try:
            acc = mt5.account_info()
            if not acc: return 0.01
            is_demo = acc.trade_mode not in [mt5.ACCOUNT_TRADE_MODE_REAL, mt5.ACCOUNT_TRADE_MODE_CONTEST]
            
            if is_demo:
                with open("config.json", "r") as f:
                    balance = float(json.load(f).get("virtual_balance", 100.0))
            else:
                balance = acc.balance

            # Base Lot (0.5% risk)
            risk_amount = balance * 0.005 
            base_lot = round(risk_amount / 20.0, 2)
            
            # 🔥 AI Multiplier: Increase size for high-conviction trades
            multiplier = 1.0
            if confidence >= 95: multiplier = 3.0
            elif confidence >= 90: multiplier = 2.0
            
            final_lot = round(base_lot * multiplier, 2)
            # Safeguard: Never exceed 10% of balance in one trade and cap at 1.0 lot for safety
            return max(0.01, min(final_lot, 1.0))
        except:
            return 0.01

    def monitor_and_close_positions(self, cfg):
        """Monitors collective swing positions and implements 'Malahaka' (Smart Trailing) when Target Profit is reached."""
        positions = mt5.positions_get()
        if not positions:
            return

        swing_positions = [p for p in positions if p.magic == self.magic_number]
        if not swing_positions:
            return

        total_profit = sum(p.profit for p in swing_positions)
        target_usd   = float(cfg.get("target_profit_usd", 2.0))

        # 🚀 Institutional Malahaka (v4.5) — Lock & Follow
        if total_profit >= target_usd:
            logger.info(f"🚀 [SWING MALAHAKA] Profit Target ${target_usd} hit. Total: ${total_profit:.2f}. Activating Profit Pursuit...")
            
            for p in swing_positions:
                tick = mt5.symbol_info_tick(p.symbol)
                if not tick: continue
                
                info = mt5.symbol_info(p.symbol)
                if not info: continue
                
                # Lock buffer: give it some room (100-200 points for swing)
                cushion = 200 * info.point
                
                if p.type == mt5.POSITION_TYPE_BUY:
                    new_sl = round(tick.bid - cushion, info.digits)
                    if new_sl > p.sl + (50 * info.point):
                        self.mt.modify_sl_tp(p.ticket, new_sl, p.tp)
                        logger.info(f"🛡️ [SWING LOCK] {p.symbol}: SL moved to {new_sl} to lock profit.")
                elif p.type == mt5.POSITION_TYPE_SELL:
                    new_sl = round(tick.ask + cushion, info.digits)
                    if p.sl == 0 or new_sl < p.sl - (50 * info.point):
                        self.mt.modify_sl_tp(p.ticket, new_sl, p.tp)
                        logger.info(f"🛡️ [SWING LOCK] {p.symbol}: SL moved to {new_sl} to lock profit.")


    def analyze_and_invest(self):
        # 0. Load user-configured settings
        cfg = self.load_swing_config()

        # 0.5 Monitor open positions for USD Profit Target
        self.monitor_and_close_positions(cfg)

        # 1. Only skip on weekends (market fully closed) — via SwingGuards
        if not SwingGuards.is_market_open():
            return

        # 2. Check if we reached the GLOBAL maximum concurrent trades limit
        current_global_trades = SwingGuards.count_open_swing_positions(self.magic_number)
        max_allowed = int(cfg.get("max_trades", 1))
        
        if current_global_trades >= max_allowed:
            return

        # 2.1 Diversification Check: Only 1 trade per symbol to prevent 'clumping'
        current_symbol_trades = SwingGuards.count_open_swing_positions(self.magic_number, symbol=self.symbol)
        if current_symbol_trades >= 1:
            return # Already have a position for this symbol

        # 3. PRE-FILTER: Technical Momentum (Before calling AI)
        df = self.mt.get_market_data(self.symbol, mt5.TIMEFRAME_H1, count=200)
        if df is None or df.empty or len(df) < 14: return
        
        import pandas_ta as ta
        rsi_series = ta.rsi(df['close'], length=14)
        if rsi_series is None or rsi_series.empty: return
        rsi = rsi_series.iloc[-1]

        # Basic filter: only proceed if RSI is not perfectly neutral (e.g. < 45 or > 55)
        if 45 < rsi < 55:
            return

        # 4. Fetch/Update Market Intel (ON-DEMAND)
        intel = self.get_market_intel()
        
        # Check if intel is missing or older than 30 minutes
        needs_update = True
        now = __import__('datetime').datetime.now()
        
        if intel and "last_update" in intel:
            last_upd = __import__('datetime').datetime.strptime(intel["last_update"], "%Y-%m-%d %H:%M")
            if (now - last_upd).total_seconds() < 1800:
                needs_update = False
        
        # 🧨 SAFETY FUSE: Don't spam if we just recently tried and failed (avoid 429)
        if needs_update:
            if hasattr(self, '_last_intel_retry'):
                if (now - self._last_intel_retry).total_seconds() < 300: # Wait 5m between retries if failing
                    return
            
            logger.info(f"🧠 [SWING] {self.symbol} requesting fresh AI Intel...")
            self._last_intel_retry = now
            from core.intel_manager import IntelManager
            intel_mgr = IntelManager(self.mt)
            updated_list = intel_mgr.update_global_intelligence([self.symbol])
            if updated_list: 
                intel = updated_list[0]
            else: 
                return # AI still throttled or no data

        if not intel:
            return

        confidence = int(intel.get("sentiment_score", 50))
        summary    = intel.get("technical_summary", "")

        # 5. Validate confidence — via SwingGuards
        if not SwingGuards.is_confidence_sufficient(confidence, cfg["min_confidence"]):
            return

        # 6. Validate signal direction — via SwingGuards
        direction = SwingGuards.is_signal_strong(summary)

        # 6.2 Investing.com Consensus Gate (Global Confirmation)
        investing_summary = intel.get("investing_consensus", "NEUTRAL").upper()
        if direction == "buy" and "SELL" in investing_summary:
            logger.info(f"🚫 [SWING] Investing.com Conflict: Rejecting BUY because Investing says {investing_summary}.")
            return
        if direction == "sell" and "BUY" in investing_summary:
            logger.info(f"🚫 [SWING] Investing.com Conflict: Rejecting SELL because Investing says {investing_summary}.")
            return
        
        # 6.5 v3.6 Strategic Alignment Gate (Triple Timeframe Alignment)
        from api.state import global_biases
        bias = global_biases.get(self.symbol, "NEUTRAL")
        if direction == "buy" and bias == "BEARISH":
            logger.info(f"🚫 [SWING] H4 Strategic Conflict: Rejecting BUY because H4 is BEARISH.")
            return
        if direction == "sell" and bias == "BULLISH":
            logger.info(f"🚫 [SWING] H4 Strategic Conflict: Rejecting SELL because H4 is BULLISH.")
            return

        # 7. Global Correlation Hedge (DXY Filter)

        from api import state
        dxy_trend = state.macro_data["dxy_trend"]
        if direction == "buy" and dxy_trend == "UP":
            logger.info(f"🚫 [SWING] Hedge Rejected: Buying EURUSD while DXY is UP is high risk.")
            return
        if direction == "sell" and dxy_trend == "DOWN":
            logger.info(f"🚫 [SWING] Hedge Rejected: Selling EURUSD while DXY is DOWN is high risk.")
            return

        if direction:
            # v5.0 Meta-Logic: Correlation Guard
            from api import state as _state
            if hasattr(_state, 'risk_manager'):
                if not _state.risk_manager.is_trade_allowed(self.symbol, direction):
                    DecisionJournal.log(self.symbol, "Swing", "BLOCK", f"Correlation Guard blocked {direction}", {"reason": "Overexposure"})
                    return
            
            # v5.0 Verification Matrix
            matrix_data = {
                "confidence": confidence, "summary": summary, "investing": investing_summary,
                "bias": bias, "dxy_trend": dxy_trend, "symbol": self.symbol
            }

            logger.info(f"🛡️ [SWING] {direction.upper()} matrix aligned | Confidence: {confidence}%")
            if self.execute_trade(direction, cfg, confidence, matrix_data):
                DecisionJournal.log(self.symbol, "Swing", "ENTRY", f"Macro Aligned: {summary}", matrix_data)
            else:
                logger.critical(f"❌ SWING EXECUTION FAILURE on {self.symbol}")
                SnapshotManager.capture_full_state()

    def execute_trade(self, order_type, cfg, confidence, matrix_data=None):
        """Surgical trade execution with diagnostics."""
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            if not tick:
                logger.error(f"Failed to get tick for {self.symbol}")
                return False

            sl_points = cfg["sl_points"]
            tp_points = cfg["tp_points"]
            lot       = self.calculate_swing_lot(confidence)

            if order_type == "buy":
                price = tick.ask
                sl = round(price - (sl_points * self.point), self.digits)
                tp = round(price + (tp_points * self.point), self.digits)
            else:
                price = tick.bid
                sl = round(price + (sl_points * self.point), self.digits)
                tp = round(price - (tp_points * self.point), self.digits)

            res = self.mt.open_order(
                self.symbol,
                order_type,
                lot,
                sl,
                tp,
                magic=self.magic_number,
                comment=f"Swing | {sl_points}/{tp_points}"
            )
            if res:
                 self.telegram.send_trade_open(self.symbol, order_type, price, lot, f"Macro Swing (Conf: {confidence}%)")
                 return True
            return False
        except Exception as e:
            logger.critical(f"💥 Failure in execute_trade: {e}")
            SnapshotManager.capture_full_state()
            return False

