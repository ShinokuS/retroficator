from __future__ import annotations

import numpy as np
from PIL import Image

from retroficator.core.background import remove_flat_background
from retroficator.core.grid import detect_grid, recover_native_grid
from retroficator.core.palette import map_to_palette, quantize_colors
from retroficator.core.pipeline import AssetPipeline, ProcessOptions


def _synthetic_pixel_art(native_size: int = 12, scale: int = 8) -> Image.Image:
    arr = np.zeros((native_size, native_size, 4), dtype=np.uint8)
    arr[..., :] = (30, 30, 40, 255)
    arr[2:10, 3:9, :] = (210, 80, 65, 255)
    arr[4:8, 5:11, :] = (245, 190, 70, 255)
    arr[1, 1, :] = (250, 250, 250, 255)
    native = Image.fromarray(arr, mode="RGBA")
    return native.resize((native_size * scale, native_size * scale), Image.Resampling.NEAREST)


def test_detect_grid_on_nearest_neighbor_pixel_art() -> None:
    image = _synthetic_pixel_art(scale=8)
    grid = detect_grid(image, max_scale=16)
    assert grid.scale_x == 8
    assert grid.scale_y == 8
    assert grid.confidence > 0.2


def test_recover_native_grid_dimensions() -> None:
    image = _synthetic_pixel_art(native_size=10, scale=6)
    recovered = recover_native_grid(image, 6, 6)
    assert recovered.size == (10, 10)


def test_flat_background_removal_is_border_connected() -> None:
    arr = np.full((10, 10, 4), (255, 0, 255, 255), dtype=np.uint8)
    arr[2:8, 2:8] = (20, 30, 40, 255)
    arr[4:6, 4:6] = (255, 0, 255, 255)
    out = np.asarray(remove_flat_background(Image.fromarray(arr, "RGBA"), tolerance=1.0))
    assert out[0, 0, 3] == 0
    assert out[4, 4, 3] == 255


def test_quantize_respects_color_limit() -> None:
    rng = np.random.default_rng(1)
    arr = rng.integers(0, 256, size=(32, 32, 4), dtype=np.uint8)
    arr[..., 3] = 255
    out = np.asarray(quantize_colors(Image.fromarray(arr, "RGBA"), 16))
    assert np.unique(out[..., :3].reshape(-1, 3), axis=0).shape[0] <= 16


def test_quantize_ignores_hidden_transparent_rgb() -> None:
    rng = np.random.default_rng(7)
    arr = rng.integers(0, 256, size=(24, 24, 4), dtype=np.uint8)
    arr[..., 3] = 0
    arr[8:12, 8:10] = (240, 20, 20, 255)
    arr[8:12, 10:12] = (20, 220, 40, 255)
    out = np.asarray(quantize_colors(Image.fromarray(arr, "RGBA"), 2))
    visible = out[..., 3] > 0
    assert np.unique(out[..., :3][visible].reshape(-1, 3), axis=0).shape[0] <= 2
    assert np.all(out[..., :3][~visible] == 0)


def test_map_to_fixed_palette() -> None:
    arr = np.array([[[250, 0, 0, 255], [0, 250, 0, 255]]], dtype=np.uint8)
    out = np.asarray(map_to_palette(Image.fromarray(arr, "RGBA"), [(255, 0, 0), (0, 255, 0)]))
    assert tuple(out[0, 0, :3]) == (255, 0, 0)
    assert tuple(out[0, 1, :3]) == (0, 255, 0)


def test_pipeline_manual_scale_with_explicit_color_limit() -> None:
    image = _synthetic_pixel_art(native_size=8, scale=8)
    result = AssetPipeline().process(
        image,
        ProcessOptions(auto_grid=False, scale_x=8, scale_y=8, limit_colors=True, max_colors=8),
    )
    assert result.image.size == (8, 8)
    assert result.report.opaque_colors <= 8


def test_pipeline_preserves_colors_by_default() -> None:
    arr = np.zeros((4, 4, 4), dtype=np.uint8)
    for y in range(4):
        for x in range(4):
            arr[y, x] = (x * 50, y * 50, (x + y) * 25, 255)
    image = Image.fromarray(arr, "RGBA")
    result = AssetPipeline().process(
        image,
        ProcessOptions(auto_grid=False, scale_x=1, scale_y=1, max_colors=2, trim_transparent=False),
    )
    assert result.report.opaque_colors > 2
