"""
When TradingView / external matrix fails, build a compatible matrix from MT5 OHLC
so dashboards and swing logic still see RSI / ADX / ATR (non-zero) per timeframe.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger("MT5MatrixFallback")

TF_MAP = {
    "5M": mt5.TIMEFRAME_M5,
    "15M": mt5.TIMEFRAME_M15,
    "1H": mt5.TIMEFRAME_H1,
    "D": mt5.TIMEFRAME_D1,
}


def _empty_tf() -> Dict[str, Any]:
    return {
        "summary": "NEUTRAL",
        "ma": "NEUTRAL",
        "osc": "NEUTRAL",
        "counts": {"buy": 0, "sell": 0, "neutral": 10},
        "indicators": {"rsi": 50.0, "adx": 20.0, "atr": 0.0},
        "patterns": [],
    }


def _recommendation_from_rsi_adx(rsi: float, adx: float) -> str:
    if adx < 18:
        return "NEUTRAL"
    if rsi <= 32:
        return "STRONG_BUY" if adx > 22 else "BUY"
    if rsi <= 42:
        return "BUY"
    if rsi >= 68:
        return "STRONG_SELL" if adx > 22 else "SELL"
    if rsi >= 58:
        return "SELL"
    return "NEUTRAL"


def _counts_from_rec(rec: str) -> Dict[str, int]:
    if "STRONG_BUY" in rec:
        return {"buy": 8, "sell": 1, "neutral": 3}
    if rec == "BUY":
        return {"buy": 5, "sell": 2, "neutral": 5}
    if "STRONG_SELL" in rec:
        return {"buy": 1, "sell": 8, "neutral": 3}
    if rec == "SELL":
        return {"buy": 2, "sell": 5, "neutral": 5}
    return {"buy": 2, "sell": 2, "neutral": 8}


def build_matrix_from_mt5(mt5_mgr, symbol: str) -> Dict[str, Any]:
    matrix: Dict[str, Any] = {}
    for label, tf in TF_MAP.items():
        df = mt5_mgr.get_market_data(symbol, tf, 180)
        if df is None or len(df) < 50:
            matrix[label] = _empty_tf()
            continue
        try:
            c = df["close"]
            rsi_s = ta.rsi(c, length=14)
            adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
            atr_s = ta.atr(df["high"], df["low"], df["close"], length=14)
            rsi = float(rsi_s.iloc[-2]) if rsi_s is not None and len(rsi_s) > 2 else 50.0
            adx = (
                float(adx_df["ADX_14"].iloc[-2])
                if adx_df is not None and "ADX_14" in adx_df.columns
                else 20.0
            )
            atr = float(atr_s.iloc[-2]) if atr_s is not None and len(atr_s) > 2 else 0.0
            if pd.isna(rsi):
                rsi = 50.0
            if pd.isna(adx):
                adx = 20.0
            if pd.isna(atr):
                atr = 0.0
            rec = _recommendation_from_rsi_adx(rsi, adx)
            counts = _counts_from_rec(rec)
            matrix[label] = {
                "summary": rec,
                "ma": "NEUTRAL",
                "osc": rec if rec != "NEUTRAL" else "NEUTRAL",
                "counts": counts,
                "indicators": {
                    "rsi": round(rsi, 2),
                    "adx": round(adx, 2),
                    "atr": round(atr, 6 if atr < 1 else 3),
                },
                "patterns": [],
            }
        except Exception as e:
            logger.debug("MT5 matrix %s %s: %s", symbol, label, e)
            matrix[label] = _empty_tf()
    return matrix


def sentiment_from_matrix(matrix: Dict[str, Any]) -> int:
    """Derive 0–100 bullish score from 1H pseudo-counts (same idea as TV path)."""
    h1 = matrix.get("1H") or {}
    counts = h1.get("counts") or {}
    b = int(counts.get("buy", 0))
    s = int(counts.get("sell", 0))
    n = int(counts.get("neutral", 1))
    tot = b + s + n
    if tot <= 0:
        return 50
    return int(round((b / tot) * 100))


def technical_summary_from_matrix(matrix: Dict[str, Any]) -> str:
    h1 = matrix.get("1H") or {}
    return str(h1.get("summary", "NEUTRAL")).replace("_", " ")
