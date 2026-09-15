# Retroficator

Retroficator is an experimental **AI-friendly pixel-art asset processor**. The goal is to turn AI-generated or otherwise "pixel-art-like" raster images into deterministic, editable, game-ready assets instead of merely applying a generic pixelation filter.

## v0.1 prototype

The first prototype intentionally focuses on the processing core before a full editor is built. It already provides:

- automatic source pixel-grid estimation;
- deterministic recovery to a native-sized raster;
- optional border-connected flat-background removal;
- adaptive color reduction (default: 24 colors);
- project-palette locking using perceptual Oklab color distance, while respecting the per-asset color limit;
- binary-alpha cleanup for crisp sprite edges;
- basic asset validation (dimensions, color count, alpha levels, tiny disconnected components);
- a local web workspace with drag-and-drop, before/after previews, diagnostics and PNG export;
- a CLI for batchable processing;
- the original PySide desktop prototype as an optional fallback.

The processing engine is intentionally separate from the interface. The browser UI, CLI and future ChatGPT plugin can therefore call the same deterministic asset pipeline.

## Install and run

Python 3.11+ is required.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
retroficator
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
retroficator
```

Retroficator starts a local server at `http://127.0.0.1:8765` and opens the browser automatically. Processing stays on the machine; the v0.1 server does not upload source assets to an external service.

Alternative launch commands:

```bash
retroficator-web
python -m retroficator
```

The old desktop prototype can still be used if needed:

```bash
pip install -e '.[gui]'
retroficator-desktop
```

## Web workflow

1. Drop a PNG, JPG or WebP into the Source area.
2. Keep auto-grid enabled first, or force a known native output size such as 32×32 or 64×64.
3. Choose the maximum per-asset color count.
4. Optionally remove a flat edge-connected background and load a project `.hex` palette.
5. Process the asset and inspect detected grid, output dimensions, color count, alpha levels and tiny components.
6. Download the lossless PNG result.

## CLI

```bash
retroficator-cli input.png -o output.png --colors 24 --remove-background
```

Force a known source-pixel scale:

```bash
retroficator-cli input.png -o output.png --scale 16 --colors 20
```

Force a target native resolution instead of scale recovery:

```bash
retroficator-cli input.png -o output.png --width 64 --height 64 --colors 24
```

Lock output to a project palette:

```bash
retroficator-cli input.png -o output.png --palette my_palette.txt
```

A palette file can be plain text; every line containing a `#RRGGBB` value is read as a permitted project color. If the project palette is larger than `--colors`, Retroficator derives an image-specific subset first.

## What v0.1 is — and is not

This is a **baseline we can test against real ChatGPT-generated assets**. The auto-grid detector is deliberately dependency-light and does not yet claim to match specialized research-grade pixel-grid recovery algorithms. The next milestone is to benchmark it against Pixel Art Fixer / Pixel Snapper on our own test corpus, then keep the best method or add a selectable backend.

v0.1 is not yet a full Aseprite/Pixelorama replacement: there are no layers, frame timeline, brushes or animation tools. Those belong in the editor layer after the asset-recovery pipeline is proven.

## Suggested evaluation workflow

1. Generate 20–50 representative assets in ChatGPT (icons, characters, props, tiles).
2. Save the untouched source PNGs in a local test folder.
3. Run each through Retroficator with auto-grid and with manually known target sizes.
4. Record failures: wrong native size, broken outlines, palette damage, background remnants, detached pixels.
5. Use those failures to drive the next algorithmic milestone rather than tuning against synthetic samples only.

## Development

```bash
pip install -e '.[dev]'
pytest
```

The repository uses MIT licensing so the processing core can later be embedded in other tooling without copyleft constraints.
