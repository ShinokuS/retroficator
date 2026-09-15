from __future__ import annotations

from dataclasses import dataclass
from math import log2

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class AxisGridEstimate:
    scale: int
    phase: int
    confidence: float


@dataclass(frozen=True)
class GridEstimate:
    scale_x: int
    scale_y: int
    phase_x: int
    phase_y: int
    confidence: float


def _rgba_array(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("RGBA"), dtype=np.float32) / 255.0


def _luma_with_alpha(image: Image.Image) -> np.ndarray:
    rgba = _rgba_array(image)
    rgb = rgba[..., :3]
    alpha = rgba[..., 3:4]
    # Composite over mid-gray so transparent areas do not create huge fake edges.
    rgb = rgb * alpha + 0.5 * (1.0 - alpha)
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def _gradient_profile(luma: np.ndarray, axis: int) -> np.ndarray:
    if axis == 1:  # vertical boundaries, profile over x
        grad = np.abs(np.diff(luma, axis=1))
        return np.mean(grad, axis=0)
    grad = np.abs(np.diff(luma, axis=0))
    return np.mean(grad, axis=1)


def _axis_score(profile: np.ndarray, scale: int, phase: int) -> float:
    if scale <= 1 or profile.size < scale * 3:
        return 0.0

    positions = np.arange(profile.size, dtype=np.int32)
    # Keep only edge energy above the background gradient floor. This makes the
    # detector reason about where visible pixel transitions happen instead of
    # averaging over large flat regions.
    floor = float(np.percentile(profile, 55))
    energy = np.maximum(profile - floor, 0.0)
    total = float(np.sum(energy))
    if total <= 1e-9:
        return 0.0

    mod = (positions + 1 - phase) % scale
    distance = np.minimum(mod, scale - mod).astype(np.float32)

    # AI pseudo-pixels often blur a logical boundary over 1-2 source pixels.
    # A narrow Gaussian therefore scores near-grid edges without demanding an
    # unrealistically perfect nearest-neighbour source.
    sigma = max(0.65, min(1.5, scale * 0.06))
    alignment = np.exp(-0.5 * (distance / sigma) ** 2)
    aligned_fraction = float(np.sum(energy * alignment) / total)

    # Prefer larger fundamental cells only when they explain essentially the
    # same edge energy. Multiples of the true scale split edges across phases
    # and therefore lose aligned_fraction; divisors fit too easily and receive
    # only a mild size reward.
    size_reward = 1.0 + 0.10 * log2(scale)
    return aligned_fraction * size_reward


def estimate_axis_grid(profile: np.ndarray, max_scale: int = 32) -> AxisGridEstimate:
    max_scale = max(1, min(max_scale, max(1, profile.size // 4)))
    best = AxisGridEstimate(scale=1, phase=0, confidence=0.0)

    raw_scores: list[tuple[float, int, int]] = []
    for scale in range(2, max_scale + 1):
        for phase in range(scale):
            score = _axis_score(profile, scale, phase)
            raw_scores.append((score, scale, phase))
            if score > best.confidence:
                best = AxisGridEstimate(scale=scale, phase=phase, confidence=score)

    if not raw_scores or best.confidence <= 0:
        return AxisGridEstimate(scale=1, phase=0, confidence=0.0)

    scores = np.array([s for s, _, _ in raw_scores], dtype=np.float32)
    median = float(np.median(scores))
    mad = float(np.median(np.abs(scores - median))) + 1e-6
    z = max(0.0, (best.confidence - median) / (1.4826 * mad))
    confidence = float(1.0 - np.exp(-z / 3.0))

    # Weak periodicity is worse than pretending we do not know the scale.
    if confidence < 0.22:
        return AxisGridEstimate(scale=1, phase=0, confidence=confidence)

    # If a divisor explains almost as much edge energy as the winning scale, the
    # winner can be a harmonic. Select the largest divisor that still retains a
    # very high fraction of the winning score; this tends to recover the true
    # logical cell rather than 2x/3x harmonics.
    best_score = best.confidence
    divisor_candidates = [
        (score, scale, phase)
        for score, scale, phase in raw_scores
        if scale < best.scale and best.scale % scale == 0 and score >= best_score * 0.94
    ]
    if divisor_candidates:
        score, scale, phase = max(divisor_candidates, key=lambda item: item[1])
        best = AxisGridEstimate(scale=scale, phase=phase, confidence=confidence)

    return AxisGridEstimate(scale=best.scale, phase=best.phase, confidence=confidence)


def detect_grid(image: Image.Image, max_scale: int = 32) -> GridEstimate:
    luma = _luma_with_alpha(image)
    x = estimate_axis_grid(_gradient_profile(luma, axis=1), max_scale=max_scale)
    y = estimate_axis_grid(_gradient_profile(luma, axis=0), max_scale=max_scale)

    confidence = float((x.confidence + y.confidence) / 2.0)
    return GridEstimate(
        scale_x=x.scale,
        scale_y=y.scale,
        phase_x=x.phase,
        phase_y=y.phase,
        confidence=confidence,
    )


def recover_native_grid(
    image: Image.Image,
    scale_x: int,
    scale_y: int | None = None,
) -> Image.Image:
    """Recover a native-resolution raster from a scaled/pseudo-pixel source.

    BOX reduction behaves as a block integrator and is intentionally followed by
    palette normalization in the pipeline. It is much less alias-prone than a
    generic bilinear resize and gives deterministic output.
    """
    if scale_y is None:
        scale_y = scale_x
    scale_x = max(1, int(scale_x))
    scale_y = max(1, int(scale_y))
    src = image.convert("RGBA")
    if scale_x == 1 and scale_y == 1:
        return src.copy()

    width = max(1, round(src.width / scale_x))
    height = max(1, round(src.height / scale_y))
    return src.resize((width, height), resample=Image.Resampling.BOX)


def resize_to_native_size(image: Image.Image, width: int, height: int) -> Image.Image:
    width = max(1, int(width))
    height = max(1, int(height))
    return image.convert("RGBA").resize((width, height), resample=Image.Resampling.BOX)
