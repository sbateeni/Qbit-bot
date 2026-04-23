import logging
import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger("RegimeDetector")

# ADX thresholds
TRENDING_THRESHOLD = 25   # ADX > 25 = Trending market
CHOPPY_THRESHOLD = 12     # Reduced for higher activity (v4.5)

class RegimeDetector:
    """
    Classifies the current market state for a given symbol.
    This drives capital allocation decisions between Scalper and Swing engines.
    
    Regimes:
        TRENDING_UP    → Swing gets priority, Scalper throttled
        TRENDING_DOWN  → Swing gets priority, Scalper throttled
        RANGING        → Scalper gets priority, Swing frozen
        CHOPPY         → ALL engines paused (money protection)
    """

    def __init__(self, mt5_manager):
        self.mt = mt5_manager
        self._cache = {}  # {symbol: {regime, adx, atr, timestamp}}

    def detect(self, symbol: str, timeframe=mt5.TIMEFRAME_H1, count: int = 100) -> dict:
        """
        Returns a dict: { regime, adx, atr, slope }
        regime: 'TRENDING_UP' | 'TRENDING_DOWN' | 'RANGING' | 'CHOPPY'
        """
        # Ensure symbol is active and selected for data acquisition
        if not mt5.symbol_select(symbol, True):
            return {"regime": "UNKNOWN", "adx": 0, "atr": 0}

        df = self.mt.get_market_data(symbol, timeframe, count)
        if df is None or df.empty or len(df) < 30:
            return {"regime": "UNKNOWN", "adx": 0, "atr": 0}

        # --- Calculate ADX ---
        adx_data = ta.adx(df['high'], df['low'], df['close'], length=14)
        if adx_data is None or adx_data.empty:
            return {"regime": "UNKNOWN", "adx": 0, "atr": 0}

        adx_col = [c for c in adx_data.columns if c.startswith("ADX_")]
        dmp_col  = [c for c in adx_data.columns if c.startswith("DMP_")]
        dmn_col  = [c for c in adx_data.columns if c.startswith("DMN_")]

        if not adx_col:
            return {"regime": "UNKNOWN", "adx": 0, "atr": 0}

        adx_val = float(adx_data[adx_col[0]].iloc[-1])
        dmp_val = float(adx_data[dmp_col[0]].iloc[-1]) if dmp_col else 0
        dmn_val = float(adx_data[dmn_col[0]].iloc[-1]) if dmn_col else 0

        # --- Calculate ATR (Volatility gauge) ---
        atr_series = ta.atr(df['high'], df['low'], df['close'], length=14)
        atr_val = float(atr_series.iloc[-1]) if atr_series is not None else 0.0

        # --- Classify Regime ---
        if adx_val < CHOPPY_THRESHOLD:
            regime = "CHOPPY"
        elif adx_val < TRENDING_THRESHOLD:
            regime = "RANGING"
        elif dmp_val > dmn_val:
            regime = "TRENDING_UP"
        else:
            regime = "TRENDING_DOWN"

        result = {
            "regime": regime,
            "adx": round(adx_val, 2),
            "atr": round(atr_val, 6),
            "dmp": round(dmp_val, 2),
            "dmn": round(dmn_val, 2),
        }

        self._cache[symbol] = result
        logger.info(f"[REGIME] {symbol}: {regime} (ADX={adx_val:.1f}, ATR={atr_val:.6f})")
        return result

    def is_scalper_green(self, symbol: str) -> bool:
        """Returns True if the current regime favours scalping (quick in-and-out)."""
        result = self._cache.get(symbol) or self.detect(symbol)
        return result["regime"] in ("RANGING",)

    def is_swing_green(self, symbol: str) -> bool:
        """Returns True if the current regime favours swing / trend following."""
        result = self._cache.get(symbol) or self.detect(symbol)
        return result["regime"] in ("TRENDING_UP", "TRENDING_DOWN")

    def get_strategic_bias(self, symbol: str) -> str:
        """
        Analyzes H4 timeframe to determine 'The General' direction.
        Returns: 'BULLISH', 'BEARISH', or 'NEUTRAL'
        """
        if not mt5.symbol_select(symbol, True):
            return "NEUTRAL"

        df = self.mt.get_market_data(symbol, mt5.TIMEFRAME_H4, count=100)
        if df is None or df.empty or len(df) < 50:
            return "NEUTRAL"

        ema = ta.ema(df['close'], length=50) # Strategic EMA
        if ema is None or len(ema) < 2: return "NEUTRAL"
        
        current_ema = float(ema.iloc[-1])
        prev_ema = float(ema.iloc[-2])
        price = float(df['close'].iloc[-1])

        # Bias logic: Price relative to EMA + EMA direction
        if price > current_ema and current_ema > prev_ema:
            return "BULLISH"
        elif price < current_ema and current_ema < prev_ema:
            return "BEARISH"
    def get_hyper_confluence(self, symbol: str) -> dict:
        """
        Institutional Grade Confluence: Analyzes M15, H1, and H4.
        Returns: { confluence: 'BUY'|'SELL'|'NEUTRAL', score: 0-100 }
        """
        try:
            h4_bias = self.get_strategic_bias(symbol) # Trend (H4)
            h1_regime = self.detect(symbol, mt5.TIMEFRAME_H1) # Momentum (H1)
            
            # M15 Quick Momentum
            df_m15 = self.mt.get_market_data(symbol, mt5.TIMEFRAME_M15, count=50)
            rsi_m15 = ta.rsi(df_m15['close'], length=14).iloc[-1] if df_m15 is not None else 50
            
            score = 0
            signal = "NEUTRAL"
            
            # Buying Confluence
            if h4_bias == "BULLISH": score += 40
            if h1_regime["regime"] == "TRENDING_UP": score += 30
            if rsi_m15 > 55: score += 30
            
            # Selling Confluence
            sell_score = 0
            if h4_bias == "BEARISH": sell_score += 40
            if h1_regime["regime"] == "TRENDING_DOWN": sell_score += 30
            if rsi_m15 < 45: sell_score += 30
            
            if score >= 70: signal = "BUY"
            elif sell_score >= 70: 
                signal = "SELL"
                score = sell_score
            
            return {"confluence": signal, "score": score, "m15_rsi": round(rsi_m15, 2)}
        except Exception as e:
            logger.error(f"Error in hyper_confluence: {e}")
            return {"confluence": "NEUTRAL", "score": 0}


    def is_safe_to_trade(self, symbol: str) -> bool:
        """Returns False in CHOPPY/UNKNOWN markets — ALL engines should pause."""
        result = self._cache.get(symbol) or self.detect(symbol)
        return result["regime"] not in ("CHOPPY", "UNKNOWN")

    def get_cached(self, symbol: str) -> dict:
        return self._cache.get(symbol, {"regime": "UNKNOWN", "adx": 0, "atr": 0})
