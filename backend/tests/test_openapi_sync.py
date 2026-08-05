"""OpenAPI verification for the offline sync endpoint (M2, Task 6.4).

Confirms ``POST /scans/sync`` is documented end-to-end: the operation exists
under bearer auth, its JSON request body is an array of ``ScanSyncItemIn``,
the 200 response resolves to ``ScanSyncOut``, and every Task 6 schema carries
the full per-item contract with worked examples.
"""

from app.main import app


def _post(path: str) -> dict:
    return app.openapi()["paths"][path]["post"]


def test_openapi_declares_sync_operation(client) -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/scans/sync" in paths

    op = _post("/api/v1/scans/sync")
    # Authorization is documented as bearer (enforced at runtime by the 401 test).
    assert op["security"] == [{"HTTPBearer": []}]
    assert "200" in op["responses"]  # OpenAPI status keys are strings
    ref = op["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert ref == "#/components/schemas/ScanSyncOut"


def test_openapi_sync_request_is_item_array(client) -> None:
    op = _post("/api/v1/scans/sync")
    body = op["requestBody"]["content"]["application/json"]["schema"]
    assert body["type"] == "array"
    assert body["items"]["$ref"] == "#/components/schemas/ScanSyncItemIn"


def test_openapi_sync_schemas_carry_full_contract(client) -> None:
    components = app.openapi()["components"]["schemas"]

    # Request item mirrors the multipart fields but transports base64 images.
    assert set(components["ScanSyncItemIn"]["properties"]) == {
        "client_scan_id",
        "images",
        "crop_id",
        "part_type",
        "device_id",
    }
    assert set(components["SyncImageIn"]["properties"]) == {
        "data",
        "content_type",
        "filename",
    }

    # Per-item outcome exposes the row on success and the error on failure.
    result = components["ScanSyncResultOut"]["properties"]
    assert {"client_scan_id", "status", "scan", "error"} <= set(result)

    # Batch envelope aggregates the counters.
    out = set(components["ScanSyncOut"]["properties"])
    assert {"results", "total", "created", "replayed", "failed"} <= out


def test_openapi_sync_explains_with_examples(client) -> None:
    components = app.openapi()["components"]["schemas"]

    out = components["ScanSyncOut"]
    assert out.get("examples"), "ScanSyncOut must ship a worked example"
    example = out["examples"][0]
    assert {"total", "created", "replayed", "failed", "results"} <= set(example)
    assert example["total"] == len(example["results"])
    assert example["created"] + example["replayed"] + example["failed"] == example["total"]

    item = components["ScanSyncItemIn"]
    assert item.get("examples"), "ScanSyncItemIn must ship a worked request example"
    request = item["examples"][0]
    assert {"client_scan_id", "images", "part_type"} <= set(request)
