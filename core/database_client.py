import os
import json
import uuid
import sqlite3
import logging
import base64
from urllib import request, parse, error
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger("DatabaseClient")


class SovereignDatabase:
    """Local SQLite database for single-user mode."""

    def __init__(self):
        self.kv_url = os.getenv("KV_REST_API_URL", "")
        self.kv_token = os.getenv("KV_REST_API_TOKEN", "")
        self.mode = "kv" if self.kv_url and self.kv_token else "sqlite"

        # Serverless containers usually allow writes only in /tmp.
        is_serverless = (
            os.getenv("VERCEL") == "1"
            or bool(os.getenv("VERCEL_ENV"))
            or os.getenv("RENDER") == "true"
        )
        if is_serverless:
            default_path = os.path.join("/tmp", "qbit_local.db")
        else:
            os.makedirs("data", exist_ok=True)
            default_path = os.path.join("data", "qbit_local.db")
        self.db_path = os.getenv("LOCAL_DB_PATH", default_path)
        if self.mode == "sqlite":
            self._init_schema()

    def _kv_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.kv_token}", "Content-Type": "application/json"}

    def _kv_call(self, command: str, *args):
        if not self.kv_url or not self.kv_token:
            return None
        url = f"{self.kv_url.rstrip('/')}/{command}/{('/'.join(parse.quote(str(a), safe='') for a in args))}"
        req = request.Request(url, headers=self._kv_headers())
        try:
            with request.urlopen(req, timeout=12) as res:
                payload = json.loads(res.read().decode("utf-8"))
                return payload.get("result")
        except Exception as exc:
            logger.error("KV call failed (%s): %s", command, exc)
            return None

    def _kv_get_json(self, key: str, default):
        val = self._kv_call("get", key)
        if val is None:
            return default
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return default
        return val

    def _kv_set_json(self, key: str, value):
        self._kv_call("set", key, json.dumps(value))

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sovereign_configs (
                    account_id TEXT PRIMARY KEY,
                    config_json TEXT NOT NULL,
                    last_ai_update TEXT
                );
                CREATE TABLE IF NOT EXISTS trade_journal (
                    id TEXT PRIMARY KEY,
                    account_id TEXT,
                    symbol TEXT,
                    strategy TEXT,
                    decision TEXT,
                    reason TEXT,
                    technical_snapshot TEXT,
                    timestamp TEXT
                );
                CREATE TABLE IF NOT EXISTS ai_optimization_notes (
                    account_id TEXT PRIMARY KEY,
                    strategic_note TEXT,
                    overall_health_score REAL,
                    suggested_tweaks TEXT,
                    identified_patterns TEXT
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
                CREATE TABLE IF NOT EXISTS broker_connections (
                    account_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    provider TEXT,
                    broker_account_id TEXT,
                    api_key_encrypted TEXT,
                    environment TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS risk_limits (
                    account_id TEXT PRIMARY KEY,
                    limits_json TEXT
                );
                CREATE TABLE IF NOT EXISTS strategy_runs (
                    id TEXT PRIMARY KEY,
                    account_id TEXT,
                    strategy TEXT,
                    status TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    account_id TEXT,
                    strategy TEXT,
                    side TEXT,
                    symbol TEXT,
                    request_payload TEXT,
                    broker_result TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS trading_accounts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    name TEXT,
                    created_at TEXT
                );
                """
            )
            conn.commit()

    # --- Account Management ---
    def get_account_config(self, account_id: str) -> Dict[str, Any]:
        if self.mode == "kv":
            return self._kv_get_json(f"cfg:{account_id}", {})
        with self._conn() as conn:
            row = conn.execute("SELECT config_json FROM sovereign_configs WHERE account_id = ?", (account_id,)).fetchone()
            return json.loads(row["config_json"]) if row else {}

    def update_account_config(self, account_id: str, tweaks: Dict[str, Any]):
        cfg = self.get_account_config(account_id)
        cfg.update(tweaks)
        if self.mode == "kv":
            self._kv_set_json(f"cfg:{account_id}", cfg)
            return
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO sovereign_configs (account_id, config_json, last_ai_update)
                VALUES (?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                  config_json=excluded.config_json,
                  last_ai_update=excluded.last_ai_update
                """,
                (account_id, json.dumps(cfg), datetime.utcnow().isoformat()),
            )
            conn.commit()

    # --- Audit Journaling ---
    def log_trade_decision(self, account_id: str, symbol: str, strategy: str, decision: str, reason: str, snapshot: Dict[str, Any] = None):
        if self.mode == "kv":
            key = f"journal:{account_id}"
            current = self._kv_get_json(key, [])
            current.append(
                {
                    "id": str(uuid.uuid4()),
                    "account_id": account_id,
                    "symbol": symbol,
                    "strategy": strategy,
                    "decision": decision,
                    "reason": reason,
                    "technical_snapshot": snapshot or {},
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            self._kv_set_json(key, current[-200:])
            return
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO trade_journal VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    account_id,
                    symbol,
                    strategy,
                    decision,
                    reason,
                    json.dumps(snapshot or {}),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()

    def get_recent_journal(self, account_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        if self.mode == "kv":
            return list(reversed(self._kv_get_json(f"journal:{account_id}", [])))[0:limit]
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM trade_journal WHERE account_id = ? ORDER BY timestamp DESC LIMIT ?",
                (account_id, limit),
            ).fetchall()
            out = []
            for r in rows:
                item = dict(r)
                item["technical_snapshot"] = json.loads(item.get("technical_snapshot") or "{}")
                out.append(item)
            return out

    # --- AI Optimization Notes ---
    def save_ai_notes(self, account_id: str, notes: Dict[str, Any]):
        if self.mode == "kv":
            payload = {
                "account_id": account_id,
                "strategic_note": notes.get("strategic_note"),
                "overall_health_score": notes.get("overall_health_score"),
                "suggested_tweaks": notes.get("suggested_tweaks", []),
                "identified_patterns": notes.get("identified_patterns", []),
            }
            self._kv_set_json(f"ainotes:{account_id}", payload)
            return
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO ai_optimization_notes VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                  strategic_note=excluded.strategic_note,
                  overall_health_score=excluded.overall_health_score,
                  suggested_tweaks=excluded.suggested_tweaks,
                  identified_patterns=excluded.identified_patterns
                """,
                (
                    account_id,
                    notes.get("strategic_note"),
                    notes.get("overall_health_score"),
                    json.dumps(notes.get("suggested_tweaks", [])),
                    json.dumps(notes.get("identified_patterns", [])),
                ),
            )
            conn.commit()

    # --- Market Intelligence ---
    def save_market_intelligence(self, intel_list: List[Dict[str, Any]]):
        """Standardized global market snapshots for local dashboard."""
        if not intel_list:
            return
        if self.mode == "kv":
            current = self._kv_get_json("market_intelligence", {})
            for item in intel_list:
                pair = item.get("pair")
                if pair:
                    current[pair] = {
                        "pair": pair,
                        "technical_summary": item.get("technical_summary"),
                        "sentiment_score": item.get("sentiment_score"),
                        "ai_note": item.get("ai_note"),
                        "matrix": item.get("matrix", {}),
                        "yf_stats": item.get("yf_stats", {}),
                        "last_update": datetime.utcnow().isoformat(),
                    }
            self._kv_set_json("market_intelligence", current)
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

    # --- SaaS Broker Connections ---
    def _enc_key(self) -> bytes:
        raw = os.getenv("BROKER_SECRET_KEY", "qbit-default-key")
        return raw.encode("utf-8")

    def _encrypt(self, value: str) -> str:
        if not value:
            return ""
        b = value.encode("utf-8")
        k = self._enc_key()
        out = bytes([b[i] ^ k[i % len(k)] for i in range(len(b))])
        return base64.urlsafe_b64encode(out).decode("utf-8")

    def _decrypt(self, value: str) -> str:
        if not value:
            return ""
        raw = base64.urlsafe_b64decode(value.encode("utf-8"))
        k = self._enc_key()
        out = bytes([raw[i] ^ k[i % len(k)] for i in range(len(raw))])
        return out.decode("utf-8")

    def upsert_broker_connection(self, user_id: str, account_id: str, provider: str, broker_account_id: str, api_key: str, environment: str = "demo"):
        if self.mode == "kv":
            payload = {
                "account_id": account_id,
                "user_id": user_id,
                "provider": provider,
                "broker_account_id": broker_account_id,
                "api_key_encrypted": self._encrypt(api_key),
                "environment": environment,
                "created_at": datetime.utcnow().isoformat(),
            }
            self._kv_set_json(f"broker:{account_id}", payload)
            return
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO broker_connections VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                  user_id=excluded.user_id,
                  provider=excluded.provider,
                  broker_account_id=excluded.broker_account_id,
                  api_key_encrypted=excluded.api_key_encrypted,
                  environment=excluded.environment
                """,
                (
                    account_id,
                    user_id,
                    provider,
                    broker_account_id,
                    self._encrypt(api_key),
                    environment,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()

    def get_broker_connection(self, account_id: str) -> Dict[str, Any]:
        if self.mode == "kv":
            row = self._kv_get_json(f"broker:{account_id}", {})
            if not row:
                return {}
            row["api_key_plain"] = self._decrypt(row.get("api_key_encrypted", ""))
            return row
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM broker_connections WHERE account_id = ?", (account_id,)).fetchone()
        if not row:
            return {}
        row = dict(row)
        row["api_key_plain"] = self._decrypt(row.get("api_key_encrypted", ""))
        return row

    # --- SaaS risk controls ---
    def get_risk_limits(self, account_id: str) -> Dict[str, Any]:
        if self.mode == "kv":
            return self._kv_get_json(f"risk:{account_id}", {})
        with self._conn() as conn:
            row = conn.execute("SELECT limits_json FROM risk_limits WHERE account_id = ?", (account_id,)).fetchone()
        return json.loads(row["limits_json"]) if row else {}

    def upsert_risk_limits(self, account_id: str, limits: Dict[str, Any]):
        if self.mode == "kv":
            self._kv_set_json(f"risk:{account_id}", limits)
            return
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO risk_limits VALUES (?, ?)
                ON CONFLICT(account_id) DO UPDATE SET limits_json=excluded.limits_json
                """,
                (account_id, json.dumps(limits)),
            )
            conn.commit()

    # --- strategy runs and observability ---
    def create_strategy_run(self, account_id: str, strategy: str, status: str = "running") -> Dict[str, Any]:
        run = {
            "id": str(uuid.uuid4()),
            "account_id": account_id,
            "strategy": strategy,
            "status": status,
            "created_at": datetime.utcnow().isoformat(),
        }
        if self.mode == "kv":
            key = f"runs:{account_id}"
            current = self._kv_get_json(key, [])
            current.append(run)
            self._kv_set_json(key, current[-200:])
            return run
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO strategy_runs VALUES (?, ?, ?, ?, ?)",
                (run["id"], run["account_id"], run["strategy"], run["status"], run["created_at"]),
            )
            conn.commit()
        return run

    def set_strategy_run_status(self, run_id: str, status: str):
        if self.mode == "kv":
            # Update across known local account bucket.
            for acc in ["default", "local-user", "local-dev-token"]:
                key = f"runs:{acc}"
                current = self._kv_get_json(key, [])
                changed = False
                for item in current:
                    if item.get("id") == run_id:
                        item["status"] = status
                        changed = True
                if changed:
                    self._kv_set_json(key, current)
                    return
            return
        with self._conn() as conn:
            conn.execute("UPDATE strategy_runs SET status = ? WHERE id = ?", (status, run_id))
            conn.commit()

    def list_strategy_runs(self, account_id: str) -> List[Dict[str, Any]]:
        if self.mode == "kv":
            return list(reversed(self._kv_get_json(f"runs:{account_id}", [])))[:50]
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM strategy_runs WHERE account_id = ? ORDER BY created_at DESC LIMIT 50",
                (account_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def log_order_event(self, account_id: str, strategy: str, side: str, symbol: str, payload: Dict[str, Any], result: Dict[str, Any]):
        if self.mode == "kv":
            key = f"orders:{account_id}"
            current = self._kv_get_json(key, [])
            current.append(
                {
                    "id": str(uuid.uuid4()),
                    "account_id": account_id,
                    "strategy": strategy,
                    "side": side,
                    "symbol": symbol,
                    "request_payload": payload,
                    "broker_result": result,
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
            self._kv_set_json(key, current[-200:])
            return
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    account_id,
                    strategy,
                    side,
                    symbol,
                    json.dumps(payload),
                    json.dumps(result),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()

    def get_ai_notes(self, account_id: str) -> Dict[str, Any]:
        if self.mode == "kv":
            return self._kv_get_json(f"ainotes:{account_id}", {})
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ai_optimization_notes WHERE account_id = ?",
                (account_id,),
            ).fetchone()
        if not row:
            return {}
        data = dict(row)
        data["suggested_tweaks"] = json.loads(data.get("suggested_tweaks") or "[]")
        data["identified_patterns"] = json.loads(data.get("identified_patterns") or "[]")
        return data

    def get_market_intelligence(self) -> List[Dict[str, Any]]:
        if self.mode == "kv":
            data = self._kv_get_json("market_intelligence", {})
            if isinstance(data, dict):
                return sorted(list(data.values()), key=lambda x: x.get("last_update", ""), reverse=True)
            return []
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM market_intelligence ORDER BY last_update DESC").fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["matrix"] = json.loads(d.get("matrix_json") or "{}")
                d["yf_stats"] = json.loads(d.get("yf_stats_json") or "{}")
                out.append(d)
            return out

    def get_accounts_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        if self.mode == "kv":
            key = f"accounts:{user_id}"
            rows = self._kv_get_json(key, [])
            if not rows:
                rows = [
                    {
                        "id": "default",
                        "user_id": user_id,
                        "name": "Local Account",
                        "created_at": datetime.utcnow().isoformat(),
                    }
                ]
                self._kv_set_json(key, rows)
            return rows
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM trading_accounts WHERE user_id = ?", (user_id,)).fetchall()
            if not rows:
                default_id = "default"
                conn.execute(
                    "INSERT OR IGNORE INTO trading_accounts VALUES (?, ?, ?, ?)",
                    (default_id, user_id, "Local Account", datetime.utcnow().isoformat()),
                )
                conn.commit()
                rows = conn.execute("SELECT * FROM trading_accounts WHERE user_id = ?", (user_id,)).fetchall()
            return [dict(r) for r in rows]

db_client = SovereignDatabase()
