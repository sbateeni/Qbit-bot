import datetime
import logging

logger = logging.getLogger("SwingGuards")

class SwingGuards:
    """
    Independent guards for the Swing Investor strategy.
    Completely separate from ScalperGuards — different timing logic,
    different risk philosophy (macro, news-FRIENDLY, not session-limited).
    """

    @staticmethod
    def is_market_open() -> bool:
        """
        Swing trading operates ANY time the market is open:
        - Monday 00:00 → Friday 23:59 (no session windows)
        - Stops ONLY on full weekend close (Saturday & Sunday)
        Unlike scalping, swing WANTS to be around during news events.
        """
        now = datetime.datetime.now()
        # Saturday = 5, Sunday = 6
        if now.weekday() >= 5:
            return False
        return True

    @staticmethod
    def count_open_swing_positions(magic: int, symbol: str = None) -> int:
        """
        Returns the number of active swing trades.
        If symbol is provided, counts for that symbol.
        Otherwise, counts ALL swing trades across the portfolio (Global).
        Returns 999 on error to safely block trading until connection is restored.
        """
        count = 0
        try:
            import MetaTrader5 as mt5
            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            if positions is None: # Possible connection error or timeout
                 return 999
            for p in positions:
                if p.magic == magic:
                    count += 1
            return count
        except:
            return 999

    @staticmethod
    def is_confidence_sufficient(confidence: int, threshold: int) -> bool:
        """
        Swing only fires when institutional confidence meets user threshold.
        Default: 80% — configurable via dashboard.
        """
        return confidence >= threshold

    @staticmethod
    def is_signal_strong(summary: str) -> str | None:
        """
        Returns 'buy', 'sell', or None based on Investing.com summary.
        Only 'Strong Buy' or 'Strong Sell' qualifies — neutral signals are ignored.
        """
        upper = summary.upper()
        if "STRONG BUY" in upper:
            return "buy"
        elif "STRONG SELL" in upper:
            return "sell"
        return None
