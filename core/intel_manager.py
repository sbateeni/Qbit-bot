import os
import json
import logging
import time
import pandas_ta as ta
import MetaTrader5 as mt5
import yfinance as yf
import requests
from tradingview_ta import TA_Handler, Interval
from brain.gemini_analyzer import GeminiAnalyzer
from core.mt5_matrix_fallback import (
    build_matrix_from_mt5,
    sentiment_from_matrix,
    technical_summary_from_matrix,
)

logger = logging.getLogger("IntelManager")


def _tv_get_analysis_with_retry(handler, attempts: int = 3):
    last_err = None
    for i in range(attempts):
        try:
            return handler.get_analysis()
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (i + 1))
    if last_err:
        raise last_err
    return handler.get_analysis()


class IntelManager:
    _shared_cache = {} # Shared across all strategy instances
    _shared_expiry = 600 # 10 minutes to minimize 429 errors
    _global_cooldown_until = 0 # Prevent any TV requests if we hit 429
    
    def __init__(self, mt5_mgr):
        self.mt = mt5_mgr
        self.brain = GeminiAnalyzer()
        self.intel_path = "logs/market_intel.json"
        
        from core.regime_detector import RegimeDetector
        from strategies.smart_scalper.guards import TradingGuards
        self.regime_detector = RegimeDetector(mt5_mgr)
        self.guards = TradingGuards()
        
        from api.state import stop_event
        self.stop_event = stop_event



    def get_institutional_matrix(self, sym):
        """Generates a multi-timeframe analysis matrix similar to Investing.com."""
        intervals = {
            "5M": Interval.INTERVAL_5_MINUTES,
            "15M": Interval.INTERVAL_15_MINUTES,
            "1H": Interval.INTERVAL_1_HOUR,
            "D": Interval.INTERVAL_1_DAY
        }
        
        # 1. Check Matrix Cache (Sovereign Optimization)
        now = time.time()
        cache_key = f"matrix_{sym}"
        if cache_key in self._shared_cache:
            last_time, last_matrix = self._shared_cache[cache_key]
            if now - last_time < 900: # 15 minutes cache
                logger.debug(f"💎 Using cached Institutional Matrix for {sym}")
                return last_matrix

        # 0. Check Global Cooldown
        if time.time() < self._global_cooldown_until:
            logger.warning(f"🕒 TradingView in cooldown due to previous 429. Skipping matrix for {sym}")
            return None

        matrix = {}
        try:
            for label, interval in intervals.items():
                if self.stop_event.is_set(): break
                
                # ⚔️ Institutional Staggered Throttle (v4.5) - Increased for Rate Limit Safety
                # We wait 6-8 seconds between each timeframe request
                time.sleep(7.0) 
                
                # Internal Mapping for TV (Broker GOLD -> TV XAUUSD)
                tv_sym = sym.replace("/", "")
                if tv_sym == "GOLD": tv_sym = "XAUUSD"
                
                handler = TA_Handler(
                    symbol=tv_sym,
                    exchange="FX_IDC" if "USD" in tv_sym else "OANDA",
                    screener="forex",
                    interval=interval,
                    timeout=12,
                )
                try:
                    analysis = _tv_get_analysis_with_retry(handler, attempts=2)
                except Exception as e:
                    if "429" in str(e):
                        logger.critical(f"🚫 RATE LIMIT HIT (429) for {sym}. Triggering 15-minute global cooldown.")
                        IntelManager._global_cooldown_until = time.time() + 900 # 15 min
                        return None
                    raise e

                # ⚔️ NaN Safety Guard (v4.5)
                import math
                
                def safe_float(val, default=0.0):
                    if val is None: return default
                    try:
                        f = float(val)
                        return default if math.isnan(f) or math.isinf(f) else f
                    except: return default

                matrix[label] = {
                    "summary": analysis.summary['RECOMMENDATION'].replace("_", " "),
                    "ma": analysis.moving_averages['RECOMMENDATION'].replace("_", " "),
                    "osc": analysis.oscillators['RECOMMENDATION'].replace("_", " "),
                    "counts": {
                        "buy": int(analysis.summary.get('BUY', 0)),
                        "sell": int(analysis.summary.get('SELL', 0)),
                        "neutral": int(analysis.summary.get('NEUTRAL', 0))
                    },
                    "indicators": {
                        "rsi": round(safe_float(analysis.indicators.get("RSI"), 50), 2),
                        "adx": round(safe_float(analysis.indicators.get("ADX"), 20), 2),
                        "atr": round(safe_float(analysis.indicators.get("ATR"), 0), 6)
                    },
                    "pivots": {
                        "classic": {
                            "pivot": round(safe_float(analysis.indicators.get("Pivot.M.Classic.Middle")), 5),
                            "s1": round(safe_float(analysis.indicators.get("Pivot.M.Classic.S1")), 5),
                            "r1": round(safe_float(analysis.indicators.get("Pivot.M.Classic.R1")), 5),
                            "s2": round(safe_float(analysis.indicators.get("Pivot.M.Classic.S2")), 5),
                            "r2": round(safe_float(analysis.indicators.get("Pivot.M.Classic.R2")), 5)
                        },
                        "fibonacci": {
                            "pivot": round(safe_float(analysis.indicators.get("Pivot.M.Fibonacci.Middle")), 5),
                            "s1": round(safe_float(analysis.indicators.get("Pivot.M.Fibonacci.S1")), 5),
                            "r1": round(safe_float(analysis.indicators.get("Pivot.M.Fibonacci.R1")), 5)
                        }
                    },
                    "patterns": self.detect_candle_patterns(analysis.indicators)
                }
            
            # 2. Update Matrix Cache
            self._shared_cache[cache_key] = (now, matrix)
            return matrix
        except Exception as e:
            if "429" in str(e):
                logger.critical(f"🚫 RATE LIMIT HIT (429) during matrix loop. Cooldown activated.")
                IntelManager._global_cooldown_until = time.time() + 900
            else:
                logger.error(f"Failed to generate matrix for {sym}: {e}")
            return None

    def detect_candle_patterns(self, ind):
        """Detects high-impact candlestick patterns from the indicator feed."""
        patterns = []
        # TradingView indicators usually have pattern detection bits (1 or -1)
        # 1 = Bullish, -1 = Bearish
        pattern_map = {
            "CDL.Engulfing": "Engulfing",
            "CDL.Doji": "Doji",
            "CDL.Hammer": "Hammer",
            "CDL.ShootingStar": "Shooting Star",
            "CDL.MorningStar": "Morning Star",
            "CDL.EveningStar": "Evening Star"
        }
        for key, name in pattern_map.items():
            val = ind.get(key, 0)
            if val > 0: patterns.append(f"Bullish {name}")
            elif val < 0: patterns.append(f"Bearish {name}")
        
        return patterns[:3] # Top 3 detected

    def _get_yf_data(self, sym):
        """Fetches secondary market data from Yahoo Finance for confirmation."""
        import math
        try:
            yf_sym = sym.replace("/", "") + "=X"
            if "XAU" in sym.upper() or sym.upper() == "GOLD": 
                yf_sym = "GC=F" # Gold Futures as proxy
            
            ticker = yf.Ticker(yf_sym)
            info = ticker.fast_info
            
            price = float(info.last_price)
            if math.isnan(price): return None
            
            prev_close = float(info.previous_close) if info.previous_close else 0
            change_pct = 0.0
            if prev_close > 0:
                change_pct = ((price - prev_close) / prev_close) * 100
                if math.isnan(change_pct): change_pct = 0.0
            
            return {
                "price": round(price, 5),
                "change_pct": round(change_pct, 2),
                "high": round(float(info.day_high), 5) if not math.isnan(float(info.day_high)) else price,
                "low": round(float(info.day_low), 5) if not math.isnan(float(info.day_low)) else price
            }
        except Exception as e:
            logger.debug(f"Yahoo Finance fetch failed for {sym}: {e}")
            return None

    def analyze_news_strategy(self):
        """Pipes upcoming High/Medium impact news to Gemini for strategic risk analysis."""
        try:
            news_events = self.guards.get_upcoming_news()
            high_impact = [e for e in news_events if e['impact'] == 'High']
            
            if not high_impact: return
            
            # Format news for Gemini
            news_summary = "\n".join([f"- {e['title']} ({e['country']}) at {e['time']}" for e in high_impact])
            
            prompt = f"Analyzer Role: Macroeconomic Risk Specialist.\nConstraint: Provide TEXT ONLY actionable advice (max 2 sentences).\nData: Upcoming High Impact Economic News.\n\nNews Events:\n{news_summary}\n\nQuestion: How should a professional trader adjust their positions for these specific events? Give a direct warning for the most at-risk currencies."
            
            import subprocess
            try:
                process = subprocess.Popen(['gemini'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
                stdout, stderr = process.communicate(input=prompt, timeout=30)
                
                if "Quota exceeded" in stderr or "quota" in stderr.lower():
                    logger.warning("🕒 Gemini CLI Quota reached. News analysis deferred.")
                    return

                if stdout:
                    insight = {
                        "time": __import__('datetime').datetime.now().strftime("%H:%M"),
                        "reason": f"Strategic News Alert: {stdout.strip()}"
                    }
                    # Append to ai_memory.json
                    if os.path.exists("logs/ai_memory.json"):
                        with open("logs/ai_memory.json", "r+", encoding='utf-8') as f:
                            try:
                                data = json.load(f)
                                if not isinstance(data, list): data = []
                            except: data = []
                            data = [insight] + data
                            f.seek(0)
                            json.dump(data[:20], f, indent=4, ensure_ascii=False)
                            f.truncate()
                    else:
                        os.makedirs("logs", exist_ok=True)
                        with open("logs/ai_memory.json", "w", encoding='utf-8') as f:
                            json.dump([insight], f, indent=4, ensure_ascii=False)
            except subprocess.TimeoutExpired:
                logger.warning("⏳ Gemini CLI timed out. Skipping this news cycle.")
                process.kill()
            except Exception as e:
                logger.debug(f"Gemini call failed: {e}")
                        
        except Exception as e:
            logger.debug(f"News strategy analysis failed: {e}")

    def update_global_intelligence(self, symbols):
        """Fetches market data from TradingView to generate a Unified Macro Pulse WITHOUT Gemini Quota limits."""
        # 0. Automatically analyze news risk every 2 hours (approx) to save quota
        now_hour = __import__('datetime').datetime.now().hour
        if not hasattr(self, '_last_news_hour'):
            self._last_news_hour = -1 # First run trigger

        if self._last_news_hour != now_hour:
            if now_hour % 2 == 0 or self._last_news_hour == -1: # Analyze on even hours OR first run
                self.analyze_news_strategy()
                self._last_news_hour = now_hour
        
        # 0.5 Update Dashboard Audit Log on Session Status
        if not self.guards.is_session_active("EURUSD"):
             from core.decision_journal import DecisionJournal
             DecisionJournal.log("GLOBAL", "Registry", "PAUSE", "Institutional Session Closed - System in Observation Mode")
             
             insight = {
                "time": __import__('datetime').datetime.now().strftime("%H:%M"),
                "reason": "🛡️ MT5 SESSION: Market closed or no fresh quotes — Observe Only until MetaTrader session is active.",
             }
             if os.path.exists("logs/ai_memory.json"):
                with open("logs/ai_memory.json", "r+", encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        if not isinstance(data, list): data = []
                    except: data = []
                    # Only add if not the same as last one to avoid spam
                    if not data or data[0]["reason"] != insight["reason"]:
                        data = [insight] + data
                        f.seek(0)
                        json.dump(data[:20], f, indent=4, ensure_ascii=False)
                        f.truncate()

        logger.info(f"🧠 Updating Global Intelligence for {len(symbols)} symbols using External Scrapers...")
        
        full_intel = []
        from api.state import global_biases

        for sym in symbols:
            import MetaTrader5 as mt5
            mt5.symbol_select(sym, True)
            # 🏛️ Multi-Timeframe Institutional Intelligence
            if self.stop_event.is_set():
                logger.info("🛑 [INTEL] Shutdown detected. Aborting refresh.")
                break
            try:
                # 1. Fetch Snapshot (Internal for verification if needed, but TV is primary now)
                # We still update the biased locally for the bot logic
                bias = self.regime_detector.get_strategic_bias(sym)
                global_biases[sym] = bias
                logger.debug(f"📊 [BIAS] {sym}: {bias} (Internal Check)")

                # 1. Generate Institutional Matrix (Real-time Technical Alignment)
                # This also populates the cache for this symbol's timeframes
                matrix = self.get_institutional_matrix(sym)
                
                # 2. Derive General Intelligence from the 1H Matrix entry (Sovereign Efficiency)
                # This avoids making a separate redundant TV call for 1H summary
                matrix_1h = matrix.get("1H", {}) if matrix else {}
                
                if matrix_1h:
                    rec = matrix_1h.get("summary", "NEUTRAL")
                    buy_count = matrix_1h.get("counts", {}).get("buy", 0)
                    sell_count = matrix_1h.get("counts", {}).get("sell", 0)
                    total = buy_count + sell_count + matrix_1h.get("counts", {}).get("neutral", 0)
                    sentiment_score = int((buy_count / total) * 100) if total > 0 else 50
                    
                    # Indicators for AI Note
                    ind = matrix_1h.get("indicators", {})
                    rsi = ind.get("rsi", 50)
                    trend_note = "هبوطي قوي" if "STRONG" in rec and "SELL" in rec else "صعودي قوي" if "STRONG" in rec and "BUY" in rec else "محايد"
                    
                    note = (
                        f"تحليل تقني لزوج {sym}: الزخم {trend_note}. "
                        f"RSI عند {rsi:.1f} مما يشير إلى {'تشبع بيعي' if rsi < 30 else 'تشبع شرائي' if rsi > 70 else 'استقرار نسبى'}. "
                    )
                    
                    intel_obj = {
                        "pair": sym.upper(),
                        "technical_summary": rec,
                        "sentiment_score": sentiment_score,
                        "ai_note": note,
                        "matrix": matrix,
                        "investing_consensus": matrix.get("D", {}).get("summary", "NEUTRAL"),
                        "pivots": self._calculate_pivots(sym) # Add Pivot Radar 🎯
                    }
                else:
                    intel_obj = None

                # 3. Augment with Yahoo Finance Data (Secondary source)
                yf_obj = self._get_yf_data(sym)
                
                if intel_obj and yf_obj:
                    intel_obj["yf_stats"] = yf_obj
                    # Add a note about the daily move
                    change_str = "+" if yf_obj['change_pct'] > 0 else ""
                    intel_obj["ai_note"] += f" تحرك يومي: {change_str}{yf_obj['change_pct']:.2f}%."

                if intel_obj:
                    intel_obj["last_update"] = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M")
                    full_intel.append(intel_obj)
                    logger.info(f"✅ [SOVEREIGN INTEL] {sym}: {intel_obj['technical_summary']} (Score: {intel_obj['sentiment_score']})")
                else:
                    logger.warning("⚠️ TV matrix failed for %s — using MT5 OHLC fallback.", sym)
                    fb_matrix = build_matrix_from_mt5(self.mt, sym)
                    score = sentiment_from_matrix(fb_matrix)
                    rec = technical_summary_from_matrix(fb_matrix)
                    ind1h = (fb_matrix.get("1H") or {}).get("indicators", {})
                    rsi1 = float(ind1h.get("rsi", 50) or 50)
                    adx1 = float(ind1h.get("adx", 20) or 20)
                    note = (
                        f"MT5 fallback (TradingView/rate-limit unavailable). "
                        f"1H RSI≈{rsi1:.1f}, ADX≈{adx1:.1f}."
                    )
                    intel_obj = {
                        "pair": sym.upper(),
                        "technical_summary": rec,
                        "sentiment_score": score,
                        "ai_note": note,
                        "matrix": fb_matrix,
                        "matrix_source": "mt5_fallback",
                        "investing_consensus": (fb_matrix.get("D") or {}).get("summary", "NEUTRAL"),
                        "pivots": self._calculate_pivots(sym),
                        "last_update": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
                    }
                    yf_obj = self._get_yf_data(sym)
                    if yf_obj:
                        intel_obj["yf_stats"] = yf_obj
                        ch = "+" if yf_obj["change_pct"] > 0 else ""
                        intel_obj["ai_note"] += f" يومي: {ch}{yf_obj['change_pct']:.2f}%."
                    full_intel.append(intel_obj)
                    logger.info("✅ [MT5 INTEL] %s: %s (Score: %s)", sym, rec, score)

            except Exception as e:
                logger.error(f"Critical failure in Intel update for {sym}: {e}")
        
        if full_intel:
            # Sort by sentiment score (highest/lowest as high alert)
            full_intel.sort(key=lambda x: abs(x['sentiment_score'] - 50), reverse=True)
            
            with open(self.intel_path, "w", encoding='utf-8') as f:
                json.dump(full_intel, f, indent=4, ensure_ascii=False)
            
            logger.info(f"💾 Market Intelligence Saved & Synced: {len(full_intel)} signals processed.")
        
        return full_intel

    def _calculate_pivots(self, sym):
        """Calculates Classic and Fibonacci Pivot Points based on Yesterday's D1 candle."""
        import MetaTrader5 as mt5
        import math
        
        # Ensure symbol is active for data
        if not mt5.symbol_select(sym, True):
            return None
            
        # Force sync of D1 history
        rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_D1, 1, 1)
        if rates is None or len(rates) == 0:
            # Secondary attempt with a small wait/refresh
            mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 1) # Poke the server
            rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_D1, 1, 1)
            if rates is None or len(rates) == 0:
                return None
        
        last_d1 = rates[0]
        h, l, c = float(last_d1['high']), float(last_d1['low']), float(last_d1['close'])
        
        if math.isnan(h) or math.isnan(l) or math.isnan(c) or (h == l == c == 0):
            return None

        pivot = (h + l + c) / 3
        
        # Classic Levels
        r1 = (2 * pivot) - l
        r2 = pivot + (h - l)
        s1 = (2 * pivot) - h
        s2 = pivot - (h - l)
        
        # Fibonacci Levels
        fib_r1 = pivot + (h - l) * 0.382
        fib_s1 = pivot - (h - l) * 0.382
        
        return {
            "classic": {
                "pivot": round(pivot, 5),
                "r1": round(r1, 5), "r2": round(r2, 5),
                "s1": round(s1, 5), "s2": round(s2, 5)
            },
            "fibonacci": {
                "pivot": round(pivot, 5),
                "r1": round(fib_r1, 5),
                "s1": round(fib_s1, 5)
            }
        }
