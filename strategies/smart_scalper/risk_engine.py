import datetime
import logging
import json
import os
import MetaTrader5 as mt5
from .signals import SignalGenerator

logger = logging.getLogger("ScalperRiskEngine")

class ScalperRiskEngine:
    """
    Manages the 'Emergency Fuse' and 'Post-Mortem Learning' for the Scalper.
    """
    def __init__(self, symbol, brain_analyzer, config_path, digits):
        self.symbol = symbol
        self.brain = brain_analyzer
        self.config_path = config_path
        self.digits = digits
        self.consecutive_losses = 0
        self.MAX_STRIKES = 2
        self.cooldown_minutes = 120

    def process_loss_history(self, last_ticket, trade_context):
        """Checks if the last trade was a loss and triggers AI learning."""
        if last_ticket is None: return False
        
        pos = mt5.positions_get(ticket=last_ticket)
        if pos and len(pos) > 0: return False # Still open
        
        # Look back 12 hours for a more comprehensive strike audit
        from_date = datetime.datetime.now() - datetime.timedelta(hours=12)
        history = mt5.history_deals_get(from_date, datetime.datetime.now())
        
        if not history: return False
        
        target = [
            d for d in history
            if hasattr(d, "position_id")
            and (d.position_id == last_ticket or d.order == last_ticket)
        ]
        if not target: return False
        
        deal = target[-1]
        if deal.profit < 0:
            self.consecutive_losses += 1
            logger.warning(f"📉 [STRIKE] Loss on #{last_ticket} ({self.symbol}). Strike {self.consecutive_losses}/{self.MAX_STRIKES}.")
            
            # 🧨 EMERGENCY FUSE: Disable ALL trading if we lose too many times
            if self.consecutive_losses >= self.MAX_STRIKES:
                logger.critical(f"🛑 [CIRCUIT BREAKER] {self.symbol} has hit {self.MAX_STRIKES} consecutive losses. Halting system.")
                from api.state import trading_enabled
                import api.state
                api.state.trading_enabled = False
                return "KILL_SWITCH"

            # Cool down
            from api.state import global_cooldowns
            global_cooldowns[self.symbol] = datetime.datetime.now()
            
            # AI Learning & Snapshot (v4.5 Sovereign)
            from brain.snapshot_manager import SnapshotManager
            SnapshotManager.capture_full_state()
            
            self._trigger_ai_learning(deal.profit, trade_context)
            return "LOSS"
        else: 
            logger.info(f"✅ Profit on #{last_ticket} ({self.symbol})! Resetting strikes.")
            self.consecutive_losses = 0 
            
            # Record a success snapshot
            from brain.snapshot_manager import SnapshotManager
            SnapshotManager.capture_full_state()
            
            return "PROFIT"

    def _trigger_ai_learning(self, profit, trade_context):
        """Gathers market context and sends it to Gemini for adjustment."""
        import MetaTrader5 as mt5_internal
        # We need a small sample of market data to see what went wrong
        from strategies.smart_scalper.signals import SignalGenerator
        
        # This is a bit ugly as it needs a MT5 manager, but we'll use a local mock or bypass
        # For simplicity, we assume the bot provides the context
        self.brain.analyze_trade_failure({
            "symbol": self.symbol, "profit": profit,
            "entry_context": trade_context
        })
