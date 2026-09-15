from __future__ import annotations

import numpy as np
from PIL import Image


def _luma(rgb: np.ndarray) -> np.ndarray:
    rgb = rgb.astype(np.float32)
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def _shifted_masks(mask: np.ndarray) -> list[np.ndarray]:
    h, w = mask.shape
    padded = np.pad(mask, 1, mode="constant", constant_values=False)
    out: list[np.ndarray] = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            out.append(padded[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w])
    return out


def _dilate(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    result = mask.copy()
    for _ in range(max(0, int(iterations))):
        nxt = result.copy()
        for shifted in _shifted_masks(result):
            nxt |= shifted
        result = nxt
    return result


def _erode(mask: np.ndarray) -> np.ndarray:
    if not np.any(mask):
        return mask.copy()
    result = mask.copy()
    for shifted in _shifted_masks(mask):
        result &= shifted
    return result


def boundary_mask(mask: np.ndarray) -> np.ndarray:
    """Return the one-pixel interior boundary of a foreground mask."""
    return mask & ~_erode(mask)


def estimate_outline_color(image: Image.Image, alpha_threshold: int = 16) -> tuple[int, int, int]:
    """Estimate the sprite's existing outline color from its darkest edge pixels."""
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    mask = rgba[..., 3] >= max(1, min(254, int(alpha_threshold)))
    edge = boundary_mask(mask)
    pixels = rgba[..., :3][edge]
    if pixels.size == 0:
        pixels = rgba[..., :3][mask]
    if pixels.size == 0:
        return (20, 20, 24)

    lum = _luma(pixels)
    cutoff = float(np.quantile(lum, 0.22))
    dark = pixels[lum <= cutoff]
    if dark.size == 0:
        dark = pixels[np.argsort(lum)[: max(1, min(8, len(pixels)))]]

    color = np.median(dark.astype(np.float32), axis=0)
    return tuple(np.clip(np.rint(color), 0, 255).astype(np.uint8).tolist())


def crisp_silhouette(
    image: Image.Image,
    alpha_threshold: int = 18,
    neighbor_threshold: int = 96,
) -> Image.Image:
    """Make recovered edge cells opaque without globally hard-cutting alpha.

    Pixel-grid reconstruction can leave genuine outline cells semi-transparent.
    A global 128 alpha threshold can delete them. This operation only promotes
    low-alpha boundary cells that touch a stronger foreground neighbor, which
    preserves the recovered silhouette without creating a halo.
    """
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    alpha = rgba[..., 3]
    low = max(1, min(254, int(alpha_threshold)))
    strong = max(low, min(255, int(neighbor_threshold)))
    visible = alpha >= low
    edge = boundary_mask(visible)

    padded = np.pad(alpha, 1, mode="constant", constant_values=0)
    h, w = alpha.shape
    max_neighbor = np.zeros_like(alpha)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            max_neighbor = np.maximum(
                max_neighbor,
                padded[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w],
            )

    promote = edge & (alpha >= low) & (alpha < 255) & (max_neighbor >= strong)
    rgba[..., 3][promote] = 255
    return Image.fromarray(rgba, mode="RGBA")


def repair_outline(
    image: Image.Image,
    strength: int = 70,
    alpha_threshold: int = 16,
    radius: int = 2,
) -> Image.Image:
    """Repair locally weak/missing dark edge pixels without flattening texture.

    The algorithm follows the *existing* outline instead of painting a new one.
    For each boundary pixel it looks at nearby boundary pixels, learns a local
    dark-edge target, and only adjusts pixels that are clear light outliers.
    This repairs broken stretches while leaving intentional bright edges alone.
    """
    strength = max(0, min(100, int(strength)))
    if strength <= 0:
        return image.convert("RGBA")

    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    alpha = rgba[..., 3]
    mask = alpha >= max(1, min(254, int(alpha_threshold)))
    edge = boundary_mask(mask)
    if not np.any(edge):
        return Image.fromarray(rgba, mode="RGBA")

    rgb = rgba[..., :3].astype(np.float32)
    lum = _luma(rgb)
    global_color = np.asarray(estimate_outline_color(image, alpha_threshold), dtype=np.float32)
    global_luma = float(_luma(global_color[None, :])[0])

    # Stronger setting means a smaller allowed lightness gap and a stronger blend.
    trigger_delta = 34.0 - (strength / 100.0) * 24.0  # 34 -> 10
    blend = 0.38 + (strength / 100.0) * 0.52          # .38 -> .90

    ys, xs = np.nonzero(edge)
    h, w = mask.shape
    out = rgb.copy()
    radius = max(1, min(4, int(radius)))

    for y, x in zip(ys.tolist(), xs.tolist()):
        local_colors: list[np.ndarray] = []
        local_luma: list[float] = []

        for ny in range(max(0, y - radius), min(h, y + radius + 1)):
            for nx in range(max(0, x - radius), min(w, x + radius + 1)):
                if ny == y and nx == x:
                    continue
                if not edge[ny, nx]:
                    continue
                local_colors.append(rgb[ny, nx])
                local_luma.append(float(lum[ny, nx]))

        # No contour context: do not invent a style from one isolated pixel.
        if len(local_luma) < 2:
            continue

        local_luma_arr = np.asarray(local_luma, dtype=np.float32)
        local_colors_arr = np.asarray(local_colors, dtype=np.float32)
        cutoff = float(np.quantile(local_luma_arr, 0.35))
        dark_local = local_colors_arr[local_luma_arr <= cutoff]
        dark_local_luma = local_luma_arr[local_luma_arr <= cutoff]
        if dark_local.size == 0:
            continue

        target = np.median(dark_local, axis=0)
        target_luma = float(np.median(dark_local_luma))

        # Avoid pushing a locally colored outline (brown/blue) all the way to a
        # global near-black unless the local contour itself is missing.
        if target_luma > global_luma + 24.0:
            target = target * 0.82 + global_color * 0.18
            target_luma = float(_luma(target[None, :])[0])

        current_luma = float(lum[y, x])
        neighbor_median = float(np.median(local_luma_arr))

        # The pixel must be an obvious local bright outlier. This is the key
        # guardrail that preserves intentional highlight runs along a silhouette.
        if current_luma <= target_luma + trigger_delta:
            continue
        if current_luma <= neighbor_median + trigger_delta * 0.55:
            continue

        out[y, x] = out[y, x] * (1.0 - blend) + target * blend

    rgba[..., :3] = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    return Image.fromarray(rgba, mode="RGBA")


def add_outer_outline(
    image: Image.Image,
    thickness: int = 1,
    color: tuple[int, int, int] | None = None,
    alpha_threshold: int = 16,
) -> Image.Image:
    """Add a true external outline, expanding the canvas to avoid clipping."""
    thickness = max(0, min(4, int(thickness)))
    if thickness <= 0:
        return image.convert("RGBA")

    src = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    pad = thickness
    rgba = np.pad(src, ((pad, pad), (pad, pad), (0, 0)), mode="constant", constant_values=0)
    mask = rgba[..., 3] >= max(1, min(254, int(alpha_threshold)))
    expanded = _dilate(mask, iterations=thickness)
    ring = expanded & ~mask

    outline_rgb = np.asarray(
        color or estimate_outline_color(image, alpha_threshold),
        dtype=np.uint8,
    )
    rgba[ring, :3] = outline_rgb
    rgba[ring, 3] = 255
    return Image.fromarray(rgba, mode="RGBA")
