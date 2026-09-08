"""UNG-ATLAS capability registry extracted from the useful LAGRANGE discovery concept.
ATLAS remains the authoritative control-plane catalog; no new bridge service is introduced.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Iterable

@dataclass
class ServiceRecord:
    system_id: str
    name: str
    base_url: str
    capabilities: set[str] = field(default_factory=set)
    kind: str = "internal"
    active: bool = True
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CapabilityRegistry:
    def __init__(self):
        self._services: dict[str, ServiceRecord] = {}
        self._lock = RLock()

    def register(self, system_id: str, name: str, base_url: str, capabilities: Iterable[str], kind: str = "internal", active: bool = True) -> ServiceRecord:
        sid = system_id.strip().upper()
        if not sid.startswith("UNG-"):
            sid = "UNG-" + sid
        caps = {c.strip().lower() for c in capabilities if c and c.strip()}
        record = ServiceRecord(sid, name.strip() or sid, base_url.rstrip("/"), caps, kind, active)
        with self._lock:
            self._services[sid] = record
        return record

    def get(self, system_id: str) -> ServiceRecord | None:
        sid = system_id.strip().upper()
        if not sid.startswith("UNG-"):
            sid = "UNG-" + sid
        with self._lock:
            return self._services.get(sid)

    def discover(self, capability: str, active_only: bool = True) -> list[ServiceRecord]:
        cap = capability.strip().lower()
        with self._lock:
            rows = [r for r in self._services.values() if cap in r.capabilities and (r.active or not active_only)]
        return sorted(rows, key=lambda r: r.system_id)

    def list(self, active_only: bool = False) -> list[ServiceRecord]:
        with self._lock:
            rows = [r for r in self._services.values() if r.active or not active_only]
        return sorted(rows, key=lambda r: r.system_id)

registry = CapabilityRegistry()
