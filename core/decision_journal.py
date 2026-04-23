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
    def log(symbol, strategy, decision, reason, data=None, account_id=None):
        """
        Records the decision to Sovereign Cloud (Supabase) and local fallback.
        account_id: The UUID of the trading account.
        decision:   'ENTRY', 'SKIP', 'BLOCK', 'EXIT'
        """
        acc_id = account_id or DEFAULT_ACC_ID
        entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "strategy": strategy,
            "decision": decision,
            "reason": reason,
            "data": data or {}
        }
        
        try:
            # 1. Local Fallback (for safety)
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

            # 2. Cloud Log (Supabase)
            db_client.log_trade_decision(acc_id, symbol, strategy, decision, reason, data)
                
            logger.info(f"📔 [JOURNAL] {acc_id[:8]}.. {strategy} {decision} {symbol}: {reason}")
        except Exception as e:
            logger.error(f"❌ Failed to write to journal: {e}")
