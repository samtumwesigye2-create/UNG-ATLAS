import json
import os
import time
import urllib.request
from datetime import datetime, timezone


def send_once():
    base = os.getenv("PULSAR_BASE_URL", "").rstrip("/")
    api_key = os.getenv("PULSAR_API_KEY", "")
    if not base or not api_key:
        return
    body = json.dumps({
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
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }).encode("utf-8")
    req = urllib.request.Request(
        base + "/events",
        data=body,
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        response.read()


while True:
    try:
        send_once()
    except Exception:
        pass
    time.sleep(60)
