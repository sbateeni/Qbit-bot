import logging
import MetaTrader5 as real_mt5

logger = logging.getLogger("MT5Proxy")

# Detection Logic: Native Windows only in local mode
try:
    mt5 = real_mt5
    logger.info("✅ Native MetaTrader5 loaded.")
except ImportError:
    logger.error("❌ MetaTrader5 library missing. Please install it with 'pip install MetaTrader5'.")
    # Fallback to prevent immediate crash but it's effectively an error
    mt5 = None
