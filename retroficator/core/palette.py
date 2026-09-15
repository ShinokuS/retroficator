from __future__ import annotations

from pathlib import Path
import re

import numpy as np
from PIL import Image

_HEX_RE = re.compile(r"#?([0-9a-fA-F]{6})")


def load_hex_palette(path: str | Path) -> list[tuple[int, int, int]]:
    colors: list[tuple[int, int, int]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        match = _HEX_RE.search(line)
        if not match:
            continue
        value = match.group(1)
        colors.append(tuple(int(value[i : i + 2], 16) for i in (0, 2, 4)))
    if not colors:
        raise ValueError("Palette file does not contain any #RRGGBB colors")
    return colors


def _srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    rgb = rgb / 255.0
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def rgb_to_oklab(rgb: np.ndarray) -> np.ndarray:
    linear = _srgb_to_linear(rgb.astype(np.float32))
    r, g, b = linear[..., 0], linear[..., 1], linear[..., 2]
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return np.stack(
        [
            0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
        ],
        axis=-1,
    )


def map_to_palette(image: Image.Image, colors: list[tuple[int, int, int]]) -> Image.Image:
    if not colors:
        return image.convert("RGBA")
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    rgb = rgba[..., :3]
    alpha = rgba[..., 3]

    palette_rgb = np.asarray(colors, dtype=np.float32)
    palette_lab = rgb_to_oklab(palette_rgb)
    flat = rgb.reshape(-1, 3).astype(np.float32)
    flat_lab = rgb_to_oklab(flat)

    result = np.empty_like(flat, dtype=np.uint8)
    chunk = 65536
    for start in range(0, flat.shape[0], chunk):
        part = flat_lab[start : start + chunk]
        d2 = np.sum((part[:, None, :] - palette_lab[None, :, :]) ** 2, axis=2)
        nearest = np.argmin(d2, axis=1)
        result[start : start + chunk] = palette_rgb[nearest].astype(np.uint8)

    out = np.empty_like(rgba)
    out[..., :3] = result.reshape(rgb.shape)
    out[..., 3] = alpha
    return Image.fromarray(out, mode="RGBA")


def quantize_colors(image: Image.Image, max_colors: int = 24) -> Image.Image:
    max_colors = max(2, min(256, int(max_colors)))
    rgba = image.convert("RGBA")
    arr = np.asarray(rgba, dtype=np.uint8)
    alpha = arr[..., 3]

    rgb = Image.fromarray(arr[..., :3], mode="RGB")
    q = rgb.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    qrgb = q.convert("RGB")
    out = np.asarray(qrgb, dtype=np.uint8).copy()
    rgba_out = np.dstack([out, alpha])
    return Image.fromarray(rgba_out, mode="RGBA")


def select_project_palette(
    image: Image.Image,
    project_colors: list[tuple[int, int, int]],
    max_colors: int,
) -> list[tuple[int, int, int]]:
    """Choose an image-specific subset from a larger allowed project palette."""
    if len(project_colors) <= max_colors:
        return list(project_colors)

    reduced = quantize_colors(image, max_colors=max_colors)
    rgba = np.asarray(reduced.convert("RGBA"), dtype=np.uint8)
    visible = rgba[..., 3] > 0
    if not np.any(visible):
        return list(project_colors[:max_colors])

    candidates, counts = np.unique(rgba[..., :3][visible].reshape(-1, 3), axis=0, return_counts=True)
    order = np.argsort(-counts)
    candidates = candidates[order]

    allowed_rgb = np.asarray(project_colors, dtype=np.float32)
    allowed_lab = rgb_to_oklab(allowed_rgb)
    cand_lab = rgb_to_oklab(candidates.astype(np.float32))

    chosen: list[int] = []
    for lab in cand_lab:
        d2 = np.sum((allowed_lab - lab[None, :]) ** 2, axis=1)
        for idx in np.argsort(d2):
            i = int(idx)
            if i not in chosen:
                chosen.append(i)
                break
        if len(chosen) >= max_colors:
            break

    if not chosen:
        chosen = [0]
    return [project_colors[i] for i in chosen]
