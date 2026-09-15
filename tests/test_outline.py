from __future__ import annotations

import numpy as np
from PIL import Image

from retroficator.core.outline import add_outer_outline, crisp_silhouette, estimate_outline_color, repair_outline


def _sprite_with_broken_edge() -> Image.Image:
    arr = np.zeros((9, 9, 4), dtype=np.uint8)
    arr[1:8, 2:7] = (210, 212, 220, 255)
    arr[1:8, 2] = (26, 29, 38, 255)
    arr[1:8, 6] = (26, 29, 38, 255)
    arr[1, 2:7] = (26, 29, 38, 255)
    arr[7, 2:7] = (26, 29, 38, 255)
    # Simulate a locally missing dark outline on the right edge.
    arr[4, 6] = (190, 192, 202, 255)
    return Image.fromarray(arr, "RGBA")


def test_estimate_outline_color_uses_dark_edge_pixels() -> None:
    color = estimate_outline_color(_sprite_with_broken_edge())
    assert max(color) < 80


def test_repair_outline_repairs_local_bright_outlier() -> None:
    image = _sprite_with_broken_edge()
    before = np.asarray(image)
    after = np.asarray(repair_outline(image, strength=80))
    assert int(after[4, 6, 0]) < int(before[4, 6, 0])
    assert int(after[4, 6, 1]) < int(before[4, 6, 1])
    assert int(after[4, 6, 2]) < int(before[4, 6, 2])
    # Interior material pixels must stay untouched.
    assert tuple(after[4, 4]) == tuple(before[4, 4])


def test_crisp_silhouette_promotes_weak_edge_cell_without_global_alpha_cut() -> None:
    arr = np.zeros((5, 5, 4), dtype=np.uint8)
    arr[2, 2] = (40, 40, 50, 255)
    arr[2, 3] = (40, 40, 50, 45)
    image = Image.fromarray(arr, "RGBA")
    after = np.asarray(crisp_silhouette(image, alpha_threshold=18, neighbor_threshold=96))
    assert after[2, 3, 3] == 255
    assert after[0, 0, 3] == 0


def test_add_outer_outline_expands_canvas_and_preserves_original() -> None:
    arr = np.zeros((3, 3, 4), dtype=np.uint8)
    arr[1, 1] = (200, 210, 220, 255)
    image = Image.fromarray(arr, "RGBA")
    outlined = np.asarray(add_outer_outline(image, thickness=1, color=(7, 8, 9)))
    assert outlined.shape[:2] == (5, 5)
    assert tuple(outlined[2, 2]) == (200, 210, 220, 255)
    assert tuple(outlined[2, 1]) == (7, 8, 9, 255)
