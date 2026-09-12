# UNG Whole-Network Mock Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, test-safe UNG-ATLAS harness that generates and executes 10,000 synthetic network events, injects bounded failures, measures cross-system behavior, and produces a technical capability/readiness report.

**Architecture:** Add an isolated `network_test` package to UNG-ATLAS. The package uses the existing ATLAS capability registry as the control-plane source of truth, generates deterministic correlated journeys, routes only through explicitly test-safe adapters, records per-event evidence, aggregates metrics, and emits JSON/Markdown reports. Run 1 defaults to dry-run and forbids production-impacting dispatch.

**Tech Stack:** Python 3, FastAPI, standard library (`dataclasses`, `random`, `statistics`, `json`, `time`, `uuid`, `urllib`), pytest.

**Spec:** `docs/superpowers/specs/2026-09-12-whole-network-mock-test-design.md`

## Global Constraints

- First run target: exactly 10,000 synthetic events.
- Every synthetic event must include `test_mode=true`, `synthetic=true`, `test_run_id`, deterministic synthetic IDs, timestamp, and sequence number.
- Default execution is dry-run/test-safe; production-impacting actions are out of scope for Run 1.
- Dispatch is refused unless the destination adapter is explicitly marked `test_safe=True`.
- Synthetic entities use reserved `MOCK-` or `TEST-` prefixes.
- No new bridge/integration bus is introduced; ATLAS remains orchestration/reporting control plane.
- Results must distinguish demonstrated capabilities from untested capabilities.
- Run 1 includes normal flow, auth/security rejection, ZIP/address failures, duplicates, ordering faults, inventory shortage, delay/timeout, dependency failure, malformed payload, stale/offline replay.

---

### Task 1: Core models and deterministic event envelope

**Files:**
- Create: `network_test/__init__.py`
- Create: `network_test/models.py`
- Create: `tests/test_network_test_models.py`

**Interfaces:**
- Produces: `TestEnvelope`, `SyntheticEvent`, `EventResult`, `ScenarioDefinition`, `RunConfig`, `RunSummary` dataclasses.

- [ ] **Step 1: Write failing model tests**

```python
from network_test.models import TestEnvelope, SyntheticEvent


def test_envelope_is_always_synthetic_and_test_mode():
    env = TestEnvelope(test_run_id="RUN-1", sequence=7, entity_id="MOCK-ORDER-000007")
    assert env.test_mode is True
    assert env.synthetic is True
    assert env.test_run_id == "RUN-1"
    assert env.sequence == 7
    assert env.entity_id.startswith("MOCK-")


def test_event_carries_correlation_and_family():
    event = SyntheticEvent(
        envelope=TestEnvelope("RUN-1", 1, "MOCK-ORDER-000001"),
        family="operations",
        scenario="shipment_journey",
        source_system="UNG-CORE",
        capability="shipment-create",
        correlation_id="CORR-000001",
        payload={"order_id": "MOCK-ORDER-000001"},
    )
    assert event.correlation_id == "CORR-000001"
    assert event.family == "operations"
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest -q tests/test_network_test_models.py`
Expected: FAIL because `network_test.models` does not exist.

- [ ] **Step 3: Implement models**

```python
# network_test/models.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TestEnvelope:
    test_run_id: str
    sequence: int
    entity_id: str
    test_mode: bool = True
    synthetic: bool = True
    timestamp: str = field(default_factory=utcnow)


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


@dataclass
class RunSummary:
    run_id: str
    attempted: int
    completed: int
    failed: int
    started_at: str
    finished_at: str
    duration_seconds: float
```

- [ ] **Step 4: Run tests and verify GREEN**

Run: `pytest -q tests/test_network_test_models.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add network_test tests/test_network_test_models.py
git commit -m "feat: add network test core models"
```

---

### Task 2: Deterministic 10,000-event generator and weighted load model

**Files:**
- Create: `network_test/generators.py`
- Create: `tests/test_network_test_generators.py`

**Interfaces:**
- Consumes: `RunConfig`, `TestEnvelope`, `SyntheticEvent`.
- Produces: `generate_events(config: RunConfig) -> list[SyntheticEvent]`.

- [ ] **Step 1: Write failing generator tests**

```python
from collections import Counter
from network_test.generators import generate_events
from network_test.models import RunConfig


def test_10000_event_generation_is_deterministic():
    cfg = RunConfig(run_id="RUN-A", event_count=10_000, seed=42)
    a = generate_events(cfg)
    b = generate_events(cfg)
    assert len(a) == 10_000
    assert [(x.family, x.scenario, x.payload) for x in a] == [(x.family, x.scenario, x.payload) for x in b]


def test_load_mix_matches_contract_exactly_for_10000():
    events = generate_events(RunConfig(run_id="RUN-A", event_count=10_000, seed=42))
    counts = Counter(x.family for x in events)
    assert counts == {
        "operations": 5500,
        "identity": 1500,
        "routing": 1000,
        "inventory": 1000,
        "finance": 500,
        "fault": 500,
    }


def test_all_entities_are_reserved_test_ids():
    events = generate_events(RunConfig(run_id="RUN-A", event_count=100, seed=42))
    assert all(e.envelope.entity_id.startswith(("MOCK-", "TEST-")) for e in events)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest -q tests/test_network_test_generators.py`
Expected: FAIL because generator is missing.

- [ ] **Step 3: Implement deterministic generator**

Implement exact family weights using integer quotas, deterministic `random.Random(seed)`, deterministic correlation IDs, reserved IDs, and scenario templates for shipment flow, driver shift, auth denial, ZIP validation, inventory, finance, and fault families. For non-10,000 counts, allocate by largest-remainder so totals equal `event_count` exactly.

Core public signature:

```python
def generate_events(config: RunConfig) -> list[SyntheticEvent]:
    ...
```

Each generated event must set `source_system`, `capability`, `correlation_id`, family/scenario, and a compact synthetic payload appropriate to the scenario.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `pytest -q tests/test_network_test_generators.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add network_test/generators.py tests/test_network_test_generators.py
git commit -m "feat: generate deterministic network mock load"
```

---

### Task 3: Scenario catalog and correlated business journeys

**Files:**
- Create: `network_test/scenarios.py`
- Create: `tests/test_network_test_scenarios.py`

**Interfaces:**
- Produces: `SCENARIOS: dict[str, ScenarioDefinition]`, `validate_correlation(events) -> dict[str, bool]`.

- [ ] **Step 1: Write failing journey tests**

```python
from network_test.scenarios import SCENARIOS, validate_correlation
from network_test.generators import generate_events
from network_test.models import RunConfig


def test_required_journeys_exist():
    required = {"shipment_journey", "driver_shift", "inventory_exception", "auth_denial", "dependency_recovery"}
    assert required <= set(SCENARIOS)


def test_generated_events_have_traceable_correlations():
    events = generate_events(RunConfig("RUN-X", event_count=1000, seed=9))
    result = validate_correlation(events)
    assert result
    assert all(result.values())
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_network_test_scenarios.py`
Expected: FAIL.

- [ ] **Step 3: Implement scenario definitions and correlation validation**

Define the five required journey families and a validator that rejects blank correlation IDs, cross-run correlation collisions, and non-test identifiers.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_network_test_scenarios.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add network_test/scenarios.py tests/test_network_test_scenarios.py
git commit -m "feat: add correlated network test journeys"
```

---

### Task 4: Test-safe adapter layer and hard dispatch guard

**Files:**
- Create: `network_test/adapters.py`
- Create: `tests/test_network_test_adapters.py`

**Interfaces:**
- Consumes: ATLAS `CapabilityRegistry` records.
- Produces: `AdapterSpec`, `AdapterRegistry`, `UnsafeDispatchError`, `dispatch_dry_run(event, adapter)`.

- [ ] **Step 1: Write failing safety tests**

```python
import pytest
from network_test.adapters import AdapterRegistry, AdapterSpec, UnsafeDispatchError


def test_unmarked_destination_is_never_dispatchable():
    reg = AdapterRegistry()
    reg.register(AdapterSpec(system_id="UNG-CORE", capability="shipment-create", base_url="https://example", test_safe=False))
    with pytest.raises(UnsafeDispatchError):
        reg.require_safe("UNG-CORE", "shipment-create")


def test_test_safe_destination_is_allowed():
    reg = AdapterRegistry()
    reg.register(AdapterSpec(system_id="UNG-CORE", capability="shipment-create", base_url="", test_safe=True))
    assert reg.require_safe("UNG-CORE", "shipment-create").test_safe is True
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_network_test_adapters.py`
Expected: FAIL.

- [ ] **Step 3: Implement adapter registry**

Adapter entries must include `system_id`, `capability`, `base_url`, `path`, `method`, and `test_safe`. `require_safe()` must fail closed if no adapter is configured or `test_safe` is false. Run 1 uses dry-run adapters only; HTTP side effects remain disabled.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_network_test_adapters.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add network_test/adapters.py tests/test_network_test_adapters.py
git commit -m "feat: add fail-closed test-safe adapters"
```

---

### Task 5: Fault injection and runner

**Files:**
- Create: `network_test/runner.py`
- Create: `tests/test_network_test_runner.py`

**Interfaces:**
- Consumes: generated events and adapter registry.
- Produces: `NetworkTestRunner.run(config) -> tuple[list[EventResult], RunSummary]`.

- [ ] **Step 1: Write failing runner tests**

```python
from network_test.models import RunConfig
from network_test.runner import NetworkTestRunner


def test_runner_completes_exact_requested_count():
    results, summary = NetworkTestRunner().run(RunConfig("RUN-10", event_count=250, seed=4))
    assert len(results) == 250
    assert summary.attempted == 250
    assert summary.completed + summary.failed == 250


def test_duplicate_and_bad_auth_are_classified_not_crashed():
    results, _ = NetworkTestRunner().run(RunConfig("RUN-F", event_count=1000, seed=4))
    reasons = {r.failure_reason for r in results if r.failure_reason}
    assert "unauthorized" in reasons or "duplicate" in reasons
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_network_test_runner.py`
Expected: FAIL.

- [ ] **Step 3: Implement dry-run execution semantics**

Implement bounded fault classification for `invalid_zip`, `unauthorized`, `duplicate`, `out_of_order`, `inventory_shortage`, `delayed_ack`, `dependency_unavailable`, `timeout_recovery`, `malformed_payload`, and `stale_offline_replay`. Use deterministic latency derived from the event sequence/seed; do not sleep during tests. Duplicate replay sets `duplicate_suppressed=True`. Recovery cases set `recovery_ok=True` when the simulated retry succeeds.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_network_test_runner.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add network_test/runner.py tests/test_network_test_runner.py
git commit -m "feat: execute dry-run network scenarios and faults"
```

---

### Task 6: Metrics, capability grading, and readiness score

**Files:**
- Create: `network_test/metrics.py`
- Create: `tests/test_network_test_metrics.py`

**Interfaces:**
- Produces: `aggregate_metrics(results) -> dict`, `grade_systems(results, advertised_capabilities) -> dict`, `readiness_score(metrics) -> float`.

- [ ] **Step 1: Write failing metric tests**

```python
from network_test.metrics import percentile, readiness_score


def test_percentile_is_stable():
    assert percentile([10, 20, 30, 40, 50], 0.50) == 30
    assert percentile([10, 20, 30, 40, 50], 0.95) == 50


def test_readiness_score_is_bounded():
    score = readiness_score({
        "success_rate": 0.98,
        "security_correctness": 1.0,
        "recovery_rate": 0.95,
        "consistency_rate": 0.99,
        "duplicate_suppression_rate": 1.0,
    })
    assert 0 <= score <= 100
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_network_test_metrics.py`
Expected: FAIL.

- [ ] **Step 3: Implement metrics**

Aggregate attempted/completed/failed, success rate, p50/p95/p99 latency, retries, duplicate suppression, consistency violations, security rejection correctness, recovery rate, throughput, family/scenario/system breakdowns. Capability grading must mark capabilities as `demonstrated`, `failed`, or `untested`; never infer success from registry advertisement alone.

Use a transparent readiness score weighting:

```python
score = 100 * (
    0.30 * success_rate
    + 0.20 * consistency_rate
    + 0.15 * security_correctness
    + 0.15 * recovery_rate
    + 0.10 * duplicate_suppression_rate
    + 0.10 * performance_factor
)
```

Clamp to `[0, 100]`.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_network_test_metrics.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add network_test/metrics.py tests/test_network_test_metrics.py
git commit -m "feat: score network test evidence"
```

---

### Task 7: JSON and Markdown technical report

**Files:**
- Create: `network_test/reporting.py`
- Create: `tests/test_network_test_reporting.py`

**Interfaces:**
- Produces: `build_report(config, results, summary, registry_records) -> dict`, `render_markdown(report) -> str`.

- [ ] **Step 1: Write failing report test**

```python
from network_test.reporting import render_markdown


def test_markdown_contains_required_sections():
    text = render_markdown({
        "run": {"run_id": "RUN-1", "event_count": 10000},
        "overall_readiness_score": 91.2,
        "aggregate": {},
        "journeys": {},
        "systems": {},
        "findings": [],
        "limits": ["Run 1 is dry-run/test-safe"],
    })
    for heading in [
        "Executive Network Readiness Summary",
        "10,000-Event Aggregate Statistics",
        "End-to-End Journey Success Rates",
        "Per-System Capability Matrix",
        "Latency and Throughput Analysis",
        "Security and Authorization Findings",
        "Failure Injection and Recovery Results",
        "Recommended Fixes",
        "Overall UNG Readiness Score",
    ]:
        assert heading in text
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_network_test_reporting.py`
Expected: FAIL.

- [ ] **Step 3: Implement report builder and renderer**

The Markdown output must include all 13 sections from the approved spec and explicitly label untested capabilities. JSON output must retain raw metric fields for machine comparison between runs.

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_network_test_reporting.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add network_test/reporting.py tests/test_network_test_reporting.py
git commit -m "feat: generate UNG network readiness report"
```

---

### Task 8: Controlled ATLAS API endpoint for named runs

**Files:**
- Create: `network_test/api.py`
- Modify: `app.py`
- Create: `tests/test_network_test_api.py`

**Interfaces:**
- Produces: `POST /v1/network-test/run`, `GET /v1/network-test/profiles`.

- [ ] **Step 1: Write failing API tests**

```python
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_run_endpoint_defaults_to_safe_dry_run():
    r = client.post("/v1/network-test/run", json={"event_count": 25, "seed": 12})
    assert r.status_code == 200
    body = r.json()
    assert body["config"]["dry_run"] is True
    assert body["summary"]["attempted"] == 25


def test_run_endpoint_rejects_live_mode_for_run1():
    r = client.post("/v1/network-test/run", json={"event_count": 25, "seed": 12, "dry_run": False})
    assert r.status_code == 400
```

- [ ] **Step 2: Run RED**

Run: `pytest -q tests/test_network_test_api.py`
Expected: FAIL.

- [ ] **Step 3: Implement API and mount router**

Use a Pydantic request model with `event_count` constrained to `1..100_000`, seed integer, optional run ID. Reject `dry_run=False` with `HTTPException(400, "run1_live_dispatch_disabled")`. Return config, summary, aggregate metrics, and report payload. Mount with:

```python
from network_test.api import router as network_test_router
app.include_router(network_test_router)
```

- [ ] **Step 4: Run GREEN**

Run: `pytest -q tests/test_network_test_api.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add network_test/api.py app.py tests/test_network_test_api.py
git commit -m "feat: expose controlled ATLAS network test endpoint"
```

---

### Task 9: Full 10,000-event acceptance run and evidence artifact

**Files:**
- Create: `scripts/run_network_mock_test.py`
- Create: `tests/test_network_test_acceptance.py`
- Generated at run time: `artifacts/network-test/<run-id>.json`
- Generated at run time: `artifacts/network-test/<run-id>.md`

**Interfaces:**
- CLI: `python scripts/run_network_mock_test.py --events 10000 --seed 20260912 --run-id RUN-20260912-A`

- [ ] **Step 1: Write acceptance test**

```python
from network_test.models import RunConfig
from network_test.runner import NetworkTestRunner
from network_test.metrics import aggregate_metrics


def test_full_10000_event_acceptance_run():
    results, summary = NetworkTestRunner().run(RunConfig("ACCEPTANCE", event_count=10_000, seed=20260912))
    metrics = aggregate_metrics(results)
    assert summary.attempted == 10_000
    assert len(results) == 10_000
    assert metrics["attempted"] == 10_000
    assert metrics["success_rate"] >= 0.90
    assert metrics["security_correctness"] >= 0.95
    assert metrics["duplicate_suppression_rate"] >= 0.95
```

- [ ] **Step 2: Run acceptance test**

Run: `pytest -q tests/test_network_test_acceptance.py`
Expected: PASS after prior tasks are complete.

- [ ] **Step 3: Implement CLI artifact writer**

CLI must run the harness, call `build_report`/`render_markdown`, create `artifacts/network-test/`, and write deterministic JSON plus Markdown report. Exit nonzero only for harness execution failure, not because findings exist.

- [ ] **Step 4: Execute the real first 10,000-event dry-run**

Run:

```bash
python scripts/run_network_mock_test.py --events 10000 --seed 20260912 --run-id RUN-20260912-A
```

Expected: two report artifacts created and console summary printed.

- [ ] **Step 5: Run full regression suite**

Run:

```bash
pytest -q
python -m compileall network_test scripts app.py capability_registry.py
```

Expected: all tests PASS; compileall exits 0.

- [ ] **Step 6: Commit**

```bash
git add scripts tests/test_network_test_acceptance.py artifacts/network-test/RUN-20260912-A.json artifacts/network-test/RUN-20260912-A.md
git commit -m "test: run 10000-event UNG network acceptance simulation"
```

---

### Task 10: CI verification and merge readiness

**Files:**
- Create: `.github/workflows/network-mock-test.yml`

**Interfaces:**
- CI verifies deterministic harness tests and 10,000-event acceptance simulation without live dispatch.

- [ ] **Step 1: Add CI workflow**

```yaml
name: UNG Network Mock Test
on:
  pull_request:
  workflow_dispatch:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt pytest httpx
      - run: pytest -q
      - run: python -m compileall network_test scripts app.py capability_registry.py
      - run: python scripts/run_network_mock_test.py --events 10000 --seed 20260912 --run-id CI-10000
```

- [ ] **Step 2: Push branch and open PR**

PR title: `Add 10,000-event UNG whole-network mock test harness`

PR body must summarize safety isolation, event mix, fault scenarios, metrics/reporting, and attach/report the acceptance-run score and findings.

- [ ] **Step 3: Verify CI evidence before merge**

Required checks: unit/integration suite, compileall, full 10,000-event dry-run. Do not claim success until GitHub Actions reports `conclusion=success`.

- [ ] **Step 4: Review generated report before merge**

Confirm the report explicitly separates `demonstrated`, `failed`, and `untested` capabilities and contains no real customer/user credentials or production transaction identifiers.

- [ ] **Step 5: Merge only after successful verification**

Merge to `main` after CI passes and the technical report is reviewed.

---

## Self-review

- Spec coverage: all safety/isolation, 10,000-event generation, weighted traffic, five core journeys, bounded fault injection, metrics, capability grading, reporting, deterministic reruns, API/CLI control, and full acceptance-run requirements are mapped to Tasks 1-10.
- Placeholder scan: no TBD/TODO or undefined implementation handoffs remain.
- Type consistency: `RunConfig`, `SyntheticEvent`, `EventResult`, `RunSummary`, `NetworkTestRunner.run`, `aggregate_metrics`, `build_report`, and `render_markdown` are defined once and reused consistently.
