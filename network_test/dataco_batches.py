"""DataCo -> canonical UNG network-test batches.

The adapter deliberately emits test-only envelopes.  It does not write directly
into operational databases: ATLAS passes each canonical event to the normal
network ingestion/propagation path.
"""
from __future__ import annotations

import csv
import io
from collections.abc import Iterable

from .models import SyntheticEvent, TestEnvelope

BATCH_SIZE = 3_000
BATCH_COUNT = 4
TOTAL_RECORDS = BATCH_SIZE * BATCH_COUNT
RUN_ID = "UNG-NETTEST-12000"


def _pick(row: dict[str, str], *names: str, default: str = "") -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return default


def dataco_event(row: dict[str, str], sequence: int, run_id: str = RUN_ID) -> SyntheticEvent:
    order_id = _pick(row, "Order Id", "order_id", default=str(sequence))
    entity_id = f"TEST-DATACO-{order_id}-{sequence}"
    correlation_id = f"{run_id}:{order_id}"
    payload = {
        "source_dataset": "DataCoSupplyChainDataset",
        "order_id": order_id,
        "customer_id": _pick(row, "Customer Id", "customer_id"),
        "product_name": _pick(row, "Product Name", "product_name"),
        "quantity": _pick(row, "Order Item Quantity", "quantity"),
        "sales": _pick(row, "Sales", "sales"),
        "profit": _pick(row, "Order Profit Per Order", "profit"),
        "order_status": _pick(row, "Order Status", "order_status"),
        "delivery_status": _pick(row, "Delivery Status", "delivery_status"),
        "shipping_mode": _pick(row, "Shipping Mode", "shipping_mode"),
        "order_city": _pick(row, "Order City", "order_city"),
        "order_country": _pick(row, "Order Country", "order_country"),
        "market": _pick(row, "Market", "market"),
        "late_delivery_risk": _pick(row, "Late_delivery_risk", "late_delivery_risk"),
        "days_shipping_real": _pick(row, "Days for shipping (real)", "days_shipping_real"),
        "days_shipping_scheduled": _pick(row, "Days for shipment (scheduled)", "days_shipping_scheduled"),
        "test_mode": True,
        "synthetic": True,
    }
    return SyntheticEvent(
        envelope=TestEnvelope(run_id, sequence, entity_id),
        family="supply_chain",
        scenario="dataco_order_scan",
        source_system="UNG-ATLAS",
        capability="network.transaction.ingest",
        correlation_id=correlation_id,
        payload=payload,
    )


def iter_batches(rows: Iterable[dict[str, str]], run_id: str = RUN_ID):
    batch: list[SyntheticEvent] = []
    sequence = 0
    for row in rows:
        if sequence >= TOTAL_RECORDS:
            break
        sequence += 1
        batch.append(dataco_event(row, sequence, run_id))
        if len(batch) == BATCH_SIZE:
            yield batch
            batch = []
    if batch:
        yield batch


def load_csv_bytes(data: bytes, run_id: str = RUN_ID):
    """Decode common DataCo encodings and return at most four 3k batches."""
    last_error = None
    for encoding in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            text = data.decode(encoding)
            return list(iter_batches(csv.DictReader(io.StringIO(text)), run_id))
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError("unsupported_dataco_encoding") from last_error


def batch_manifest(batches: list[list[SyntheticEvent]]) -> dict:
    return {
        "run_id": RUN_ID,
        "batch_size": BATCH_SIZE,
        "requested_batches": BATCH_COUNT,
        "actual_batches": len(batches),
        "records": sum(len(batch) for batch in batches),
        "test_mode": True,
        "synthetic": True,
    }
