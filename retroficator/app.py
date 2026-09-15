from __future__ import annotations


def main() -> int:
    try:
        from .gui.main_window import run_gui
    except ImportError as exc:
        raise SystemExit(
            "GUI dependencies are missing. Install with: pip install -e '.[gui]'\n"
            f"Original error: {exc}"
        ) from exc
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
