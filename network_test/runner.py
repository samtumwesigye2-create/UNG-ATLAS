"""Fail-closed ATLAS whole-network propagation runner."""
from __future__ import annotations

import asyncio
import time
from dataclasses import asdict
from typing import Awaitable, Callable

from capability_registry import CapabilityRegistry, registry
from .models import EventResult, SyntheticEvent

Sender = Callable[[str, dict], Awaitable[dict]]


class UnsafeDestination(RuntimeError):
    pass


def destinations_for(event: SyntheticEvent, catalog: CapabilityRegistry = registry):
    """Discover subscribers through ATLAS; never hard-code a competing bridge."""
    return catalog.discover(event.capability, active_only=True)


def wire_event(event: SyntheticEvent) -> dict:
    body = asdict(event)
    # Defense in depth: adapters cannot remove these test markers.
    body["envelope"]["test_mode"] = True
    body["envelope"]["synthetic"] = True
    body["payload"]["test_mode"] = True
    body["payload"]["synthetic"] = True
    return body


async def dispatch(event: SyntheticEvent, sender: Sender, catalog: CapabilityRegistry = registry) -> list[EventResult]:
    services = destinations_for(event, catalog)
    if not services:
        return [EventResult(event, None, "failed", 0.0, failure_reason="no_capability_subscriber")]

    results = []
    body = wire_event(event)
    for service in services:
        if not service.base_url:
            results.append(EventResult(event, service.system_id, "failed", 0.0, failure_reason="missing_base_url"))
            continue
        started = time.perf_counter()
        try:
            response = await sender(service.base_url, body)
            latency = (time.perf_counter() - started) * 1000
            results.append(EventResult(event, service.system_id, "accepted", latency, response=response or {}))
        except Exception as exc:
            latency = (time.perf_counter() - started) * 1000
            results.append(EventResult(event, service.system_id, "failed", latency, failure_reason=str(exc)[:300]))
    return results


async def run_batch(events: list[SyntheticEvent], sender: Sender, catalog: CapabilityRegistry = registry, concurrency: int = 25):
    """Propagate a bounded batch while preserving per-event correlation/results."""
    semaphore = asyncio.Semaphore(max(1, min(concurrency, 100)))

    async def one(event):
        async with semaphore:
            return await dispatch(event, sender, catalog)

    nested = await asyncio.gather(*(one(event) for event in events))
    return [result for group in nested for result in group]


def summarize(results: list[EventResult]) -> dict:
    attempted = len(results)
    accepted = sum(r.status == "accepted" for r in results)
    failed = attempted - accepted
    latencies = sorted(r.latency_ms for r in results if r.latency_ms >= 0)
    avg = sum(latencies) / len(latencies) if latencies else 0.0
    p95 = latencies[min(len(latencies)-1, int(len(latencies)*0.95))] if latencies else 0.0
    systems = {}
    for result in results:
        sid = result.destination_system or "UNROUTED"
        row = systems.setdefault(sid, {"attempted": 0, "accepted": 0, "failed": 0})
        row["attempted"] += 1
        row[result.status if result.status in ("accepted", "failed") else "failed"] += 1
    return {
        "attempted_deliveries": attempted,
        "accepted": accepted,
        "failed": failed,
        "success_rate": accepted / attempted if attempted else 0.0,
        "average_latency_ms": round(avg, 3),
        "p95_latency_ms": round(p95, 3),
        "systems": systems,
    }
