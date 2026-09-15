from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

from .grid import detect_grid, recover_native_grid, resize_to_native_size


@dataclass(frozen=True)
class RecoveryInfo:
    backend: str
    step_x: float
    step_y: float
    cols: int
    rows: int
    confidence: str
    consensus: str
    scale_x: int
    scale_y: int
    phase_x: int = 0
    phase_y: int = 0


def recover_auto(image: Image.Image, mode: str = "full") -> tuple[Image.Image, RecoveryInfo]:
    """Recover the native pseudo-pixel grid using Pixel Art Fixer.

    Pixel Art Fixer combines several independent grid detectors and uses a
    two-stage reconstruction that decides cell structure separately from final
    cell color. If it is unavailable, Retroficator falls back to the original
    lightweight detector so manual/dev workflows still work.
    """
    src = image.convert("RGBA")

    try:
        from pixelfixer.api import process as pixel_fixer_process
    except ImportError:
        legacy = detect_grid(src)
        sx = legacy.scale_x if legacy.scale_x > 1 else 1
        sy = legacy.scale_y if legacy.scale_y > 1 else 1
        out = recover_native_grid(src, sx, sy)
        return out, RecoveryInfo(
            backend="legacy-fallback",
            step_x=float(sx),
            step_y=float(sy),
            cols=out.width,
            rows=out.height,
            confidence=f"{legacy.confidence:.0%}",
            consensus="legacy",
            scale_x=sx,
            scale_y=sy,
            phase_x=legacy.phase_x,
            phase_y=legacy.phase_y,
        )

    rgba = np.asarray(src, dtype=np.uint8)
    result = pixel_fixer_process(rgba, mode=mode, return_png=False)
    out = Image.fromarray(result["array"].astype(np.uint8), mode="RGBA")
    step_x = float(result["step_x"])
    step_y = float(result["step_y"])
    return out, RecoveryInfo(
        backend="pixel-art-fixer",
        step_x=step_x,
        step_y=step_y,
        cols=int(result["cols"]),
        rows=int(result["rows"]),
        confidence=str(result.get("confidence", "unknown")),
        consensus=str(result.get("consensus", "")),
        scale_x=max(1, round(step_x)),
        scale_y=max(1, round(step_y)),
    )


def recover_manual_scale(image: Image.Image, scale_x: int, scale_y: int) -> tuple[Image.Image, RecoveryInfo]:
    out = recover_native_grid(image, scale_x, scale_y)
    return out, RecoveryInfo(
        backend="manual-scale",
        step_x=float(scale_x),
        step_y=float(scale_y),
        cols=out.width,
        rows=out.height,
        confidence="manual",
        consensus="forced-scale",
        scale_x=max(1, int(scale_x)),
        scale_y=max(1, int(scale_y)),
    )


def recover_manual_size(image: Image.Image, width: int, height: int) -> tuple[Image.Image, RecoveryInfo]:
    src = image.convert("RGBA")
    out = resize_to_native_size(src, width, height)
    return out, RecoveryInfo(
        backend="manual-size",
        step_x=src.width / max(1, width),
        step_y=src.height / max(1, height),
        cols=out.width,
        rows=out.height,
        confidence="manual",
        consensus="forced-size",
        scale_x=max(1, round(src.width / max(1, width))),
        scale_y=max(1, round(src.height / max(1, height))),
    )
