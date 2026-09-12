# UNG Whole-Network Mock Test Design

Date: 2026-09-12
Status: Approved in chat, pending written-spec review
Owner: UNG-ATLAS control plane

## Goal

Exercise the UNG network end-to-end with synthetic operational traffic, observe how systems interact under normal and failure conditions, and produce a technical capability and readiness report based on measured results rather than isolated unit checks.

The first execution target is 10,000 synthetic events. All test traffic must be unmistakably tagged as non-production data and must not create irreversible production-side effects.

## Control-plane role

UNG-ATLAS is the orchestration and reporting control plane for the test. It discovers registered systems and capabilities through the existing capability registry, selects participating services, dispatches synthetic events through real interfaces where safe, records results, and aggregates metrics.

No new bridge or replacement integration bus is introduced. Existing system boundaries remain authoritative.

## Test scope

The first run covers operational scenarios that span the UNG network rather than independent single-service checks. Synthetic actors and records include users, drivers, vehicles, warehouses, ZIP destinations, packages, freight, pickups, deliveries, inventory movements, finance events, identity/auth events, alerts, telemetry/location updates, and documents.

Representative event families:

- identity/session creation, authorization checks, denied access, expired credentials
- ZIP/address lookup and destination validation
- shipment creation, pickup assignment, route execution, scan events, delivery completion
- warehouse intake, sortation, inventory changes, handoff and dispatch
- driver UGATU actions including pickup, delivery, POD/POP, documents and offline-sync recovery
- finance/accounting events associated with operational transactions
- telemetry, monitoring, alerting and service-health events
- intentionally malformed, duplicated, delayed and conflicting events

## Safety and isolation

Every synthetic event carries a test envelope with:

- `test_mode=true`
- `test_run_id`
- `synthetic=true`
- deterministic synthetic entity IDs
- event timestamp and sequence number

The harness must refuse to dispatch to an endpoint unless it is explicitly marked test-safe in the scenario configuration. Destructive or financially binding actions are simulated or routed only to existing non-production/test-safe handlers.

Test entities use reserved prefixes such as `MOCK-`, `TEST-`, or equivalent system-safe identifiers. The report must distinguish simulated behavior from live network behavior.

## Load model

The initial 10,000-event run is weighted to resemble ordinary network use while still producing enough edge conditions to reveal integration problems.

Planned mix:

- 55% normal operational flow
- 15% authentication/authorization and user/device/session events
- 10% routing/address/ZIP lookups
- 10% inventory/warehouse/sortation events
- 5% finance/reporting events
- 5% controlled fault and recovery scenarios

Events are grouped into correlated journeys so the test can measure complete business outcomes, not just HTTP success codes.

## Scenario model

Each scenario defines:

- source system or layer
- destination system/capability
- synthetic payload generator
- expected status/event/result
- correlation ID
- timeout and retry allowance
- data-consistency assertions
- recovery expectation when faults are injected

Core journeys include:

1. Customer/order creation -> destination ZIP validation -> shipment -> warehouse handling -> driver assignment -> pickup -> transit -> delivery -> proof -> reporting.
2. Driver starts shift -> receives assignment -> executes pickup and delivery scans -> document/POD/POP flow -> offline interruption -> sync recovery -> shift reconciliation.
3. Inventory shortage -> exception -> alternate handling -> alert propagation -> final consistency check.
4. Authentication denial and expired-session flow -> security response -> audit event.
5. Temporary downstream service failure -> retry/backoff or graceful failure -> recovery -> duplicate/idempotency verification.

## Fault injection

The first run includes bounded controlled faults rather than indiscriminate stress. Fault cases include:

- invalid or unknown ZIP/address
- bad credentials or insufficient role
- duplicate event/idempotency-key replay
- out-of-order event
- inventory shortage
- delayed acknowledgement
- temporary dependency unavailable
- timeout followed by recovery
- malformed payload
- stale device/offline transaction replay

The harness records whether each service rejects, retries, compensates, queues, recovers or corrupts state.

## Measurements

Per event and per journey, capture:

- dispatch timestamp
- acknowledgement timestamp
- completion timestamp
- latency
- response/result class
- retry count
- failure reason
- correlation ID continuity
- duplicate suppression outcome
- downstream systems reached
- data-consistency result
- recovery result

System-level metrics:

- events attempted/accepted/completed/failed
- success percentage
- p50/p95/p99 latency where available
- timeout/retry rate
- duplicate handling rate
- consistency violations
- security rejection correctness
- recovery success rate
- observed throughput during the run

## Analysis and capability grading

The report grades each participating system in these dimensions:

- Functionality: does it perform its advertised capabilities correctly?
- Integration: can it exchange and correlate data correctly with other systems?
- Reliability: does it avoid data loss and uncontrolled failure?
- Resilience: does it recover from temporary faults and offline conditions?
- Security: are invalid or unauthorized actions correctly rejected and audited?
- Observability: can failures and transaction paths be diagnosed from available telemetry?
- Performance: latency and demonstrated throughput under the test load.

Grades must be evidence-based from test measurements. Unsupported capability claims are not counted as demonstrated.

## Reporting output

The first report should contain:

1. Executive network readiness summary.
2. Systems/capabilities actually exercised.
3. 10,000-event aggregate statistics.
4. End-to-end journey success rates.
5. Per-system capability matrix.
6. Latency and throughput analysis.
7. Data consistency and idempotency analysis.
8. Security and authorization findings.
9. Failure-injection and recovery results.
10. Bottlenecks and dependency hotspots.
11. Critical/high/medium/low findings.
12. Recommended fixes in priority order.
13. Overall UNG readiness score and explicit limits of what the run proved.

## Implementation shape

The implementation belongs in UNG-ATLAS as a test-orchestration package with clear isolation from normal control-plane behavior. Proposed modules:

- `network_test/models.py` — event, scenario, result and metric models
- `network_test/generators.py` — deterministic synthetic data generation
- `network_test/scenarios.py` — correlated operational journeys
- `network_test/runner.py` — dispatch, timing, retry and fault orchestration
- `network_test/adapters.py` — capability-safe service adapters
- `network_test/metrics.py` — aggregation and scoring
- `network_test/reporting.py` — JSON and Markdown technical reports
- `tests/` — deterministic unit/integration tests for the harness

A CLI or controlled ATLAS endpoint starts a named run with an event count, seed and scenario profile. Default behavior is dry-run/test-safe; live production-impacting behavior is opt-in and outside this first test.

## Acceptance criteria

The design is accepted as implemented when:

- a deterministic 10,000-event run can be generated from a fixed seed
- all emitted test data is tagged and isolated
- correlated journeys can be traced from source to final result
- controlled faults are exercised without destabilizing the live network
- metrics and failure reasons are captured per system and per journey
- the report clearly separates demonstrated capability from untested capability
- repeated runs with the same seed produce materially reproducible test distributions
- automated tests cover generator determinism, safety guards, correlation, fault injection, metric aggregation and report generation

## First execution sequence

1. Discover ATLAS-registered systems and capabilities.
2. Validate which endpoints are test-safe.
3. Generate the deterministic 10,000-event dataset.
4. Execute normal-flow scenarios first.
5. Execute bounded fault scenarios.
6. Aggregate metrics and consistency checks.
7. Produce the technical capability/readiness report.
8. Review failures before increasing to 100,000 events or sustained-load testing.

## Explicit non-goals for run 1

- proving theoretical maximum production capacity
- destructive chaos testing
- billing or settlement against real external accounts
- replacing existing service-specific tests
- declaring an untested capability operational

Run 1 is a controlled evidence-gathering integration test. Higher-volume performance testing follows only after the 10,000-event network run is clean enough to justify it.
