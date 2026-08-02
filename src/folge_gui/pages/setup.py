"""Setup page — prerequisites, resolved provider settings, .env / config.yaml editors."""

from __future__ import annotations

from nicegui import ui

from folge_gui import config_io, prereqs
from folge_gui.a11y import LiveRegion, heading, landmark
from folge_gui.components import page_shell
from folge_gui.theme import COLOR

_CHECK_ICON = {True: "check_circle", False: "error"}
_CHECK_COLOR = {True: COLOR["status_success"], False: COLOR["status_error"]}


def build() -> None:
    main = page_shell("/setup")
    live = LiveRegion()

    with main:
        heading("Setup", level=1, classes="text-2xl font-bold m-0")
        ui.label(
            "Check that the tools folge-cli needs are available, review which vision "
            "provider is active, and manage your .env and config.yaml files."
        ).classes("text-base").style(f"color:{COLOR['text_muted']}")

        _prerequisites_section(live)
        _provider_section(live)
        _env_editor_section(live)
        _config_yaml_editor_section(live)


# ---------------------------------------------------------------------------

def _prerequisites_section(live: LiveRegion) -> None:
    with ui.column().classes("fg-card w-full p-5 gap-3"):
        heading("Prerequisites", level=2, classes="text-xl font-semibold m-0")
        ui.label(
            "uv and Pandoc are required for the Full Pipeline and Publish steps. "
            "pdfinfo and pymupdf are used for PDF/UA validation."
        ).classes("text-sm").style(f"color:{COLOR['text_muted']}")

        results_list = landmark("ul", label="Prerequisite check results").classes(
            "w-full flex flex-col gap-1 list-none p-0 m-0"
        )

        async def run_checks() -> None:
            check_btn.disable()
            live.announce("Checking prerequisites…")
            results_list.clear()
            checks = await prereqs.check_prerequisites()
            with results_list:
                for r in checks:
                    _render_check_row(r)
            failures = [r.name for r in checks if not r.ok and r.severity == "error"]
            warnings = [r.name for r in checks if not r.ok and r.severity == "warning"]
            if failures:
                live.announce(f"Prerequisite check complete. Missing: {', '.join(failures)}.")
            elif warnings:
                live.announce(f"Prerequisite check complete, with warnings: {', '.join(warnings)}.")
            else:
                live.announce("Prerequisite check complete. Everything required is available.")
            check_btn.enable()

        check_btn = ui.button("Check prerequisites", icon="fact_check", on_click=run_checks)


def _render_check_row(r: prereqs.CheckResult) -> None:
    color = _CHECK_COLOR[r.ok] if r.ok or r.severity == "error" else COLOR["status_warning"]
    icon = _CHECK_ICON[r.ok] if r.ok or r.severity == "error" else "warning"
    with ui.element("li").classes("w-full"):
        with ui.row().classes("items-center gap-2 py-1"):
            ui.icon(icon).props('aria-hidden="true"').style(f"color:{color}")
            ui.label(f"{r.name}: {r.detail}").classes("text-sm")


# ---------------------------------------------------------------------------

def _provider_section(live: LiveRegion) -> None:
    with ui.column().classes("fg-card w-full p-5 gap-3"):
        heading("Vision provider settings", level=2, classes="text-xl font-semibold m-0")

        active = config_io.active_provider_name()
        ui.label(
            f"Active provider (from .env / config.yaml): {active}"
        ).classes("text-sm font-medium").style(f"color:{COLOR['text']}")

        table_container = ui.column().classes("w-full gap-2")

        def render_table() -> None:
            table_container.clear()
            settings = config_io.all_provider_settings()
            with table_container:
                columns = [
                    {"name": "name", "label": "Provider", "field": "name", "align": "left"},
                    {"name": "base_url", "label": "Base URL", "field": "base_url", "align": "left"},
                    {"name": "model", "label": "Model", "field": "model", "align": "left"},
                    {"name": "api_key", "label": "API key", "field": "api_key", "align": "left"},
                ]
                rows = []
                for name, cfg in settings.items():
                    rows.append({
                        "name": (name + " (active)") if name == active else name,
                        "base_url": cfg["base_url"] or "—",
                        "model": cfg["model"] or "—",
                        "api_key": config_io.mask_secret(cfg["api_key"]) if cfg["api_key"] is not None
                        else "not needed",
                    })
                grid = ui.table(columns=columns, rows=rows, row_key="name").props(
                    'aria-label="Resolved settings for every provider" wrap-cells flat bordered'
                )
                grid.classes("w-full")

        render_table()
        ui.button("Refresh resolved settings", icon="refresh", on_click=render_table).props(
            "outline"
        )

        heading("Check provider reachability", level=3, classes="text-base font-semibold mt-2")
        with ui.row().classes("items-center gap-3 flex-wrap"):
            provider_select = ui.select(
                options=list(config_io.PROVIDERS), value=active, label="Provider"
            ).props("outlined dense").classes("w-48")
            result_container = ui.row().classes("items-center gap-2")

            async def check_one() -> None:
                name = provider_select.value
                live.announce(f"Checking {name}…")
                result = await prereqs.check_provider_reachable(name)
                color = COLOR["status_success"] if result.ok else COLOR["status_warning"]
                icon_name = "check_circle" if result.ok else "warning"
                result_container.clear()
                with result_container:
                    ui.icon(icon_name).props('aria-hidden="true"').style(f"color:{color}")
                    ui.label(f"{name}: {result.detail}").classes("text-sm").style(f"color:{color}")
                live.announce(
                    f"{name}: {'reachable' if result.ok else 'not reachable'} — {result.detail}"
                )

            ui.button("Check", icon="wifi_tethering", on_click=check_one)


# ---------------------------------------------------------------------------

def _env_editor_section(live: LiveRegion) -> None:
    with ui.column().classes("fg-card w-full p-5 gap-3"):
        heading(".env file", level=2, classes="text-xl font-semibold m-0")
        ui.label(
            "Provider base URLs, models, and API keys. This file contains secrets — "
            "anything typed here is visible in plain text on this page."
        ).classes("text-sm").style(f"color:{COLOR['text_muted']}")

        status_label = ui.label("Not loaded yet.").classes("text-xs").style(
            f"color:{COLOR['text_muted']}"
        )
        editor = ui.textarea(label="File contents").props("outlined").classes("w-full font-mono")
        editor.props('rows="14" spellcheck="false"')
        editor.visible = False

        def do_load() -> None:
            state = config_io.read_env()
            editor.set_value(state.text)
            editor.visible = True
            if state.exists:
                status_label.set_text(f"Loaded from {state.path}")
            else:
                status_label.set_text(
                    f"No .env found yet — showing envTemplate. Saving will create {state.path}."
                )
            live.announce("Loaded .env into the editor.")
            save_btn.enable()

        def do_save() -> None:
            config_io.write_env(editor.value or "")
            status_label.set_text(f"Saved to {config_io.ENV_PATH}")
            ui.notify("Saved .env", type="positive")
            live.announce(".env saved.")

        with ui.row().classes("gap-2"):
            ui.button("Load .env", icon="folder_open", on_click=do_load)
            save_btn = ui.button("Save .env", icon="save", on_click=do_save)
            save_btn.disable()


# ---------------------------------------------------------------------------

def _config_yaml_editor_section(live: LiveRegion) -> None:
    with ui.column().classes("fg-card w-full p-5 gap-3"):
        heading("config.yaml", level=2, classes="text-xl font-semibold m-0")
        ui.label(
            "Non-secret defaults (validation thresholds, provider tuning). "
            "Checked for valid YAML before saving."
        ).classes("text-sm").style(f"color:{COLOR['text_muted']}")

        status_label = ui.label("Not loaded yet.").classes("text-xs").style(
            f"color:{COLOR['text_muted']}"
        )
        editor = ui.textarea(label="File contents").props("outlined").classes("w-full font-mono")
        editor.props('rows="14" spellcheck="false"')
        editor.visible = False
        error_label = ui.label("").classes("text-sm")
        error_label.visible = False

        def do_load() -> None:
            state = config_io.read_config_yaml()
            editor.set_value(state.text)
            editor.visible = True
            error_label.visible = False
            if state.exists:
                status_label.set_text(f"Loaded from {state.path}")
            else:
                status_label.set_text(
                    f"No config.yaml found yet. Saving will create {state.path}."
                )
            live.announce("Loaded config.yaml into the editor.")
            save_btn.enable()

        def do_save() -> None:
            try:
                config_io.write_config_yaml(editor.value or "")
            except config_io.InvalidYamlError as exc:
                error_label.set_text(f"Not saved — invalid YAML: {exc}")
                error_label.style(f"color:{COLOR['status_error']}")
                error_label.visible = True
                error_label.props('role="alert"')
                live.announce(f"config.yaml was not saved because it is not valid YAML: {exc}")
                return
            error_label.visible = False
            status_label.set_text(f"Saved to {config_io.CONFIG_YAML_PATH}")
            ui.notify("Saved config.yaml", type="positive")
            live.announce("config.yaml saved.")

        with ui.row().classes("gap-2"):
            ui.button("Load config.yaml", icon="folder_open", on_click=do_load)
            save_btn = ui.button("Save config.yaml", icon="save", on_click=do_save)
            save_btn.disable()
