import os
import sys
import json
import sqlite3
import unittest

# Add parent dir to path to import core/api
sys.path.append(os.getcwd())

from core.database_client import SovereignDatabase

class TestSovereignSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use a temporary test db
        cls.test_db = "data/test_sovereign.db"
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)
        
        # Monkeypatch SovereignDatabase to use test db
        from core import database_client
        def mock_init(self):
            os.makedirs("data", exist_ok=True)
            self.db_path = "data/test_sovereign.db"
            self._init_schema()
        
        database_client.SovereignDatabase.__init__ = mock_init
        cls.db = SovereignDatabase()

    def test_db_schema(self):
        """Verify that all required tables exist."""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        required = ["sovereign_configs", "trade_journal", "ai_optimization_notes", "market_intelligence"]
        for table in required:
            self.assertIn(table, tables, f"Table {table} missing from local DB")
        conn.close()

    def test_config_crud(self):
        """Test local config storage."""
        test_cfg = {"rsi_oversold": 20, "rsi_overbought": 80}
        self.db.update_config("test_scalper", test_cfg)
        
        retrieved = self.db.get_config("test_scalper")
        self.assertEqual(retrieved["rsi_oversold"], 20)
        self.assertEqual(retrieved["rsi_overbought"], 80)

    def test_journal_logging(self):
        """Test trade decision logging."""
        self.db.log_trade_decision("EURUSD", "Scalper", "BUY", "RSI is low", {"rsi": 25})
        logs = self.db.get_recent_journal(limit=1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["symbol"], "EURUSD")
        self.assertEqual(logs[0]["technical_snapshot"]["rsi"], 25)

    def test_market_intelligence(self):
        """Test market intelligence storage."""
        intel = [{
            "pair": "GBPUSD",
            "technical_summary": "Bullish",
            "sentiment_score": 75,
            "ai_note": "Breaking resistance",
            "matrix": {"D": "Strong Trend"},
            "yf_stats": {"vol": 0.012}
        }]
        self.db.save_market_intelligence(intel)
        stored = self.db.get_market_intelligence()
        self.assertTrue(any(i["pair"] == "GBPUSD" for i in stored))

if __name__ == "__main__":
    unittest.main()
