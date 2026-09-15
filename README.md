# Retroficator

Retroficator is an experimental **AI-friendly pixel-art asset processor**. The goal is to turn AI-generated or otherwise "pixel-art-like" raster images into deterministic, editable, game-ready assets instead of merely applying a generic pixelation filter.

## Current prototype

The project is web-first: a local FastAPI backend serves a browser workspace while the image-processing engine remains independent from the UI. The same engine can later be exposed to a richer editor, batch jobs and a ChatGPT plugin.

The current pipeline provides:

- high-quality pseudo-pixel grid recovery through the open-source Retro Diffusion Pixel Art Fixer;
- detected source cell size and native raster dimensions;
- two-stage pixel reconstruction instead of a generic resize;
- automatic trimming of transparent margins after grid recovery;
- optional border-connected flat-background removal;
- adaptive color reduction (default: 24 colors);
- project-palette locking using perceptual Oklab distance;
- binary-alpha cleanup for crisp sprite edges;
- asset validation (dimensions, color count, alpha levels, tiny disconnected components);
- a local web workspace with drag-and-drop, before/after previews, diagnostics and PNG export;
- a CLI for batch processing.

## Install and run

Python 3.11+ and Git are required. The Pixel Art Fixer dependency is pinned to a known upstream commit for reproducible installs.

```bash
python -m venv .venv
source .venv/bin/activate          # Linux / WSL / macOS
python -m pip install --upgrade pip
pip install -e .
retroficator
```

Windows PowerShell activation is:

```powershell
.\.venv\Scripts\Activate.ps1
```

Retroficator starts at `http://127.0.0.1:8765`. Processing is local; source assets are not uploaded by Retroficator.

After pulling an update that changes dependencies, run `pip install -e .` again before restarting the server.

## Web workflow

1. Drop a PNG, JPG or WebP into Source.
2. Leave **High-quality native grid detection** enabled for AI-generated fake pixel art.
3. Leave **Trim transparent margins** enabled for isolated sprites/icons.
4. Choose a maximum per-asset color count.
5. Optionally remove a flat background or load a project `.hex` palette.
6. Recover the asset.
7. Inspect **Source cell size**, **Detected native grid**, **Confidence** and **Output size**. A successful recovery often looks visually similar at the same display size; the important change is that the result is now a small true-pixel raster rather than a 1000+ px imitation.
8. Download the PNG.

`Force exact output size` is a manual override, not the normal asset workflow. It directly resamples to the requested dimensions and should only be used when the intended native canvas is already known.

## CLI

```bash
retroficator-cli input.png -o output.png --colors 24
```

Force a known source pixel scale:

```bash
retroficator-cli input.png -o output.png --scale 12 --colors 20
```

Keep transparent margins instead of trimming them:

```bash
retroficator-cli input.png -o output.png --keep-margins
```

Lock output to a project palette:

```bash
retroficator-cli input.png -o output.png --palette my_palette.txt
```

A palette file can be plain text; every line containing a `#RRGGBB` value is read as a permitted project color. If the project palette is larger than `--colors`, Retroficator derives an image-specific subset first.

## Processing architecture

```text
source image
    ↓
optional background isolation
    ↓
Pixel Art Fixer consensus grid detection
    ↓
two-stage native pixel reconstruction
    ↓
binary alpha / project palette cleanup
    ↓
transparent-margin trim
    ↓
validation + export
```

The previous lightweight Retroficator detector remains in the codebase as a fallback/manual development path, but it is no longer the primary auto-recovery engine.

## Development

```bash
pip install -e '.[dev]'
pytest
```

Retroficator is MIT licensed. Pixel Art Fixer is an MIT-licensed upstream dependency maintained by Retro Diffusion and is pinned in `pyproject.toml`.
