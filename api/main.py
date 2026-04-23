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

# 🛤️ Include Modular Routes with /api prefix for dashboard compatibility
app.include_router(router, prefix="/api")

# Routes moved to central router for consistent /api prefixing

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
