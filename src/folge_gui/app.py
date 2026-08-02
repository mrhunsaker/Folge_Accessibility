"""folge_gui application entry point — registers routes and starts the server.

Primary way to run this: ``uv sync --all-packages`` once from the
repository root (folge_gui is a uv workspace member — see
``src/folge_gui/pyproject.toml``), then ``uv run folge_gui``. That launches
this module's :func:`main` via the ``folge_gui`` console script on port
8765.

It also still works stand-alone with ``python -m folge_gui`` or
``python src/folge_gui/app.py`` (see ``src/folge_gui/README.md``); the
sys.path fix-up below makes the second form work even without an editable
install, by making the ``src/`` directory (this file's grandparent)
importable so that both ``folge_gui`` and its sibling ``folge_cli`` package
can be found.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from nicegui import ui  # noqa: E402

from folge_gui.theme import apply_theme  # noqa: E402


@ui.page("/")
def _home_page() -> None:
    apply_theme()
    from folge_gui.pages import home
    home.build()


@ui.page("/setup")
def _setup_page() -> None:
    apply_theme()
    from folge_gui.pages import setup
    setup.build()


@ui.page("/steps")
def _steps_page() -> None:
    apply_theme()
    from folge_gui.pages import steps_page
    steps_page.build()


@ui.page("/pipeline")
def _pipeline_page() -> None:
    apply_theme()
    from folge_gui.pages import pipeline_page
    pipeline_page.build()


def main() -> None:
    """Start the NiceGUI server for folge_gui."""
    try:
        import folge_cli  # noqa: F401
    except ImportError as exc:  # pragma: no cover - startup guard
        print(
            "folge_gui could not import folge_cli.\n"
            "Make sure you're running from an environment where the project "
            "is installed (e.g. after `uv sync` at the repository root), or "
            "set PYTHONPATH to include the `src` directory.\n"
            f"Original error: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    ui.run(
        title="Folge GUI",
        favicon="\u267f",  # ♿ — thematically apt, and NiceGUI supports emoji favicons
        dark=False,
        language="en-US",
        reload=False,
        show=True,
        port=8765,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
