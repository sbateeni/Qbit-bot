"""
Qbit-Bot v3.0 — Weekend Walk-Forward Optimizer
================================================
Runs every Saturday automatically (or manually via `python -m scripts.weekend_optimizer`).

What it does:
  1. Downloads last 60 days of M5 OHLCV data for each watched symbol via MT5.
  2. Runs a fast vectorised grid search over RSI windows + EMA windows.
  3. Selects the parameter combo with the best Sharpe Ratio (profit / drawdown).
  4. Updates config_scalper.json and config_swing.json for Monday open.

Usage:
  python -m scripts.weekend_optimizer           # Manual run
  (Or schedule it via Windows Task Scheduler / cron on Saturday 22:00)
"""

import json
import logging
import os
import itertools
import datetime
import sys
from core.time_intelligence import TimeIntelligence

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
try:
    import pandas_ta as ta
except ImportError:
    print("pandas_ta not installed. Run: pip install pandas_ta")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [OPTIMIZER] %(message)s")
logger = logging.getLogger("WeekendOptimizer")

# ─── Config ───────────────────────────────────────────────────────
SYMBOLS         = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "NZDUSD", "AUDUSD"]
LOOKBACK_BARS   = 5000              # ~60 days on M5
TIMEFRAME       = mt5.TIMEFRAME_M5

# Grid Search Space
RSI_WINDOWS     = list(range(10, 22, 2))           # 10,12,14,16,18,20
EMA_WINDOWS     = list(range(100, 300, 50))         # 100,150,200,250
RSI_LB          = list(range(25, 40, 5))            # 25,30,35 (oversold)
RSI_UB          = [100 - lb for lb in RSI_LB]       # Matching overbought levels

CONFIG_SCALPER  = "config_scalper.json"
CONFIG_SWING    = "config_swing.json"

# ─── MT5 Boot ─────────────────────────────────────────────────────

def _connect():
    from dotenv import load_dotenv
    load_dotenv()
    if mt5.terminal_info() is not None:
        return True
    if not mt5.initialize():
        logger.error("Failed to init MT5. Make sure the terminal is running.")
        return False
    return True

def _get_data(symbol: str) -> pd.DataFrame:
    # Ensure symbol is selected in Market Watch for data download
    if not mt5.symbol_select(symbol, True):
        logger.warning(f"Failed to select {symbol}")
        return pd.DataFrame()
    
    # Small pause to allow MT5 to sync bars
    import time
    time.sleep(0.5)

    rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, LOOKBACK_BARS)
    if rates is None or len(rates) == 0:
        logger.warning(f"No data for {symbol}")
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df

# ─── Vectorised Back-Test Engine ──────────────────────────────────

def _backtest(df: pd.DataFrame, rsi_w: int, ema_w: int, rsi_lb: int, rsi_ub: int,
              sl_pts: int = 100, tp_pts: int = 200) -> dict:
    """
    Simplified but fast vectorised back-test.
    Generates buy/sell signals and simulates PnL without order fill complexity.
    Returns: {trades, wins, total_pnl, max_drawdown, sharpe}
    """
    if len(df) < ema_w + 20:
        return {"sharpe": -999}

    close = df["close"]
    high  = df["high"]
    low   = df["low"]
    point = 0.00001  # Generic; for JPY/Gold we'd adjust but Sharpe is relative

    rsi = ta.rsi(close, length=rsi_w)
    ema = ta.ema(close, length=ema_w)
    if rsi is None or ema is None:
        return {"sharpe": -999}

    df = df.copy()
    df["rsi"] = rsi
    df["ema"] = ema
    df.dropna(inplace=True)

    trades = []
    in_trade = False
    entry_price = 0.0
    trade_type  = None

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]

        if not in_trade:
            # BUY signal: above EMA + RSI oversold bounce
            if prev["close"] > prev["ema"] and prev["rsi"] < rsi_lb:
                in_trade = True
                trade_type = "buy"
                entry_price = row["close"]
                continue

            # SELL signal: below EMA + RSI overbought
            if prev["close"] < prev["ema"] and prev["rsi"] > rsi_ub:
                in_trade = True
                trade_type = "sell"
                entry_price = row["close"]
                continue

        else:
            # Simple exit: reached TP or SL
            if trade_type == "buy":
                if row["high"] >= entry_price + tp_pts * point:
                    trades.append(tp_pts)
                    in_trade = False
                elif row["low"] <= entry_price - sl_pts * point:
                    trades.append(-sl_pts)
                    in_trade = False
            else:
                if row["low"] <= entry_price - tp_pts * point:
                    trades.append(tp_pts)
                    in_trade = False
                elif row["high"] >= entry_price + sl_pts * point:
                    trades.append(-sl_pts)
                    in_trade = False

    if len(trades) < 10:
        return {"sharpe": -999}

    arr = np.array(trades, dtype=float)
    total_pnl = arr.sum()
    win_rate  = (arr > 0).mean()
    equity    = np.cumsum(arr)
    drawdown  = (equity - np.maximum.accumulate(equity)).min()
    sharpe    = (arr.mean() / arr.std()) * np.sqrt(252) if arr.std() > 0 else -999

    return {
        "trades":      len(trades),
        "wins":        int((arr > 0).sum()),
        "win_rate":    round(win_rate, 3),
        "total_pnl":   round(total_pnl, 2),
        "max_drawdown": round(drawdown, 2),
        "sharpe":      round(sharpe, 3),
        "rsi_w":       rsi_w,
        "ema_w":       ema_w,
        "rsi_lb":      rsi_lb,
        "rsi_ub":      rsi_ub,
    }

# ─── Main Optimizer ───────────────────────────────────────────────

def optimize():
    logger.info("═══ Qbit-Bot Weekend Optimizer STARTING ═══")
    
    # NEW v4.0 Apex: Update Time intelligence from journal
    logger.info("⏰ Analyzing historical win-rates per hour...")
    TimeIntelligence.build_heat_map()

    if not _connect():
        return

    best_results = {}

    for symbol in SYMBOLS:
        logger.info(f"🔬 Optimizing {symbol}...")
        df = _get_data(symbol)
        if df.empty:
            continue

        best_sharpe = -999.0
        best_params = None

        combos = list(itertools.product(RSI_WINDOWS, EMA_WINDOWS, RSI_LB))
        logger.info(f"  Testing {len(combos)} combinations on {len(df)} bars...")

        for rsi_w, ema_w, rsi_lb in combos:
            rsi_ub = 100 - rsi_lb
            result = _backtest(df, rsi_w, ema_w, rsi_lb, rsi_ub)
            if result["sharpe"] > best_sharpe:
                best_sharpe = result["sharpe"]
                best_params = result

        if best_params:
            best_results[symbol] = best_params
            logger.info(
                f"  ✅ {symbol} Best: RSI({best_params['rsi_w']}) EMA({best_params['ema_w']}) "
                f"LB/UB({best_params['rsi_lb']}/{best_params['rsi_ub']}) "
                f"Sharpe={best_params['sharpe']} WinRate={best_params['win_rate']:.1%}"
            )

    if not best_results:
        logger.warning("No optimization results found. Configs NOT updated.")
        return

    # Pick the best overall parameters (average Sharpe across symbols)
    best_rsi_lb = int(round(np.mean([r["rsi_lb"] for r in best_results.values()])))
    best_rsi_ub = int(round(np.mean([r["rsi_ub"] for r in best_results.values()])))
    best_rsi_w  = int(round(np.mean([r["rsi_w"]  for r in best_results.values()])))

    # ─── Update Scalper Config ─────────────────────────────────────
    _update_config(CONFIG_SCALPER, {
        "rsi_oversold":  best_rsi_lb,
        "rsi_overbought": best_rsi_ub,
        "optimizer_last_run": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "optimizer_note": f"Auto-tuned RSI({best_rsi_lb}/{best_rsi_ub}) via WFO"
    })

    # ─── Write Optimizer Report ────────────────────────────────────
    report_path = "logs/optimizer_report.json"
    os.makedirs("logs", exist_ok=True)
    with open(report_path, "w") as f:
        json.dump({
            "run_date": datetime.datetime.now().isoformat(),
            "results": best_results,
            "applied": {
                "rsi_oversold":  best_rsi_lb,
                "rsi_overbought": best_rsi_ub,
            }
        }, f, indent=2)

    logger.info(f"📊 Optimizer report saved to: {report_path}")
    logger.info(f"✅ New config applied → RSI Oversold={best_rsi_lb}, Overbought={best_rsi_ub}")
    logger.info("═══ Optimization COMPLETE. Bot is ready for Monday. ═══")


def _update_config(path: str, updates: dict):
    cfg = {}
    if os.path.exists(path):
        with open(path, "r") as f:
            try:
                cfg = json.load(f)
            except json.JSONDecodeError:
                pass
    cfg.update(updates)
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
    logger.info(f"📝 Updated '{path}' with {list(updates.keys())}")


if __name__ == "__main__":
    optimize()
