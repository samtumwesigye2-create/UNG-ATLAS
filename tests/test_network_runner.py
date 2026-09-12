import asyncio

from capability_registry import CapabilityRegistry
from network_test.dataco_batches import dataco_event
from network_test.runner import dispatch, run_batch, summarize


def catalog():
    c = CapabilityRegistry()
    c.register("UGASHIP", "UGASHIP", "https://test.invalid/ugaship", ["network.transaction.ingest"])
    c.register("VECTOR", "VECTOR", "https://test.invalid/vector", ["network.transaction.ingest"])
    return c


async def ok_sender(url, body):
    assert body["envelope"]["test_mode"] is True
    assert body["envelope"]["synthetic"] is True
    assert body["payload"]["test_mode"] is True
    return {"ok": True, "destination": url}


def test_event_propagates_to_all_capability_subscribers():
    event = dataco_event({"Order Id": "77"}, 1)
    results = asyncio.run(dispatch(event, ok_sender, catalog()))
    assert {r.destination_system for r in results} == {"UNG-UGASHIP", "UNG-VECTOR"}
    assert all(r.status == "accepted" for r in results)


def test_no_subscriber_fails_closed():
    event = dataco_event({"Order Id": "77"}, 1)
    results = asyncio.run(dispatch(event, ok_sender, CapabilityRegistry()))
    assert results[0].status == "failed"
    assert results[0].failure_reason == "no_capability_subscriber"


def test_batch_summary_measures_propagation():
    events = [dataco_event({"Order Id": str(i)}, i) for i in range(1, 11)]
    results = asyncio.run(run_batch(events, ok_sender, catalog(), concurrency=4))
    summary = summarize(results)
    assert summary["attempted_deliveries"] == 20
    assert summary["accepted"] == 20
    assert summary["failed"] == 0
    assert summary["success_rate"] == 1.0
    assert set(summary["systems"]) == {"UNG-UGASHIP", "UNG-VECTOR"}
