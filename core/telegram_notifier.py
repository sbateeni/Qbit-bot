import os
import logging
import requests
import json
from datetime import datetime

logger = logging.getLogger("TelegramNotifier")

class TelegramNotifier:
    """
    Qbit-Bot v4.0 — Telegram Notification Gateway
    Sends real-time alerts to your phone for every important trading event.
    
    Setup:
        1. Message @BotFather on Telegram → /newbot → get your TOKEN
        2. Message @userinfobot → get your CHAT_ID
        3. Add to .env:
           TELEGRAM_BOT_TOKEN=your_token_here
           TELEGRAM_CHAT_ID=your_chat_id_here
    """

    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.token and self.chat_id)
        self.notified_file = "logs/notified_trades.json"
        
        if not self.enabled:
            logger.info("📱 Telegram: Not configured (TELEGRAM_BOT_TOKEN missing in .env). Skipping.")

    def _get_notified_ids(self):
        if not os.path.exists(self.notified_file):
            os.makedirs("logs", exist_ok=True)
            with open(self.notified_file, "w") as f:
                json.dump({"open": [], "closed": []}, f)
            return {"open": [], "closed": []}
        try:
            with open(self.notified_file, "r") as f:
                return json.load(f)
        except:
            return {"open": [], "closed": []}

    def _mark_as_notified(self, trade_id, context="open"):
        data = self._get_notified_ids()
        if trade_id not in data[context]:
            data[context].append(trade_id)
            # Keep only last 500 to save memory
            data[context] = data[context][-500:]
            with open(self.notified_file, "w") as f:
                json.dump(data, f)

    def send(self, message: str):
        """Sends a raw message to Telegram."""
        if not self.enabled:
            return
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            logger.warning(f"📱 Telegram send failed: {e}")

    def send_trade_open(self, symbol: str, direction: str, price: float, lot: float, reason: str = ""):
        emoji = "🟢" if direction.upper() == "BUY" else "🔴"
        dir_ar = "شراء" if direction.upper() == "BUY" else "بيع"
        now = datetime.now().strftime("%H:%M:%S")
        self.send(
            f"{emoji} <b>تم فتح صفقة جديدة</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"📌 الزوج: <b>{symbol}</b>\n"
            f"📐 الاتجاه: <b>{dir_ar}</b>\n"
            f"💰 السعر: <b>{price}</b>\n"
            f"📦 الحجم: <b>{lot} لوط</b>\n"
            f"🧠 السبب: {reason}\n"
            f"🕐 الوقت: {now}"
        )
        if hasattr(self, '_current_ticket'):
             self._mark_as_notified(self._current_ticket, "open")


    def send_trade_close(self, symbol: str, profit: float, reason: str = ""):
        emoji = "✅" if profit >= 0 else "❌"
        res_ar = "ربح" if profit >= 0 else "خسارة"
        profit_str = f"+${profit:.2f}" if profit >= 0 else f"-${abs(profit):.2f}"
        now = datetime.now().strftime("%H:%M:%S")
        self.send(
            f"{emoji} <b>تم إغلاق الصفقة ({res_ar})</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"📌 الزوج: <b>{symbol}</b>\n"
            f"💵 النتيجة: <b>{profit_str}</b>\n"
            f"📋 السبب: {reason}\n"
            f"🕐 الوقت: {now}"
        )
        if hasattr(self, '_current_deal'):
             self._mark_as_notified(self._current_deal, "closed")


    def send_panic(self, total_positions: int):
        self.send(
            f"🚨 <b>تفعيل وضع الطوارئ (PANIC)</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"🛑 تم إغلاق جميع الصفقات المفتوحة ({total_positions}).\n"
            f"🛡️ تم تفعيل حامي السيولة وتجميد الحساب.\n"
            f"🕐 الوقت: {datetime.now().strftime('%H:%M:%S')}"
        )

    def send_drawdown_alert(self, current_dd: float, limit: float):
        self.send(
            f"⚠️ <b>تحذير: تراجع الحساب (Drawdown)</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"📉 التراجع الحالي: <b>{current_dd:.2f}%</b>\n"
            f"🚧 الحد الأقصى: <b>{limit:.1f}%</b>\n"
            f"🕐 الوقت: {datetime.now().strftime('%H:%M:%S')}"
        )

    def send_daily_report(self, total_profit: float, trades: int, win_rate: float):
        emoji = "📈" if total_profit >= 0 else "📉"
        self.send(
            f"{emoji} <b>التقرير اليومي للأداء</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"💵 صافي الربح/الخسارة: <b>${total_profit:+.2f}</b>\n"
            f"🔢 عدد الصفقات: <b>{trades}</b>\n"
            f"🎯 نسبة النجاح: <b>{win_rate:.0f}%</b>\n"
            f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d')}"
        )
