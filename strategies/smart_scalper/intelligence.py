import time
import os
import json
import logging
import feedparser
import MetaTrader5 as mt5

logger = logging.getLogger("ScalperIntelligence")

class ScalperIntelligence:
    """
    Handles all AI-driven decisions and fundamental news gathering for the Scalper.
    """
    def __init__(self, brain_analyzer, symbol):
        self.brain = brain_analyzer
        self.symbol = symbol
        self.last_gemini_time = 0

    def ask_gemini_verdict(self, signal_type, rsi, price):
        """Asks Gemini for a verdict based on both Technicals and Fundamentals."""
        # 1. Quota Shield & Filter
        now = time.time()
        if now - self.last_gemini_time < 60: return True
        if not (rsi < 28 or rsi > 72): return True

        # 2. Fetch Fresh News & Deep Intel for AI
        news_context = "No major news."
        deep_intel_ctx = ""
        try:
            feed = feedparser.parse("https://www.dailyfx.com/feeds/market-alert")
            headlines = [entry.title for entry in feed.entries[:3]]
            news_context = " | ".join(headlines)
            
            # Read High-Fidelity Institutional Intel
            if os.path.exists("logs/market_intel.json"):
                with open("logs/market_intel.json", "r", encoding='utf-8') as f:
                    intel_list = json.load(f)
                    symbol_intel = next((item for item in intel_list if item['pair'] == self.symbol), {})
                    deep_intel_ctx = symbol_intel.get("ai_note", "")
        except: pass

        prompt = f"""
        Signal: {signal_type} @ {price}
        RSI: {rsi}
        News Alert: {news_context}
        Institutional Matrix: {deep_intel_ctx}
        
        Is this setup safe for a high-frequency institutional scalp? 
        Respond with 'YES' or 'NO' followed by a briefly technical reason in Arabic.
        """
        
        try:
            res = self.brain.generate_content(prompt)
            verdict = res.text.upper() if res else "YES"
            self.last_gemini_time = now
            return "YES" in verdict
        except Exception as e:
            logger.warning(f"Scalper verdict failed: {e}")
            return True # Fallback to technicals
