from __future__ import annotations


def main() -> int:
    """Launch the local web interface."""
    try:
        from .web.server import run_web
    except ImportError as exc:
        raise SystemExit(
            "Web dependencies are missing. Reinstall Retroficator with: pip install -e .\n"
            f"Original error: {exc}"
        ) from exc
    return run_web()


def desktop_main() -> int:
    """Launch the legacy desktop prototype when the optional GUI extra is installed."""
    try:
        from .gui.main_window import run_gui
    except ImportError as exc:
        raise SystemExit(
            "Desktop GUI dependencies are missing. Install with: pip install -e '.[gui]'\n"
            f"Original error: {exc}"
        ) from exc
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
