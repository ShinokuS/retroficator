from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .alpha import normalize_alpha
from .asset import trim_transparent
from .background import remove_flat_background
from .palette import load_hex_palette, map_to_palette, quantize_colors, select_project_palette
from .recovery import RecoveryInfo, recover_auto, recover_manual_scale, recover_manual_size
from .validation import ValidationReport, validate_asset


@dataclass
class ProcessOptions:
    auto_grid: bool = True
    scale_x: int = 1
    scale_y: int = 1
    target_width: int | None = None
    target_height: int | None = None
    # Palette reduction is intentionally opt-in. Pixel Art Fixer's two-stage
    # reconstruction already preserves source colours; quantising it again by
    # default destroys rare highlights, material texture and outline shades.
    limit_colors: bool = False
    max_colors: int = 24
    remove_background: bool = False
    background_tolerance: float = 24.0
    palette_path: str | None = None
    # Keep reconstructed alpha by default. Hard 0/255 alpha is useful for some
    # engines, but can thin one-cell outlines on AI-generated transparent art.
    binary_alpha: bool = False
    alpha_threshold: int = 128
    trim_transparent: bool = True
    trim_padding: int = 1
    trim_alpha_threshold: int = 8
    recovery_mode: str = "full"


@dataclass
class ProcessResult:
    image: Image.Image
    grid: RecoveryInfo
    report: ValidationReport


class AssetPipeline:
    def process(self, image: Image.Image, options: ProcessOptions) -> ProcessResult:
        work = image.convert("RGBA")

        if options.remove_background:
            work = remove_flat_background(work, tolerance=options.background_tolerance)

        if options.target_width and options.target_height:
            work, grid = recover_manual_size(work, options.target_width, options.target_height)
        elif options.auto_grid:
            work, grid = recover_auto(work, mode=options.recovery_mode)
        else:
            work, grid = recover_manual_scale(work, options.scale_x, options.scale_y)

        if options.binary_alpha:
            work = normalize_alpha(work, threshold=options.alpha_threshold)

        # Crop the empty model canvas before optional colour reduction. Besides
        # making a useful game asset, this prevents invisible RGB values in the
        # transparent margin from consuming palette slots.
        if options.trim_transparent and not (options.target_width and options.target_height):
            threshold = 1 if options.binary_alpha else max(1, min(254, int(options.trim_alpha_threshold)))
            work = trim_transparent(work, alpha_threshold=threshold, padding=options.trim_padding)

        if options.palette_path:
            palette = load_hex_palette(Path(options.palette_path))
            selected = (
                select_project_palette(work, palette, max_colors=options.max_colors)
                if options.limit_colors
                else palette
            )
            work = map_to_palette(work, selected)
        elif options.limit_colors:
            work = quantize_colors(work, max_colors=options.max_colors)

        report = validate_asset(work)
        return ProcessResult(image=work, grid=grid, report=report)
