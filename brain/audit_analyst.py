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
        # Targeted confirm model for Sovereign v4.5 with fallbacks
        self.model_tiers = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
        self.default_account_id = os.getenv("DEFAULT_ACCOUNT_ID", "00000000-0000-0000-0000-000000000000")
        
    def perform_audit(self, auto_apply=True):
        """Redesigned feedback loop: Read Local Journal -> Extract Patterns -> Suggest/Apply Tweaks."""
        if not self.client:
            return False
            
        try:
            # 1. Load Data from Local Journal
            journal_path = "logs/trade_journal.json"
            if not os.path.exists(journal_path):
                return False
                
            with open(journal_path, "r") as f:
                journal_data = json.load(f)[-60:]
            
            snapshot_data = {} 

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
            
            # Save Insights to Local File
            with open("logs/ai_optimization_notes.json", "w") as f:
                json.dump(notes, f, indent=4)
                
            if auto_apply:
                self.apply_tweaks(notes.get("suggested_tweaks", {}))
                
            logger.info(f"✅ Sovereign Local Audit Complete. Health Score: {notes.get('overall_health_score')}%")
            return True
        except Exception as e:
            logger.error(f"💥 Sovereign Audit failed: {e}")
            return False

    def apply_tweaks(self, tweaks):
        """Surgically applies AI-suggested tweaks to Local Config with safety bounds."""
        if not tweaks: return
        
        try:
            # Fetch current config from local file
            cfg_path = "config_scalper.json"
            cfg = {}
            if os.path.exists(cfg_path):
                with open(cfg_path, "r") as f:
                    cfg = json.load(f)
            
            if not cfg: 
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
                with open(cfg_path, "w") as f:
                    json.dump(cfg, f, indent=4)
                logger.info(f"🛡️ Sovereign Local Auto-Tuning Applied: {applied}")
                
        except Exception as e:
            logger.error(f"Failed to apply auto-tuning: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    analyst = AuditAnalyst()
    analyst.perform_audit(auto_apply=True)
