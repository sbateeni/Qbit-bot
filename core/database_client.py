import os
import json
import uuid
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger("DatabaseClient")

class SovereignDatabase:
    """Local SQLite database for single-user mode."""

    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.db_path = os.path.join("data", "qbit_local.db")
        self._init_schema()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sovereign_configs (
                    key TEXT PRIMARY KEY,
                    config_json TEXT NOT NULL,
                    last_ai_update TEXT
                );
                CREATE TABLE IF NOT EXISTS trade_journal (
                    id TEXT PRIMARY KEY,
                    symbol TEXT,
                    strategy TEXT,
                    decision TEXT,
                    reason TEXT,
                    technical_snapshot TEXT,
                    timestamp TEXT
                );
                CREATE TABLE IF NOT EXISTS ai_optimization_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategic_note TEXT,
                    overall_health_score REAL,
                    suggested_tweaks TEXT,
                    identified_patterns TEXT,
                    timestamp TEXT
                );
                CREATE TABLE IF NOT EXISTS market_intelligence (
                    pair TEXT PRIMARY KEY,
                    technical_summary TEXT,
                    sentiment_score REAL,
                    ai_note TEXT,
                    matrix_json TEXT,
                    yf_stats_json TEXT,
                    last_update TEXT
                );
                """
            )
            conn.commit()

    # --- Configuration Management ---
    def get_config(self, key: str = "default") -> Dict[str, Any]:
        with self._conn() as conn:
            row = conn.execute("SELECT config_json FROM sovereign_configs WHERE key = ?", (key,)).fetchone()
            return json.loads(row["config_json"]) if row else {}

    def update_config(self, key: str, tweaks: Dict[str, Any]):
        cfg = self.get_config(key)
        cfg.update(tweaks)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO sovereign_configs (key, config_json, last_ai_update)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                  config_json=excluded.config_json,
                  last_ai_update=excluded.last_ai_update
                """,
                (key, json.dumps(cfg), datetime.utcnow().isoformat()),
            )
            conn.commit()

    # --- Audit Journaling ---
    def log_trade_decision(self, symbol: str, strategy: str, decision: str, reason: str, snapshot: Dict[str, Any] = None):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO trade_journal VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    symbol,
                    strategy,
                    decision,
                    reason,
                    json.dumps(snapshot or {}),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()

    def get_recent_journal(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM trade_journal ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            out = []
            for r in rows:
                item = dict(r)
                item["technical_snapshot"] = json.loads(item.get("technical_snapshot") or "{}")
                out.append(item)
            return out

    # --- AI Optimization Notes ---
    def save_ai_notes(self, notes: Dict[str, Any]):
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO ai_optimization_notes (strategic_note, overall_health_score, suggested_tweaks, identified_patterns, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    notes.get("strategic_note"),
                    notes.get("overall_health_score"),
                    json.dumps(notes.get("suggested_tweaks", [])),
                    json.dumps(notes.get("identified_patterns", [])),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()

    def get_ai_notes(self) -> Dict[str, Any]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ai_optimization_notes ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
        if not row:
            return {}
        data = dict(row)
        data["suggested_tweaks"] = json.loads(data.get("suggested_tweaks") or "[]")
        data["identified_patterns"] = json.loads(data.get("identified_patterns") or "[]")
        return data

    # --- Market Intelligence ---
    def save_market_intelligence(self, intel_list: List[Dict[str, Any]]):
        if not intel_list:
            return
        for item in intel_list:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO market_intelligence VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(pair) DO UPDATE SET
                      technical_summary=excluded.technical_summary,
                      sentiment_score=excluded.sentiment_score,
                      ai_note=excluded.ai_note,
                      matrix_json=excluded.matrix_json,
                      yf_stats_json=excluded.yf_stats_json,
                      last_update=excluded.last_update
                    """,
                    (
                        item.get("pair"),
                        item.get("technical_summary"),
                        item.get("sentiment_score"),
                        item.get("ai_note"),
                        json.dumps(item.get("matrix", {})),
                        json.dumps(item.get("yf_stats", {})),
                        datetime.utcnow().isoformat(),
                    ),
                )
                conn.commit()

    def get_market_intelligence(self) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM market_intelligence ORDER BY last_update DESC").fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["matrix"] = json.loads(d.get("matrix_json") or "{}")
                d["yf_stats"] = json.loads(d.get("yf_stats_json") or "{}")
                out.append(d)
            return out

db_client = SovereignDatabase()
