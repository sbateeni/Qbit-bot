import os
import time
import logging

from core.broker_factory import get_broker_for_account
from core.database_client import db_client
from core.mt5_bridge import MT5Manager


logger = logging.getLogger("QbitBot.Worker")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def _env_symbols():
    raw = os.getenv("WORKER_SYMBOLS", "EURUSD,GBPUSD,USDJPY")
    return [x.strip() for x in raw.split(",") if x.strip()]


def run_worker_once():
    mt5_manager = MT5Manager()
    account_id = os.getenv("WORKER_ACCOUNT_ID", "")
    strategy = os.getenv("WORKER_STRATEGY", "smart_scalper")
    if not account_id:
        logger.info("WORKER_ACCOUNT_ID missing, worker idle")
        return

    runs = [r for r in db_client.list_strategy_runs(account_id) if r.get("status") == "running" and r.get("strategy") == strategy]
    if not runs:
        logger.info("No running strategy runs for account=%s strategy=%s", account_id, strategy)
        return

    broker = get_broker_for_account(account_id, mt5_manager)
    prices = broker.get_prices(_env_symbols())
    logger.info("Worker tick account=%s strategy=%s prices=%s", account_id, strategy, list(prices.keys()))


def run_forever():
    interval = int(os.getenv("WORKER_INTERVAL_SEC", "5"))
    while True:
        try:
            run_worker_once()
        except Exception as exc:
            logger.exception("Worker cycle failed: %s", exc)
        time.sleep(interval)


if __name__ == "__main__":
    run_forever()
