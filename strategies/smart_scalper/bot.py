import os
import time
import logging
import json
import datetime
import pandas as pd
import MetaTrader5 as mt5

from .signals import SignalGenerator
from .guards import TradingGuards
from .executor import TradeExecutor
from .intelligence import ScalperIntelligence
from .risk_engine import ScalperRiskEngine
from .portfolio_guard import allow_new_entry
from brain.snapshot_manager import SnapshotManager

from core.database_client import db_client
from core.execution_guard import ExecutionGuard
from core.decision_journal import DecisionJournal
from core.time_intelligence import TimeIntelligence
from core.order_flow import OrderFlowAnalyzer
from core.telegram_notifier import TelegramNotifier
from brain.gemini_analyzer import GeminiAnalyzer

logger = logging.getLogger("SmartScalper")

class SmartScalper:
    def __init__(self, mt5_manager, symbol, timeframe, volume=0.1, account_id=None):
        self.mt = mt5_manager
        self.symbol = symbol
        self.timeframe = timeframe
        self.account_id = account_id or os.getenv("DEFAULT_ACCOUNT_ID")
        self.base_volume = volume
        self.mode = "standard"
        self.last_ticket = None
        self.last_trade_context = {}
        self.in_trade = False
        self.session_filter_active = True
        self.cooldown_minutes = 60
        
        info = mt5.symbol_info(symbol)
        self.point = info.point if info else 0.0001
        self.digits = info.digits if info else 5
        self.telegram = TelegramNotifier()

        # Modular Components
        self.brain_analyzer = GeminiAnalyzer()
        self.intel = ScalperIntelligence(self.brain_analyzer, self.symbol)
        self.risk_engine = ScalperRiskEngine(self.symbol, self.brain_analyzer, "config_scalper.json", self.digits)
        
        self.load_config()

    def set_mode(self, new_mode: str):
        """Switch between 'standard' and 'aggressive' trading modes."""
        self.mode = new_mode
        # Persist so it survives restarts
        try:
            cfg = {}
            if os.path.exists("config_scalper.json"):
                with open("config_scalper.json", "r") as f:
                    cfg = json.load(f)
            cfg["mode"] = new_mode
            with open("config_scalper.json", "w") as f:
                json.dump(cfg, f, indent=4)
        except: pass

    def load_config(self):
        """Pulls account-specific Sovereign tuning from the cloud (Supabase)."""
        try:
            cfg = db_client.get_account_config(self.account_id)
            if not cfg:
                # Local Fallback
                with open("config_scalper.json", "r") as f:
                    cfg = json.load(f)
            
            self.rsi_oversold = cfg.get("rsi_oversold", 30)
            self.rsi_overbought = cfg.get("rsi_overbought", 70)
            self.sl_points = cfg.get("sl_points", 150)
            self.tp_points = cfg.get("tp_points", 300)
            self.mode = cfg.get("mode", "standard")
            # Secondary params default to institutional standards
            self.block_mean_reversion_high_adx = cfg.get("block_mean_reversion_high_adx", True)
            self.adx_mr_block_level = float(cfg.get("adx_mr_block_level", 38))
            self.safety_stop_usd = float(cfg.get("safety_stop_usd", 5.0))
            self.exec_max_spread_atr_ratio = float(cfg.get("exec_max_spread_atr_ratio", 1.35))
            self.atr_filter_enabled = bool(cfg.get("atr_filter_enabled", True))
            self.atr_percentile_window = int(cfg.get("atr_percentile_window", 120))
            self.atr_min_percentile = float(cfg.get("atr_min_percentile", 12.0))
            self.atr_max_percentile = float(cfg.get("atr_max_percentile", 92.0))
        except:
            self.rsi_oversold = 30
            self.rsi_overbought = 70
            self.sl_points = 150
            self.tp_points = 300
            self.block_mean_reversion_high_adx = True
            self.adx_mr_block_level = 38.0
            self.safety_stop_usd = 5.0
            self.exec_max_spread_atr_ratio = 1.35
            self.atr_filter_enabled = True
            self.atr_percentile_window = 120
            self.atr_min_percentile = 12.0
            self.atr_max_percentile = 92.0

    def analyze_and_trade(self):
        """Main execution loop for a specific symbol."""
        # 1. Guards
        if not TradingGuards.is_session_active(self.symbol): return
        if not TradingGuards.can_open_more(): return
        if not allow_new_entry(self.symbol): return
        if self.session_filter_active and not TradingGuards.is_news_safe(self.symbol): return
        
        # v4.5 Active Mode: Increased spread limit
        spread_limit = 9.0 if self.session_filter_active else 20.0
        if not TradingGuards.is_spread_valid(self.mt, self.symbol, spread_limit): return

        # 2. Management & Learning
        self.load_config()
        status = self.risk_engine.process_loss_history(self.last_ticket, self.last_trade_context)
        if status == "KILL_SWITCH":
             self.telegram.send(f"🚨 <b>EMERGENCY SHUTDOWN</b> on {self.symbol} after max strikes.", "🧨")
             self.last_ticket = None
             return
        elif status in ["LOSS", "PROFIT"]:
             self.last_ticket = None
             self.load_config() # Reload if AI adjusted config

        # 3. Position & Confluence Monitor
        from core.regime_detector import RegimeDetector
        rd = RegimeDetector(self.mt)
        confluence = rd.get_hyper_confluence(self.symbol)
        
        # INCREASE DATA DEPTH (Fixing Gemini reported ATR=0 issue)
        df_data = self.mt.get_market_data(self.symbol, self.timeframe, count=150)
        adx_val = 25
        if df_data is not None and not df_data.empty:
            df_data = SignalGenerator.calculate_indicators(df_data, self.mt, self.symbol)[0]
            row = df_data.iloc[-1]
            adx_val = float(row["ADX_14"]) if pd.notna(row.get("ADX_14")) else 25.0

        TradeExecutor.handle_trailing_stop(self.mt, self.symbol, self.point, self.digits, adx_val)

        # 4. Sovereign Multi-Tier Safety Gates (Ultra-Strong Mode)
        # 4.1. Static AI Health Exposure Scaling
        h_score = 100
        if os.path.exists("logs/ai_optimization_notes.json"):
            try:
                with open("logs/ai_optimization_notes.json", "r") as f:
                    h_score = json.load(f).get("overall_health_score", 100)
            except: pass
        
        # Reduced volume if system health is struggling
        effective_volume = self.base_volume
        if h_score < 60:
            effective_volume = round(self.base_volume * 0.5, 2)
            if effective_volume < 0.01: effective_volume = 0.01

        # 4.2. Dual-Strike Shadow Lock (Symbol Level)
        # If last 2 trades on this sym were losses, lock for 4 hours
        from strategies.smart_scalper.portfolio_guard import is_symbol_locked_by_performance
        if is_symbol_locked_by_performance(self.symbol):
            return

        all_pos = self.mt.positions_get(symbol=self.symbol)
        if all_pos and any(p.magic == 777777 for p in all_pos): return

        # 4. Signals Generation (using deeper history for stability)
        df = self.mt.get_market_data(self.symbol, self.timeframe, count=200)
        if df is None or df.empty: return
        df, bb_l_col, bb_u_col, h1_trend = SignalGenerator.calculate_indicators(df, self.mt, self.symbol)
        if not bb_l_col: return
        
        last = df.iloc[-2]
        closed_idx = len(df) - 2
        close_p, low_p, high_p = last['close'], last['low'], last['high']
        rsi_14, ema_200, ema_slope = last['RSI_14'], last['EMA_200'], last['EMA_Slope']
        adx = (
            float(last["ADX_14"])
            if "ADX_14" in last.index and pd.notna(last["ADX_14"])
            else 25.0
        )
        bb_l, bb_u = last[bb_l_col], last[bb_u_col]
        sweep_status = last.get('Liquidity_Sweep', 'NONE')

        if self.atr_filter_enabled:
            if not SignalGenerator.atr_volatility_gate(
                df,
                closed_idx,
                window=self.atr_percentile_window,
                min_percentile=self.atr_min_percentile,
                max_percentile=self.atr_max_percentile,
            ):
                return
        
        # 🏛️ REGIME CONTEXT
        from api import state
        regime_data = state.regime_detector.get_cached(self.symbol)
        regime = regime_data.get("regime", "RANGING")
        inst_consensus = regime_data.get("summary", "Neutral")

        # Momentum Filter
        if abs(ema_slope) < 0.4: return

        # Fetch Institutional Intel for Sentiment
        intel_sentiment = 50
        try:
            if os.path.exists("logs/market_intel.json"):
                with open("logs/market_intel.json", "r", encoding='utf-8') as f:
                    intel_list = json.load(f)
                    symbol_intel = next((item for item in intel_list if item['pair'] == self.symbol), {})
                    intel_sentiment = int(symbol_intel.get("sentiment_score", 50))
        except: pass

        lot = TradeExecutor.calculate_lot(self.symbol, risk_percent=1.0, sentiment=intel_sentiment)
        sl_dist, tp_dist = self.sl_points * self.point, self.tp_points * self.point
        
        setup_found = False
        action = None
        reason = None

        # 🌊 CATEGORY A: TREND-FOLLOWING (Waterfall/Moon Logic)
        if adx > 30:
            if regime == "TRENDING_DOWN" and rsi_14 > 45:
                action = "SELL"
                reason = "Waterfall Follower"
            elif regime == "TRENDING_UP" and rsi_14 < 55:
                action = "BUY"
                reason = "Moon Follower"
        
        # ⚖️ CATEGORY B: MEAN REVERSION (Standard Logic)
        if not action:
            if ((close_p > (ema_200 - 100 * self.point)) and (rsi_14 < self.rsi_oversold) and (low_p <= bb_l)) or (sweep_status == "BULLISH_SWEEP"):
                if regime != "TRENDING_DOWN" or "Buy" in inst_consensus:
                   action = "BUY"
                   reason = "Dip Hunter"
            elif ((close_p < (ema_200 + 100 * self.point)) and (rsi_14 > self.rsi_overbought) and (high_p >= bb_u)) or (sweep_status == "BEARISH_SWEEP"):
                if regime != "TRENDING_UP" or "Sell" in inst_consensus:
                   action = "SELL"
                   reason = "Peak Hunter"

        # 🚀 EXECUTION GATING (Filter Check)
        if action:
            # v5.0 Meta-Logic: Block counter-trend mean reversion when trend strength is extreme
            if self.block_mean_reversion_high_adx and adx > self.adx_mr_block_level:
                if reason in ("Dip Hunter", "Peak Hunter"):
                    DecisionJournal.log(self.symbol, "Scalper", "BLOCK", f"High ADX ({adx:.1f}) blocked MR {action}", {"adx": adx, "rsi": rsi_14, "regime": regime}, account_id=self.account_id)
                    return

        if action:
            # v5.0 Verification Chain: Surgical execution with validation
            matrix_data = {
                "rsi": rsi_14, "adx": adx, "close": close_p, "ema": ema_200, 
                "regime": regime, "inst_consensus": inst_consensus, "sentiment": intel_sentiment
            }

            if self.intel.ask_gemini_verdict(action, rsi_14, close_p):
                if not ExecutionGuard.is_liquidity_safe(self.symbol, self.mt, max_spread_atr_ratio=self.exec_max_spread_atr_ratio):
                    DecisionJournal.log(self.symbol, "Scalper", "SKIP", f"Spread unsafe for {action}", matrix_data, account_id=self.account_id)
                    return
                
                if not ExecutionGuard.is_profit_safe(self.symbol, lot, self.safety_stop_usd):
                    DecisionJournal.log(self.symbol, "Scalper", "SKIP", f"Profit potential unsafe for {action}", matrix_data, account_id=self.account_id)
                    return

                tick = mt5.symbol_info_tick(self.symbol)
                if not tick:
                    logger.error(f"Failed to get tick for {self.symbol}")
                    SnapshotManager.capture_full_state()
                    return

                price = tick.ask if action == "BUY" else tick.bid
                sl = round(price - sl_dist, self.digits) if action == "BUY" else round(price + sl_dist, self.digits)
                tp = round(price + tp_dist, self.digits) if action == "BUY" else round(price - tp_dist, self.digits)
                
                res = self.mt.open_order(self.symbol, action.lower(), lot, sl, tp)
                if res:
                    self.last_ticket = res.order
                    self.last_trade_context = {"type": action, "rsi": rsi_14, "ema_200": ema_200, "price": price}
                    DecisionJournal.log(self.symbol, "Scalper", "ENTRY", f"{reason} | Matrix Aligned", matrix_data, account_id=self.account_id)
                    self.telegram.send_trade_open(self.symbol, action, price, lot, f"Sovereign v4.5 {reason}")
                    setup_found = True
                else:
                    logger.critical(f"❌ EXECUTION FAILURE for {action} on {self.symbol}")
                    SnapshotManager.capture_full_state() # Surgical Diagnostic

        if not setup_found:
            from api.state import iteration
            if iteration % 100 == 0:
                logger.info(f"🔭 [{self.symbol}] Scanning... RSI: {rsi_14:.1f} | Regime: {regime}")

    def _is_trend_aligned(self, signal_type):
        """Cross-checks current signal with the Institutional H4 Strategic Bias."""
        from api.state import global_biases
        bias = global_biases.get(self.symbol, "NEUTRAL")
        if signal_type.upper() == "BUY":
            if bias == "BEARISH": return False
        elif signal_type.upper() == "SELL":
            if bias == "BULLISH": return False
        return True
