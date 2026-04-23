import os
import json
import datetime
import time
import math
from fastapi import APIRouter, HTTPException
from core.mt5_proxy import mt5
from api import state
from api.utils import read_config, merge_config, CONFIG_GLOBAL, CONFIG_SCALPER

router = APIRouter(tags=["Trading"])

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

@router.get("/account")
def get_account_info():
    acc = state.mt5_mgr.account_info()
    if not acc:
        raise HTTPException(status_code=500, detail="MT5 not connected")
    mode = "Real" if acc.trade_mode in [mt5.ACCOUNT_TRADE_MODE_REAL, mt5.ACCOUNT_TRADE_MODE_CONTEST] else "Demo"
    return sanitize_nan({
        "balance": acc.balance, 
        "equity": acc.equity, 
        "currency": acc.currency,
        "mode": mode,
        "name": acc.name,
        "server": acc.server
    })

@router.get("/positions")
def get_open_positions():
    positions = state.mt5_mgr.positions_get()
    if not positions: return []
    return sanitize_nan([
        {
            "ticket": p.ticket, "symbol": p.symbol, "volume": p.volume,
            "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
            "open_price": p.price_open, "current_price": p.price_current,
            "profit": p.profit, "magic": p.magic
        } for p in positions
    ])

@router.post("/positions/close/{ticket}")
def close_specific_position(ticket: int):
    success = state.mt5_mgr.close_position(ticket)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to close position {ticket}")
    return {"message": f"Position {ticket} closed"}

@router.post("/panic")
def panic_button():
    success = state.mt5_mgr.close_all_positions()
    if not success: raise HTTPException(status_code=500, detail="Panic failed")
    return {"message": "Panic: All positions closed"}

@router.get("/mode")
def get_current_mode():
    if state.scalpers:
        return {"mode": list(state.scalpers.values())[0].mode}
    cfg = read_config(CONFIG_SCALPER)
    return {"mode": cfg.get("mode", "standard")}

@router.post("/mode/{new_mode}")
def set_trading_mode(new_mode: str):
    if not state.scalpers: raise HTTPException(status_code=503, detail="Not ready")
    for bot in state.scalpers.values():
        bot.set_mode(new_mode)
    return {"message": f"Updated to {new_mode}", "mode": new_mode}

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

@router.get("/trading/filter-status")
def get_filter_status():
    return {"active": state.session_filter_active}

@router.post("/trading/filter/toggle")
def toggle_session_filter():
    state.session_filter_active = not state.session_filter_active
    return {"active": state.session_filter_active}

@router.get("/history")
def get_trade_history(period: str = "day"):
    state.mt5_mgr.keep_alive()
    now_ts = int(time.time())
    offsets = {"day": 86400, "week": 604800, "month": 2592000, "year": 31536000, "all": now_ts}
    start_ts = now_ts - offsets.get(period, 86400)
    if period == "all": start_ts = 0

    deals = state.mt5_mgr.history_deals_get(start_ts, now_ts + 86400)
    if not deals: return {"total_profit": 0, "trades": []}
    
    trade_list = []
    total_profit = 0
    magics = {123456: "Scalper", 777777: "Swing", 999999: "Sniper"}

    for d in deals:
        if d.profit != 0 and d.symbol:
            magic = d.magic
            if magic == 0: # Try entry deal search
                entry_deals = state.mt5_mgr.history_deals_get(position=d.position_id)
                if entry_deals:
                    for ed in entry_deals:
                        if ed.magic != 0: magic = ed.magic; break
            
            trade_list.append({
                "ticket": d.order, "symbol": d.symbol, "profit": round(d.profit, 2),
                "volume": round(d.volume, 2),
                "strategy": magics.get(magic, "Manual"),
                "time": datetime.datetime.fromtimestamp(d.time).strftime("%d/%m %H:%M")
            })
            total_profit += d.profit
    return sanitize_nan({"total_profit": round(total_profit, 2), "trades": trade_list[::-1][:50]})

@router.get("/trading/journal")
def get_trading_journal():
    path = "logs/trade_journal.json"
    if os.path.exists(path):
        with open(path, "r", encoding='utf-8') as f:
            try:
                data = json.load(f)
                return sanitize_nan(data[-20:])
            except: return []
    return []

@router.post("/unlock-system")
def unlock_system():
    state.trading_enabled = True
    return {"message": "System unlocked. Trading resumed."}
