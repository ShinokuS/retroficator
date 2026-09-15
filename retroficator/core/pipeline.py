from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .alpha import normalize_alpha
from .background import remove_flat_background
from .grid import GridEstimate, detect_grid, recover_native_grid, resize_to_native_size
from .palette import load_hex_palette, map_to_palette, quantize_colors, select_project_palette
from .validation import ValidationReport, validate_asset


@dataclass
class ProcessOptions:
    auto_grid: bool = True
    scale_x: int = 1
    scale_y: int = 1
    target_width: int | None = None
    target_height: int | None = None
    max_colors: int = 24
    remove_background: bool = False
    background_tolerance: float = 24.0
    palette_path: str | None = None
    max_auto_scale: int = 32
    binary_alpha: bool = True
    alpha_threshold: int = 128


@dataclass
class ProcessResult:
    image: Image.Image
    grid: GridEstimate
    report: ValidationReport


class AssetPipeline:
    def process(self, image: Image.Image, options: ProcessOptions) -> ProcessResult:
        src = image.convert("RGBA")
        grid = detect_grid(src, max_scale=options.max_auto_scale)

        work = src
        if options.remove_background:
            work = remove_flat_background(work, tolerance=options.background_tolerance)

        if options.target_width and options.target_height:
            work = resize_to_native_size(work, options.target_width, options.target_height)
        else:
            sx = grid.scale_x if options.auto_grid and grid.scale_x > 1 else options.scale_x
            sy = grid.scale_y if options.auto_grid and grid.scale_y > 1 else options.scale_y
            work = recover_native_grid(work, sx, sy)

        if options.binary_alpha:
            work = normalize_alpha(work, threshold=options.alpha_threshold)

        if options.palette_path:
            palette = load_hex_palette(Path(options.palette_path))
            selected = select_project_palette(work, palette, max_colors=options.max_colors)
            work = map_to_palette(work, selected)
        else:
            work = quantize_colors(work, max_colors=options.max_colors)

        report = validate_asset(work)
        return ProcessResult(image=work, grid=grid, report=report)
