import os
import json
import datetime
import time
import logging
from core.mt5_proxy import mt5
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api import state

logger = logging.getLogger("APIRouter")
router = APIRouter()

CONFIG_GLOBAL = "config.json"
CONFIG_SCALPER = "config_scalper.json"
CONFIG_SWING = "config_swing.json"
CONFIG_SNIPER = "config_sniper.json"
AI_MEMORY_PATH = "logs/ai_memory.json"

def _read_config(path: str) -> dict:
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return {}

def _merge_config(path: str, updates: dict) -> dict:
    cfg = _read_config(path)
    cfg.update(updates)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    return cfg

class VirtualBalanceBody(BaseModel):
    balance: float

class TargetProfitBody(BaseModel):
    target: float

class ScalperConfigBody(BaseModel):
    rsi_oversold: int
    rsi_overbought: int
    sl_points: int
    tp_points: int
    target_profit_usd: float
    safety_stop_usd: float

class SwingConfigBody(BaseModel):
    tp_points: int
    sl_points: int
    min_confidence: int
    max_trades: int
    target_profit_usd: float

@router.get("/scalper-config")
def get_scalper_config(account_id: str = "default"):
    """Fetch AI-tuned Scalper params from Sovereign Cloud (Supabase)."""
    from core.database_client import db_client
    acc_id = account_id if account_id != "default" else os.getenv("DEFAULT_ACCOUNT_ID")
    
    cfg = db_client.get_account_config(acc_id)
    if not cfg:
        # Fallback to local file for compatibility
        cfg = _read_config(CONFIG_SCALPER)
        
    return {
        "rsi_oversold": cfg.get("rsi_oversold", 30),
        "rsi_overbought": cfg.get("rsi_overbought", 70),
        "sl_points": cfg.get("sl_points", 150),
        "tp_points": cfg.get("tp_points", 300),
        "target_profit_usd": cfg.get("target_profit_usd", 2.0),
        "safety_stop_usd": cfg.get("safety_stop_usd", 1.0)
    }

@router.post("/scalper-config")
def set_scalper_config(body: ScalperConfigBody, account_id: str = "default"):
    """Manually update or AI-tune account configuration in the Cloud."""
    from core.database_client import db_client
    acc_id = account_id if account_id != "default" else os.getenv("DEFAULT_ACCOUNT_ID")
    
    db_client.update_account_config(acc_id, body.dict())
    
    # Notify local bots to reload if they match this account
    for bot in state.scalpers.values():
        if hasattr(bot, 'load_config'): bot.load_config()
    return {"message": "Sovereign Cloud config updated."}

@router.get("/sniper-config")
def get_sniper_config():
    from strategies.tv_sniper.config import load_config
    return load_config()

@router.post("/sniper-config")
def set_sniper_config(body: dict):
    from strategies.tv_sniper.config import save_config
    save_config(body)
    return {"message": "Sniper config updated"}

@router.get("/swing-config")
def get_swing_config():
    cfg = _read_config(CONFIG_SWING)
    return {
        "tp_points": cfg.get("tp_points", 1500),
        "sl_points": cfg.get("sl_points", 500),
        "min_confidence": cfg.get("min_confidence", 80),
        "max_trades": cfg.get("max_trades", 1),
        "target_profit_usd": cfg.get("target_profit_usd", 2.0)
    }

@router.post("/swing-config")
def set_swing_config(body: SwingConfigBody):
    _merge_config(CONFIG_SWING, body.dict())
    for bot in state.swing_investors.values():
        if hasattr(bot, 'load_swing_config'): bot.load_swing_config()
    return {"message": "Swing config updated"}

@router.get("/account")
def get_account_info():
    state.mt5_mgr.keep_alive()
    acc = mt5.account_info()
    if not acc:
        raise HTTPException(status_code=500, detail="MT5 not connected")
    
    # 0 = Demo, 1 = Real (Contest), 2 = Real
    mode = "Real" if acc.trade_mode in [mt5.ACCOUNT_TRADE_MODE_REAL, mt5.ACCOUNT_TRADE_MODE_CONTEST] else "Demo"
    
    return {
        "balance": acc.balance, 
        "equity": acc.equity, 
        "currency": acc.currency,
        "mode": mode,
        "name": acc.name,
        "server": acc.server
    }

@router.get("/global-config")
def get_global_config():
    cfg = _read_config(CONFIG_GLOBAL)
    return {
        "virtual_balance": cfg.get("virtual_balance", 100.0)
    }

@router.post("/global-config")
def set_global_config(body: dict):
    _merge_config(CONFIG_GLOBAL, body)
    # Trigger reload for all bots
    for bot in list(state.scalpers.values()) + list(state.swing_investors.values()):
        if hasattr(bot, 'load_config'): bot.load_config()
        if hasattr(bot, 'load_swing_config'): bot.load_swing_config()
    return {"message": "Global config updated"}

@router.get("/positions")
def get_open_positions():
    state.mt5_mgr.keep_alive()
    positions = mt5.positions_get()
    if not positions: return []
    return [
        {
            "ticket": p.ticket, "symbol": p.symbol, "volume": p.volume,
            "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
            "open_price": p.price_open, "current_price": p.price_current,
            "profit": p.profit, "magic": p.magic
        } for p in positions
    ]

@router.post("/positions/close/{ticket}")
def close_specific_position(ticket: int):
    success = state.mt5_mgr.close_position(ticket)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to close position {ticket}")
    return {"message": f"Position {ticket} closed"}

@router.get("/mode")
def get_current_mode():
    if state.scalpers:
        return {"mode": list(state.scalpers.values())[0].mode}
    # Fallback: read from persisted config
    cfg = _read_config(CONFIG_SCALPER)
    return {"mode": cfg.get("mode", "standard")}

@router.post("/mode/{new_mode}")
def set_trading_mode(new_mode: str):
    if not state.scalpers: raise HTTPException(status_code=503, detail="Not ready")
    if new_mode.lower() not in ["standard", "aggressive"]:
        raise HTTPException(status_code=400, detail="Invalid mode")
    for bot in state.scalpers.values():
        bot.set_mode(new_mode)
    return {"message": f"Updated to {new_mode}", "mode": new_mode}

@router.post("/panic")
def panic_button():
    success = state.mt5_mgr.close_all_positions()
    if not success: raise HTTPException(status_code=500, detail="Panic failed")
    return {"message": "Panic: All positions closed"}

@router.get("/insight")
def get_gemini_insight():
    cfg = _read_config(CONFIG_SCALPER)
    return {
        "message": f"AI has self-calibrated {cfg.get('ai_adjustment_count', 0)} times.",
        "ai_count": cfg.get("ai_adjustment_count", 0),
        "last_update": cfg.get("last_ai_update", "Never"),
        "params": {
            "rsi_oversold": cfg.get("rsi_oversold", 30),
            "rsi_overbought": cfg.get("rsi_overbought", 70),
            "sl_points": cfg.get("sl_points", 100),
            "tp_points": cfg.get("tp_points", 200),
        }
    }

@router.get("/ai-insights")
def get_ai_insights():
    """Recent Gemini adjustment summaries (Legacy Support)."""
    if not os.path.exists(AI_MEMORY_PATH):
        return []
    try:
        with open(AI_MEMORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []

@router.get("/audit/notes")
def get_audit_notes(account_id: str = "default"):
    """Fetch AI Audit Insights from local DB."""
    from core.database_client import db_client
    acc_id = account_id if account_id != "default" else os.getenv("DEFAULT_ACCOUNT_ID")
    
    notes = db_client.get_ai_notes(acc_id)
    if notes:
        return notes
        
    # Fallback to local file for backward compatibility
    if os.path.exists("logs/ai_optimization_notes.json"):
        with open("logs/ai_optimization_notes.json", "r", encoding='utf-8') as f:
            return json.load(f)
    return {}

@router.get("/trading/journal")
def get_trading_journal(account_id: str = "default"):
    """Fetch the Live Execution Logic Trace from Sovereign Cloud."""
    from core.database_client import db_client
    acc_id = account_id if account_id != "default" else os.getenv("DEFAULT_ACCOUNT_ID")
    
    # Try to fetch from DB
    res = db_client.get_recent_journal(acc_id, limit=50)
    if res:
        return res
        
    # Fallback to local file
    if os.path.exists("logs/trade_journal.json"):
        with open("logs/trade_journal.json", "r", encoding='utf-8') as f:
            try:
                return json.load(f)[-50:]
            except: pass
    return []

@router.get("/market/prices")
def get_market_prices():
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "USDCAD", "AUDUSD", "USDCHF", "NZDUSD"]
    prices = {}
    for sym in symbols:
        tick = mt5.symbol_info_tick(sym)
        if tick: prices[sym] = {"bid": tick.bid, "ask": tick.ask}
    return prices

@router.get("/regimes")
def get_regimes():
    """Returns the current market regime with Hyper-Confluence Matrix (v4.5)."""
    from core.regime_detector import RegimeDetector
    from api.state import mt5_mgr, global_biases
    
    rd = RegimeDetector(mt5_mgr)
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "USDCAD", "AUDUSD", "USDCHF", "NZDUSD"]
    results = {}
    
    # Load Intel Data (Pivots/Summaries)
    intel_data = {}
    if os.path.exists("logs/market_intel.json"):
        with open("logs/market_intel.json", "r", encoding='utf-8') as f:
            try:
                raw_intel = json.load(f)
                intel_data = {
                    str(item.get("pair", "")).replace("/", "").upper(): item
                    for item in raw_intel
                }
            except: pass

    for sym in symbols:
        try:
            # Main Regime + Confluence (M15, H1, H4)
            data = rd.detect(sym, count=50)
            data["confluence"] = rd.get_hyper_confluence(sym)
            data["bias"] = global_biases.get(sym, "NEUTRAL")
            
            # Inject Intel Data
            pair_intel = intel_data.get(sym, {})
            data["summary"] = pair_intel.get("technical_summary", "NEUTRAL")
            data["pivot"] = pair_intel.get("matrix", {}).get("D", {}).get("pivots", {}).get("classic", {}).get("pivot", "—")
            
            results[sym] = data
        except Exception as e:
            logger.error(f"Error fetching regime for {sym}: {e}")
            results[sym] = {"regime": "UNKNOWN", "adx": 0, "atr": 0, "confluence": {"score": 0}}
            
    return results

@router.post("/unlock-system")
def unlock_system():
    """Manually resets the Equity Guardian and enables trading."""
    state.trading_enabled = True
    return {"message": "System unlocked. Trading resumed."}

@router.get("/logs")
def get_bot_logs():
    return list(state.log_buffer)

@router.get("/trading/status")
def get_trading_status():
    cooldown = False
    cooldown_rem = 0
    if state.scalpers:
        for bot in state.scalpers.values():
            if hasattr(bot, 'last_loss_time') and bot.last_loss_time:
                elapsed = (datetime.datetime.now() - bot.last_loss_time).total_seconds() / 60
                if elapsed < bot.cooldown_minutes:
                    cooldown = True
                    cooldown_rem = max(cooldown_rem, bot.cooldown_minutes - elapsed)
    
    return {
        "enabled": state.trading_enabled,
        "cooldown": cooldown,
        "cooldown_remaining": round(cooldown_rem, 1)
    }

@router.post("/trading/start")
def start_trading():
    state.trading_enabled = True
    return {"message": "Started", "enabled": True}

@router.post("/trading/pause")
def pause_trading():
    state.trading_enabled = False
    return {"message": "Paused", "enabled": False}

def disable_trading():
    """Internal helper to disarm the system on emergency."""
    state.trading_enabled = False
    _merge_config(CONFIG_GLOBAL, {"trading_enabled": False})
    logger.error("🛑 SYSTEM DISARMED: Emergency disable triggered.")

@router.get("/trading/filter-status")
def get_filter_status():
    return {"active": state.session_filter_active}

@router.post("/trading/filter/toggle")
def toggle_session_filter():
    state.session_filter_active = not state.session_filter_active
    return {"active": state.session_filter_active}

@router.get("/virtual-balance")
def get_virtual_balance():
    cfg = _read_config(CONFIG_SCALPER)
    return {"balance": float(cfg.get("virtual_balance", 10.0))}

@router.post("/virtual-balance")
def set_virtual_balance(body: VirtualBalanceBody):
    _merge_config(CONFIG_SCALPER, {"virtual_balance": body.balance})
    return {"balance": body.balance}

@router.get("/target-profit")
def get_target_profit():
    cfg = _read_config(CONFIG_SCALPER)
    return {"target": float(cfg.get("target_profit_usd", 2.0))}

@router.post("/target-profit")
def set_target_profit(body: TargetProfitBody):
    _merge_config(CONFIG_SCALPER, {"target_profit_usd": body.target})
    return {"target": body.target}

@router.get("/history")
def get_trade_history(period: str = "day"):
    state.mt5_mgr.keep_alive()
    now_ts = int(time.time())
    start_ts = now_ts - 86400 # Default 1 day
    if period == "week": start_ts = now_ts - 604800
    elif period == "month": start_ts = now_ts - 2592000
    elif period == "year": start_ts = now_ts - 31536000
    elif period == "all": start_ts = 0

    trade_list = []
    total_profit = 0
    
    # Get all deals including positions
    deals = mt5.history_deals_get(start_ts, now_ts + 86400)
    if not deals: return {"total_profit": 0, "trades": []}
    
    # Map Magic to Name Helper
    def get_strategy(magic):
        if magic == 123456: return "Scalper"
        if magic == 777777: return "Swing"
        if magic == 999999: return "Sniper"
        return "Manual"

    for d in deals:
        # We look for EXIT deals (out or in/out) as they represent a closed profit
        if d.profit != 0 and d.symbol:
            # TRY TO FIND MAGIC: In MT5, EXIT deals might lose the magic. 
            # We look at the magic property, if 0, we try to find it in the position history
            magic = d.magic
            if magic == 0:
                # Search for the ENTRY deal of this position to find the magic
                pos_id = d.position_id
                entry_deals = mt5.history_deals_get(position=pos_id)
                if entry_deals:
                    for ed in entry_deals:
                        if ed.magic != 0:
                            magic = ed.magic
                            break
            
            trade_list.append({
                "ticket": d.order, "symbol": d.symbol, "profit": round(d.profit, 2),
                "volume": round(d.volume, 2),
                "strategy": get_strategy(magic),
                "magic": magic,
                "time": datetime.datetime.fromtimestamp(d.time).strftime("%d/%m %H:%M")
            })
            total_profit += d.profit
    return {"total_profit": round(total_profit, 2), "trades": trade_list[::-1][:50]}

@router.get("/analytics")
def get_analytics(period: str = "all"):
    state.mt5_mgr.keep_alive()
    now_ts = int(time.time())
    start_ts = 0
    if period == "day": start_ts = now_ts - 86400
    elif period == "week": start_ts = now_ts - 604800
    elif period == "month": start_ts = now_ts - 2592000

    deals = mt5.history_deals_get(start_ts, now_ts + 86400)
    if not deals: return {"total_profit": 0, "win_rate": 0, "total_trades": 0, "strategies": {}}

    def get_strategy(magic):
        if magic == 123456: return "Scalper"
        if magic == 777777: return "Swing"
        if magic == 999999: return "Sniper"
        return "Manual"

    wins = 0
    total = 0
    gross_profit = 0
    gross_loss = 0
    strat_perf = {}

    for d in deals:
        if d.profit != 0 and d.symbol:
            profit = d.profit
            total += 1
            if profit > 0:
                wins += 1
                gross_profit += profit
            else:
                gross_loss += abs(profit)
                
            magic = d.magic
            if magic == 0:
                pos_id = d.position_id
                entry_deals = mt5.history_deals_get(position=pos_id)
                if entry_deals:
                    for ed in entry_deals:
                        if ed.magic != 0:
                            magic = ed.magic
                            break
            
            strat = get_strategy(magic)
            if strat not in strat_perf:
                strat_perf[strat] = {"profit": 0, "trades": 0, "wins": 0}
            strat_perf[strat]["profit"] += profit
            strat_perf[strat]["trades"] += 1
            if profit > 0: strat_perf[strat]["wins"] += 1

    win_rate = (wins / total * 100) if total > 0 else 0
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (round(gross_profit, 2) if gross_profit > 0 else 0)

    for s in strat_perf:
        s_trades = strat_perf[s]["trades"]
        strat_perf[s]["win_rate"] = round((strat_perf[s]["wins"] / s_trades * 100), 1) if s_trades > 0 else 0
        strat_perf[s]["profit"] = round(strat_perf[s]["profit"], 2)

    return {
        "total_profit": round(gross_profit - gross_loss, 2),
        "win_rate": round(win_rate, 1),
        "total_trades": total,
        "profit_factor": profit_factor,
        "strategies": strat_perf
    }

def _fx_session_label(utc_hour: int) -> tuple:
    """Cosmetic FX session name from UTC hour (dashboard only; not a trade gate)."""
    if 0 <= utc_hour < 2 or utc_hour >= 22:
        session, session_color = "Sydney", "text-sky-400"
    elif 2 <= utc_hour < 9:
        session, session_color = "Tokyo", "text-red-400"
    elif 7 <= utc_hour < 16:
        session, session_color = "London", "text-blue-400"
    elif 13 <= utc_hour < 22:
        session, session_color = "New York", "text-emerald-400"
    else:
        session, session_color = "Overlap", "text-amber-400"
    if 13 <= utc_hour < 16:
        session = "London-NY Overlap 🔥"
        session_color = "text-amber-400"
    return session, session_color


@router.get("/market-status")
def get_market_status():
    """
    Dashboard truth: MT5 connection + fresh quotes + trade mode.
    Does NOT use local weekend calendar to override the broker.
    """
    import datetime

    from strategies.smart_scalper.guards import TradingGuards

    now = datetime.datetime.utcnow()
    utc_hour = now.hour
    session, session_color = _fx_session_label(utc_hour)
    system_on = bool(getattr(state, "trading_enabled", True))

    term = mt5.terminal_info()
    connected = term is not None and getattr(term, "connected", False)

    if not connected:
        return {
            "status": "MT5 disconnected",
            "color": "text-rose-500",
            "session": "OFFLINE",
            "is_open": False,
            "mt5_market_open": False,
            "system_trading_enabled": system_on,
            "stop_reason": "mt5_disconnected",
            "trading_mode": "👁️ OBSERVATION",
            "utc_hour": utc_hour,
        }

    is_mt5_market = bool(TradingGuards.is_session_active("EURUSD"))

    if not is_mt5_market:
        return {
            "status": "MT5 — market closed / no fresh quotes",
            "color": "text-rose-400",
            "session": "MT5_CLOSED",
            "is_open": False,
            "mt5_market_open": False,
            "system_trading_enabled": system_on,
            "stop_reason": "mt5_market_closed",
            "trading_mode": "👁️ OBSERVATION",
            "utc_hour": utc_hour,
        }

    trading_mode = "⚔️ TRADING" if (is_mt5_market and system_on) else "👁️ OBSERVATION"
    return {
        "status": f"Live — {session}",
        "color": session_color,
        "session": session,
        "is_open": True,
        "mt5_market_open": True,
        "system_trading_enabled": system_on,
        "stop_reason": None if system_on else "system_paused",
        "utc_hour": utc_hour,
        "trading_mode": trading_mode,
    }


@router.get("/trading/journal")
def get_trading_journal():
    """Returns the latest institutional decision log."""
    path = "logs/trade_journal.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            try:
                data = json.load(f)
                return data[-20:] # Return last 20 entries
            except:
                return []
    return []

@router.get("/audit/notes")
def get_audit_notes():
    """Returns strategic AI optimization notes."""
    path = "logs/ai_optimization_notes.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            try:
                return json.load(f)
            except:
                return {
            "strategic_note": "Awaiting first autonomous audit cycle...",
            "suggested_tweaks": [],
            "overall_health_score": 100
        }
    return {
            "strategic_note": "Awaiting first autonomous audit cycle...",
            "suggested_tweaks": [],
            "overall_health_score": 100
        }

@router.get("/news")
def get_market_news():
    from strategies.smart_scalper.guards import TradingGuards
    return TradingGuards.get_upcoming_news()

@router.get("/audit/snapshot")
def get_system_snapshot():
    from brain.snapshot_manager import SnapshotManager
    return SnapshotManager.capture_full_state()

@router.get("/strategy/evolution")
def get_evolution():
    if not os.path.exists("logs/strategy_evolution.json"): return []
    with open("logs/strategy_evolution.json", "r") as f:
        return json.load(f)[::-1][:50]
