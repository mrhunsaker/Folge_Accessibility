"""Shared, reusable UI building blocks for every folge_gui page.

Keeping these in one place means the accessibility guarantees (labeled
fields, live-region announcements, focus-visible controls, status never
conveyed by color alone) are implemented once and reused everywhere, rather
than re-derived per page with room for a page to forget one.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from nicegui import app, ui
from nicegui.element import Element

from folge_gui.a11y import LiveRegion, heading, landmark
from folge_gui.process_runner import ProcessRun, StepStatus
from folge_gui.steps import FieldSpec, StepSpec
from folge_gui.theme import COLOR

NAV_ITEMS: list[tuple[str, str, str]] = [
    ("/", "Home", "home"),
    ("/setup", "Setup", "tune"),
    ("/steps", "Steps", "checklist"),
    ("/pipeline", "Full Pipeline", "route"),
]

STATUS_META: dict[StepStatus, dict] = {
    StepStatus.PENDING: {"icon": "radio_button_unchecked", "text": "Not started", "color": COLOR["status_pending"], "spin": False},
    StepStatus.RUNNING: {"icon": "autorenew", "text": "Running", "color": COLOR["status_running"], "spin": True},
    StepStatus.WAITING_INPUT: {"icon": "help", "text": "Needs your input", "color": COLOR["status_waiting"], "spin": False},
    StepStatus.SUCCESS: {"icon": "check_circle", "text": "Completed", "color": COLOR["status_success"], "spin": False},
    StepStatus.ERROR: {"icon": "error", "text": "Failed", "color": COLOR["status_error"], "spin": False},
    StepStatus.CANCELLED: {"icon": "cancel", "text": "Cancelled", "color": COLOR["status_pending"], "spin": False},
}


# ---------------------------------------------------------------------------
# Page shell: skip link, header, primary nav landmark, main landmark, footer
# ---------------------------------------------------------------------------

def page_shell(active_path: str) -> Element:
    """Build the shared chrome and return the ``<main>`` container for page content.

    :param active_path: current route, used to mark the matching nav link
        with ``aria-current="page"`` (WCAG 2.4.8 Location) and a visible
        indicator that doesn't rely on color alone.
    """
    with ui.header().classes("items-center").style(
        f"background:{COLOR['bg_raised']}; color:{COLOR['text']}; "
        f"border-bottom: 1px solid {COLOR['border']}; padding: 0 1rem;"
    ):
        with ui.row().classes("w-full items-center justify-between flex-wrap").style("max-width:1200px; margin:0 auto;"):
            ui.link("Folge GUI", "/").classes("text-lg font-bold no-underline").style(
                f"color:{COLOR['text']};"
            )
            with landmark("nav", label="Primary").classes("flex flex-row gap-1 flex-wrap"):
                for path, label, icon in NAV_ITEMS:
                    is_active = path == active_path
                    link = ui.link(label, path).classes(
                        "no-underline px-3 py-2 rounded flex items-center gap-1 text-sm font-medium"
                    )
                    if is_active:
                        link.props('aria-current="page"')
                        link.style(
                            f"background:{COLOR['fill_primary']}; color:#ffffff;"
                        )
                    else:
                        link.style(f"color:{COLOR['text']};")
            exit_btn = ui.button("Exit", icon="power_settings_new").props(
                'outline color=negative aria-label="Exit folge_gui and stop the server"'
            )

    main = landmark("main", label="Main content").classes("w-full gap-6").props(
        'id="main-content" tabindex="-1"'
    ).style("max-width:1200px; margin:0 auto; padding: 1.5rem 1rem 3rem;")

    ui.skip_link("Skip to main content", target=main)

    with ui.footer().classes("items-center justify-center").style(
        f"background:{COLOR['bg_raised']}; color:{COLOR['text_muted']}; "
        f"border-top: 1px solid {COLOR['border']}; padding: 0.75rem;"
    ):
        ui.label(
            "folge_gui — an accessible companion interface to folge_cli. "
            "It does not modify folge_cli."
        ).classes("text-xs")

    exit_live = LiveRegion(politeness="assertive")

    async def do_exit() -> None:
        dialog = confirm_dialog(
            title="Exit folge_gui?",
            message=(
                "This stops the folge_gui server — for anyone using it right now, "
                "not just this browser tab. If a step or the pipeline is still "
                "running, let it finish first. To reopen the app afterward, run "
                "`uv run folge_gui` again."
            ),
            choices=[("Cancel", "cancel"), ("Exit", "exit")],
            urgent=True,
        )
        choice = await dialog
        if choice != "exit":
            return

        exit_live.announce("Shutting down folge_gui.")
        main.clear()
        with main:
            heading("folge_gui has been shut down", level=1, classes="text-2xl font-bold m-0")
            ui.label(
                "The server has stopped. You can close this tab now, or run "
                "`uv run folge_gui` again to reopen it."
            ).classes("text-base").style(f"color:{COLOR['text_muted']}")
        exit_btn.disable()

        ui.timer(1.0, app.shutdown, once=True)

    exit_btn.on_click(do_exit)

    return main


# ---------------------------------------------------------------------------
# Status badge (icon + color + text — never color alone)
# ---------------------------------------------------------------------------

def status_badge(initial: StepStatus = StepStatus.PENDING) -> tuple[Element, Callable[[StepStatus], None]]:
    container = ui.row().classes("items-center gap-2")
    state = {"status": initial}

    def render() -> None:
        container.clear()
        meta = STATUS_META[state["status"]]
        with container:
            ui.icon(meta["icon"]).props('aria-hidden="true"').classes(
                "animate-spin" if meta["spin"] else ""
            ).style(f"color:{meta['color']}; font-size:1.25rem;")
            ui.label(meta["text"]).classes("text-sm font-medium").style(f"color:{meta['color']}")

    def update(status: StepStatus) -> None:
        state["status"] = status
        render()

    render()
    return container, update


# ---------------------------------------------------------------------------
# Accessible command-output console
# ---------------------------------------------------------------------------

def console(*, height: str = "16rem") -> tuple[Element, Element]:
    wrapper = ui.column().classes("w-full gap-1")
    with wrapper:
        ui.label("Command output").classes("text-sm font-semibold").style(
            f"color:{COLOR['text_muted']}"
        )
        log = ui.log(max_lines=4000).classes("fg-console w-full p-3").style(
            f"height:{height}; overflow-y:auto; white-space:pre-wrap;"
        )
        log.props('role="log" aria-label="Command output" tabindex="0"')
    return wrapper, log


# ---------------------------------------------------------------------------
# Form fields, driven by FieldSpec
# ---------------------------------------------------------------------------

def render_field(spec: FieldSpec, values: dict) -> None:
    """Render one form control for *spec*, keeping *values[spec.key]* live-updated."""
    if spec.key not in values:
        values[spec.key] = False if spec.kind == "checkbox" else spec.default

    label = spec.label + (" (required)" if spec.required else "")

    if spec.kind in ("text", "password", "number"):
        el = ui.input(label=label, value=values[spec.key], placeholder=spec.placeholder)
        el.props("outlined dense" + (" type=password" if spec.kind == "password" else ""))
        el.classes("w-full")
        if spec.kind == "number":
            el.props('inputmode="decimal"')
        if spec.required:
            el.props('aria-required="true"')
        el.on_value_change(lambda e, k=spec.key: values.__setitem__(k, e.value or ""))
        if spec.help:
            help_id = f"{el.html_id}-help"
            ui.label(spec.help).props(f'id="{help_id}"').classes("text-xs -mt-1").style(
                f"color:{COLOR['text_muted']}"
            )
            el.props(f'aria-describedby="{help_id}"')

    elif spec.kind == "paths":
        el = ui.textarea(label=label, value=values[spec.key], placeholder=spec.placeholder)
        el.props("outlined dense").classes("w-full")
        el.props('rows="3"')
        if spec.required:
            el.props('aria-required="true"')
        el.on_value_change(lambda e, k=spec.key: values.__setitem__(k, e.value or ""))
        if spec.help:
            help_id = f"{el.html_id}-help"
            ui.label(spec.help).props(f'id="{help_id}"').classes("text-xs -mt-1").style(
                f"color:{COLOR['text_muted']}"
            )
            el.props(f'aria-describedby="{help_id}"')

    elif spec.kind == "select":
        display = {opt: (opt if opt else "Use configured default") for opt in spec.options}
        current = values[spec.key] or None
        el = ui.select(options=display, label=label, value=current, clearable=not spec.required)
        el.props("outlined dense").classes("w-full")
        if spec.required:
            el.props('aria-required="true"')
        el.on_value_change(lambda e, k=spec.key: values.__setitem__(k, e.value or ""))
        if spec.help:
            ui.label(spec.help).classes("text-xs -mt-1").style(f"color:{COLOR['text_muted']}")

    elif spec.kind == "multiselect":
        current_list = [x for x in values[spec.key].split(",") if x]
        el = ui.select(options=spec.options, label=label, value=current_list, multiple=True)
        el.props('outlined dense use-chips').classes("w-full")
        if spec.required:
            el.props('aria-required="true"')

        def _on_multi(e, k=spec.key):
            values[k] = ",".join(e.value or [])

        el.on_value_change(_on_multi)
        if spec.help:
            ui.label(spec.help).classes("text-xs -mt-1").style(f"color:{COLOR['text_muted']}")

    elif spec.kind == "checkbox":
        el = ui.checkbox(spec.label, value=bool(values[spec.key]))
        el.on_value_change(lambda e, k=spec.key: values.__setitem__(k, bool(e.value)))
        if spec.help:
            ui.label(spec.help).classes("text-xs -mt-1 ml-8").style(f"color:{COLOR['text_muted']}")


# ---------------------------------------------------------------------------
# Step card: one folge_cli sub-command as a self-contained, runnable form
# ---------------------------------------------------------------------------

def step_card(spec: StepSpec, *, cwd: Path) -> Element:
    values: dict = {}

    card = ui.column().classes("fg-card w-full p-5 gap-3")
    live = LiveRegion()

    with card:
        with ui.row().classes("items-center gap-2"):
            ui.icon(spec.icon).props('aria-hidden="true"').style(f"color:{COLOR['primary']}")
            heading(spec.title, level=3, classes="text-lg font-semibold m-0")
        ui.label(spec.description).classes("text-sm").style(f"color:{COLOR['text_muted']}")

        if spec.notes:
            with ui.row().classes("items-start gap-2 p-3 rounded w-full").style(
                f"background:{COLOR['bg_sunken']}"
            ):
                ui.icon("info").props('aria-hidden="true"').style(
                    f"color:{COLOR['status_info']}; margin-top:2px;"
                )
                ui.label(spec.notes).classes("text-xs").style(f"color:{COLOR['text_muted']}")

        with ui.column().classes("w-full gap-2"):
            for f in spec.fields:
                render_field(f, values)

        badge_container, update_badge = status_badge()

        with ui.row().classes("items-center gap-3 w-full flex-wrap"):
            run_btn = ui.button(f"Run: {spec.title}", icon="play_arrow").props(
                f'aria-label="Run {spec.title}"'
            )
            cancel_btn = ui.button("Cancel", icon="stop").props(
                'outline color=negative aria-label="Cancel the running command"'
            )
            cancel_btn.visible = False
            ui.space()
            badge_container

        console_wrap, log = console()
        console_wrap.visible = False

        current: dict = {"run": None}

        async def do_run() -> None:
            missing = [
                f.label for f in spec.fields
                if f.required and not str(values.get(f.key, "")).strip()
            ]
            if missing:
                msg = f"Please fill in: {', '.join(missing)}"
                ui.notify(msg, type="negative")
                live.announce(f"{spec.title}: {msg}")
                return

            while True:
                args = spec.build_args(values)
                console_wrap.visible = True
                log.clear()
                log.push(f"$ folge-cli {' '.join(args)}")

                run = ProcessRun(args=args, cwd=cwd)
                current["run"] = run
                run.on_line(log.push)

                outcome: dict = {"status": None}

                async def on_status(status: StepStatus) -> None:
                    outcome["status"] = status
                    update_badge(status)
                    if status == StepStatus.RUNNING:
                        run_btn.disable()
                        cancel_btn.visible = True
                        live.announce(f"{spec.title}: running")
                    elif status == StepStatus.SUCCESS:
                        run_btn.enable()
                        cancel_btn.visible = False
                        live.announce(f"{spec.title}: completed successfully")
                    elif status == StepStatus.ERROR:
                        run_btn.enable()
                        cancel_btn.visible = False
                        live.announce(f"{spec.title}: failed. See the command output for details.")
                    elif status == StepStatus.CANCELLED:
                        run_btn.enable()
                        cancel_btn.visible = False
                        live.announce(f"{spec.title}: cancelled")

                run.on_status(on_status)
                await run.start()

                if outcome["status"] == StepStatus.CANCELLED:
                    break  # explicit cancel — no quality gate to answer

                # Quality gate: force an explicit decision before moving on,
                # the same way pipeline.py pauses after its manual-review
                # step rather than letting a bad intermediate result flow
                # silently into the next stage.
                succeeded = outcome["status"] == StepStatus.SUCCESS
                gate = confirm_dialog(
                    title="Review before continuing" if succeeded else "Step failed",
                    message=(
                        f"{spec.title} finished. Review its output above — and any "
                        f"files it wrote, outside the GUI if you'd like — before "
                        f"moving on."
                        if succeeded else
                        f"{spec.title} failed. Check the command output above, fix "
                        f"the issue (outside the GUI if needed), and choose what to "
                        f"do next."
                    ),
                    choices=[("Re-process this step", "reprocess"), ("Continue", "continue")],
                    urgent=True,
                )
                choice = await gate
                if choice == "reprocess":
                    live.announce(f"Re-processing {spec.title}")
                    continue
                live.announce(f"Continuing past {spec.title}")
                break

        def do_cancel() -> None:
            if current["run"] is not None:
                current["run"].cancel()
                live.announce(f"Cancelling {spec.title}")

        run_btn.on_click(do_run)
        cancel_btn.on_click(do_cancel)

    return card


# ---------------------------------------------------------------------------
# Ordered status tracker (used by the Full Pipeline page)
# ---------------------------------------------------------------------------

def ordered_status_list(labels: list[str]) -> tuple[Element, Callable[[int, StepStatus, str], None]]:
    """An accessible ``<ol>`` of stage nodes. Returns an ``update(index, status, detail)`` callable."""
    container = landmark("ol", label="Pipeline stages").classes(
        "w-full flex flex-col gap-2 list-none p-0 m-0"
    )
    nodes: list[dict] = []
    with container:
        for label_text in labels:
            li = ui.element("li").classes("w-full")
            nodes.append({"li": li, "status": StepStatus.PENDING, "label": label_text, "detail": ""})

    def render_node(i: int) -> None:
        n = nodes[i]
        n["li"].clear()
        meta = STATUS_META[n["status"]]
        with n["li"]:
            with ui.row().classes("items-center gap-3 p-3 rounded w-full flex-nowrap").style(
                f"background:{COLOR['bg_raised']}; border-left: 5px solid {meta['color']};"
            ):
                ui.icon(meta["icon"]).props('aria-hidden="true"').classes(
                    "animate-spin" if meta["spin"] else ""
                ).style(f"color:{meta['color']}; font-size:1.4rem; flex-shrink:0;")
                with ui.column().classes("gap-0"):
                    ui.label(f"{i + 1}. {n['label']}").classes("font-medium")
                    detail_suffix = f" — {n['detail']}" if n["detail"] else ""
                    ui.label(f"{meta['text']}{detail_suffix}").classes("text-xs").style(
                        f"color:{COLOR['text_muted']}"
                    )

    for i in range(len(nodes)):
        render_node(i)

    def update(i: int, status: StepStatus, detail: str = "") -> None:
        nodes[i]["status"] = status
        nodes[i]["detail"] = detail
        render_node(i)

    return container, update


# ---------------------------------------------------------------------------
# Generic accessible confirmation dialog (used for pipeline input() prompts)
# ---------------------------------------------------------------------------

def confirm_dialog(
    *,
    title: str,
    message: str,
    choices: list[tuple[str, str]],
    urgent: bool = False,
) -> Element:
    """Build a modal dialog with the given ``(label, return_value)`` choice buttons.

    Await the returned dialog (``result = await dialog``) to open it and
    resolve to the chosen value once the person picks a button. ``urgent``
    marks it ``role="alertdialog"`` and prevents dismissal via Escape or an
    outside click, so a decision that matters (e.g. whether to keep running
    an unreachable-provider pipeline) can't be lost by an accidental
    dismissal the way a plain terminal prompt never could be either.
    """
    dialog = ui.dialog().props(
        f'aria-modal="true" role="{"alertdialog" if urgent else "dialog"}" '
        f'aria-labelledby="{title.lower().replace(" ", "-")}-title"'
    )
    if urgent:
        dialog.props("persistent")
    with dialog, ui.card().classes("fg-card p-5 gap-3").style("max-width:32rem;"):
        heading(title, level=2, classes="text-lg font-semibold m-0").props(
            f'id="{title.lower().replace(" ", "-")}-title"'
        )
        ui.label(message).classes("text-sm")
        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            for label, value in choices:
                ui.button(label, on_click=lambda v=value: dialog.submit(v))
    return dialog
