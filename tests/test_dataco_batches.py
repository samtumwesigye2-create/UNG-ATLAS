from network_test.dataco_batches import BATCH_COUNT, BATCH_SIZE, RUN_ID, batch_manifest, iter_batches


def rows(n):
    for i in range(1, n + 1):
        yield {
            "Order Id": str(i),
            "Customer Id": str(100000 + i),
            "Product Name": f"Product {i}",
            "Order Item Quantity": "1",
            "Sales": "25.00",
            "Order Profit Per Order": "4.00",
            "Order Status": "COMPLETE",
            "Delivery Status": "Advance shipping",
            "Shipping Mode": "Standard Class",
            "Order City": "Test City",
            "Order Country": "Test Country",
            "Market": "Test",
            "Late_delivery_risk": "0",
        }


def test_exact_four_batches_of_three_thousand():
    batches = list(iter_batches(rows(15000)))
    assert len(batches) == BATCH_COUNT == 4
    assert all(len(batch) == BATCH_SIZE == 3000 for batch in batches)
    assert sum(map(len, batches)) == 12000


def test_events_are_correlated_and_test_only():
    event = next(iter_batches(rows(1)))[0]
    assert event.envelope.test_mode is True
    assert event.envelope.synthetic is True
    assert event.envelope.test_run_id == RUN_ID
    assert event.envelope.entity_id.startswith("TEST-DATACO-")
    assert event.correlation_id.startswith(RUN_ID + ":")
    assert event.payload["test_mode"] is True


def test_manifest_reports_12000():
    batches = list(iter_batches(rows(12000)))
    manifest = batch_manifest(batches)
    assert manifest["records"] == 12000
    assert manifest["actual_batches"] == 4
    assert manifest["batch_size"] == 3000
