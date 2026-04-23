import os
import json
import logging
from google import genai
from dotenv import load_dotenv
import re

logger = logging.getLogger("GeminiAnalyzer")

class GeminiAnalyzer:
    activity_feed = []
    
    def __init__(self, config_path="config.json", memory_path="logs/ai_memory.json"):
        """Initialize connection to Google Gemini and setup config tracking."""
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            logger.warning("GEMINI_API_KEY not set properly in .env. Analysis will fail until set.")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)
            
        self.model_tiers = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
        self.config_path = config_path
        self.memory_path = memory_path
        
        # Ensure logs directory exists
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        self.load_memory()
        
        # Initialize the learning config if it doesn't exist yet
        if not os.path.exists(self.config_path):
            default_config = {
                "rsi_oversold": 30, "rsi_overbought": 70,
                "sl_points": 50, "tp_points": 100,
                "virtual_balance": 10.0, "target_profit_usd": 2.0
            }
            with open(self.config_path, "w") as f:
                json.dump(default_config, f, indent=4)

    def load_memory(self):
        """Loads AI activity feed from disk."""
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r") as f:
                    GeminiAnalyzer.activity_feed = json.load(f)
            except: GeminiAnalyzer.activity_feed = []

    def save_memory(self):
        """Saves AI activity feed to disk."""
        try:
            with open(self.memory_path, "w") as f:
                json.dump(GeminiAnalyzer.activity_feed, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save AI memory: {e}")

    def validate_adjustments(self, adjustments):
        """Audit Gemini suggestions to prevent 'suicidal' parameters."""
        valid = {}
        for key, val in adjustments.items():
            if key == "rsi_oversold":
                valid[key] = max(20, min(val, 45)) 
            elif key == "rsi_overbought":
                valid[key] = max(55, min(val, 80)) 
            elif key == "sl_points":
                valid[key] = max(10, min(val, 200)) 
            else:
                valid[key] = val
        return valid

    def update_local_config(self, adjustments):
        """Updates the local config.json file after validation."""
        import datetime
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
            
            safe_adjustments = self.validate_adjustments(adjustments)
            updated = False
            for key, value in safe_adjustments.items():
                if key in config:
                    config[key] = value
                    updated = True
                    
            if updated:
                # 📊 Audit trail: stamp when Gemini last touched the config
                config["last_ai_update"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                config["ai_adjustment_count"] = config.get("ai_adjustment_count", 0) + 1
                with open(self.config_path, "w") as f:
                    json.dump(config, f, indent=4)
                logger.info(f"🛡️ AI Adjustment #{config['ai_adjustment_count']} Applied: {safe_adjustments}")
        except Exception as e:
            logger.error(f"Failed to update config: {e}")

    def generate_content(self, prompt, model_override=None):
        """Unified robust content generation with multi-tier fallback and retries."""
        if not self.client: return None
        
        tiers = [model_override] if model_override else self.model_tiers
        
        for model_id in tiers:
            for attempt in range(2):
                try:
                    logger.debug(f"🧠 Generating content via {model_id} (Attempt {attempt+1})...")
                    response = self.client.models.generate_content(model=model_id, contents=prompt)
                    if response: return response
                except Exception as e:
                    logger.warning(f"⚠️ {model_id} failed: {e}")
                    if "503" in str(e) or "429" in str(e):
                        __import__('time').sleep(3)
                        continue
                    break # Critical error, skip to next model
        return None

    def log_evolution(self, trade_data, analysis, before_cfg, after_cfg):
        """Logs the detailed evolution of the strategy to a file."""
        evo_path = "logs/strategy_evolution.json"
        entry = {
            "timestamp": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "trade_failed": trade_data,
            "market_snapshot": trade_data.get("indicators", {}), # Capture technical levels
            "ai_analysis": analysis,
            "config_change": {
                "before": before_cfg,
                "after": after_cfg
            }
        }
        try:
            history = []
            if os.path.exists(evo_path):
                with open(evo_path, "r") as f:
                    history = json.load(f)
            history.append(entry)
            with open(evo_path, "w") as f:
                json.dump(history, f, indent=4)
        except Exception as e:
            logger.error(f"Evolution logging failed: {e}")

    def analyze_trade_failure(self, trade_data):
        logger.info("Sending failed trade context to Gemini for deep analysis...")
        
        # Capture config BEFORE change
        before_config = {}
        try:
            with open(self.config_path, "r") as f:
                before_config = json.load(f)
        except: pass

        prompt = f"""
        <system_identity>
        You are the 'Institutional Quant Lead' for Qbit-Bot. 
        Your goal is to perform a rigorous post-mortem on failed trades to protect unified capital.
        </system_identity>

        <trade_context>
        FAILED_TRADE: {json.dumps(trade_data)}
        CURRENT_BOT_CONFIG: {json.dumps(before_config)}
        </trade_context>

        <mandatory_constraints>
        1. GROUNDING: Analyze ONLY the provided market_data. Do not assume outside conditions.
        2. SAFETY: If the loss was caused by volatility exceeding 2.0x ATR, you MUST increase SL_POINTS.
        3. PRECISION: Your JSON output must be perfectly valid. 
        4. REASONING: Your 'analysis' field must be in Arabic (اللغة العربية). Summarize the <thinking> block clearly.
        </mandatory_constraints>

        <instructions>
        Perform a step-by-step audit using the following tags:
        1. <thinking>: Detailed technical decomposition.
        2. <json_output>: Providing the valid adjustments.
        </instructions>

        Respond ONLY with a valid JSON inside <json_output> tags.
        Example format:
        <json_output>
        {{"analysis": "REASON", "adjustments": {{"rsi_oversold": 25, "rsi_overbought": 75, "sl_points": 150}}}}
        </json_output>
        """

        
        response = self.generate_content(prompt)
        if not response: 
            logger.error("❌ All Gemini model tiers failed for trade failure analysis.")
            return None
        
        try:
            output = response.text.strip()
            
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if not json_match: return None
            
            parsed = json.loads(json_match.group())
            
            # Apply changes
            self.update_local_config(parsed.get("adjustments", {}))
            
            # Capture config AFTER change
            after_config = {}
            with open(self.config_path, "r") as f:
                after_config = json.load(f)

            # Store in UI feed
            GeminiAnalyzer.activity_feed.insert(0, {
                "time": __import__('datetime').datetime.now().strftime("%d/%m %H:%M"),
                "reason": parsed.get("analysis", "No reason provided"),
                "changes": parsed.get("adjustments", {}),
                "model": response.model_id if hasattr(response, 'model_id') else "unknown"
            })
            GeminiAnalyzer.activity_feed = GeminiAnalyzer.activity_feed[:20]
            self.save_memory()
            
            # LOG EVOLUTION FOR HISTORY
            self.log_evolution(trade_data, parsed.get("analysis"), before_config, after_config)
            
            return parsed
        except Exception as e:
            logger.error(f"Gemini Analysis Failed: {e}")
            return None
