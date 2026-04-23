import MetaTrader5 as mt5
import logging

logger = logging.getLogger("OrderFlow")

class OrderFlowAnalyzer:
    """
    Qbit-Bot v4.0 — Institutional Order Flow Analysis
    Detects buying vs selling pressure from real tick volume data.
    This is the 'X-Ray' of the market — revealing where smart money is flowing.
    """

    @staticmethod
    def get_pressure(symbol: str, lookback_candles: int = 10) -> str:
        """
        Compares Bullish vs Bearish tick volume across the last N candles.
        
        Returns:
            'BUYING_PRESSURE'  — institutions are accumulating longs
            'SELLING_PRESSURE' — institutions are distributing / shorting
            'BALANCED'         — no dominant side
        """
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, lookback_candles)
        if rates is None or len(rates) < 3:
            return "BALANCED"

        bull_vol = 0.0
        bear_vol = 0.0

        for r in rates:
            close = r['close']
            open_ = r['open']
            tick_vol = r['tick_volume']
            
            # If candle closed higher than it opened = bullish tick volume
            if close > open_:
                bull_vol += tick_vol
            elif close < open_:
                bear_vol += tick_vol
            else:
                # Doji — split evenly
                bull_vol += tick_vol / 2
                bear_vol += tick_vol / 2

        total = bull_vol + bear_vol
        if total == 0:
            return "BALANCED"

        bull_pct = bull_vol / total * 100

        if bull_pct >= 62:
            logger.info(f"🐂 [{symbol}] Buying Pressure: {bull_pct:.0f}% bullish volume")
            return "BUYING_PRESSURE"
        elif bull_pct <= 38:
            logger.info(f"🐻 [{symbol}] Selling Pressure: {100-bull_pct:.0f}% bearish volume")
            return "SELLING_PRESSURE"
        return "BALANCED"

    @staticmethod
    def is_aligned_with_signal(symbol: str, signal_type: str) -> bool:
        """
        Cross-checks the signal direction with the Order Flow pressure.
        Returns False if institutions are going the opposite direction.
        """
        pressure = OrderFlowAnalyzer.get_pressure(symbol)

        if signal_type.upper() == "BUY" and pressure == "SELLING_PRESSURE":
            logger.warning(f"⚡ [{symbol}] Order Flow Conflict: BUY signal but institutions SELLING.")
            return False
        if signal_type.upper() == "SELL" and pressure == "BUYING_PRESSURE":
            logger.warning(f"⚡ [{symbol}] Order Flow Conflict: SELL signal but institutions BUYING.")
            return False
        return True
