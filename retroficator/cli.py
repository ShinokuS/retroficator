from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from .core import AssetPipeline, ProcessOptions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert pixel-art-like images into clean game-ready rasters.")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--colors", type=int, default=24, help="Maximum adaptive palette size (default: 24)")
    parser.add_argument("--scale", type=int, default=None, help="Manual source pixel scale. Omit for auto detection.")
    parser.add_argument("--width", type=int, default=None, help="Force native output width")
    parser.add_argument("--height", type=int, default=None, help="Force native output height")
    parser.add_argument("--remove-background", action="store_true")
    parser.add_argument("--background-tolerance", type=float, default=24.0)
    parser.add_argument("--palette", type=str, default=None, help="Text/GPL-like file containing #RRGGBB colors")
    parser.add_argument("--keep-soft-alpha", action="store_true", help="Do not force alpha to 0/255")
    parser.add_argument("--keep-margins", action="store_true", help="Do not crop transparent margins after recovery")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if (args.width is None) != (args.height is None):
        raise SystemExit("--width and --height must be supplied together")

    options = ProcessOptions(
        auto_grid=args.scale is None and args.width is None,
        scale_x=args.scale or 1,
        scale_y=args.scale or 1,
        target_width=args.width,
        target_height=args.height,
        max_colors=args.colors,
        remove_background=args.remove_background,
        background_tolerance=args.background_tolerance,
        palette_path=args.palette,
        binary_alpha=not args.keep_soft_alpha,
        trim_transparent=not args.keep_margins,
    )

    with Image.open(args.input) as image:
        result = AssetPipeline().process(image, options)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.image.save(args.output)
    print(
        f"Saved {args.output} | output {result.report.width}x{result.report.height} | "
        f"native grid {result.grid.cols}x{result.grid.rows} | "
        f"cell {result.grid.step_x:.2f}x{result.grid.step_y:.2f}px | "
        f"{result.report.opaque_colors} colors | "
        f"{result.grid.backend} confidence={result.grid.confidence}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
