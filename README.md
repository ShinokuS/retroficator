# Retroficator

Retroficator is an experimental **AI-friendly pixel-art asset processor**. The goal is to turn AI-generated or otherwise "pixel-art-like" raster images into deterministic, editable, game-ready assets instead of merely applying a generic pixelation filter.

## v0.1 prototype

The first prototype intentionally focuses on the processing core before a full editor is built. It already provides:

- automatic source pixel-grid estimation;
- deterministic recovery to a native-sized raster;
- optional border-connected flat-background removal;
- adaptive color reduction (default: 24 colors);
- project-palette locking using perceptual Oklab color distance, while still respecting the per-asset color limit;
- binary-alpha cleanup for crisp sprite edges;
- basic asset validation (dimensions, color count, alpha levels, tiny disconnected components);
- a simple desktop GUI with drag-and-drop, before/after preview and PNG export;
- a CLI for batchable processing.

The architecture keeps the processing engine separate from the UI so the same operations can later be exposed to a richer editor and to a ChatGPT plugin/tool surface.

## Install (Windows / macOS / Linux)

Python 3.11+ is required.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[gui]"
retroficator
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[gui]'
retroficator
```

You can also launch it with:

```bash
python -m retroficator
```

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

Likewise, v0.1 is not yet a full Aseprite/Pixelorama replacement: there are no layers, frame timeline, brushes or animation tools. Those belong in the editor layer after the asset-recovery pipeline is proven.

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

The repository uses MIT licensing so the processing core can later be embedded in a desktop editor or other tooling without copyleft constraints.
