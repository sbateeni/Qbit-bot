import os
from dotenv import load_dotenv
from core.telegram_notifier import TelegramNotifier

# Load credentials
load_dotenv()

def test_connection():
    print("--- Sending Apex v4.0 connection test ---")
    notifier = TelegramNotifier()
    
    if not notifier.enabled:
        print(f"FAILED: Telegram is NOT enabled. Token: '{notifier.token[:5]}...', ID: '{notifier.chat_id}'")
        return

    test_msg = (
        "🤖 <b>Qbit-Bot Apex v4.0 — Connected!</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "✅ Telegram Notification Engine: ONLINE\n"
        "🛡️ Emergency Fuse System: ARMED\n"
        "🧬 Weekly Auto-Optimizer: READY\n\n"
        "Your bot is now fully operational and linked to your phone. You will receive alerts here."
    )
    
    try:
        notifier.send(test_msg)
        print("SUCCESS! Check your Telegram.")
    except Exception as e:
        print(f"ERROR: Failed to send: {e}")

if __name__ == "__main__":
    test_connection()
