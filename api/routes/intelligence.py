import os
import json
import datetime
import logging
import math
import feedparser
from fastapi import APIRouter
from api import state
from api.utils import read_config

router = APIRouter(tags=["Intelligence"])
logger = logging.getLogger("IntelligenceRouter")

def sanitize_nan(data):
    if isinstance(data, dict):
        return {k: sanitize_nan(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_nan(v) for v in data]
    try:
        if math.isnan(data) or math.isinf(data):
            return 0.0
    except:
        pass
    return data

@router.get("/market-intelligence")
def get_market_intelligence():
    try:
        with open("logs/market_intel.json", "r", encoding='utf-8') as f:
            data = json.load(f)
            return sanitize_nan(data)
    except Exception:
        return {"technical_summary": "Neutral", "sentiment_score": 50, "ai_note": "Awaiting fresh data..."}

@router.get("/market/prices")
def get_market_prices():
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "USDCAD", "AUDUSD", "USDCHF", "NZDUSD"]
    prices = {}
    for sym in symbols:
        tick = state.mt5_mgr.symbol_info_tick(sym)
        if tick: prices[sym] = {"bid": tick.bid, "ask": tick.ask}
    return sanitize_nan(prices)

@router.get("/regimes")
def get_regimes():
    from core.regime_detector import RegimeDetector
    rd = RegimeDetector(state.mt5_mgr)
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "USDCAD", "AUDUSD", "USDCHF", "NZDUSD"]
    results = {}
    
    intel_data = {}
    if os.path.exists("logs/market_intel.json"):
        with open("logs/market_intel.json", "r", encoding='utf-8') as f:
            try:
                raw_intel = json.load(f)
                intel_data = {str(item.get("pair", "")).replace("/", "").upper(): item for item in raw_intel}
            except: pass

    for sym in symbols:
        try:
            data = rd.detect(sym, count=50)
            data["confluence"] = rd.get_hyper_confluence(sym)
            data["bias"] = state.global_biases.get(sym, "NEUTRAL")
            pair_intel = intel_data.get(sym, {})
            data["summary"] = pair_intel.get("technical_summary", "NEUTRAL")
            
            pivot_val = pair_intel.get("matrix", {}).get("D", {}).get("pivots", {}).get("classic", {}).get("pivot", "—")
            # If pivot_val is a float and is NaN, replace with "—"
            if isinstance(pivot_val, float) and math.isnan(pivot_val):
                pivot_val = "—"
            data["pivot"] = pivot_val
            
            results[sym] = data # sanitize_nan will be applied to the whole dict at the end
        except Exception:
            results[sym] = {"regime": "UNKNOWN", "adx": 0, "atr": 0, "confluence": {"score": 0}}
    return sanitize_nan(results)

@router.get("/news")
def get_market_news():
    economic = []
    try:
        from strategies.smart_scalper.guards import TradingGuards
        economic = TradingGuards.get_upcoming_news()
    except Exception: pass

    alerts = []
    try:
        feed = feedparser.parse("https://www.dailyfx.com/feeds/market-alert")
        for entry in feed.entries[:8]:
            alerts.append({"title": entry.title, "link": entry.link, "published": getattr(entry, 'published', "Just now")})
    except Exception: pass

    return {"news": alerts, "economic": economic}

@router.get("/market-status")
def get_market_status():
    from strategies.smart_scalper.guards import TradingGuards
    now = datetime.datetime.utcnow()
    utc_hour = now.hour
    
    # Session Labels
    if 0 <= utc_hour < 2 or utc_hour >= 22: session, color = "Sydney", "text-sky-400"
    elif 2 <= utc_hour < 9: session, color = "Tokyo", "text-red-400"
    elif 7 <= utc_hour < 16: session, color = "London", "text-blue-400"
    elif 13 <= utc_hour < 22: session, color = "New York", "text-emerald-400"
    else: session, color = "Overlap", "text-amber-400"
    
    system_on = state.trading_enabled
    term = state.mt5_mgr.terminal_info()
    connected = term is not None and getattr(term, "connected", False)

    if not connected:
        return {"status": "MT5 disconnected", "color": "text-rose-500", "session": "OFFLINE", "is_open": False, "system_trading_enabled": system_on, "stop_reason": "mt5_disconnected"}

    is_mt5_market = bool(TradingGuards.is_session_active("EURUSD"))
    trading_mode = "⚔️ TRADING" if (is_mt5_market and system_on) else "👁️ OBSERVATION"
    
    return {
        "status": f"Live — {session}" if is_mt5_market else "MT5 — market closed",
        "color": color if is_mt5_market else "text-rose-400",
        "session": session,
        "is_open": is_mt5_market,
        "mt5_market_open": is_mt5_market,
        "system_trading_enabled": system_on,
        "trading_mode": trading_mode,
        "utc_hour": utc_hour
    }
