from __future__ import annotations

from collections import deque

import numpy as np
from PIL import Image


def _estimate_border_color(rgb: np.ndarray) -> np.ndarray:
    border = np.concatenate(
        [rgb[0, :, :], rgb[-1, :, :], rgb[:, 0, :], rgb[:, -1, :]], axis=0
    )
    return np.median(border.astype(np.float32), axis=0)


def remove_flat_background(image: Image.Image, tolerance: float = 24.0) -> Image.Image:
    """Remove a mostly-flat background connected to the canvas border.

    Only pixels connected to an outer edge are removed, so similarly-colored
    regions enclosed inside the sprite are preserved.
    """
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    rgb = rgba[..., :3]
    h, w = rgb.shape[:2]
    if h == 0 or w == 0:
        return image.convert("RGBA")

    bg = _estimate_border_color(rgb)
    dist = np.sqrt(np.sum((rgb.astype(np.float32) - bg[None, None, :]) ** 2, axis=2))
    eligible = dist <= float(tolerance)

    visited = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()

    def enqueue(y: int, x: int) -> None:
        if not visited[y, x] and eligible[y, x]:
            visited[y, x] = True
            q.append((y, x))

    for x in range(w):
        enqueue(0, x)
        enqueue(h - 1, x)
    for y in range(h):
        enqueue(y, 0)
        enqueue(y, w - 1)

    while q:
        y, x = q.popleft()
        if y > 0:
            enqueue(y - 1, x)
        if y + 1 < h:
            enqueue(y + 1, x)
        if x > 0:
            enqueue(y, x - 1)
        if x + 1 < w:
            enqueue(y, x + 1)

    rgba[visited, 3] = 0
    return Image.fromarray(rgba, mode="RGBA")
