"""OpenAPI verification for the explain endpoint (M2, Task 5.5).

Confirms the generated OpenAPI schema documents ``GET /scans/{scan_id}/explain``
end-to-end: the operation exists under bearer auth, its 200 response resolves to
``ScanExplainOut``, and that component lists the full Task 5 contract —
diagnosis + confidence band/advice, top-5, heatmap/overlay, plain-language
explanation, pipeline timing, and model provenance — with a worked example.
"""

from app.main import app

# The full Task 5 response contract, as exposed to API consumers.
_EXPECTED_TOP_LEVEL = {
    "scan_id",
    "disease",
    "confidence",
    "top5",
    "heatmap",
    "heatmap_url",
    "overlay_url",
    "explanation",
    "timing",
    "model",
}


def _get(path: str) -> dict:
    return app.openapi()["paths"][path]["get"]


def test_openapi_declares_explain_operation(client) -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/scans/{scan_id}/explain" in paths

    op = _get("/api/v1/scans/{scan_id}/explain")
    assert "200" in op["responses"]  # OpenAPI status keys are strings
    # Authorization is documented as bearer (enforced at runtime by 401/404 tests).
    assert op["security"] == [{"HTTPBearer": []}]
    ref = op["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert ref == "#/components/schemas/ScanExplainOut"


def test_openapi_schema_covers_full_contract(client) -> None:
    components = app.openapi()["components"]["schemas"]
    props = set(components["ScanExplainOut"]["properties"])
    assert props >= _EXPECTED_TOP_LEVEL

    # Confidence band exposes the score, its level, and expert advice.
    confidence = components["ExplainConfidenceOut"]["properties"]
    assert {"top", "level", "advice"} <= set(confidence)

    # Timing exposes every measured stage (Task 5.4).
    timing = set(components["ExplainTimingOut"]["properties"])
    assert timing == {
        "preprocessing_time_ms",
        "inference_time_ms",
        "processing_time_ms",
        "heatmap_time_ms",
    }


def test_openapi_explains_payload_with_example(client) -> None:
    out = app.openapi()["components"]["schemas"]["ScanExplainOut"]
    assert out.get("examples"), "ScanExplainOut must ship a worked example"
    example = out["examples"][0]
    assert {"disease", "confidence", "top5", "explanation", "timing", "model"} <= set(example)
    assert set(example["timing"]) == {
        "preprocessing_time_ms",
        "inference_time_ms",
        "processing_time_ms",
        "heatmap_time_ms",
    }
