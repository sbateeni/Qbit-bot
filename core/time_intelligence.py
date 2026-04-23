import json
import os
import logging
import datetime

logger = logging.getLogger("TimeIntelligence")

HEATMAP_PATH = "logs/time_heat_map.json"

class TimeIntelligence:
    """
    Qbit-Bot v4.0 — Time-of-Day Engine
    Learns the best and worst hours for each symbol from historical trade data.
    """

    @staticmethod
    def build_heat_map(journal_path="logs/trade_journal.json"):
        """
        Analyzes the Decision Journal to build a win-rate heatmap by hour.
        Called weekly by the Auto-Optimizer.
        """
        if not os.path.exists(journal_path):
            logger.warning("No trade journal found to analyze.")
            return {}

        with open(journal_path, "r") as f:
            try:
                entries = json.load(f)
            except:
                return {}

        # Aggregate wins/losses per symbol per hour
        stats = {}  # {symbol: {hour: {"wins": 0, "losses": 0}}}
        for entry in entries:
            if entry.get("action") != "ENTRY":
                continue
            symbol = entry.get("symbol", "UNKNOWN")
            ts = entry.get("timestamp", "")
            try:
                hour = datetime.datetime.fromisoformat(ts).hour
            except:
                continue

            if symbol not in stats:
                stats[symbol] = {}
            if hour not in stats[symbol]:
                stats[symbol][hour] = {"wins": 0, "losses": 0, "total": 0}

            profit = entry.get("context", {}).get("profit", 0)
            stats[symbol][hour]["total"] += 1
            if profit and profit > 0:
                stats[symbol][hour]["wins"] += 1
            else:
                stats[symbol][hour]["losses"] += 1

        # Convert to win_rate map
        heat_map = {}
        for symbol, hours in stats.items():
            heat_map[symbol] = {}
            for hour, data in hours.items():
                total = data["total"]
                win_rate = (data["wins"] / total * 100) if total > 0 else 50
                heat_map[symbol][str(hour)] = round(win_rate, 1)

        os.makedirs("logs", exist_ok=True)
        with open(HEATMAP_PATH, "w") as f:
            json.dump(heat_map, f, indent=2)

        logger.info(f"⏰ Time Heatmap built for {len(heat_map)} symbols.")
        return heat_map

    @staticmethod
    def get_time_score(symbol: str) -> float:
        """
        Returns the win-rate score for the current hour for a symbol.
        Returns 50.0 (neutral) if no data available.
        """
        if not os.path.exists(HEATMAP_PATH):
            return 50.0

        try:
            with open(HEATMAP_PATH, "r") as f:
                heat_map = json.load(f)
            hour = str(datetime.datetime.now().hour)
            return heat_map.get(symbol, {}).get(hour, 50.0)
        except:
            return 50.0

    @staticmethod
    def is_golden_hour(symbol: str, min_score: float = 60.0) -> bool:
        """Returns True if current hour has a win rate above the threshold."""
        return TimeIntelligence.get_time_score(symbol) >= min_score

    @staticmethod
    def is_danger_hour(symbol: str, max_score: float = 40.0) -> bool:
        """Returns True if this hour is historically bad for this symbol."""
        return TimeIntelligence.get_time_score(symbol) <= max_score
