import pandas as pd
import pandas_ta as ta
import logging
import MetaTrader5 as mt5

logger = logging.getLogger("ScalperSignals")

class SignalGenerator:
    @staticmethod
    def calculate_indicators(df, mt5_mgr, symbol):
        """Calculates RSI, EMA, BBands, ATR, EMA Slope, and H1 MTF Trend."""
        h1_trend = "UNKNOWN"
        try:
            df["EMA_200"] = ta.ema(df["close"], length=200)
            df["RSI_14"] = ta.rsi(df["close"], length=14)
            df["ATR_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)
            df["ATR"] = df["ATR_14"]  # alias for legacy / helpers
            adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
            if adx_df is not None and isinstance(adx_df, pd.DataFrame) and "ADX_14" in adx_df.columns:
                df["ADX_14"] = adx_df["ADX_14"]
            else:
                df["ADX_14"] = float("nan")

            
            # 1. EMA Slope (Market Chop Filter) -> difference over 5 candles
            # Scaled to basis points for easier reading (e.g. comparing to 0.5)
            df['EMA_Slope'] = (df['EMA_200'] - df['EMA_200'].shift(5)) / df['EMA_200'].shift(5) * 10000 
            
            # 2. Multi-Timeframe Trend (H1)
            # Fetch last 250 candles of H1 to get a valid 200 EMA
            df_h1 = mt5_mgr.get_market_data(symbol, mt5.TIMEFRAME_H1, count=250)
            if df_h1 is not None and not df_h1.empty:
                df_h1['EMA_200'] = ta.ema(df_h1['close'], length=200)
                last_h1 = df_h1.iloc[-1]
                if not pd.isna(last_h1['EMA_200']):
                    if last_h1['close'] > last_h1['EMA_200']: h1_trend = "UP"
                    elif last_h1['close'] < last_h1['EMA_200']: h1_trend = "DOWN"
            
            bbands = ta.bbands(df['close'], length=20, std=2)
            
            # 3. Institutional Liquidity Sweep (Lookback 30 candles)
            df['Prev_High_30'] = df['high'].shift(1).rolling(window=30).max()
            df['Prev_Low_30']  = df['low'].shift(1).rolling(window=30).min()
            
            # A sweep is when High > Prev_High AND Close < Prev_High (Bullish Fakeout)
            # OR Low < Prev_Low AND Close > Prev_Low (Bearish Fakeout)
            df['Liquidity_Sweep'] = "NONE"
            df.loc[(df['high'] > df['Prev_High_30']) & (df['close'] < df['Prev_High_30']), 'Liquidity_Sweep'] = "BEARISH_SWEEP"
            df.loc[(df['low'] < df['Prev_Low_30']) & (df['close'] > df['Prev_Low_30']), 'Liquidity_Sweep'] = "BULLISH_SWEEP"

            if bbands is not None:
                df = pd.concat([df, bbands], axis=1)
                bb_l_col = [c for c in bbands.columns if c.startswith('BBL')][0]
                bb_u_col = [c for c in bbands.columns if c.startswith('BBU')][0]
                return df, bb_l_col, bb_u_col, h1_trend
            return df, None, None, h1_trend
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return df, None, None, h1_trend

    @staticmethod
    def atr_volatility_gate(
        df: pd.DataFrame,
        closed_row_index: int,
        window: int = 120,
        min_percentile: float = 12.0,
        max_percentile: float = 92.0,
    ) -> bool:
        """
        Uses ATR on the last *closed* bar vs rolling history on prior closed bars.
        Blocks dead markets (ATR too low vs history) and chaos spikes (ATR too high).
        """
        col = "ATR_14" if "ATR_14" in df.columns else "ATR"
        if col not in df.columns:
            return True
        try:
            atr_now = float(df[col].iloc[closed_row_index])
            if pd.isna(atr_now) or atr_now <= 0:
                return False
            start = max(0, closed_row_index - window)
            hist = df[col].iloc[start:closed_row_index].dropna()
            if len(hist) < 25:
                return True
            lo = float(hist.quantile(min_percentile / 100.0))
            hi = float(hist.quantile(max_percentile / 100.0))
            return lo <= atr_now <= hi
        except Exception:
            return True

    @staticmethod
    def get_atr_levels(df, multiplier_sl=1.5, multiplier_tp=2.5, digits=5):
        """Calculates SL and TP distances based on ATR."""
        try:
            col = "ATR_14" if "ATR_14" in df.columns else "ATR"
            atr_val = float(df[col].dropna().iloc[-1])
            sl_dist = round(atr_val * multiplier_sl, digits)
            tp_dist = round(atr_val * multiplier_tp, digits)
            return sl_dist, tp_dist
        except:
            return None, None

    @staticmethod
    def near_round_number(price, threshold_points=50, point=0.00001):
        """
        Detects if price is near an institutional round number (e.g. 1.12000, 150.00).
        Protects against fake-outs at these high-liquidity levels.
        """
        # For FX (e.g. 1.12543), round numbers are at 000, 500, 1000 pips
        # For JPY (e.g. 150.234), round numbers are at .000, .500
        # Simple check: is price within X points of a .00 level?
        p_scaled = price / (100 * point) # Scale to 'pips'
        dist = abs(p_scaled - round(p_scaled))
        return dist * 100 < threshold_points
