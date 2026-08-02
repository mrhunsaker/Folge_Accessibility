"""Full Pipeline page.

Runs the real, unmodified ``folge-cli pipeline`` command and translates its
console output into a live visual tracker. ``folge-cli pipeline`` pauses
twice for a terminal ``input()`` answer (a provider-availability
confirmation, and a mandatory review-before-rendering gate); this page
detects those exact prompts as they're printed and substitutes an accessible
modal dialog for each, then writes the chosen answer back to the
subprocess's stdin — so the pipeline behaves exactly as it does at a
terminal, just with a browser-native way to answer it.
"""

from __future__ import annotations

from nicegui import ui

from folge_cli.config import PROJECT_ROOT, PROVIDERS
from folge_gui.a11y import LiveRegion, heading
from folge_gui.components import confirm_dialog, console, ordered_status_list, page_shell, render_field
from folge_gui.process_runner import PROVIDER_CONFIRM_PROMPT, REVIEW_PROMPT, ProcessRun, StepStatus
from folge_gui.steps import ORIENTATIONS, TARGET_FORMATS, FieldSpec
from folge_gui.theme import COLOR

STAGE_LABELS: list[str] = [
    "Prerequisites check",
    "Provider check",
    "Vision processing (batch-process)",
    "Merge guide + vision results",
    "Validate schema & content",
    "Manual review pause",
    "Render Markdown",
    "Publish target formats",
]

#: Order matches STAGE_LABELS. Matched against the "complete — <label>"
#: suffix folge_cli.pipeline prints after each of its 8 counter.tick() calls.
_TICK_LABELS: list[str] = [
    "prerequisites OK",
    "provider check OK",
    "batch vision processing done",
    "merge done",
    "validation done",
    "manual review done",
    "render done",
    "all phases done",
]

_FIELDS: list[FieldSpec] = [
    FieldSpec("guide", "Guide JSON", default="guide.json", required=True),
    FieldSpec("output", "Output directory", default="output", required=True),
    FieldSpec(
        "targets", "Target formats", kind="multiselect", options=TARGET_FORMATS,
        default=",".join(TARGET_FORMATS), required=True,
        help="Everything unchecked here is skipped.",
    ),
    FieldSpec(
        "provider", "Provider", kind="select", options=[""] + PROVIDERS,
        help="Leave blank to use the provider configured in Setup.",
    ),
    FieldSpec("api_key", "API key override", kind="password",
              help="Optional — overrides the key from .env for this run only."),
    FieldSpec("orientation", "PDF orientation", kind="select", options=ORIENTATIONS, default="portrait"),
]


def build() -> None:
    main = page_shell("/pipeline")
    live = LiveRegion()

    with main:
        heading("Full Pipeline", level=1, classes="text-2xl font-bold m-0")
        ui.label(
            "Runs folge-cli pipeline end to end: prerequisites, provider check, vision "
            "processing, merge, validation, a manual-review pause, rendering, and "
            "publishing. Requires uv and Pandoc — check Setup first."
        ).classes("text-base").style(f"color:{COLOR['text_muted']}")

        values: dict = {}
        with ui.column().classes("fg-card w-full p-5 gap-2"):
            heading("Run settings", level=2, classes="text-lg font-semibold m-0")
            for f in _FIELDS:
                render_field(f, values)

        with ui.column().classes("fg-card w-full p-5 gap-3"):
            heading("Progress", level=2, classes="text-lg font-semibold m-0")
            _tracker, update_stage = ordered_status_list(STAGE_LABELS)

        with ui.row().classes("items-center gap-3"):
            run_btn = ui.button("Run full pipeline", icon="play_arrow").props(
                'aria-label="Run the full pipeline"'
            )
            cancel_btn = ui.button("Cancel", icon="stop").props(
                'outline color=negative aria-label="Cancel the running pipeline"'
            )
            cancel_btn.visible = False

        console_wrap, log = console(height="24rem")

        current: dict = {"run": None, "stage_index": -1, "dialog": None}

        def reset_tracker() -> None:
            for i in range(len(STAGE_LABELS)):
                update_stage(i, StepStatus.PENDING)
            current["stage_index"] = -1

        def mark_running(i: int, detail: str = "") -> None:
            update_stage(i, StepStatus.RUNNING, detail)
            current["stage_index"] = i

        async def on_line(line: str) -> None:
            log.push(line)
            stripped = line.strip()
            upper = stripped.upper()

            if "CHECKING PREREQUISITES" in upper:
                mark_running(0)
            elif "CHECKING PROVIDER" in upper:
                mark_running(1)
            elif upper.startswith("STEP 1-2"):
                mark_running(2)
            elif upper.startswith("STEP 3:"):
                mark_running(3)
            elif upper.startswith("STEP 4:"):
                mark_running(4)
            elif upper.startswith("STEP 4B"):
                mark_running(5)
            elif upper.startswith("STEP 5:"):
                mark_running(6)
            elif upper.startswith("STEP 6:"):
                mark_running(7)

            for i, tick_label in enumerate(_TICK_LABELS):
                if f"complete \u2014 {tick_label}" in stripped or f"complete - {tick_label}" in stripped:
                    update_stage(i, StepStatus.SUCCESS)
                    live.announce(f"{STAGE_LABELS[i]}: complete")
                    break

            if upper.startswith("FATAL") or upper.startswith("ERROR:"):
                if current["stage_index"] >= 0:
                    update_stage(current["stage_index"], StepStatus.ERROR, stripped[:150])
                live.announce(f"Pipeline error: {stripped}")

        async def on_prompt(prompt: str) -> None:
            run = current["run"]
            if run is None:
                return

            if prompt == PROVIDER_CONFIRM_PROMPT:
                update_stage(1, StepStatus.WAITING_INPUT, "provider may not be reachable")
                live.announce(
                    "The pipeline is asking whether to continue even though the selected "
                    "provider may not be reachable."
                )
                dialog = confirm_dialog(
                    title="Provider may not be available",
                    message=(
                        "folge-cli couldn't confirm the selected vision provider is "
                        "reachable. The pipeline will fail at the vision-processing step "
                        "if it truly isn't. Continue anyway?"
                    ),
                    choices=[("Stop the pipeline", "n"), ("Continue anyway", "y")],
                    urgent=True,
                )
                current["dialog"] = dialog
                answer = await dialog
                current["dialog"] = None
                await run.send_input(answer or "n")
                if run.status != StepStatus.SUCCESS:
                    update_stage(1, StepStatus.RUNNING)

            elif prompt == REVIEW_PROMPT:
                update_stage(5, StepStatus.WAITING_INPUT, "waiting for your review")
                live.announce(
                    "Manual review required. The pipeline is paused until you choose to "
                    "continue to rendering or re-verify the enriched JSON."
                )
                dialog = confirm_dialog(
                    title="Manual review required",
                    message=(
                        "Before rendering, review output/guide.enriched.json and, if it "
                        "was generated, output/manual-attention-needed.md in your file "
                        "browser. Once you're satisfied, continue to rendering — or ask "
                        "folge-cli to re-run validation on the enriched JSON first."
                    ),
                    choices=[("Re-verify enriched JSON", "R"), ("Continue to rendering", "C")],
                    urgent=True,
                )
                current["dialog"] = dialog
                answer = await dialog
                current["dialog"] = None
                await run.send_input(answer or "C")
                detail = "re-verifying…" if answer == "R" else ""
                if run.status != StepStatus.SUCCESS:
                    update_stage(5, StepStatus.RUNNING, detail)

        async def do_run() -> None:
            missing = [f.label for f in _FIELDS if f.required and not str(values.get(f.key, "")).strip()]
            if missing:
                ui.notify(f"Please fill in: {', '.join(missing)}", type="negative")
                live.announce(f"Cannot start the pipeline: missing {', '.join(missing)}")
                return

            args = ["pipeline", values["guide"], values["output"]]
            if values.get("targets"):
                args += ["--targets", values["targets"]]
            if values.get("provider"):
                args += ["--provider", values["provider"]]
            if values.get("api_key"):
                args += ["--api-key", values["api_key"]]
            if values.get("orientation"):
                args += ["--orientation", values["orientation"]]

            reset_tracker()
            log.clear()
            log.push(f"$ folge-cli {' '.join(args)}")
            run_btn.disable()
            cancel_btn.visible = True
            live.announce("Pipeline started.")

            run = ProcessRun(args=args, cwd=PROJECT_ROOT)
            current["run"] = run
            run.on_line(on_line)
            run.on_prompt(on_prompt)

            async def on_status(status: StepStatus) -> None:
                if status == StepStatus.SUCCESS:
                    run_btn.enable()
                    cancel_btn.visible = False
                    live.announce("Pipeline finished successfully.")
                elif status == StepStatus.ERROR:
                    run_btn.enable()
                    cancel_btn.visible = False
                    if current["stage_index"] >= 0:
                        update_stage(current["stage_index"], StepStatus.ERROR)
                    live.announce("Pipeline stopped with an error. Check the command output for details.")
                elif status == StepStatus.CANCELLED:
                    run_btn.enable()
                    cancel_btn.visible = False
                    if current["stage_index"] >= 0:
                        update_stage(current["stage_index"], StepStatus.CANCELLED)
                    live.announce("Pipeline cancelled.")

            run.on_status(on_status)
            await run.start()

        def do_cancel() -> None:
            if current["dialog"] is not None:
                current["dialog"].submit(None)
            if current["run"] is not None:
                current["run"].cancel()
                live.announce("Cancelling the pipeline…")

        run_btn.on_click(do_run)
        cancel_btn.on_click(do_cancel)
