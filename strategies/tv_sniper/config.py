import json
import logging
import os

CONFIG_PATH = "config_sniper.json"
logger = logging.getLogger("TVSniperConfig")

def get_default_config():
    return {
        "enabled": False,
        "magic_number": 999999,
        "volume": 0.05,
        "use_limit_orders": True,
        "limit_cushion_points": 20,
        "stop_loss_points": 300,
        "take_profit_points": 900,
        "minimum_tf_confluence": 2,
        "rsi_oversold": 35,
        "rsi_overbought": 65,
        "active_timeframes": ["15M", "1H", "D"]
    }

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return get_default_config()
    try:
        with open(CONFIG_PATH, "r", encoding='utf-8') as f:
            data = json.load(f)
            # Merge with defaults to ensure missing keys exist
            defaults = get_default_config()
            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        logger.error(f"Failed to load {CONFIG_PATH}: {e}")
        return get_default_config()

def save_config(new_config):
    try:
        with open(CONFIG_PATH, "w", encoding='utf-8') as f:
            json.dump(new_config, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Failed to save {CONFIG_PATH}: {e}")
        return False
