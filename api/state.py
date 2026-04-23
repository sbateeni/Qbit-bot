import threading
from collections import deque
from core.mt5_bridge import MT5Manager

mt5_mgr = MT5Manager()
scalpers = {}
swing_investors = {}
sniper_engines = {}
stop_event = threading.Event()

trading_enabled = True
session_filter_active = True

log_buffer = deque(maxlen=50)

macro_data = {
    "dxy_price": 0.0,
    "dxy_trend": "NEUTRAL",
    "last_macro_update": 0
}

global_biases = {}

global_cooldowns = {}

iteration = 0

# Session high-water mark for equity (updated by trading engine for drawdown from peak)
equity_peak_session = 0.0
