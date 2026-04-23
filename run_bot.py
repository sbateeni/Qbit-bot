import logging
import MetaTrader5 as mt5
from core.mt5_bridge import MT5Manager
from strategies.smart_scalper import SmartScalper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RunBot")

def main():
    logger.info("Initializing Qbit-bot Core Systems...")
    mt5_mgr = MT5Manager()
    
    if not mt5_mgr.keep_alive():
        logger.error("Could not connect to MT5. Make sure the terminal is running.")
        return

    # Choose your trading symbol (Change depending on your broker, e.g., 'EURUSD' or 'XAUUSDm')
    symbol = "EURUSD"
    
    if not mt5.symbol_select(symbol, True):
        logger.error(f"Failed to enable symbol '{symbol}'. Please check your broker symbol names.")
        return

    timeframe = mt5.TIMEFRAME_M5
    volume = 0.1
    
    # Initialize the scalper strategy
    scalper = SmartScalper(mt5_mgr, symbol, timeframe, volume=volume)
    
    # Run the scalper continuously
    scalper.run(interval_seconds=5)

if __name__ == "__main__":
    main()
