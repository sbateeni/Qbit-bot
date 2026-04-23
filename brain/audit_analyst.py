import os
import json
import logging
import time
from google import genai
from dotenv import load_dotenv
from core.database_client import db_client

load_dotenv()

logger = logging.getLogger("AuditAnalyst")

class AuditAnalyst:
    """
    The 'Autonomous Feedback Loop' based on Karpathy Engineering.
    Analyzes journals and system state to suggest and APPLY optimizations.
    Uses the new Google GenAI SDK with Robust Multi-Tier Fallback.
    """
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.error("GEMINI_API_KEY not found in .env")
            self.client = None
            return
            
        self.client = genai.Client(api_key=self.api_key)
        # Targeted confirm model for Sovereign v4.5
        self.model_tiers = ['gemini-2.5-flash']
        self.default_account_id = os.getenv("DEFAULT_ACCOUNT_ID", "00000000-0000-0000-0000-000000000000")
        
    def perform_audit(self, account_id=None, auto_apply=True):
        """Redesigned feedback loop: Read Supabase Journal -> Extract Patterns -> Suggest/Apply Tweaks."""
        if not self.client:
            return False
            
        acc_id = account_id or self.default_account_id

        try:
            # 1. Load Data from Supabase
            journal_data = db_client.get_recent_journal(acc_id, limit=60)
            snapshot_data = {} # To be expanded to fetch from DB snapshots

            if not journal_data:
                logger.debug("Audit checked: Not enough journal data yet.")
                return False

            # 2. Construct Prompt for Sovereign Analysis
            prompt = f"""
            You are the Sovereign Qbit-Bot Audit Analyst.
            Analyze the following trading journal and system state to identify optimization opportunities.
            
            --- TRADE JOURNAL ---
            {json.dumps(journal_data, indent=2)}
            
            --- SYSTEM SNAPSHOT ---
            {json.dumps(snapshot_data, indent=2)}
            
            Strategy Requirements:
            1. Identify recurring 'SKIP' / 'BLOCK' reasons (Spread, Confluence, Liquidity). 
            2. Detect symbol-specific underperformance (Win rate < 40% is critical).
            3. Propose surgically precise parameter tweaks for 'config_scalper.json'.
            4. Provide a master 'Strategic Note' (English) for the Sovereign Dashboard explaining 'why' these changes.
            
            Return ONLY a valid JSON object:
            {{
              'identified_patterns': [], 
              'suggested_tweaks': {{
                  'rsi_oversold': new_val, 
                  'rsi_overbought': new_val, 
                  'sl_points': new_val, 
                  'tp_points': new_val, 
                  'max_spread_pips': new_val
              }}, 
              'overall_health_score': 1-100, 
              'strategic_note': ''
            }}
            """

            # 3. Request AI Analysis with Retries
            response = None
            for model_id in self.model_tiers:
                for attempt in range(2):
                    try:
                        logger.info(f"🧠 Consulting Sovereign Mind via {model_id}...")
                        response = self.client.models.generate_content(model=model_id, contents=prompt)
                        if response: break
                    except Exception as e:
                        if "503" in str(e): time.sleep(3); continue
                        break
                if response: break

            if not response: return False

            # 4. Parse and Save
            import re
            output = response.text.strip()
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if not json_match: return False
                
            notes = json.loads(json_match.group())
            notes["last_audit"] = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            notes["ai_model"] = model_id
            
            # Save Insights to Supabase
            db_client.save_ai_notes(acc_id, notes)
                
            if auto_apply:
                self.apply_tweaks(acc_id, notes.get("suggested_tweaks", {}))
                
            logger.info(f"✅ Sovereign Cloud Audit Complete for {acc_id}. Health Score: {notes.get('overall_health_score')}%")
            return True
        except Exception as e:
            logger.error(f"💥 Sovereign Audit failed: {e}")
            return False

    def apply_tweaks(self, account_id, tweaks):
        """Surgically applies AI-suggested tweaks to Cloud Config with safety bounds."""
        if not tweaks: return
        
        try:
            # Fetch current config from DB
            cfg = db_client.get_account_config(account_id)
            if not cfg: 
                # Create default config if missing
                cfg = {"rsi_oversold": 30, "rsi_overbought": 70, "sl_points": 150, "tp_points": 300}
            
            # Validation & Boundary Logic (Institutional Safety)
            bounds = {
                "rsi_oversold": (15, 45),
                "rsi_overbought": (55, 85),
                "sl_points": (50, 1000),
                "tp_points": (50, 2000),
                "max_spread_pips": (5, 100)
            }
            
            applied = {}
            for key, val in tweaks.items():
                if key in bounds:
                    low, high = bounds[key]
                    safe_val = max(low, min(val, high))
                    if cfg.get(key) != safe_val:
                        cfg[key] = safe_val
                        applied[key] = safe_val
            
            if applied:
                db_client.update_account_config(account_id, applied)
                logger.info(f"🛡️ Sovereign Cloud Auto-Tuning Applied to {account_id}: {applied}")
                
        except Exception as e:
            logger.error(f"Failed to apply auto-tuning: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    analyst = AuditAnalyst()
    analyst.perform_audit(auto_apply=True)
