# Qbit Online Forex SaaS (Render)

## Architecture
- Render Static Web serves `dashboard`.
- Render Web Service serves FastAPI from `api/index.py`.
- Render Worker runs `worker/strategy_worker.py` continuously (24/7).
- Local DB client uses Redis (`REDIS_URL`) when available.
- FXCM executes demo/live trades for connected accounts.

## Required Environment Variables
- `REDIS_URL`
- `FXCM_ACCOUNT_ID`
- `FXCM_API_TOKEN`
- `FXCM_ENV` (`demo` or `live`)
- `WORKER_ACCOUNT_ID`
- `WORKER_STRATEGY`
- `WORKER_INTERVAL_SEC`
- `VITE_API_URL` (dashboard only, set to Render API URL)

## Deployment Flow
1. Push code to GitHub.
2. Create Render Blueprint from `render.yaml`.
3. Fill environment variables for API + Worker + Dashboard.
4. Set `VITE_API_URL` to your API service URL (example: `https://qbit-api.onrender.com`).
5. Verify:
   - `/api/health`
   - `/api/v2/ops/health`
   - worker logs in Render dashboard

## User Flow
1. User opens dashboard and links broker account.
2. User configures risk limits.
3. User starts strategy run.
4. Worker executes strategies continuously.

## Safety Defaults
- Strategy intent rejects symbols outside `allowed_instruments`.
- Strategy intent rejects volume above `max_position_size`.
- Start in demo mode until live approval.
