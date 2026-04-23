import logging
import os
import time
import requests
import xml.etree.ElementTree as ET
import datetime
import MetaTrader5 as mt5

logger = logging.getLogger("ScalperGuards")

class TradingGuards:
    """
    Session = MetaTrader market state (quotes + trade mode), not local PC clock.
    """
    MAX_GLOBAL_POSITIONS = 5
    # Fallback symbols if the requested one is not in Market Watch
    _SESSION_FALLBACKS = ("EURUSD", "GBPUSD", "USDJPY", "GOLD", "XAUUSD")

    _cached_news = None
    _news_last_fetched = None

    @staticmethod
    def _max_tick_age_sec() -> float:
        try:
            return float(os.getenv("MT5_MAX_TICK_AGE_SEC", "300"))
        except ValueError:
            return 300.0

    @staticmethod
    def is_session_active(symbol: str | None = None) -> bool:
        """
        True when MT5 is connected and the symbol (or a liquid fallback) has
        a fresh tick and trading is not DISABLED — i.e. broker session is effectively open.
        """
        term = mt5.terminal_info()
        if term is None or not term.connected:
            return False

        preferred = (symbol or os.getenv("MT5_SESSION_REFERENCE", "EURUSD")).upper().replace("/", "")
        candidates = (preferred,) + tuple(
            s for s in TradingGuards._SESSION_FALLBACKS if s.upper() != preferred
        )

        for sym in candidates:
            if not mt5.symbol_select(sym, True):
                continue
            info = mt5.symbol_info(sym)
            if info is None:
                continue
            if int(info.trade_mode) == int(mt5.SYMBOL_TRADE_MODE_DISABLED):
                continue
            if int(info.trade_mode) == int(mt5.SYMBOL_TRADE_MODE_CLOSEONLY):
                continue
            tick = mt5.symbol_info_tick(sym)
            if tick is None:
                continue
            age = time.time() - float(tick.time)
            if age > TradingGuards._max_tick_age_sec():
                logger.debug("MT5 session: stale tick %.0fs on %s", age, sym)
                continue
            return True

        logger.info("MT5 session: no tradable symbol with fresh quotes (tried %s)", preferred)
        return False

    @staticmethod
    def can_open_more():
        """Checks if scalper-specific position cap is reached. Ignores Swing trades (magic 777777)."""
        all_pos = mt5.positions_get()
        # Only count scalper positions — swing positions (777777) are sandboxed
        scalper_count = sum(1 for p in (all_pos or []) if p.magic != 777777)
        return scalper_count < TradingGuards.MAX_GLOBAL_POSITIONS

    @staticmethod
    def is_spread_valid(mt5_mgr, symbol, limit):
        """Checks if market spread is within acceptable limits. Dynamic for Gold."""
        # Gold spread is naturally higher (points-wise). Adjusting limit for Gold.
        is_gold = "XAU" in symbol.upper() or "GOLD" in symbol.upper()
        effective_limit = limit * 4 if is_gold else limit # Allow ~40pips for Gold vs 10 for FX
        
        return mt5_mgr.is_spread_safe(symbol, max_spread_pips=effective_limit)

    @staticmethod
    def is_news_safe(symbol, pause_mins_before=15, pause_mins_after=15):
        """Checks for High Impact news on the symbol's currencies using ForexFactory XML."""
        now = datetime.datetime.now()
        
        # Refresh API cache every 4 hours to save bandwidth
        if not TradingGuards._cached_news or not TradingGuards._news_last_fetched or (now - TradingGuards._news_last_fetched).total_seconds() > 14400:
            try:
                res = requests.get('https://nfs.faireconomy.media/ff_calendar_thisweek.xml', timeout=5)
                if res.status_code == 200:
                    TradingGuards._cached_news = ET.fromstring(res.content)
                    TradingGuards._news_last_fetched = now
                    logger.info("📅 Economic Calendar (News Engine) updated successfully.")
            except Exception as e:
                logger.error(f"Failed to fetch news calendar: {e}")
                return True # Default to safe if API is down
                
        if not TradingGuards._cached_news: return True

        base, quote = symbol[:3].upper(), symbol[3:6].upper()
        # v4.0 Apex: Also monitor USD as a global risk factor for all pairs
        currencies_to_watch = {base, quote, "USD"}
        
        for event in TradingGuards._cached_news.findall('event'):
            impact = event.find('impact').text.strip() if event.find('impact') is not None else ''
            country = event.find('country').text.strip() if event.find('country') is not None else ''
            
            # Target High impact (red) news
            if impact == 'High' and country in currencies_to_watch:
                time_str = event.find('time').text.strip() if event.find('time') is not None else ''
                date_str = event.find('date').text.strip() if event.find('date') is not None else ''
                
                if time_str.lower() in ['all day', 'tentative', '']:
                    continue
                
                try:
                    # FF time is EST.
                    event_dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%m-%d-%Y %I:%M%p")
                    # Simplified conversion: EST is UTC-5 (or UTC-4 in DST).
                    # We use a 7-hour offset to reach OS Local (Assuming UTC+3)
                    event_dt_local = event_dt + datetime.timedelta(hours=7) 
                    
                    time_diff_mins = (event_dt_local - now).total_seconds() / 60.0
                    
                    if -pause_mins_after <= time_diff_mins <= pause_mins_before:
                        news_title = event.find('title').text if event.find('title') is not None else 'News'
                        logger.warning(f"🚨 NEWS SHIELD: '{news_title}' ({country}) active. Trading HALTED.")
                        return False
                except Exception: continue

        return True

    @staticmethod
    def get_upcoming_news():
        """Returns a list of parsed upcoming news events for the dashboard."""
        if not TradingGuards._cached_news:
            TradingGuards.is_news_safe("EURUSD") # Force a fetch if empty
        if not TradingGuards._cached_news: return []
        
        events_list = []
        now = datetime.datetime.now()
        
        for event in TradingGuards._cached_news.findall('event'):
            impact = event.find('impact').text.strip() if event.find('impact') is not None else ''
            country = event.find('country').text.strip() if event.find('country') is not None else ''
            title = event.find('title').text.strip() if event.find('title') is not None else ''
            date_str = event.find('date').text.strip() if event.find('date') is not None else ''
            time_str = event.find('time').text.strip() if event.find('time') is not None else ''
            
            if impact not in ['High', 'Medium']: continue # Filter out low impact
            if time_str.lower() in ['all day', 'tentative', '']: continue
            
            try:
                event_dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%m-%d-%Y %I:%M%p")
                event_dt_local = event_dt + datetime.timedelta(hours=7)
                
                # Only show news happening in the last hour or upcoming
                if event_dt_local > now - datetime.timedelta(hours=1):
                    events_list.append({
                        "impact": impact,
                        "country": country,
                        "title": title,
                        "time": event_dt_local.strftime("%I:%M %p"),
                        "timestamp": event_dt_local.timestamp()
                    })
            except: continue
        
        # Sort chronologically
        events_list.sort(key=lambda x: x["timestamp"])
        return events_list[:10] # Return the next 10 important events
