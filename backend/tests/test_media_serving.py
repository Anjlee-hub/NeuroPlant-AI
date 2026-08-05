"""Integration test for the ``/media`` static mount (M2.1).

Media URLs returned by the scan API (uploaded image, processed image,
Grad-CAM heatmaps) are served from the local storage directory. This guards
the wiring between ``LocalStorageService.url()`` and ``app.main``'s mount so
the frontend images actually resolve.
"""

import pytest
from app.services.storage import get_storage_service


@pytest.mark.asyncio
async def test_media_urls_are_served_by_the_app(client):
    svc = get_storage_service()
    key = svc.save(b"\x89PNG-fake-bytes", "image/png", user_id=9, subdir="heatmaps")
    assert key.startswith("9/heatmaps/")

    response = await client.get(f"/media/{key}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"\x89PNG-fake-bytes"


@pytest.mark.asyncio
async def test_missing_media_returns_404(client):
    response = await client.get("/media/12345/does-not-exist.png")
    assert response.status_code == 404
