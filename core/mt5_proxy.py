import os
import platform
import logging

logger = logging.getLogger("MT5Proxy")

# Detection Logic: Is this a Windows machine with MT5 potential?
IS_WINDOWS = platform.system() == "Windows"
IS_CLOUD = bool(os.getenv("RENDER")) or bool(os.getenv("VERCEL_ENV")) or os.getenv("VERCEL") == "1"

mt5 = None

if IS_WINDOWS and not IS_CLOUD:
    try:
        import MetaTrader5 as real_mt5
        mt5 = real_mt5
        logger.info("✅ Native MetaTrader5 detected and loaded.")
    except ImportError:
        logger.warning("⚠️ MetaTrader5 library missing on Windows. Using Proxy.")
else:
    logger.info(f"🌐 Cloud/Linux environment detected ({platform.system()}). Activating MT5 Mock Proxy.")

# --- MT5 Mock Class ---
class MT5Mock:
    """Provides safe, non-crashing attributes for Cloud/Linux environments."""
    def __init__(self):
        self.version = lambda: (5, 0, "SaaS Mock")
        self.last_error = lambda: (0, "No error in proxy mode")
        
        # Fundamental Constants
        self.TIMEFRAME_M1 = 1
        self.TIMEFRAME_M5 = 5
        self.TIMEFRAME_M15 = 15
        self.TIMEFRAME_H1 = 60
        self.TIMEFRAME_H4 = 240
        self.TIMEFRAME_D1 = 1440
        
        self.ORDER_TYPE_BUY = 0
        self.ORDER_TYPE_SELL = 1
        
    def initialize(self, *args, **kwargs): return False
    def login(self, *args, **kwargs): return False
    def account_info(self): return None
    def terminal_info(self): return None
    def symbols_total(self): return 0
    def symbol_info(self, symbol): return None
    def symbol_info_tick(self, symbol): return None
    def copy_rates_from_pos(self, *args, **kwargs): return None
    def shutdown(self): pass

# Set the global mt5 variable to the mock if real one is missing
if mt5 is None:
    mt5 = MT5Mock()
