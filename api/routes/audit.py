import os
import json
import math
from fastapi import APIRouter
from api.utils import read_config, AI_MEMORY_PATH, CONFIG_SCALPER

router = APIRouter(tags=["Audit"])

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

@router.get("/audit/snapshot")
def get_system_snapshot():
    from brain.snapshot_manager import SnapshotManager
    snapshot = SnapshotManager.capture_full_state()
    return sanitize_nan(snapshot)

@router.get("/audit/notes")
def get_audit_notes():
    path = "logs/ai_optimization_notes.json"
    if os.path.exists(path):
        with open(path, "r", encoding='utf-8') as f:
            try: return sanitize_nan(json.load(f))
            except: pass
    return {
        "strategic_note": "Awaiting first autonomous audit cycle...",
        "suggested_tweaks": [],
        "overall_health_score": 100
    }

@router.get("/strategy/evolution")
def get_evolution():
    path = "logs/strategy_evolution.json"
    if not os.path.exists(path): return []
    with open(path, "r") as f:
        try: return sanitize_nan(json.load(f)[::-1][:50])
        except: return []

@router.get("/ai-insights")
def get_ai_insights():
    """Recent Gemini adjustment summaries (Legacy Support)."""
    if not os.path.exists(AI_MEMORY_PATH): return []
    try:
        with open(AI_MEMORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return sanitize_nan(data if isinstance(data, list) else [])
    except: return []

@router.get("/insight")
def get_legacy_insight():
    cfg = read_config(CONFIG_SCALPER)
    return sanitize_nan({
        "message": f"AI has self-calibrated {cfg.get('ai_adjustment_count', 0)} times.",
        "ai_count": cfg.get("ai_adjustment_count", 0),
        "last_update": cfg.get("last_ai_update", "Never"),
        "params": {
            "rsi_oversold": cfg.get("rsi_oversold", 30),
            "rsi_overbought": cfg.get("rsi_overbought", 70),
            "sl_points": cfg.get("sl_points", 100),
            "tp_points": cfg.get("tp_points", 200),
        }
    })

@router.get("/logs")
def get_bot_logs():
    from api import state
    return list(state.log_buffer)
