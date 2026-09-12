from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

def utcnow(): return datetime.now(timezone.utc).isoformat()

@dataclass(frozen=True)
class TestEnvelope:
    test_run_id: str
    sequence: int
    entity_id: str
    test_mode: bool = True
    synthetic: bool = True
    timestamp: str = field(default_factory=utcnow)
    def __post_init__(self):
        if not self.entity_id.startswith(("MOCK-","TEST-")): raise ValueError("reserved_test_id_required")

@dataclass(frozen=True)
class SyntheticEvent:
    envelope: TestEnvelope
    family: str
    scenario: str
    source_system: str
    capability: str
    correlation_id: str
    payload: dict[str, Any]
    fault: str | None = None

@dataclass
class EventResult:
    event: SyntheticEvent
    destination_system: str | None
    status: str
    latency_ms: float
    retries: int = 0
    failure_reason: str | None = None
    duplicate_suppressed: bool | None = None
    consistency_ok: bool | None = None
    recovery_ok: bool | None = None
    response: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ScenarioDefinition:
    name: str
    family: str
    capability: str
    expected_status: str = "accepted"
    timeout_seconds: float = 3.0
    retry_allowance: int = 1

@dataclass(frozen=True)
class RunConfig:
    run_id: str
    event_count: int = 10_000
    seed: int = 20260912
    dry_run: bool = True
    def __post_init__(self):
        if self.event_count < 1: raise ValueError("event_count_must_be_positive")
        if not self.dry_run: raise ValueError("run1_requires_dry_run")

@dataclass
class RunSummary:
    run_id: str
    attempted: int
    completed: int
    failed: int
    started_at: str
    finished_at: str
    duration_seconds: float
