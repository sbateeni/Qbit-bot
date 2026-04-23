import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api import state
from api.utils import read_config, merge_config, CONFIG_GLOBAL, CONFIG_SCALPER, CONFIG_SWING

router = APIRouter(tags=["Config"])

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

class VirtualBalanceBody(BaseModel):
    balance: float

class TargetProfitBody(BaseModel):
    target: float

@router.get("/scalper-config")
def get_scalper_config():
    cfg = read_config(CONFIG_SCALPER)
    return {
        "rsi_oversold": cfg.get("rsi_oversold", 30),
        "rsi_overbought": cfg.get("rsi_overbought", 70),
        "sl_points": cfg.get("sl_points", 150),
        "tp_points": cfg.get("tp_points", 300),
        "target_profit_usd": cfg.get("target_profit_usd", 2.0),
        "safety_stop_usd": cfg.get("safety_stop_usd", 1.0)
    }

@router.post("/scalper-config")
def set_scalper_config(body: ScalperConfigBody):
    merge_config(CONFIG_SCALPER, body.dict())
    for bot in state.scalpers.values():
        if hasattr(bot, 'load_config'): bot.load_config()
    return {"message": "Scalper config updated locally."}

@router.get("/swing-config")
def get_swing_config():
    cfg = read_config(CONFIG_SWING)
    return {
        "tp_points": cfg.get("tp_points", 1500),
        "sl_points": cfg.get("sl_points", 500),
        "min_confidence": cfg.get("min_confidence", 80),
        "max_trades": cfg.get("max_trades", 1),
        "target_profit_usd": cfg.get("target_profit_usd", 2.0)
    }

@router.post("/swing-config")
def set_swing_config(body: SwingConfigBody):
    merge_config(CONFIG_SWING, body.dict())
    for bot in state.swing_investors.values():
        if hasattr(bot, 'load_swing_config'): bot.load_swing_config()
    return {"message": "Swing config updated"}

@router.get("/global-config")
def get_global_config():
    cfg = read_config(CONFIG_GLOBAL)
    return {"virtual_balance": cfg.get("virtual_balance", 100.0)}

@router.post("/global-config")
def set_global_config(body: dict):
    merge_config(CONFIG_GLOBAL, body)
    for bot in list(state.scalpers.values()) + list(state.swing_investors.values()):
        if hasattr(bot, 'load_config'): bot.load_config()
        if hasattr(bot, 'load_swing_config'): bot.load_swing_config()
    return {"message": "Global config updated"}

@router.get("/safety-stop")
def get_safety_stop():
    cfg = read_config(CONFIG_GLOBAL)
    return {"stop": cfg.get("safety_stop_usd", 1.0)}

@router.post("/safety-stop")
def set_safety_stop(data: dict):
    new_stop = data.get("stop", 1.0)
    merge_config(CONFIG_GLOBAL, {"safety_stop_usd": float(new_stop)})
    return {"message": f"Safety stop set to ${new_stop}", "stop": new_stop}

@router.get("/virtual-balance")
def get_virtual_balance():
    cfg = read_config(CONFIG_SCALPER)
    return {"balance": float(cfg.get("virtual_balance", 10.0))}

@router.post("/virtual-balance")
def set_virtual_balance(body: VirtualBalanceBody):
    merge_config(CONFIG_SCALPER, {"virtual_balance": body.balance})
    return {"balance": body.balance}

@router.get("/target-profit")
def get_target_profit():
    cfg = read_config(CONFIG_SCALPER)
    return {"target": float(cfg.get("target_profit_usd", 2.0))}

@router.post("/target-profit")
def set_target_profit(body: TargetProfitBody):
    merge_config(CONFIG_SCALPER, {"target_profit_usd": body.target})
    return {"target": body.target}
