import os
import json

CONFIG_GLOBAL = "config.json"
CONFIG_SCALPER = "config_scalper.json"
CONFIG_SWING = "config_swing.json"
CONFIG_SNIPER = "config_sniper.json"
AI_MEMORY_PATH = "logs/ai_memory.json"

def read_config(path: str) -> dict:
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return {}

def merge_config(path: str, updates: dict) -> dict:
    cfg = read_config(path)
    cfg.update(updates)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    return cfg
