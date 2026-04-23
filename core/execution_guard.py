import MetaTrader5 as mt5
import logging

logger = logging.getLogger("ExecutionGuard")

class ExecutionGuard:
    """
    Institutional Execution Layer.
    Ensures that trades are ONLY executed when market liquidity is high
    and spreads are narrow.
    """
    
    @staticmethod
    def is_liquidity_safe(symbol, mt5_manager, max_spread_atr_ratio=1.5):
        """
        Checks if the current spread is acceptable relative to historical volatility.
        Institutional standard: Spread should not exceed 1.5x of a 14-period ATR (average noise).
        """
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            return False
            
        current_spread = symbol_info.spread # in points
        point = symbol_info.point
        
        # Get ATR to compare spread vs volatility
        df = mt5_manager.get_market_data(symbol, mt5.TIMEFRAME_M5, count=20)
        if df is None or len(df) < 14:
            # Fallback to absolute spread check if ATR fails
            logger.warning(f"⚠️ [{symbol}] ATR missing. Falling back to absolute spread check.")
            return current_spread < 20 # 20 points fallback
            
        # Calculate ATR(14) in points
        high_low = df['high'] - df['low']
        atr = high_low.rolling(window=14).mean().iloc[-1] / point
        
        # If spread > ATR * ratio, liquidity is poor/spiky
        if current_spread > (atr * max_spread_atr_ratio):
            logger.warning(f"🚫 [{symbol}] Execution Blocked: High Spread ({current_spread} pts) vs ATR ({atr:.1f} pts).")
            return False
            
        return True

    @staticmethod
    def is_profit_safe(symbol, volume, safety_stop_usd):
        """
        Anti-Bleeding Filter.
        Ensures the cost of entry (spread) doesn't consume too much of the stop-loss budget.
        """
        info = mt5.symbol_info(symbol)
        if not info: return False
        
        # Calculate cost in USD of 1 pip spread for this volume
        # Simplified for major pairs (approx $1 per pip for 0.1 lot)
        tick_value = info.trade_tick_value
        spread_points = info.spread
        
        # Spread cost = spread_points * tick_value (per 1.0 lot) 
        # But tick_value is usually for 1 lot and 1 tick. 
        # MT5: profit = (close-open) * volume * tick_value / tick_size
        den = (info.trade_tick_size / info.point) if info.point else 1.0
        if not den or den == 0:
            den = 1.0
        cost_usd = (spread_points * volume * tick_value) / den
        
        # If the spread 'eats' more than 40% of our safety stop, the trade is dead on arrival.
        if cost_usd > (safety_stop_usd * 0.4):
            logger.warning(f"🚫 [{symbol}] Spread Trap: Cost ${cost_usd:.2f} too high for ${safety_stop_usd} stop.")
            return False
            
        return True

    @staticmethod
    def check_slippage(request_price, actual_price, max_slippage_points=5):
        """Verifies if the fill price was within acceptable slippage."""
        slippage = abs(request_price - actual_price)
        return slippage <= max_slippage_points
