"""
Qbit-Bot Sovereign Cloud API
Cloud API Entry Point
"""
import os
from typing import Any, Dict, List
from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.auth import get_current_user
from core.broker_factory import get_broker_for_account
from core.database_client import db_client

app = FastAPI(title="Qbit-Bot Sovereign Cloud API", version="5.0")

# CORS for SaaS frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Local-DB API Routes ==========

class _NoopMT5Manager:
    def keep_alive(self):
        return True

    def open_order(self, *args, **kwargs):
        return None

    def close_position(self, *args, **kwargs):
        return False


mt5_manager = _NoopMT5Manager()


class BrokerConnectionBody(BaseModel):
    account_id: str
    provider: str = Field(default="fxcm")
    broker_account_id: str
    api_key: str
    environment: str = Field(default="demo")


class RiskLimitBody(BaseModel):
    account_id: str
    max_daily_loss: float = 100.0
    max_open_trades: int = 3
    max_position_size: float = 1000
    allowed_instruments: list[str] = Field(default_factory=lambda: ["EUR_USD"])


class TradeIntentBody(BaseModel):
    account_id: str
    strategy: str
    symbol: str
    side: str
    units: float
    stop_loss: float | None = None
    take_profit: float | None = None


@app.get("/api/health")
def health():
    return {
        "status": "online",
        "version": "5.0 Sovereign SaaS",
        "environment": os.getenv("VERCEL_ENV", "local"),
        "database": f"local-{db_client.mode}"
    }


@app.get("/")
def root():
    return {
        "service": "Qbit-Bot API",
        "status": "online",
        "docs": "/docs",
        "health": "/api/health",
        "ops_health": "/api/v2/ops/health",
        "message": "API is running. Use /docs for interactive endpoints.",
    }


@app.get("/api/audit/notes")
def get_audit_notes(account_id: str = None):
    """AI Audit Insights from local DB."""
    if not account_id:
        return {}
    return db_client.get_ai_notes(account_id)


@app.get("/api/trading/journal")
def get_journal(account_id: str = None, limit: int = 50):
    """Trade execution journal from local DB."""
    if not account_id:
        return []
    return db_client.get_recent_journal(account_id, limit=limit)


@app.get("/api/market/intelligence")
def get_market_intelligence():
    """Global market snapshots (local DB)."""
    return db_client.get_market_intelligence()


@app.get("/api/accounts")
def get_accounts(user_id: str = None):
    """Fetch trading accounts for a local user."""
    if not user_id:
        return []
    return db_client.get_accounts_for_user(user_id)


@app.get("/api/v2/accounts")
def get_my_accounts(user: Dict[str, Any] = Depends(get_current_user)):
    return db_client.get_accounts_for_user(user["id"])


@app.post("/api/v2/broker/connection")
def save_broker_connection(body: BrokerConnectionBody, user: Dict[str, Any] = Depends(get_current_user)):
    db_client.upsert_broker_connection(
        user_id=user["id"],
        account_id=body.account_id,
        provider=body.provider,
        broker_account_id=body.broker_account_id,
        api_key=body.api_key,
        environment=body.environment,
    )
    return {"saved": True}


@app.get("/api/v2/broker/account/{account_id}")
def get_broker_account(account_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    broker = get_broker_for_account(account_id, mt5_manager)
    account = broker.get_account()
    if not account:
        raise HTTPException(status_code=404, detail="No broker account data")
    return account


@app.get("/api/v2/broker/positions/{account_id}")
def get_broker_positions(account_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    broker = get_broker_for_account(account_id, mt5_manager)
    return broker.get_positions()


@app.get("/api/v2/broker/ping/{account_id}")
def ping_broker(account_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    broker = get_broker_for_account(account_id, mt5_manager)
    account = broker.get_account()
    if not account or account.get("error"):
        return {"ok": False, "provider": "fxcm-rest", "account_id": account_id, "details": account}
    return {"ok": True, "provider": "fxcm-rest", "account_id": account_id, "details": account}


@app.post("/api/v2/risk/limits")
def save_risk_limits(body: RiskLimitBody, user: Dict[str, Any] = Depends(get_current_user)):
    db_client.upsert_risk_limits(
        body.account_id,
        {
            "max_daily_loss": body.max_daily_loss,
            "max_open_trades": body.max_open_trades,
            "max_position_size": body.max_position_size,
            "allowed_instruments": body.allowed_instruments,
        },
    )
    return {"saved": True}


@app.get("/api/v2/risk/limits/{account_id}")
def get_risk_limits(account_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    return db_client.get_risk_limits(account_id)


@app.post("/api/v2/trade/intent")
def create_trade_intent(body: TradeIntentBody, user: Dict[str, Any] = Depends(get_current_user)):
    broker = get_broker_for_account(body.account_id, mt5_manager)
    limits = db_client.get_risk_limits(body.account_id)
    if limits.get("allowed_instruments") and body.symbol not in limits.get("allowed_instruments", []):
        raise HTTPException(status_code=400, detail="Instrument not allowed by risk policy")
    if limits.get("max_position_size") and body.units > float(limits.get("max_position_size", 0)):
        raise HTTPException(status_code=400, detail="Position size exceeds risk policy")
    result = broker.open_market_order(
        symbol=body.symbol,
        side=body.side,
        units=body.units,
        stop_loss=body.stop_loss,
        take_profit=body.take_profit,
        client_tag=f"{body.strategy}:{user['id']}",
    )
    db_client.log_order_event(
        account_id=body.account_id,
        strategy=body.strategy,
        side=body.side,
        symbol=body.symbol,
        payload=body.model_dump(),
        result=result,
    )
    return result


@app.post("/api/v2/strategy/start")
def start_strategy(account_id: str, strategy: str, user: Dict[str, Any] = Depends(get_current_user)):
    run = db_client.create_strategy_run(account_id=account_id, strategy=strategy, status="running")
    return {"run": run}


@app.post("/api/v2/strategy/pause")
def pause_strategy(run_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    db_client.set_strategy_run_status(run_id, "paused")
    return {"updated": True}


@app.post("/api/v2/strategy/stop")
def stop_strategy(run_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    db_client.set_strategy_run_status(run_id, "stopped")
    return {"updated": True}


@app.get("/api/v2/strategy/runs/{account_id}")
def list_strategy_runs(account_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    return db_client.list_strategy_runs(account_id)


@app.get("/api/v2/ops/health")
def ops_health():
    return {
        "api": "ok",
        "env": os.getenv("VERCEL_ENV", "local"),
        "database": f"local-{db_client.mode}",
        "worker_mode": os.getenv("WORKER_MODE", "external"),
    }


@app.get("/api/scalper-config")
def get_scalper_config(account_id: str = None):
    """Get AI-tuned scalper parameters for an account."""
    if not account_id:
        return {
            "rsi_oversold": 30, "rsi_overbought": 70,
            "sl_points": 150, "tp_points": 300,
            "target_profit_usd": 2.0, "safety_stop_usd": 1.0
        }
    return db_client.get_account_config(account_id) or {}


# ---------- Legacy dashboard compatibility endpoints ----------
@app.get("/api/account")
def legacy_account():
    return {
        "balance": 0.0,
        "equity": 0.0,
        "currency": "USD",
        "mode": "Demo",
        "name": "Qbit Local",
        "server": "fxcm-forexconnect",
    }


@app.get("/api/news")
def legacy_news():
    return []


@app.get("/api/market-intelligence")
def legacy_market_intelligence():
    return db_client.get_market_intelligence()


@app.get("/api/history")
def legacy_history(period: str = "day"):
    return {"total_profit": 0.0, "trades": [], "period": period}


@app.get("/api/trading/filter-status")
def legacy_filter_status():
    return {"active": False}


@app.get("/api/market-status")
def legacy_market_status():
    return {
        "status": "Live",
        "session": "Cloud",
        "is_open": True,
        "mt5_market_open": True,
        "system_trading_enabled": True,
        "stop_reason": None,
        "trading_mode": "TRADING",
        "color": "text-emerald-400",
    }


@app.get("/api/logs")
def legacy_logs():
    return []


@app.get("/api/market/prices")
def legacy_market_prices():
    return {}


@app.get("/api/trading/status")
def legacy_trading_status():
    return {"enabled": True, "cooldown": False, "cooldown_remaining": 0}


@app.get("/api/positions")
def legacy_positions():
    return []


@app.get("/api/ai-insights")
def legacy_ai_insights():
    return []


@app.get("/api/strategy/evolution")
def legacy_strategy_evolution():
    return []


@app.get("/api/mode")
def legacy_mode():
    return {"mode": "standard"}


@app.get("/api/insight")
def legacy_insight():
    return {
        "message": "System running in SaaS compatibility mode.",
        "ai_count": 0,
        "last_update": "N/A",
        "params": {},
    }


@app.get("/api/regimes")
def legacy_regimes(account_id: str = "default"):
    return {"account_id": account_id, "items": {}}


@app.get("/api/global-config")
def legacy_global_config():
    return {"virtual_balance": 100.0}


@app.post("/api/global-config")
def legacy_set_global_config(body: Dict[str, Any]):
    return {"saved": True, "config": body}


# ASGI entry point
