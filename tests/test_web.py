from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image

from retroficator.web.server import app


def _png_bytes() -> bytes:
    image = Image.new("RGBA", (16, 16), (255, 255, 255, 255))
    for y in range(4, 12):
        for x in range(4, 12):
            image.putpixel((x, y), (30, 80, 160, 255))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_process_image() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/process",
        files={"image": ("asset.png", _png_bytes(), "image/png")},
        data={
            "auto_grid": "false",
            "scale_x": "1",
            "scale_y": "1",
            "max_colors": "8",
            "remove_background": "true",
            "binary_alpha": "true",
            "trim_transparent": "false",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["report"]["width"] == 16
    assert data["report"]["height"] == 16
    assert data["report"]["opaque_colors"] <= 8
    assert data["grid"]["backend"] == "manual-scale"
    assert data["image_base64"]
