import logging
import datetime
import os
import sys
from api.state import log_buffer

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")


class LogCollector(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        log_buffer.append({
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "msg": msg,
            "level": record.levelname
        })

def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    os.makedirs(LOG_DIR, exist_ok=True)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)

    collector = LogCollector()
    collector.setLevel(logging.INFO)
    collector.setFormatter(fmt)

    for h in list(root.handlers):
        root.removeHandler(h)
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    root.addHandler(fh)
    root.addHandler(collector)
