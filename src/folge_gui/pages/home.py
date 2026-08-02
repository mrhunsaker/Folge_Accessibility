"""Landing page: what this app is, and where to go next."""

from __future__ import annotations

from nicegui import ui

from folge_gui.a11y import heading, icon_with_label
from folge_gui.components import page_shell
from folge_gui.theme import COLOR


def build() -> None:
    main = page_shell("/")

    with main:
        heading("Folge Accessibility — GUI", level=1, classes="text-2xl font-bold m-0")
        ui.label(
            "A companion interface to folge-cli: check your setup, run individual "
            "pipeline steps, or run the whole publishing pipeline — all from the browser."
        ).classes("text-base").style(f"color:{COLOR['text_muted']}")

        with ui.row().classes("w-full gap-4 flex-wrap"):
            _nav_card(
                "/setup", "tune", "Setup",
                "Check prerequisites, view resolved provider settings, and edit "
                "your .env and config.yaml files.",
            )
            _nav_card(
                "/steps", "checklist", "Steps",
                "Run any individual folge-cli command — batch-process, merge, "
                "validate, render, publish, and more — with its own form and live output.",
            )
            _nav_card(
                "/pipeline", "route", "Full Pipeline",
                "Run the entire pipeline end to end, with a visual tracker for "
                "each stage and accessible prompts at the points that normally "
                "need a decision from you.",
            )

        with ui.column().classes("w-full gap-2 mt-4"):
            heading("Before you start", level=2, classes="text-xl font-semibold m-0")
            with ui.column().classes("gap-1"):
                icon_with_label(
                    "check_circle", "Run this from the project root, or point Setup at your project.",
                    icon_color=COLOR["status_success"],
                )
                icon_with_label(
                    "check_circle", "guide.json (exported from Folge) and an images/ folder should be in place.",
                    icon_color=COLOR["status_success"],
                )
                icon_with_label(
                    "check_circle", "Visit Setup first to confirm uv, Pandoc, and your vision provider are ready.",
                    icon_color=COLOR["status_success"],
                )


def _nav_card(path: str, icon: str, title: str, description: str) -> None:
    with ui.link(target=path).classes("no-underline").style("flex: 1 1 260px; min-width: 260px;"):
        with ui.column().classes("fg-card p-5 gap-2 h-full").style("min-height: 10rem;"):
            with ui.row().classes("items-center gap-2"):
                ui.icon(icon).props('aria-hidden="true"').style(f"color:{COLOR['primary']}; font-size:1.5rem;")
                ui.label(title).classes("text-lg font-semibold").style(f"color:{COLOR['text']}")
            ui.label(description).classes("text-sm").style(f"color:{COLOR['text_muted']}")
            ui.label(f"Go to {title} →").classes("text-sm font-medium mt-auto").style(
                f"color:{COLOR['link']}"
            )
