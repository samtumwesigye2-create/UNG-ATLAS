from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from datetime import datetime, timezone


def send_heartbeat() -> bool:
    base = os.getenv("PULSAR_BASE_URL", "").rstrip("/")
    api_key = os.getenv("PULSAR_API_KEY", "")
    if not base or not api_key:
        return False

    payload = {
        "category": "system_metric",
        "source": "atlas",
        "severity": "info",
        "actor": "UNG-ATLAS",
        "action": "heartbeat",
        "resource": "control_infrastructure",
        "status": "online",
        "payload": {
            "service": "UNG-ATLAS",
            "environment": "production",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    request = urllib.request.Request(
        base + "/events",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        response.read()
    return True


def _loop() -> None:
    while True:
        try:
            send_heartbeat()
        except Exception:
            pass
        time.sleep(60)


def start_heartbeat() -> None:
    threading.Thread(target=_loop, name="pulsar-heartbeat", daemon=True).start()
