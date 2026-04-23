import time
import datetime
import logging
import json
import threading
import os
import MetaTrader5 as mt5
from strategies.smart_scalper import SmartScalper
from strategies.swing_investor.bot import SwingInvestor
from strategies.news_sniper.bot import NewsSniper
from strategies.tv_sniper import TVSniperEngine
from core.intel_manager import IntelManager
from core.regime_detector import RegimeDetector
from core.risk_manager import RiskManager
from api import state
from brain.snapshot_manager import SnapshotManager
from brain.audit_analyst import AuditAnalyst

ENGINE_RISK_CACHE = {"dd_pct": 5.0, "hourly": 25.0, "iter": -1}


def _engine_risk_limits(iteration: int):
    """Reload risk thresholds from config.json periodically."""
    if iteration % 45 != 0 and ENGINE_RISK_CACHE["iter"] >= 0:
        return ENGINE_RISK_CACHE
    ENGINE_RISK_CACHE["iter"] = iteration
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    r = cfg.get("risk") or {}
    ENGINE_RISK_CACHE["dd_pct"] = float(r.get("max_equity_drawdown_percent", 5.0))
    ENGINE_RISK_CACHE["hourly"] = float(r.get("hourly_panic_loss_usd", 25.0))
    return ENGINE_RISK_CACHE


def run_scalper_loop():
    """Background engine managing multiple currency pairs."""
    logger = logging.getLogger("QbitBot.TradingEngine")
    
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "USDCAD", "AUDUSD", "USDCHF", "NZDUSD"]
    
    # Institutional SaaS Context
    account_id = os.getenv("DEFAULT_ACCOUNT_ID", "00000000-0000-0000-0000-000000000000")
    
    # Initialize scalper for each symbol with account context
    for sym in symbols:
        state.scalpers[sym] = SmartScalper(state.mt5_mgr, sym, mt5.TIMEFRAME_M5, volume=0.1, account_id=account_id)
        
    # Initialize Swing Investor & Sniper Engine for each symbol
    for sym in symbols:
        state.swing_investors[sym] = SwingInvestor(state.mt5_mgr, sym)
        state.sniper_engines[sym] = TVSniperEngine(state.mt5_mgr, sym)
    
    # Initialize News Sniper
    sniper = NewsSniper(state.mt5_mgr)
    
    intel_mgr = IntelManager(state.mt5_mgr)
    last_intel_update = 0
    last_audit_run = 0 # Track time for AI Audits (Throttling)
    
    # v3.0 — Phase 1 & 2: Institutional Intelligence Layer
    regime_detector = RegimeDetector(state.mt5_mgr)
    risk_manager = RiskManager(state.mt5_mgr)
    state.regime_detector = regime_detector
    state.risk_manager = risk_manager
    
    logger.info(f"Engine Started: Monitoring {len(symbols)} symbols: {symbols}")
    analyst = AuditAnalyst()
    
    while not state.stop_event.is_set():
        state.iteration += 1
        
        # 🧠 PHASE 1: Autonomous Audit (Time-Based to save Gemini Quota)
        # Runs every 1 hour (3600s) OR on the very first iteration
        now = time.time()
        if (now - last_audit_run > 3600) or (state.iteration == 1):
            logger.info(f"🤖 [SOVEREIGN CLOUD AUDIT] Starting feedback loop for {account_id[:8]}...")
            # Run with auto_apply=True and account_id
            threading.Thread(target=analyst.perform_audit, kwargs={"account_id": account_id, "auto_apply": True}, daemon=True).start()
            last_audit_run = now
            
        limits = _engine_risk_limits(state.iteration)
        acc = mt5.account_info()
        if acc:
            if state.equity_peak_session <= 0:
                state.equity_peak_session = float(acc.equity)
            else:
                state.equity_peak_session = max(state.equity_peak_session, float(acc.equity))

        if not state.mt5_mgr.check_connection():
            logger.warning("📡 [ENGINE] Connection unstable. Pausing operations...")
            time.sleep(5)
            continue

        # v5.0 Karpathy Principle: Safety Diagnostic Check
        if state.iteration % 1000 == 0:
            SnapshotManager.capture_full_state()

        was_trading = state.trading_enabled
        if state.risk_manager:
            peak = state.equity_peak_session if state.equity_peak_session > 0 else None
            is_safe = state.risk_manager.check_global_drawdown(
                max_drawdown_percent=limits["dd_pct"],
                session_equity_peak=peak,
            )
            is_hourly_safe = state.risk_manager.check_hourly_panic(max_loss_usd=limits["hourly"])

            if not is_safe or not is_hourly_safe:
                state.trading_enabled = False
                if was_trading:
                    logger.critical("🛑 [ENGINE] SYSTEM LOCKED BY RISK GUARDIAN.")

        if not state.trading_enabled:
            time.sleep(2)
            continue

        if state.iteration % 90 == 0:
            try:
                from strategies.smart_scalper.portfolio_guard import evaluate_and_arm_cooldown_from_history

                evaluate_and_arm_cooldown_from_history()
            except Exception:
                pass
        
        # 0. Global Heartbeat (Every ~10 seconds)
        if state.iteration % 10 == 0:
            pos_count = len(mt5.positions_get() or [])
            logger.info(f"🔄 Engine Heartbeat | Open: {pos_count} | Shield: {'ON' if state.session_filter_active else 'OFF'}")

        # 1. Run Scalper Bots (Optimized for higher activity in v4.5)
        for sym, bot in state.scalpers.items():
            bot.session_filter_active = state.session_filter_active
            if not mt5.symbol_select(sym, True): continue
            
            # Regime Gate: Scalper now fires in RANGING AND TRENDING markets (Pullbacks)
            # Only pauses in CHOPPY (dangerous) markets
            regime = regime_detector.detect(sym, count=50)
            if regime["regime"] == "CHOPPY":
                continue  # Silent pause — market is dead/unpredictable
            
            bot.analyze_and_trade()
                
        # 2. Run Swing Investor Bots (Ranked by Strength)
        # Get latest intel and sort symbols by sentiment_score
        intel_list = []
        for intel_path in ("logs/market_intel.json", "market_intel.json"):
            try:
                if os.path.exists(intel_path):
                    with open(intel_path, "r", encoding="utf-8") as f:
                        intel_list = json.load(f)
                    if not isinstance(intel_list, list):
                        intel_list = [intel_list]
                    break
            except Exception:
                intel_list = []

        # Create a ranking map
        ranking = {item['pair'].replace("/", "").upper(): item['sentiment_score'] for item in intel_list}
        
        # Sort swing_investors keys by ranking (descending)
        sorted_swing_keys = sorted(
            state.swing_investors.keys(), 
            key=lambda k: ranking.get(k, 0), 
            reverse=True
        )

        for sym in sorted_swing_keys:
            bot = state.swing_investors[sym]
            if not mt5.symbol_select(sym, True): continue
            
            # Regime Gate: Swing only fires in TRENDING markets
            regime = regime_detector.get_cached(sym)  # Already computed above
            if regime["regime"] == "CHOPPY":
                continue
            if regime["regime"] == "RANGING":
                continue  # Scalper's turn in ranging markets
            
            # 2. Run Swing Investor (Macro Strategy)
        for sym, swing in state.swing_investors.items():
            swing.analyze_and_invest()
            swing.monitor_and_close_positions(swing.load_swing_config())

        # 3. Run TV Sniper (Indicator-Based Sniper)
        for sym, sniper_eng in state.sniper_engines.items():
            sniper_eng.analyze_and_trade(intel_list)
            sniper_eng.manage_active_positions()
        
        # 4. Run News Sniper (High Volatility Core)
        sniper.scan_for_events()
        sniper.monitor_gaps()
        
        # 4. Phase 4: Institutional Weekend Cycler (v3.0 Auto-Optimizer)
        now_dt = datetime.datetime.now()
        if now_dt.weekday() == 5 and now_dt.hour >= 20: # Saturday after 8 PM
            try:
                with open("config_scalper.json", "r") as f:
                    cfg = json.load(f)
                last_run = cfg.get("optimizer_last_run", "")
                today_str = now_dt.strftime("%Y-%m-%d")
                
                if last_run != today_str:
                    logger.info("📅 Saturday Night: Triggering Automatic Institutional Optimizer...")
                    import subprocess
                    import sys
                    # Use absolute path to venv if exists, otherwise fallback to sys.executable
                    python_cmd = os.path.join("venv", "Scripts", "python.exe") if os.path.exists("venv") else sys.executable
                    subprocess.Popen([python_cmd, "-m", "scripts.weekend_optimizer"], start_new_session=True)
                    # We don't update the config here, the script itself will update 'optimizer_last_run' on success
            except Exception as e:
                logger.error(f"❌ Failed to trigger auto-optimizer: {e}")
                SnapshotManager.capture_full_state() # Capture state for debugging failure

        # 5. Macro Sentinel Awareness & Global Intelligence Update
        now = time.time()

        if now - state.macro_data["last_macro_update"] > 30:
            update_macro_sentinel()
            state.macro_data["last_macro_update"] = now
            
        # v4.5 Sovereign: Periodic Global Intel Refresh (Every 15 minutes)
        if now - last_intel_update > 900 and not state.stop_event.is_set(): 
            logger.info("📡 [ENGINE] Triggering Scheduled Global Intelligence Refresh for all symbols...")
            # Run in a separate thread to avoid blocking the main trading loop
            threading.Thread(target=intel_mgr.update_global_intelligence, args=(symbols,), daemon=True).start()
            last_intel_update = now
        
        # 9. Sync & Audit (v4.5) — Ensures Telegram is always accurate
        state.mt5_mgr.audit_notifications()
        
        # Check stop event here too
        if state.stop_event.is_set():
            break
            
        time.sleep(1) # Reduced from 2 for faster response to stop signal

def update_macro_sentinel():
    """Tracks DXY to provide a global context for all bots."""
    logger = logging.getLogger("MacroSentinel")
    # Most brokers use 'USDX' or 'DXY' or 'USDOLLAR'
    for dxy_sym in ["USDX", "DXY", "USDOLLAR"]:
        if mt5.symbol_select(dxy_sym, True):
            tick = mt5.symbol_info_tick(dxy_sym)
            if tick:
                prev_price = state.macro_data["dxy_price"]
                state.macro_data["dxy_price"] = tick.bid
                if prev_price > 0:
                    if tick.bid > prev_price: state.macro_data["dxy_trend"] = "UP"
                    elif tick.bid < prev_price: state.macro_data["dxy_trend"] = "DOWN"
                logger.info(f"🌍 Macro Sentinel: {dxy_sym} @ {tick.bid} ({state.macro_data['dxy_trend']})")
                return
    state.macro_data["dxy_trend"] = "NEUTRAL" # Fallback if symbol not found
