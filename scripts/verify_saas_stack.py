import os
import json
from urllib import request


def check(url: str):
    try:
        with request.urlopen(url, timeout=10) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except Exception as exc:
        return 0, {"error": str(exc)}


if __name__ == "__main__":
    base = os.getenv("VERIFY_BASE_URL", "http://127.0.0.1:8000")
    targets = [
        f"{base}/api/health",
        f"{base}/api/v2/ops/health",
    ]
    for t in targets:
        code, payload = check(t)
        print(f"{t} -> {code}")
        print(payload)
