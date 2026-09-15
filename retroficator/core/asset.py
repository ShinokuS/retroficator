from __future__ import annotations

import numpy as np
from PIL import Image


def trim_transparent(image: Image.Image, alpha_threshold: int = 1, padding: int = 1) -> Image.Image:
    """Crop transparent margins without resampling the recovered pixel grid."""
    src = image.convert("RGBA")
    rgba = np.asarray(src, dtype=np.uint8)
    visible = rgba[..., 3] >= max(1, min(255, int(alpha_threshold)))
    if not np.any(visible):
        return src.copy()

    ys, xs = np.where(visible)
    pad = max(0, int(padding))
    left = max(0, int(xs.min()) - pad)
    top = max(0, int(ys.min()) - pad)
    right = min(src.width, int(xs.max()) + 1 + pad)
    bottom = min(src.height, int(ys.max()) + 1 + pad)
    return src.crop((left, top, right, bottom))
