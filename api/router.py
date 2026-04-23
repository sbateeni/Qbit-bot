from fastapi import APIRouter
from api.routes import trading, config, intelligence, audit

# Sovereign Integrated Router v5.0
# Consolidates all modular sub-routes into a single entry point
router = APIRouter()

# 🛡️ Trading & Account Operations
router.include_router(trading.router)

# ⚙️ Configuration & Parameter Tuning
router.include_router(config.router)

# 🧠 Market Intelligence & Sentiment
router.include_router(intelligence.router)

# 🕵️ Audit, Diagnostics & Logs
router.include_router(audit.router)
