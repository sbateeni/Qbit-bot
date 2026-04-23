import logging
import MetaTrader5 as mt5
from core.mt5_bridge import MT5Manager
from strategies.tv_sniper.config import load_config
from strategies.tv_sniper.logic import TVSniperLogic
from core.telegram_notifier import TelegramNotifier

class TVSniperEngine:
    def __init__(self, mt5_mgr: MT5Manager, symbol: str):
        self.mt5 = mt5_mgr
        self.symbol = symbol
        self.logger = logging.getLogger(f"TVSniper[{symbol}]")
        self.config = load_config()
        self.magic_number = self.config.get("magic_number", 999999)
        self.cooldown_until = 0
        self.telegram = TelegramNotifier()

    def get_symbol_intel(self, all_intel: list) -> dict:
        for item in all_intel:
            if item.get("pair") == self.symbol:
                return item
        return {}

    def analyze_and_trade(self, global_intel_list: list):
        # Reload config to apply real-time changes
        self.config = load_config()
        if not self.config.get("enabled", False):
            return

        intel_data = self.get_symbol_intel(global_intel_list)
        if not intel_data:
            return

        tick = mt5.symbol_info_tick(self.symbol)
        if not tick:
            return
            
        current_price = tick.ask # Approximate

        decision = TVSniperLogic.evaluate(self.symbol, intel_data, current_price, self.config)
        
        # We don't want to log HOLD every second.
        if decision["action"] == "HOLD":
            return

        # Check for open orders/positions using this magic number
        # Note: In a full architecture, we'd ensure MT5 bridge supports filtering by magic number.
        positions = mt5.positions_get(symbol=self.symbol) or []
        for pos in positions:
            if pos.magic == self.magic_number:
                return # Already have an active sniper position

        orders = mt5.orders_get(symbol=self.symbol) or []
        for ord in orders:
            if ord.magic == self.magic_number:
                return # Already have an active sniper limit order waiting
        
        self.logger.info(f"🎯 [SNIPER] {decision['action']} signal triggered on {self.symbol}. Reason: {decision['reason']}")
        
        # Calculate precise points mapping based on symbol digits
        info = mt5.symbol_info(self.symbol)
        if not info: return
        point = info.point

        tp_points = self.config.get("take_profit_points", 900)
        sl_points = self.config.get("stop_loss_points", 300)
        volume = self.config.get("volume", 0.05)
        use_limits = self.config.get("use_limit_orders", True)

        try:
            if decision["action"] == "BUY":
                if use_limits:
                    # Place Buy Limit at target_price
                    entry_price = decision["target_price"]
                    sl = entry_price - (sl_points * point)
                    tp = entry_price + (tp_points * point)
                    
                    res = self.mt5.place_order(
                        symbol=self.symbol,
                        order_type=mt5.ORDER_TYPE_BUY_LIMIT,
                        volume=volume,
                        price=entry_price,
                        sl=sl,
                        tp=tp,
                        magic=self.magic_number,
                        comment="TV_Sniper_B_Limit"
                    )
                    if res:
                        self.telegram.send(f"🎯 <b> Sniper Buy Limit</b>\n📌 {self.symbol} at {entry_price}\n🧠 {decision['reason']}")
                else:
                    # Market Buy
                    res = self.mt5.execute_trade(self.symbol, "BUY", volume, sl_points, tp_points, self.magic_number, comment="TV_Sniper_Buy")
                    if res:
                         self.telegram.send_trade_open(self.symbol, "BUY", tick.ask, volume, f"TV Sniper: {decision['reason']}")
                    
            elif decision["action"] == "SELL":
                if use_limits:
                    # Place Sell Limit at target_price
                    entry_price = decision["target_price"]
                    sl = entry_price + (sl_points * point)
                    tp = entry_price - (tp_points * point)
                    
                    res = self.mt5.place_order(
                        symbol=self.symbol,
                        order_type=mt5.ORDER_TYPE_SELL_LIMIT,
                        volume=volume,
                        price=entry_price,
                        sl=sl,
                        tp=tp,
                        magic=self.magic_number,
                        comment="TV_Sniper_S_Limit"
                    )
                    if res:
                        self.telegram.send(f"🎯 <b> Sniper Sell Limit</b>\n📌 {self.symbol} at {entry_price}\n🧠 {decision['reason']}")
                else:
                    # Market Sell
                    res = self.mt5.execute_trade(self.symbol, "SELL", volume, sl_points, tp_points, self.magic_number, comment="TV_Sniper_Sell")
                    if res:
                        self.telegram.send_trade_open(self.symbol, "SELL", tick.bid, volume, f"TV Sniper: {decision['reason']}")
                    
        except Exception as e:
            self.logger.error(f"Failed to execute Sniper Trade: {e}")

    def manage_active_positions(self):
        """Implements Smart Trailing (Malahaka) for active sniper positions."""
        positions = mt5.positions_get(symbol=self.symbol)
        if not positions: return
        
        info = mt5.symbol_info(self.symbol)
        if not info: return
        
        tick = mt5.symbol_info_tick(self.symbol)
        if not tick: return

        for p in positions:
            if p.magic != self.magic_number: continue
            
            # Start trailing once we have reached at least 200 points profit
            profit_points = (p.profit / p.volume) / (info.trade_tick_value / info.point) if info.trade_tick_value else 0
            
            # 🚀 Malahaka Trailing (v4.5)
            # Lock in profit if we are up significant points
            cushion = 150 * info.point
            
            if p.type == mt5.POSITION_TYPE_BUY:
                new_sl = round(tick.bid - cushion, info.digits)
                if new_sl > p.sl + (50 * info.point):
                    self.mt5.modify_sl_tp(p.ticket, new_sl, p.tp)
                    self.logger.info(f"🛡️ [SNIPER LOCK] {self.symbol}: SL moved to {new_sl}")
            elif p.type == mt5.POSITION_TYPE_SELL:
                new_sl = round(tick.ask + cushion, info.digits)
                if p.sl == 0 or new_sl < p.sl - (50 * info.point):
                    self.mt5.modify_sl_tp(p.ticket, new_sl, p.tp)
                    self.logger.info(f"🛡️ [SNIPER LOCK] {self.symbol}: SL moved to {new_sl}")
