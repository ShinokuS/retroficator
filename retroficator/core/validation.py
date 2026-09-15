from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class ValidationReport:
    width: int
    height: int
    opaque_colors: int
    alpha_levels: int
    transparent_pixels: int
    tiny_components: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def _count_tiny_components(mask: np.ndarray, max_area: int = 2) -> int:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    tiny = 0

    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            q: deque[tuple[int, int]] = deque([(y, x)])
            seen[y, x] = True
            area = 0
            while q:
                cy, cx = q.popleft()
                area += 1
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if area <= max_area:
                tiny += 1
    return tiny


def validate_asset(image: Image.Image) -> ValidationReport:
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    alpha = rgba[..., 3]
    opaque = alpha > 0
    if np.any(opaque):
        colors = np.unique(rgba[..., :3][opaque].reshape(-1, 3), axis=0)
        opaque_colors = int(colors.shape[0])
    else:
        opaque_colors = 0

    return ValidationReport(
        width=image.width,
        height=image.height,
        opaque_colors=opaque_colors,
        alpha_levels=int(np.unique(alpha).size),
        transparent_pixels=int(np.sum(alpha == 0)),
        tiny_components=_count_tiny_components(opaque),
    )
