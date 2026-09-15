from __future__ import annotations

import numpy as np
from PIL import Image


def normalize_alpha(image: Image.Image, threshold: int = 128) -> Image.Image:
    """Convert alpha to a binary pixel-art mask while preserving RGB values."""
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    rgba[..., 3] = np.where(rgba[..., 3] >= int(threshold), 255, 0).astype(np.uint8)
    return Image.fromarray(rgba, mode="RGBA")
