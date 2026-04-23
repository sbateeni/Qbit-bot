import logging

logger = logging.getLogger("TVSniperLogic")

class TVSniperLogic:
    @staticmethod
    def evaluate(symbol: str, intel_data: dict, current_price: float, config: dict) -> dict:
        """
        Evaluates local TradingView intel against live price to find sniper entries.
        Returns:
            {"action": "BUY"|"SELL"|"HOLD", "target_price": float, "sl_price": float, "reason": str}
        """
        if not intel_data or "matrix" not in intel_data:
            return {"action": "HOLD", "reason": "No intel matrix available"}

        matrix = intel_data["matrix"]
        
        # 1. Evaluate Confluence across active timeframes
        buy_score = 0
        sell_score = 0
        
        for tf in config["active_timeframes"]:
            if tf in matrix:
                summary = matrix[tf].get("summary", "")
                if "STRONG BUY" in summary:
                    buy_score += 1
                elif "STRONG SELL" in summary:
                    sell_score += 1
        
        min_confluence = config.get("minimum_tf_confluence", 2)
        is_bullish = buy_score >= min_confluence
        is_bearish = sell_score >= min_confluence
        
        if not is_bullish and not is_bearish:
            return {"action": "HOLD", "reason": f"Insufficient Confluence (B:{buy_score}/S:{sell_score} vs {min_confluence})"}

        # 2. Daily Pivot Proximity & Momentum Filter
        try:
            # Get typical daily pivots
            daily_pivots = matrix["D"]["pivots"]["classic"]
            s1, s2 = daily_pivots["s1"], daily_pivots["s2"]
            r1, r2 = daily_pivots["r1"], daily_pivots["r2"]
        except KeyError:
            return {"action": "HOLD", "reason": "Pivot data missing"}

        # Get Momentum (RSI) for the lowest active timeframe (15M or 1H)
        base_tf = config["active_timeframes"][0]
        try:
            rsi = matrix[base_tf]["indicators"]["rsi"]
        except KeyError:
            rsi = 50 # Fallback

        rsi_oversold = config.get("rsi_oversold", 35)
        rsi_overbought = config.get("rsi_overbought", 65)
        cushion_pts = config.get("limit_cushion_points", 20)
        cushion = cushion_pts * 0.00001 # Approximation, will be scaled in bot.py

        if is_bullish and rsi <= rsi_oversold:
            # Look for S1 or S2 bounce
            if abs(current_price - s1) < (cushion * 5) or current_price > s1:
                return {
                    "action": "BUY",
                    "target_price": s1 + cushion,  # Place limit slightly above S1
                    "sl_price": s2,                # SL at S2
                    "reason": f"Bullish Confluence + RSI({rsi:.1f}) Oversold + Near S1({s1})"
                }

        if is_bearish and rsi >= rsi_overbought:
            # Look for R1 or R2 rejection
            if abs(current_price - r1) < (cushion * 5) or current_price < r1:
                return {
                    "action": "SELL",
                    "target_price": r1 - cushion,  # Place limit slightly below R1
                    "sl_price": r2,                # SL at R2
                    "reason": f"Bearish Confluence + RSI({rsi:.1f}) Overbought + Near R1({r1})"
                }
                
        return {"action": "HOLD", "reason": f"Waiting for Pivot approach (Price: {current_price})"}
