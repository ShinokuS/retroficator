from __future__ import annotations

import base64
import io
import tempfile
import webbrowser
from dataclasses import asdict
from pathlib import Path
from threading import Timer

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from retroficator.core.pipeline import AssetPipeline, ProcessOptions

app = FastAPI(title="Retroficator", version="0.3.0")
_pipeline = AssetPipeline()
_STATIC_DIR = Path(__file__).with_name("static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/styles.css")
def styles() -> FileResponse:
    return FileResponse(_STATIC_DIR / "styles.css", media_type="text/css")


@app.get("/app.js")
def javascript() -> FileResponse:
    return FileResponse(_STATIC_DIR / "app.js", media_type="application/javascript")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/process")
async def process_asset(
    image: UploadFile = File(...),
    palette: UploadFile | None = File(default=None),
    auto_grid: bool = Form(default=True),
    scale_x: int = Form(default=1),
    scale_y: int = Form(default=1),
    target_width: int | None = Form(default=None),
    target_height: int | None = Form(default=None),
    limit_colors: bool = Form(default=False),
    max_colors: int = Form(default=24),
    remove_background: bool = Form(default=False),
    background_tolerance: float = Form(default=24.0),
    binary_alpha: bool = Form(default=False),
    alpha_threshold: int = Form(default=128),
    trim_transparent: bool = Form(default=True),
    crisp_edges: bool = Form(default=True),
    edge_alpha_threshold: int = Form(default=18),
    repair_outline: bool = Form(default=True),
    outline_strength: int = Form(default=70),
    outer_outline: int = Form(default=0),
) -> dict:
    if max_colors < 2 or max_colors > 256:
        raise HTTPException(status_code=400, detail="max_colors must be between 2 and 256")
    if scale_x < 1 or scale_y < 1:
        raise HTTPException(status_code=400, detail="scale values must be >= 1")
    if (target_width is None) != (target_height is None):
        raise HTTPException(status_code=400, detail="target width and height must be set together")
    if outline_strength < 0 or outline_strength > 100:
        raise HTTPException(status_code=400, detail="outline_strength must be between 0 and 100")
    if outer_outline < 0 or outer_outline > 4:
        raise HTTPException(status_code=400, detail="outer_outline must be between 0 and 4")
    if edge_alpha_threshold < 1 or edge_alpha_threshold > 254:
        raise HTTPException(status_code=400, detail="edge_alpha_threshold must be between 1 and 254")

    payload = await image.read()
    if len(payload) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image is larger than 25 MB")

    try:
        source = Image.open(io.BytesIO(payload))
        source.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Unsupported or invalid image") from exc

    palette_path: str | None = None
    temp_palette: tempfile.NamedTemporaryFile | None = None
    try:
        if palette is not None and palette.filename:
            palette_bytes = await palette.read()
            temp_palette = tempfile.NamedTemporaryFile(suffix=".hex", delete=False)
            temp_palette.write(palette_bytes)
            temp_palette.close()
            palette_path = temp_palette.name

        options = ProcessOptions(
            auto_grid=auto_grid,
            scale_x=scale_x,
            scale_y=scale_y,
            target_width=target_width,
            target_height=target_height,
            limit_colors=limit_colors,
            max_colors=max_colors,
            remove_background=remove_background,
            background_tolerance=background_tolerance,
            palette_path=palette_path,
            binary_alpha=binary_alpha,
            alpha_threshold=alpha_threshold,
            trim_transparent=trim_transparent,
            crisp_edges=crisp_edges,
            edge_alpha_threshold=edge_alpha_threshold,
            repair_outline=repair_outline,
            outline_strength=outline_strength,
            outer_outline=outer_outline,
        )
        result = _pipeline.process(source, options)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if temp_palette is not None:
            try:
                Path(temp_palette.name).unlink(missing_ok=True)
            except OSError:
                pass

    output = io.BytesIO()
    result.image.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode("ascii")

    return {
        "image_base64": encoded,
        "grid": asdict(result.grid),
        "report": result.report.to_dict(),
        "source": {"width": source.width, "height": source.height},
        "processing": {
            "limit_colors": limit_colors,
            "max_colors": max_colors if limit_colors else None,
            "binary_alpha": binary_alpha,
            "palette_locked": bool(palette_path),
            "crisp_edges": crisp_edges and not binary_alpha,
            "repair_outline": repair_outline,
            "outline_strength": outline_strength if repair_outline else None,
            "outer_outline": outer_outline,
        },
    }


def run_web(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> int:
    import uvicorn

    url = f"http://{host}:{port}"
    if open_browser:
        Timer(0.8, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_web())
