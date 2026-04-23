import threading
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.state import stop_event
from api.logger_config import setup_logging
from api.trading_engine import run_scalper_loop
from api.router import router

app = FastAPI(title="Qbit-bot Integrated Core")

# 🛡️ Security / CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🛤️ Include Modular Routes
app.include_router(router)

@app.get("/safety-stop")
def get_safety_stop():
    import json
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            return {"stop": config.get("safety_stop_usd", 1.0)}
    except:
        return {"stop": 1.0}

@app.post("/safety-stop")
def set_safety_stop(data: dict):
    import json
    new_stop = data.get("stop", 1.0)
    try:
        config = {}
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
        except: pass
        
        config["safety_stop_usd"] = float(new_stop)
        with open("config.json", "w") as f:
            f.write(json.dumps(config, indent=4))
        return {"message": f"Safety stop set to ${new_stop}", "stop": new_stop}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/market-intelligence")
def get_market_intelligence():
    """Returns deep sentiment data from Investing.com & AI analysis."""
    import json
    try:
        with open("logs/market_intel.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"technical_summary": "Neutral", "sentiment_score": 50, "ai_note": "Awaiting fresh data..."}

@app.get("/news")
def get_market_news():
    """Fetches high-impact economic news from DailyFX RSS feed."""
    import feedparser
    try:
        feed = feedparser.parse("https://www.dailyfx.com/feeds/market-alert")
        news_items = []
        for entry in feed.entries[:8]: # Last 8 news
            news_items.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.published if hasattr(entry, 'published') else "Just now"
            })
        return {"news": news_items}
    except Exception as e:
        return {"news": [{"title": "News Feed currently unavailable.", "link": "#", "published": ""}]}

# 🚂 Global thread reference for clean shutdown
trading_thread = None

@app.on_event("startup")
async def startup_event():
    global trading_thread
    setup_logging()
    trading_thread = threading.Thread(target=run_scalper_loop, daemon=True)
    trading_thread.start()

@app.on_event("shutdown")
def shutdown_event():
    import logging
    logger = logging.getLogger("Shutdown")
    logger.info("🛑 [SHUTDOWN] Signal received. Disarming engines...")
    
    # 1. Signal all loops to stop
    stop_event.set()
    
    # 2. Wait for the main trading thread to exit gracefully
    if trading_thread and trading_thread.is_alive():
        logger.info("⏳ [SHUTDOWN] Waiting for trading engine to park assets...")
        trading_thread.join(timeout=5.0) # Avoid hanging indefinitely
        
    logger.info("✅ [SHUTDOWN] All systems parked. Safe to terminate.")

# Run with: uvicorn api.main:app --reload
