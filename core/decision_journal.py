import json
import datetime
import os
import logging
from core.database_client import db_client

logger = logging.getLogger("DecisionJournal")

JOURNAL_FILE = "logs/trade_journal.json"
DEFAULT_ACC_ID = os.getenv("DEFAULT_ACCOUNT_ID", "00000000-0000-0000-0000-000000000000")

class DecisionJournal:
    """
    Structured Institutional Audit Trail.
    Records every 'Thought Process' of the bot for later analysis.
    """
    
    @staticmethod
    def log(symbol, strategy, decision, reason, data=None):
        """
        Records the decision to local audit trail.
        decision:   'ENTRY', 'SKIP', 'BLOCK', 'EXIT'
        """
        entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "strategy": strategy,
            "decision": decision,
            "reason": reason,
            "data": data or {}
        }
        
        try:
            # 1. Local Journal
            os.makedirs("logs", exist_ok=True)
            journal = []
            if os.path.exists(JOURNAL_FILE):
                with open(JOURNAL_FILE, "r") as f:
                    try:
                        journal = json.load(f)
                    except:
                        journal = []
            
            journal.append(entry)
            journal = journal[-1000:]
            with open(JOURNAL_FILE, "w") as f:
                json.dump(journal, f, indent=4)

            logger.info(f"📔 [JOURNAL] {strategy} {decision} {symbol}: {reason}")
        except Exception as e:
            logger.error(f"❌ Failed to write to journal: {e}")
