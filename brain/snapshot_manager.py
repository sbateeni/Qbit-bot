import os
import json
import datetime
import MetaTrader5 as mt5
import logging

logger = logging.getLogger("SnapshotManager")

class SnapshotManager:
    """
    Aggregates data from ALL pages and configurations for AI analysis.
    This is the "Brain" that feeds the Google CLI for auto-tuning.
    """
    
    BASE_DIR = os.getcwd()
    LOGS_DIR = os.path.join(BASE_DIR, "logs")
    SNAPSHOT_FILE = os.path.join(LOGS_DIR, "system_snapshot.json")
    
    @staticmethod
    def capture_full_state():
        """Captures the state of every trading component and configuration."""
        configs = SnapshotManager._get_all_configs()
        snapshot = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "health": SnapshotManager._get_health_status(),
            "configs": configs,
            "runtime": SnapshotManager._get_runtime_state(),
            "market_intel": SnapshotManager._enrich_market_intel(SnapshotManager._get_market_intel()),
            "active_positions": SnapshotManager._get_active_positions(),
            "recent_history": SnapshotManager._get_recent_history(),
            "performance": SnapshotManager._get_performance_summary(),
            "terminal_logs": SnapshotManager._get_recent_logs(),
            "warnings": SnapshotManager._collect_warnings(configs),
        }
        
        # Save to file
        try:
            if not os.path.exists(SnapshotManager.LOGS_DIR):
                os.makedirs(SnapshotManager.LOGS_DIR)
                
            with open(SnapshotManager.SNAPSHOT_FILE, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=4)
            
            logger.info("📸 System State Captured for AI Analysis.")
            return snapshot
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return None

    @staticmethod
    def _get_health_status():
        acc = mt5.account_info()
        return {
            "balance": acc.balance if acc else 0,
            "equity": acc.equity if acc else 0,
            "drawdown": (acc.balance - acc.equity) if acc else 0,
            "server": acc.server if acc else "Unknown",
            "is_connected": mt5.terminal_info().connected if mt5.terminal_info() else False
        }

    @staticmethod
    def _get_all_configs():
        paths = {
            "global": "config.json",
            "scalper": "config_scalper.json",
            "swing": "config_swing.json",
            "sniper": "config_sniper.json"
        }
        configs = {}
        for key, path in paths.items():
            if os.path.exists(path):
                with open(path, "r") as f:
                    try: configs[key] = json.load(f)
                    except: configs[key] = {}
        return configs

    @staticmethod
    def _get_market_intel():
        path = "logs/market_intel.json"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try: return json.load(f)
                except: return []
        return []

    @staticmethod
    def _enrich_market_intel(intel_list):
        if not isinstance(intel_list, list):
            return []
        now = datetime.datetime.now()
        out = []
        for item in intel_list:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            stale = False
            lu = row.get("last_update") or ""
            try:
                dt = datetime.datetime.strptime(lu, "%Y-%m-%d %H:%M")
                stale = (now - dt).total_seconds() > 2700
            except Exception:
                stale = True
            note = (row.get("ai_note") or "").lower()
            if "temporarily unavailable" in note or "awaiting" in note:
                stale = True
            row["intel_stale"] = stale
            out.append(row)
        return out

    @staticmethod
    def _get_runtime_state():
        out = {}
        try:
            from api import state
            from strategies.smart_scalper.guards import TradingGuards

            out["trading_enabled"] = bool(getattr(state, "trading_enabled", True))
            try:
                out["mt5_market_open"] = bool(TradingGuards.is_session_active("EURUSD"))
            except Exception:
                out["mt5_market_open"] = None
            out["session_filter_active"] = bool(getattr(state, "session_filter_active", True))
            out["equity_peak_session"] = float(getattr(state, "equity_peak_session", 0.0) or 0.0)
            out["engine_iteration"] = int(getattr(state, "iteration", 0) or 0)
            md = getattr(state, "macro_data", None) or {}
            out["dxy_trend"] = md.get("dxy_trend", "NEUTRAL")
            out["dxy_price"] = md.get("dxy_price", 0.0)
        except Exception as e:
            out["error"] = str(e)
        circ = os.path.join(SnapshotManager.LOGS_DIR, "scalper_portfolio_circuit.json")
        if os.path.exists(circ):
            try:
                with open(circ, "r", encoding="utf-8") as f:
                    out["scalper_portfolio_circuit"] = json.load(f)
            except Exception:
                pass
        return out

    @staticmethod
    def _collect_warnings(configs):
        warnings = []
        try:
            from strategies.smart_scalper.portfolio_guard import optimizer_note_matches_rsi

            sc = configs.get("scalper") or {}
            aligned = optimizer_note_matches_rsi(sc)
            if aligned is False:
                warnings.append(
                    "scalper: optimizer_note RSI levels do not match rsi_oversold / rsi_overbought in config"
                )
        except Exception:
            pass
        return warnings

    @staticmethod
    def _get_active_positions():
        positions = mt5.positions_get()
        if not positions: return []
        return [
            {
                "symbol": p.symbol, "type": "BUY" if p.type == 0 else "SELL",
                "profit": p.profit, "volume": p.volume, "magic": p.magic,
                "duration_mins": (datetime.datetime.now().timestamp() - p.time) / 60
            } for p in positions
        ]

    @staticmethod
    def _get_recent_history():
        from_date = datetime.datetime.now() - datetime.timedelta(hours=24)
        history = mt5.history_deals_get(from_date, datetime.datetime.now())
        if not history: return []
        return [
            {
                "symbol": d.symbol, "profit": d.profit, "magic": d.magic,
                "time": datetime.datetime.fromtimestamp(d.time).strftime("%H:%M")
            } for d in history if d.profit != 0
        ][-20:] # Last 20 deals

    @staticmethod
    def _get_performance_summary():
        """Calculates global performance metrics for the audit report."""
        try:
            from_date = datetime.datetime.now() - datetime.timedelta(days=30)
            history = mt5.history_deals_get(from_date, datetime.datetime.now())
            if not history: return {"total_profit": 0, "win_rate": 0}
            
            total_profit = 0
            wins = 0
            total = 0
            strat_perf = {}
            
            # Strategy mapping
            magics = {123456: "Scalper", 777777: "Swing", 999999: "Sniper"}
            
            for d in history:
                if d.profit != 0 and d.symbol:
                    total += 1
                    total_profit += d.profit
                    if d.profit > 0: wins += 1
                    
                    strat = magics.get(d.magic, "Manual")
                    if strat not in strat_perf:
                        strat_perf[strat] = {"profit": 0, "trades": 0}
                    strat_perf[strat]["profit"] += d.profit
                    strat_perf[strat]["trades"] += 1
            
            return {
                "total_profit": round(total_profit, 2),
                "win_rate": round(wins/total*100, 1) if total > 0 else 0,
                "total_executions": total,
                "breakdown": strat_perf
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def _get_recent_logs():
        lines = []
        path = os.path.join(SnapshotManager.LOGS_DIR, "app.log")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()[-40:]
            except Exception as e:
                logger.debug("Could not read app.log: %s", e)
        try:
            from api.state import log_buffer

            buf = list(log_buffer)[-20]
            lines.extend([f"[{b['time']}] {b['level']}: {b['msg']}\n" for b in buf])
        except Exception:
            pass
        return lines[-60:]
