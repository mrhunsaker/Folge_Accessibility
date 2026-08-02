"""Steps page — every individual folge_cli sub-command, run on its own."""

from __future__ import annotations

from nicegui import ui

from folge_cli.config import PROJECT_ROOT
from folge_gui.a11y import heading
from folge_gui.components import page_shell, step_card
from folge_gui.steps import STEPS
from folge_gui.theme import COLOR


def build() -> None:
    main = page_shell("/steps")

    with main:
        heading("Steps", level=1, classes="text-2xl font-bold m-0")
        ui.label(
            "Each card below runs one folge-cli command directly, the same way you'd "
            "type it at a terminal. Paths are relative to the project root unless you "
            "give an absolute path."
        ).classes("text-base").style(f"color:{COLOR['text_muted']}")
        ui.label(f"Project root: {PROJECT_ROOT}").classes("text-xs font-mono").style(
            f"color:{COLOR['text_muted']}"
        )

        with ui.column().classes("w-full gap-4"):
            for spec in STEPS:
                step_card(spec, cwd=PROJECT_ROOT)
