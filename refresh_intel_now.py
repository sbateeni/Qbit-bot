import os
import sys
import logging
from core.mt5_bridge import MT5Manager
from core.intel_manager import IntelManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IntelRefresher")

def main():
    mt = MT5Manager()
        
    intel = IntelManager(mt)
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "USDCAD", "AUDUSD", "USDCHF", "NZDUSD"]
    logger.info("Triggering manual global intelligence refresh...")
    intel.update_global_intelligence(symbols)
    logger.info("Refresh complete. Pivot points should now be populated.")

if __name__ == "__main__":
    main()
