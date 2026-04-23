"""
Portfolio-level risk for Smart Scalper (magic 123456):
caps concurrent exposure, USD-cluster size, rolling loss budgets, and cooldowns after loss clusters.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import MetaTrader5 as mt5

logger = logging.getLogger("ScalperPortfolioGuard")

SCALPER_MAGIC = 123456
CIRCUIT_PATH = os.path.join("logs", "scalper_portfolio_circuit.json")
CONFIG_PATH = "config_scalper.json"


def _load_cfg() -> Dict[str, Any]:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _circuit_path() -> str:
    os.makedirs(os.path.dirname(CIRCUIT_PATH), exist_ok=True)
    return CIRCUIT_PATH


def _read_circuit() -> Dict[str, Any]:
    path = _circuit_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_circuit(data: Dict[str, Any]) -> None:
    try:
        with open(_circuit_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error("Failed to write scalper circuit file: %s", e)


def _is_usd_pair(symbol: str) -> bool:
    s = symbol.upper().replace("/", "")
    return "USD" in s


def _closed_scalper_deals(from_dt: datetime.datetime, to_dt: datetime.datetime) -> List[Any]:
    deals = mt5.history_deals_get(from_dt, to_dt)
    if not deals:
        return []
    out = []
    for d in deals:
        if getattr(d, "magic", 0) != SCALPER_MAGIC:
            continue
        if getattr(d, "entry", None) == mt5.DEAL_ENTRY_OUT:
            out.append(d)
    return out


def _sum_profit(deals: List[Any]) -> float:
    return float(sum(getattr(d, "profit", 0.0) for d in deals))


def _open_scalper_positions() -> List[Any]:
    pos = mt5.positions_get()
    if not pos:
        return []
    return [p for p in pos if getattr(p, "magic", 0) == SCALPER_MAGIC]


def _global_cooldown_active(cfg: Dict[str, Any]) -> Tuple[bool, str]:
    c = _read_circuit()
    until_s = c.get("global_cooldown_until")
    if not until_s:
        return False, ""
    try:
        until = datetime.datetime.fromisoformat(until_s)
    except Exception:
        _write_circuit({})
        return False, ""
    if datetime.datetime.now() >= until:
        _write_circuit({})
        return False, ""
    return True, c.get("reason", "cooldown")


def set_global_cooldown(minutes: int, reason: str) -> None:
    until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    _write_circuit(
        {
            "global_cooldown_until": until.isoformat(timespec="seconds"),
            "reason": reason,
            "set_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
    )
    logger.warning("Scalper portfolio cooldown %sm — %s", minutes, reason)


def allow_new_entry(symbol: str) -> bool:
    """
    Returns True if this symbol may open a new Scalper position.
    """
    cfg = _load_cfg()
    blocked, why = _global_cooldown_active(cfg)
    if blocked:
        logger.info("Portfolio guard: blocked (%s)", why)
        return False

    open_pos = _open_scalper_positions()
    max_sym = int(cfg.get("portfolio_max_scalper_positions", 4))
    if len(open_pos) >= max_sym:
        logger.info("Portfolio guard: max scalper positions %s/%s", len(open_pos), max_sym)
        return False

    max_usd = int(cfg.get("portfolio_max_usd_pairs_open", 4))
    if _is_usd_pair(symbol):
        usd_open = sum(1 for p in open_pos if _is_usd_pair(getattr(p, "symbol", "")))
        if usd_open >= max_usd:
            logger.info("Portfolio guard: USD-cluster cap %s/%s", usd_open, max_usd)
            return False

    now = datetime.datetime.now()
    sym_cd = int(cfg.get("portfolio_symbol_loss_cooldown_minutes", 12))
    if sym_cd > 0:
        deals = _closed_scalper_deals(now - datetime.timedelta(minutes=sym_cd * 3), now)
        deals.sort(key=lambda d: int(getattr(d, "time", 0)))
        for d in reversed(deals):
            if getattr(d, "symbol", "") != symbol:
                continue
            if getattr(d, "profit", 0) < 0:
                t = datetime.datetime.fromtimestamp(int(d.time))
                if (now - t).total_seconds() < sym_cd * 60:
                    logger.info("Portfolio guard: symbol %s in post-loss cooldown", symbol)
                    return False
            break

    hourly_cap = float(cfg.get("portfolio_hourly_loss_cap_usd", 55.0))
    if hourly_cap > 0:
        h_deals = _closed_scalper_deals(now - datetime.timedelta(hours=1), now)
        pnl_h = _sum_profit(h_deals)
        if pnl_h <= -hourly_cap:
            logger.warning("Portfolio guard: hourly loss floor hit (%.2f <= -%.2f)", pnl_h, hourly_cap)
            set_global_cooldown(int(cfg.get("portfolio_hourly_cooldown_minutes", 20)), "hourly_loss_cap")
            return False

    daily_cap = float(cfg.get("portfolio_daily_loss_cap_usd", 200.0))
    if daily_cap > 0:
        d_deals = _closed_scalper_deals(now - datetime.timedelta(hours=24), now)
        pnl_d = _sum_profit(d_deals)
        if pnl_d <= -daily_cap:
            logger.warning("Portfolio guard: daily loss floor hit (%.2f <= -%.2f)", pnl_d, daily_cap)
            set_global_cooldown(int(cfg.get("portfolio_daily_cooldown_minutes", 120)), "daily_loss_cap")
            return False

    win_m = int(cfg.get("portfolio_loss_cluster_minutes", 40))
    min_losses = int(cfg.get("portfolio_loss_cluster_count", 5))
    cd_m = int(cfg.get("portfolio_cluster_cooldown_minutes", 25))
    if win_m > 0 and min_losses > 0 and cd_m > 0:
        recent = _closed_scalper_deals(now - datetime.timedelta(minutes=win_m), now)
        losses = [d for d in recent if getattr(d, "profit", 0) < 0]
        if len(losses) >= min_losses:
            set_global_cooldown(cd_m, f"loss_cluster_{len(losses)}_in_{win_m}m")
            logger.warning(
                "Portfolio guard: loss cluster (%s losses in %sm) — cooldown %sm",
                len(losses),
                win_m,
                cd_m,
            )
            return False

    return True


def evaluate_and_arm_cooldown_from_history() -> None:
    """
    Optional safety net: if the bot restarts mid-storm, next tick can arm cooldown from recent deals.
    Called from trading loop occasionally (not every second).
    """
    cfg = _load_cfg()
    blocked, _ = _global_cooldown_active(cfg)
    if blocked:
        return
    now = datetime.datetime.now()
    win_m = int(cfg.get("portfolio_loss_cluster_minutes", 40))
    min_losses = int(cfg.get("portfolio_loss_cluster_count", 5))
    cd_m = int(cfg.get("portfolio_cluster_cooldown_minutes", 25))
    if win_m <= 0 or min_losses <= 0:
        return
    recent = _closed_scalper_deals(now - datetime.timedelta(minutes=win_m), now)
    losses = [d for d in recent if getattr(d, "profit", 0) < 0]
    if len(losses) >= min_losses:
        set_global_cooldown(cd_m, f"loss_cluster_{len(losses)}_in_{win_m}m_restart")


def optimizer_note_matches_rsi(cfg: Dict[str, Any]) -> Optional[bool]:
    """True if optimizer_note RSI(lb/ub) matches rsi_oversold/overbought; None if not parseable."""
    note = cfg.get("optimizer_note") or ""
    m = re.search(r"RSI\(\s*(\d+)\s*/\s*(\d+)\s*\)", note, re.I)
    if not m:
        return None
    lb, ub = int(m.group(1)), int(m.group(2))
def is_symbol_locked_by_performance(symbol: str) -> bool:
    """
    Shadow Lock: If the last 2 trades for this symbol were losses, 
    lock it for 4 hours to prevent revenge trading or catching a bad trend.
    """
    now = datetime.datetime.now()
    # Check last 12 hours for the last 2 deals
    deals = _closed_scalper_deals(now - datetime.timedelta(hours=12), now)
    deals.sort(key=lambda d: int(getattr(d, "time", 0)))
    
    sym_deals = [d for d in deals if getattr(d, "symbol", "") == symbol]
    if len(sym_deals) < 2:
        return False
    
    # Check if the last TWO are losses
    last_two = sym_deals[-2:]
    if all(getattr(d, "profit", 0) < 0 for d in last_two):
        last_loss_time = datetime.datetime.fromtimestamp(int(last_two[-1].time))
        if (now - last_loss_time).total_seconds() < 4 * 3600: # 4 Hour Shadow Lock
            logger.warning(f"🛡️ ULTRA-STRONG GUARD: Symbol {symbol} is SHADOW LOCKED for 4 hours due to dual losses.")
            return True
            
    return False
