import logging
import json
import os
import MetaTrader5 as mt5

logger = logging.getLogger("QbitBot.ScalperExecutor")

class TradeExecutor:
    @staticmethod
    def calculate_lot(symbol, risk_percent=1.0, sentiment=50):
        """Calculates dynamic lot size with AI Multiplier and Performance Weighting (v3.5)."""
        try:
            acc = mt5.account_info()
            if not acc: return 0.01
            is_demo = acc.trade_mode not in [mt5.ACCOUNT_TRADE_MODE_REAL, mt5.ACCOUNT_TRADE_MODE_CONTEST]
            
            if is_demo:
                with open("config.json", "r") as f:
                    balance = float(json.load(f).get("virtual_balance", 100.0))
            else:
                balance = acc.balance

            risk_amount = balance * (risk_percent / 100.0)
            base_lot = round(risk_amount / 10.0, 2)
            
            # 1. 🔥 AI Multiplier: Confidence based
            multiplier = 1.0
            if sentiment >= 95 or sentiment <= 5: multiplier = 3.0
            elif sentiment >= 85 or sentiment <= 15: multiplier = 2.0
            
            # 2. 📊 Performance-Weighted Multiplier (Phase 3)
            perf_mult = 1.0
            try:
                if os.path.exists("logs/optimizer_report.json"):
                    with open("logs/optimizer_report.json", "r") as f:
                        report = json.load(f)
                        stats = report.get("results", {}).get(symbol.upper(), {})
                        sharpe = float(stats.get("sharpe", 0))
                        if sharpe > 5.0: perf_mult = 1.5   # Elite performer
                        elif sharpe > 2.0: perf_mult = 1.25 # Strong performer
                        elif sharpe < 1.0: perf_mult = 0.8  # Underperformer
            except: pass

            # For Gold (GOLD), we cut volume by 50% for safety
            is_gold = "XAU" in symbol.upper() or "GOLD" in symbol.upper()
            gold_reduct = 0.5 if is_gold else 1.0
            
            lot = round(base_lot * multiplier * perf_mult * gold_reduct, 2)
            return max(0.01, min(lot, 1.0))
        except:
            return 0.01

    @staticmethod
    def handle_trailing_stop(mt5_mgr, symbol, point, digits, adx=25):
        """Manages trailing stop and cash sniper closes with REGIME awareness (v3.8)."""
        positions = mt5.positions_get(symbol=symbol)
        if not positions: return

        target_cash = 2.0
        safety_stop = 1.0
        trail_points = 300
        
        tick = mt5.symbol_info_tick(symbol)
        info = mt5.symbol_info(symbol)
        if not tick or not info: return

        try:
            if os.path.exists("config_scalper.json"):
                with open("config_scalper.json", "r") as f:
                    cfg = json.load(f)
                    target_cash = cfg.get("target_profit_usd", 2.0)
                    safety_stop = cfg.get("safety_stop_usd", 1.0)

            # 🏛️ REGIME ADAPTATION (v3.8)
            # TRENDING (ADX > 25) -> Hunter Mode: stretch targets, tight trail
            # RANGING  (ADX < 20) -> Farmer Mode: snap quick profits, loose trail
            if adx > 25:
                # We don't stretch target_cash here anymore as we use Adaptive Malahaka
                # but we keep it for legacy safety stop/logic if needed
                trail_points = 200  # Tighter trail to ride the move
            elif adx < 20:
                trail_points = 500  # Loose trail to survive chop noise
            else:
                trail_points = 300
        except Exception as e:
            logger.error(f"Error in trailing config read: {e}")
            trail_points = 300

        for pos in positions:
            # 🛡️ Skip trades not opened by the Scalper (e.g. Swing Investor trades)
            if pos.magic != 123456:
                continue

            # 1. 🚀 Institutional Adaptive Malahaka (v4.5)
            # Dynamic Cushion based on Profit %
            if pos.profit >= target_cash:
                # Calculate $ cushion: 25% of current profit, but at least $0.50 and max $5.0
                cushion_usd = max(0.5, min(pos.profit * 0.25, 5.0))
                
                # Convert $ cushion to Price Points for this symbol
                # Roughly: Points = (USD / Lot) / (TickValue / Point)
                lot = pos.volume
                tick_val = info.trade_tick_value if info.trade_tick_value else 1.0
                points_to_trail = (cushion_usd / lot) / (tick_val / point)
                
                if pos.type == mt5.POSITION_TYPE_BUY:
                    new_sl = round(tick.bid - (points_to_trail * point), digits)
                    if new_sl > pos.sl + (10 * point):
                         logger.info(f"🚀 [ADAPTIVE MALAHAKA] Profit ${pos.profit:.2f}. SL raised to {new_sl} (Locked: ~${pos.profit - cushion_usd:.2f})")
                         mt5_mgr.modify_sl_tp(pos.ticket, new_sl, pos.tp)
                elif pos.type == mt5.POSITION_TYPE_SELL:
                    new_sl = round(tick.ask + (points_to_trail * point), digits)
                    if pos.sl == 0 or new_sl < pos.sl - (10 * point):
                         logger.info(f"🚀 [ADAPTIVE MALAHAKA] Profit ${pos.profit:.2f}. SL lowered to {new_sl} (Locked: ~${pos.profit - cushion_usd:.2f})")
                         mt5_mgr.modify_sl_tp(pos.ticket, new_sl, pos.tp)

            # 2. Safety Cash Stop (Emergency floor)
            if pos.profit <= -safety_stop:
                logger.warning(f"🚨 SAFETY STOP: Loss threshold ${safety_stop} hit on {symbol}. Emergency close.")
                mt5_mgr.close_all_positions(symbol=symbol, magic_filter=123456)
                return True

            # 3. Trailing logic
            if pos.type == mt5.POSITION_TYPE_BUY:
                new_sl = round(pos.price_current - (trail_points * point), digits)
                if new_sl > pos.sl + (50 * point):
                    mt5_mgr.modify_sl_tp(pos.ticket, new_sl, pos.tp)
            elif pos.type == mt5.POSITION_TYPE_SELL:
                new_sl = round(pos.price_current + (trail_points * point), digits)
                if pos.sl == 0 or new_sl < pos.sl - (50 * point):
                    mt5_mgr.modify_sl_tp(pos.ticket, new_sl, pos.tp)
        return False
