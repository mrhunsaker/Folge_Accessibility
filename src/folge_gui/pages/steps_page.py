"""Steps page — every individual folge_cli sub-command, run on its own."""

from __future__ import annotations

from nicegui import ui

from folge_cli.config import PROJECT_ROOT, PROJECTS_DIR
from folge_gui.a11y import heading
from folge_gui.components import active_project, page_shell, project_selector, step_card
from folge_gui.steps import STEPS, project_defaults
from folge_gui.theme import COLOR


def build() -> None:
    main = page_shell("/steps")
    project = active_project()
    defaults = project_defaults(project)

    with main:
        heading("Steps", level=1, classes="text-2xl font-bold m-0")
        ui.label(
            "Each card below runs one folge-cli command directly, the same way you'd "
            "type it at a terminal. Pick an active project to pre-fill every path "
            "field; you can edit any path for a one-off run."
        ).classes("text-base").style(f"color:{COLOR['text_muted']}")

        project_selector("/steps")

        if project:
            ui.label(f"Active project: {PROJECTS_DIR / project}").classes(
                "text-xs font-mono"
            ).style(f"color:{COLOR['text_muted']}")

        with ui.column().classes("w-full gap-4"):
            for spec in STEPS:
                step_card(spec, cwd=PROJECT_ROOT, defaults=defaults)
