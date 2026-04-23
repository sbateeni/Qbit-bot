import MetaTrader5 as mt5
import pandas as pd
import os
import logging
import datetime
from dotenv import load_dotenv
from typing import Optional, Union, Dict, Any
from core.telegram_notifier import TelegramNotifier
from core.models import TradeOrder, PendingOrder

# Standardized AI Audit Logger
logger = logging.getLogger("QbitBot")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def _resolve_order_filling(symbol: str):
    """Broker-compatible filling mode (IOC / FOK / RETURN) from symbol metadata."""
    info = mt5.symbol_info(symbol)
    if not info:
        return mt5.ORDER_FILLING_IOC
    fm = int(info.filling_mode)
    if fm & mt5.SYMBOL_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    if fm & mt5.SYMBOL_FILLING_IOC:
        return mt5.ORDER_FILLING_IOC
    if fm & mt5.SYMBOL_FILLING_RETURN:
        return mt5.ORDER_FILLING_RETURN
    return mt5.ORDER_FILLING_IOC


class MT5Manager:
    def __init__(self):
        """Initializes connection to MetaTrader 5 using credentials from .env."""
        load_dotenv()
        self.login = os.getenv("MT5_LOGIN")
        self.password = os.getenv("MT5_PASSWORD")
        self.server = os.getenv("MT5_SERVER")
        self.telegram = TelegramNotifier()
        
        self.connect()

    def positions_get(self, **kwargs):
        """Wrapper for mt5.positions_get to ensure connection is alive."""
        self.keep_alive()
        return mt5.positions_get(**kwargs)

    def orders_get(self, **kwargs):
        """Wrapper for mt5.orders_get to ensure connection is alive."""
        self.keep_alive()
        return mt5.orders_get(**kwargs)

    def history_deals_get(self, *args, **kwargs):
        """Wrapper for mt5.history_deals_get to ensure connection is alive."""
        self.keep_alive()
        return mt5.history_deals_get(*args, **kwargs)

    def find_terminal_path(self):
        """Searches common Windows directories for the MT5 terminal executable."""
        common_paths = [
            os.getenv("MT5_PATH"), # Priority 1: User's .env path
            "C:/Program Files/MetaTrader 5/terminal64.exe",
            "C:/Program Files (x86)/MetaTrader 5/terminal64.exe",
            # Add broker-specific variations frequently used
            "C:/Program Files/MetaTrader 5 Admiral Markets/terminal64.exe",
            "C:/Program Files/Admiral Markets MT5/terminal64.exe",
            "C:/Program Files/Exness MetaTrader 5/terminal64.exe",
            "C:/Program Files/GTC MetaTrader 5/terminal64.exe"
        ]
        
        for path in common_paths:
            if path and os.path.exists(path):
                logger.info(f"🔍 Auto-detected MT5 Terminal at: {path}")
                return path
        
        logger.error("❌ Could not find terminal64.exe automatically. Please ensure MT5 is installed.")
        return None

    def connect(self):
        """Initialize connection to MetaTrader 5."""
        # Try finding the terminal automatically first if needed
        terminal_path = self.find_terminal_path()
        
        # If terminal is already running, initialize() without path is faster
        if mt5.terminal_info() is not None:
             logger.info("Successfully attached to active MT5 terminal.")
             return True

        if mt5.initialize(path=terminal_path) if terminal_path else mt5.initialize():
            logger.info("Successfully connected to MetaTrader 5.")
            
            # Login if env variables are available
            login_str = os.getenv("MT5_LOGIN", "0")
            if login_str and login_str.isdigit() and int(login_str) > 0:
                login_id = int(login_str)
                password = os.getenv("MT5_PASSWORD")
                server = os.getenv("MT5_SERVER")
                if mt5.login(login_id, password=password, server=server):
                    logger.info(f"Logged into account #{login_id}")
                else:
                    logger.error(f"Login failed: {mt5.last_error()}")
            return True
        else:
            logger.error(f"mt5.initialize() failed. Error: {mt5.last_error()}")
            return False

    def check_connection(self) -> bool:
        """
        The 'Safety Valve': Rigorous check of terminal state and connection.
        If this returns False, the bot should immediately pause execution.
        """
        try:
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                logger.critical("❌ MT5 Terminal not detected/initialized.")
                return self.connect()
            
            if not terminal_info.connected:
                logger.warning("⚠️ MT5 Terminal is running but NOT CONNECTED to broker.")
                return self.connect()
            
            # Check if trading is allowed on the account level
            acc_info = mt5.account_info()
            if acc_info is None:
                logger.error("❌ Could not retrieve account info for safety check.")
                return False
            
            if not acc_info.trade_allowed:
                logger.error("🚫 Trading is NOT ALLOWED on this account/terminal.")
                return False

            return True
        except Exception as e:
            logger.critical(f"🔥 Critical failure in check_connection: {e}")
            return False

    def keep_alive(self):
        """Wrapper for check_connection to maintain backward compatibility."""
        return self.check_connection()

    def get_market_data(self, symbol, timeframe, count):
        """Returns a Pandas DataFrame of historical OHLCV data."""
        self.keep_alive()
        
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None:
            logger.error(f"Failed to get market data for {symbol}, error code: {mt5.last_error()}")
            return pd.DataFrame()
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def open_order(self, symbol: str, order_type: str, volume: float, stop_loss: float, take_profit: float, magic: int = 123456, comment: str = "Qbit Open"):
        """
        Handles Buy/Sell orders with robust Pydantic validation and try-except safety (Karpathy-style).
        """
        try:
            # 1. Connection Safety Check
            if not self.check_connection():
                logger.error(f"Order aborted for {symbol}: Connection not secure.")
                return None

            # 2. Pydantic Type & Range Validation
            order_data = TradeOrder(
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                sl=stop_loss,
                tp=take_profit,
                magic=magic,
                comment=comment
            )

            if not mt5.symbol_select(order_data.symbol, True):
                logger.error(f"Failed to select symbol {order_data.symbol}")
                return None

            tick = mt5.symbol_info_tick(order_data.symbol)
            if tick is None:
                logger.error(f"Failed to get tick for {order_data.symbol}")
                return None

            # Determine Mt5 order type and execution price
            if order_data.order_type == 'buy':
                order_type_mt5 = mt5.ORDER_TYPE_BUY
                price = tick.ask
            elif order_data.order_type == 'sell':
                order_type_mt5 = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                logger.error(f"Invalid order_type: {order_data.order_type}")
                return None
            
            fill = _resolve_order_filling(order_data.symbol)
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": order_data.symbol,
                "volume": float(order_data.volume),
                "type": order_type_mt5,
                "price": price,
                "sl": float(order_data.sl),
                "tp": float(order_data.tp),
                "deviation": order_data.deviation,
                "magic": order_data.magic,
                "comment": order_data.comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": fill,
            }

            # 3. Execution with detailed result analysis
            logger.info(f"🚀 Sending {order_data.order_type.upper()} request for {order_data.symbol} | Vol: {order_data.volume}")
            result = mt5.order_send(request)
            
            if result is None:
                logger.error(f"Order send failed (result is None). Error: {mt5.last_error()}")
                return None

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                # Handle specific fill errors
                if result.retcode == mt5.TRADE_RETCODE_INVALID_FILL and fill != mt5.ORDER_FILLING_IOC:
                    logger.warning("Invalid fill mode detected. Retrying with IOC...")
                    request["type_filling"] = mt5.ORDER_FILLING_IOC
                    result = mt5.order_send(request)
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        logger.info(f"Order placed successfully after IOC retry: Ticket #{result.order}")
                        return result
                
                logger.error(f"❌ Order failed on server | Code: {result.retcode} | Desc: {result.comment}")
                return None

            logger.info(f"✅ Order placed successfully: Ticket #{result.order}, Volume: {order_data.volume}")
            self.telegram._current_ticket = result.order
            return result

        except Exception as e:
            logger.critical(f"💥 SYSTEM FAILURE during open_order execution: {str(e)}", exc_info=True)
            return None

    def place_order(self, symbol: str, order_type: int, volume: float, price: float, sl: float, tp: float, magic: int, comment: str = "Qbit Limit"):
        """Places Pending Orders (Limit/Stop) with Pydantic validation and safety try-except."""
        try:
            if not self.check_connection():
                return None

            order_data = PendingOrder(
                symbol=symbol,
                order_type=order_type,
                price=price,
                volume=volume,
                sl=sl,
                tp=tp,
                magic=magic,
                comment=comment
            )

            fill = _resolve_order_filling(order_data.symbol)
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": order_data.symbol,
                "volume": float(order_data.volume),
                "type": order_data.order_type,
                "price": float(order_data.price),
                "sl": float(order_data.sl),
                "tp": float(order_data.tp),
                "deviation": order_data.deviation,
                "magic": int(order_data.magic),
                "comment": order_data.comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": fill,
            }

            logger.info(f"⏳ Placing PENDING order for {order_data.symbol} at {order_data.price}")
            result = mt5.order_send(request)
            
            if not (result and result.retcode == mt5.TRADE_RETCODE_DONE):
                if result and result.retcode == mt5.TRADE_RETCODE_INVALID_FILL and fill != mt5.ORDER_FILLING_IOC:
                    request["type_filling"] = mt5.ORDER_FILLING_IOC
                    result = mt5.order_send(request)
            
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                err = result.retcode if result else mt5.last_error()
                logger.error(f"❌ Pending Order failed | Code: {err}")
                return None

            logger.info(f"✅ Pending order placed: Ticket #{result.order} for {order_data.symbol}")
            return result
        except Exception as e:
            logger.critical(f"💥 Failure in place_order: {e}")
            return None

    def execute_trade(self, symbol, order_type, volume, sl_points, tp_points, magic, comment="Qbit Exec"):
        """A simplified execution wrapper that calculates SL/TP from points automatically."""
        tick = mt5.symbol_info_tick(symbol)
        if not tick: return None
        
        info = mt5.symbol_info(symbol)
        if not info: return None
        
        point = info.point
        if order_type.upper() == "BUY":
            sl = tick.ask - (sl_points * point)
            tp = tick.ask + (tp_points * point)
        else:
            sl = tick.bid + (sl_points * point)
            tp = tick.bid - (tp_points * point)
            
        return self.open_order(symbol, order_type, volume, sl, tp, magic, comment)

    def close_position(self, ticket: int):
        """Closes a specific position with internal safety checks."""
        try:
            if not self.check_connection():
                return False
            
            pos_info = mt5.positions_get(ticket=ticket)
            if pos_info is None or len(pos_info) == 0:
                logger.error(f"Position {ticket} not found.")
                return False
            
            pos = pos_info[0]
            tick = mt5.symbol_info_tick(pos.symbol)
            if tick is None:
                logger.error(f"Failed to get tick for {pos.symbol}")
                return False
                
            order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
            
            fill = _resolve_order_filling(pos.symbol)
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": order_type,
                "position": pos.ticket,
                "price": price,
                "deviation": 20,
                "magic": pos.magic,
                "comment": f"Close | {pos.comment}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": fill,
            }
            
            result = mt5.order_send(request)
            if not (result and result.retcode == mt5.TRADE_RETCODE_DONE):
                if result and result.retcode == mt5.TRADE_RETCODE_INVALID_FILL and fill != mt5.ORDER_FILLING_IOC:
                    request["type_filling"] = mt5.ORDER_FILLING_IOC
                    result = mt5.order_send(request)
            
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                err = result.retcode if result else mt5.last_error()
                logger.error(f"❌ Failed to close position {ticket} | Code: {err}")
                return False

            logger.info(f"✅ Position {ticket} closed successfully.")
            self.telegram._current_deal = result.order
            self.telegram.send_trade_close(pos.symbol, result.profit, "Strategy Exit")
            return True
        except Exception as e:
            logger.critical(f"💥 Error closing position {ticket}: {e}")
            return False

    def partial_close(self, ticket: int, percentage: float = 0.5):
        """Closes a portion of a position to lock in profit."""
        try:
            if not self.check_connection(): return False
            pos_info = mt5.positions_get(ticket=ticket)
            if not pos_info: return False
            
            pos = pos_info[0]
            close_volume = round(pos.volume * percentage, 2)
            if close_volume < 0.01: return False
            
            tick = mt5.symbol_info_tick(pos.symbol)
            order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": close_volume,
                "type": order_type,
                "position": pos.ticket,
                "price": price,
                "deviation": 20,
                "magic": pos.magic,
                "comment": f"Partial {int(percentage*100)}% | {pos.comment}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": _resolve_order_filling(pos.symbol),
            }
            
            res = mt5.order_send(request)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"✅ Partial close successful for #{ticket} | Vol: {close_volume}")
                return True
            return False
        except Exception as e:
            logger.error(f"Partial close error: {e}")
            return False

    def move_to_breakeven(self, ticket: int, padding_pips: float = 2.0):
        """Moves SL to entry price + small padding to cover commissions."""
        try:
            pos_info = mt5.positions_get(ticket=ticket)
            if not pos_info: return False
            pos = pos_info[0]
            
            info = mt5.symbol_info(pos.symbol)
            point = info.point
            
            if pos.type == mt5.ORDER_TYPE_BUY:
                new_sl = round(pos.price_open + (padding_pips * 10 * point), info.digits)
                if pos.sl < new_sl: # Only move up
                    return self.modify_sl_tp(ticket, new_sl, pos.tp)
            else:
                new_sl = round(pos.price_open - (padding_pips * 10 * point), info.digits)
                if pos.sl == 0 or pos.sl > new_sl: # Only move down
                    return self.modify_sl_tp(ticket, new_sl, pos.tp)
            return False
        except Exception as e:
            logger.error(f"Breakeven error: {e}")
            return False

    def modify_sl_tp(self, ticket: int, sl: float, tp: float):
        """Modifies Stop Loss and Take Profit for an existing position with safety checks."""
        try:
            if not self.check_connection():
                return False
            
            # We need the symbol for modification request
            pos = mt5.positions_get(ticket=ticket)
            if not pos: 
                logger.error(f"Modification failed: Position {ticket} not found.")
                return False
            
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": pos[0].symbol,
                "position": ticket,
                "sl": float(sl),
                "tp": float(tp),
            }
            
            logger.info(f"🛠️ Modifying SL/TP for #{ticket} | SL: {sl}, TP: {tp}")
            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                err = result.retcode if result else mt5.last_error()
                logger.error(f"❌ Modification failed for {ticket} | Code: {err}")
                return False
                
            return True
        except Exception as e:
            logger.critical(f"💥 Critical error in modify_sl_tp for #{ticket}: {e}")
            return False

    def close_all_positions(self, symbol=None, magic_filter=None):
        """A safety function to exit the market. Closes all open positions, optionally filtering by magic number."""
        self.keep_alive()
        
        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if positions is None or len(positions) == 0:
            logger.info("No open positions to close.")
            return True

        success = True
        for pos in positions:
            if magic_filter is not None and pos.magic != magic_filter:
                continue
                
            tick = mt5.symbol_info_tick(pos.symbol)
            if tick is None:
                continue
                
            # Opposite order type to close
            order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            # Opposite price
            price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
            
            fill = _resolve_order_filling(pos.symbol)
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": order_type,
                "position": pos.ticket,
                "price": price,
                "deviation": 20,
                "magic": pos.magic, # Preserve Strategy Magic
                "comment": f"Auto Close | {pos.comment}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": fill,
            }
            
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_INVALID_FILL and fill != mt5.ORDER_FILLING_IOC:
                request["type_filling"] = mt5.ORDER_FILLING_IOC
                result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                err = result.retcode if result else mt5.last_error()
                logger.error(f"Failed to close position {pos.ticket}, retcode={err}")
                success = False
            else:
                logger.info(f"Closed position {pos.ticket} successfully.")
                self.telegram._current_deal = result.order
                self.telegram.send_trade_close(pos.symbol, pos.profit, "Bulk/Safety Exit")
                
    def audit_notifications(self):
        """Cross-checks live MT5 state with notification log and sends missing alerts."""
        try:
            notified = self.telegram._get_notified_ids()
            
            # 1. Audit Open Positions
            positions = mt5.positions_get()
            if positions:
                for pos in positions:
                    if pos.ticket not in notified["open"]:
                        logger.info(f"🔍 Found unnotified open position: {pos.ticket}")
                        self.telegram._current_ticket = pos.ticket
                        direction = "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"
                        self.telegram.send_trade_open(pos.symbol, direction, pos.price_open, pos.volume, "Notification Auditor (Sync)")

            # 2. Audit Closed Deals (Today)
            start_of_day = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            history = mt5.history_deals_get(start_of_day, datetime.datetime.now())
            if history:
                for deal in history:
                    # Filter for trades (DEAL_ENTRY_OUT = closing a position)
                    if deal.entry == mt5.DEAL_ENTRY_OUT and deal.ticket not in notified["closed"]:
                        logger.info(f"🔍 Found unnotified closed deal: {deal.ticket}")
                        self.telegram._current_deal = deal.ticket
                        self.telegram.send_trade_close(deal.symbol, deal.profit, "Notification Auditor (Sync)")
        except Exception as e:
            logger.error(f"Audit fails: {e}")

    def check_daily_drawdown(self, limit_percent=5.0):
        """If today's loss > limit_percent of balance, stop trading."""
        import datetime
        account = mt5.account_info()
        if account is None: return False
        
        start_of_day = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        history = mt5.history_deals_get(start_of_day, datetime.datetime.now())
        
        today_profit = sum(d.profit for d in history) if history else 0
        drawdown = (abs(today_profit) / account.balance) * 100 if today_profit < 0 else 0
        
        if drawdown >= limit_percent:
            logger.error(f"🚨 DAILY DRAWDOWN LIMIT REACHED ({drawdown:.2f}%). Closing all.")
            self.close_all_positions()
            return True
        return False

    def is_spread_safe(self, symbol, max_spread_pips=5.0, verbose=False):
        """Protects against high spread. Accurate for 5, 4, 3, and 2 digit brokers."""
        info = mt5.symbol_info(symbol)
        if info is None: return False
        
        if info.digits in [5, 3]:
            spread_pips = info.spread / 10.0
        else:
            spread_pips = info.spread
        
        if verbose:
            logger.info(f"📊 {symbol} Current Spread: {spread_pips:.1f} pips.")
            
        if spread_pips > max_spread_pips:
            logger.warning(f"⚠️ High spread on {symbol}: {spread_pips:.1f} pips. (Safe Limit: {max_spread_pips})")
            return False
        return True

    def reaches_max_trades(self, max_trades=3):
        """Limit the number of simultaneous open positions."""
        positions = mt5.positions_get()
        if positions and len(positions) >= max_trades:
            logger.info(f"🛑 Max open trades reached ({max_trades}). Skipping new signal.")
            return True
        return False
