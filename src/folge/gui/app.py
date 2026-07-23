"""Step-by-step wizard GUI for the Folge Vision Pipeline.

Uses NiceGUI with Catppuccin Macchiato theme. Each pipeline step runs
independently with mandatory approval gates and retry support.
"""

import json
import threading
from pathlib import Path

from nicegui import app, ui

from folge.gui.theme import CATPPUCCIN_COLORS, BASE, TEXT

PROJECT_ROOT = Path(__file__).resolve().parents[3]

STEPS = [
    {"id": "prereq", "label": "Prerequisites", "icon": "checklist"},
    {"id": "provider", "label": "Provider", "icon": "cloud"},
    {"id": "batch", "label": "Batch Process", "icon": "image"},
    {"id": "merge", "label": "Merge", "icon": "merge"},
    {"id": "review", "label": "Manual Review", "icon": "edit_note"},
    {"id": "validate", "label": "Validate", "icon": "verified"},
    {"id": "publish", "label": "Publish", "icon": "publish"},
]


class PipelineWizard:
    """Main wizard controller managing state, UI, and pipeline execution."""

    def __init__(self):
        self.current_step = 0
        self.is_running = False
        self.step_results = {}
        self.enriched_data = None
        self.enriched_path = None

        self._pending = []
        self._pending_lock = threading.Lock()

        self.step_buttons = []
        self.progress_bar = None
        self.progress_label = None
        self.status_label = None
        self.log = None
        self.run_btn = None
        self.retry_btn = None
        self.continue_btn = None

        self.guide_input = None
        self.images_input = None
        self.output_input = None
        self.pdf_check = None
        self.docx_check = None
        self.html_check = None
        self.pptx_check = None
        self.github_check = None
        self.confidence_slider = None
        self.provider_select = None
        self.api_key_input = None
        self.model_input = None
        self.base_url_input = None
        self.api_key_row = None
        self.model_row = None
        self.base_url_row = None

        self.right_panel = None
        self.codemirror_container = None
        self.attention_container = None
        self.codemirror = None

    def build(self):
        ui.colors(**CATPPUCCIN_COLORS)
        ui.query("body").classes("bg-base text-text")

        with ui.column().classes("w-full h-screen p-4 gap-2"):
            with ui.row().classes("w-full items-center"):
                ui.icon("auto_awesome", size="xl", color="primary")
                ui.label("Folge Vision Pipeline").classes("text-h4 text-weight-bold")
                ui.space()
                ui.button(
                    "Exit", icon="power_settings_new", on_click=self._on_exit
                ).props("color=negative flat")
                ui.label("v0.1").classes("text-caption text-subtext ml-2")

            ui.separator()

            with ui.row().classes("w-full gap-1 justify-center"):
                for i, step in enumerate(STEPS):
                    btn = (
                        ui.button(step["label"], icon=step["icon"])
                        .props("flat no-caps size=sm")
                        .classes("step-indicator")
                    )
                    self.step_buttons.append(btn)

            ui.separator()

            with ui.row().classes("w-full flex-1 gap-4"):
                with ui.column().classes("flex-1 gap-2 overflow-auto"):
                    self._build_config_section()

                    with ui.card().classes("w-full"):
                        ui.label("Log").classes("text-weight-bold")
                        self.log = (
                            ui.log(max_lines=200)
                            .classes("w-full font-mono text-sm")
                            .style(
                                f"background-color: {BASE}; color: {TEXT}; min-height: 150px;"
                            )
                        )

                    self.progress_bar = ui.linear_progress(
                        value=0, show_value=False
                    ).classes("w-full")
                    self.progress_label = ui.label("Ready").classes(
                        "text-center text-subtext"
                    )

                    with ui.row().classes("w-full justify-center gap-4"):
                        self.run_btn = ui.button(
                            "Run Next Step", icon="play_arrow", on_click=self._on_run
                        ).props("color=primary size=lg")
                        self.retry_btn = (
                            ui.button(
                                "Retry Step", icon="refresh", on_click=self._on_retry
                            )
                            .props("color=warning size=lg")
                            .classes("hidden")
                        )
                        self.continue_btn = (
                            ui.button(
                                "Continue to Next Step",
                                icon="arrow_forward",
                                on_click=self._on_continue,
                            )
                            .props("color=positive size=lg")
                            .classes("hidden")
                        )

                    with ui.row().classes("w-full justify-between"):
                        self.status_label = ui.label("Idle").classes("text-subtext")
                        ui.label("Folge Vision Pipeline").classes("text-subtext")

                self.right_panel = (
                    ui.card()
                    .classes("flex-1 gap-2 overflow-auto")
                    .style("min-height: 400px;")
                )
                with self.right_panel:
                    ui.label("Manual Review Editor").classes("text-h6 text-weight-bold")
                    ui.separator()
                    self.codemirror_container = ui.column().classes("w-full")
                    with self.codemirror_container:
                        ui.label(
                            "Run the Manual Review step to load the editor."
                        ).classes("text-subtext")
                    ui.separator()
                    ui.label("Manual Attention Needed").classes("text-weight-bold")
                    self.attention_container = ui.column().classes("w-full")
                    with self.attention_container:
                        ui.label("No attention results yet.").classes("text-subtext")

        self._update_step_indicators()
        ui.timer(0.1, self._drain_pending)

    def _on_exit(self):
        # Schedule stop after current event loop iteration to avoid RuntimeWarning
        ui.timer(0.1, lambda: app.stop(), once=True)

    def _build_config_section(self):
        with ui.card().classes("w-full"):
            ui.label("Step 0: Configure").classes("text-h6 text-weight-bold")

            with ui.column().classes("w-full gap-2"):
                with ui.row().classes("w-full items-center gap-2"):
                    self.guide_input = ui.input(
                        label="Guide JSON",
                        placeholder="guide.json",
                        on_change=self._validate_config,
                    ).classes("flex-grow")
                    ui.button(
                        "Browse",
                        on_click=lambda: self._pick_file(
                            self.guide_input, "JSON files (*.json)"
                        ),
                    ).props("flat color=info")

                with ui.row().classes("w-full items-center gap-2"):
                    self.images_input = ui.input(
                        label="Images Directory",
                        placeholder="images/",
                        value=str(PROJECT_ROOT / "images"),
                        on_change=self._validate_config,
                    ).classes("flex-grow")
                    ui.button(
                        "Browse", on_click=lambda: self._pick_folder(self.images_input)
                    ).props("flat color=info")

                with ui.row().classes("w-full items-center gap-2"):
                    self.output_input = ui.input(
                        label="Output Directory",
                        placeholder="output/",
                        value=str(PROJECT_ROOT / "output"),
                        on_change=self._validate_config,
                    ).classes("flex-grow")
                    ui.button(
                        "Browse", on_click=lambda: self._pick_folder(self.output_input)
                    ).props("flat color=info")

                ui.separator()

                ui.label("Target Formats:").classes("text-weight-bold")
                with ui.row().classes("gap-4"):
                    self.pdf_check = ui.checkbox("PDF", value=True)
                    self.docx_check = ui.checkbox("DOCX", value=True)
                    self.html_check = ui.checkbox("HTML", value=True)
                    self.pptx_check = ui.checkbox("PPTX", value=True)
                    self.github_check = ui.checkbox("GitHub", value=False)

                with ui.row().classes("w-full gap-8 items-center"):
                    with ui.column():
                        ui.label("Min Confidence:").classes("text-weight-bold")
                        self.confidence_slider = ui.slider(
                            min=0, max=1, step=0.05, value=0.8
                        ).classes("w-40")
                        ui.label().bind_text_from(
                            self.confidence_slider, "value", lambda v: f"{v:.2f}"
                        )
                    with ui.column():
                        ui.label("Vision Provider:").classes("text-weight-bold")
                        self.provider_select = ui.select(
                            [
                                "ollama",
                                "lmstudio",
                                "llamacpp",
                                "openrouter",
                                "openai",
                                "gemini",
                                "claude",
                            ],
                            value="ollama",
                            label="Provider",
                            on_change=self._on_provider_change,
                        ).classes("w-48")

                with ui.column().classes("w-full gap-2"):
                    self.api_key_row = ui.row().classes(
                        "w-full items-center gap-2 hidden"
                    )
                    with self.api_key_row:
                        self.api_key_input = ui.input(
                            label="API Key",
                            password=True,
                            password_toggle_button=True,
                            placeholder="sk-...",
                        ).classes("flex-grow")

                    self.model_row = ui.row().classes("w-full items-center gap-2")
                    with self.model_row:
                        self.model_input = ui.input(
                            label="Model Override (optional)",
                            placeholder="Leave empty for provider default",
                        ).classes("flex-grow")

                    self.base_url_row = ui.row().classes("w-full items-center gap-2")
                    with self.base_url_row:
                        self.base_url_input = ui.input(
                            label="Base URL Override (optional)",
                            placeholder="Leave empty for provider default",
                        ).classes("flex-grow")

    def _pick_file(self, target_input, filter_str=""):
        self._open_browser(target_input, mode="file", pattern="*.json")

    def _pick_folder(self, target_input):
        self._open_browser(target_input, mode="dir")

    def _open_browser(self, target_input, mode="file", pattern="*.json"):
        dialog = ui.dialog()

        current_val = target_input.value or ""
        try:
            start = Path(current_val) if current_val else PROJECT_ROOT
            if not start.exists():
                start = PROJECT_ROOT
            if not start.is_dir():
                start = start.parent
        except Exception:
            start = PROJECT_ROOT

        def navigate_to(directory: Path, container):
            container.clear()
            with container:
                if directory != directory.parent:
                    with ui.row().classes(
                        "w-full items-center gap-2 cursor-pointer hover:bg-surface0 p-2 rounded"
                    ):
                        ui.icon("arrow_upward", color="info")
                        up_label = ui.label(str(directory.parent)).classes(
                            "text-info flex-grow"
                        )
                        up_label.on(
                            "click", lambda: navigate_to(directory.parent, container)
                        )

                ui.label(f"\U0001f4c1 {directory}").classes("text-weight-bold w-full")

                try:
                    entries = sorted(
                        directory.iterdir(),
                        key=lambda p: (not p.is_dir(), p.name.lower()),
                    )
                except PermissionError:
                    ui.label("Permission denied").classes("text-negative w-full")
                    return

                for entry in entries:
                    if entry.name.startswith("."):
                        continue
                    if mode == "file" and not entry.is_file():
                        continue
                    if mode == "dir" and not entry.is_dir():
                        continue
                    if mode == "file" and pattern and not entry.match(pattern):
                        continue

                    with ui.row().classes(
                        "w-full items-center gap-2 cursor-pointer hover:bg-surface0 p-2 rounded"
                    ):
                        icon = "folder" if entry.is_dir() else "description"
                        color = "warning" if entry.is_dir() else "text"
                        ui.icon(icon, color=color)
                        lbl = ui.label(entry.name).classes("flex-grow")

                        if entry.is_dir():
                            lbl.on(
                                "click", lambda e, p=entry: navigate_to(p, container)
                            )
                        else:
                            lbl.on("click", lambda e, p=entry: _select(p))

        def _select(path: Path):
            target_input.value = str(path)
            dialog.close()

        with dialog, ui.card().classes("w-full max-w-2xl"):
            ui.label("Browse Files").classes("text-h6")
            ui.separator()
            file_list = (
                ui.column().classes("w-full overflow-auto").style("max-height: 400px;")
            )
            ui.separator()
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=dialog.close).props("flat")

        navigate_to(start, file_list)
        dialog.open()

    def _validate_config(self, e=None):
        guide = self.guide_input.value if self.guide_input else ""
        return bool(guide.strip())

    def _get_targets(self):
        targets = []
        if self.pdf_check and self.pdf_check.value:
            targets.append("pdf")
        if self.docx_check and self.docx_check.value:
            targets.append("docx")
        if self.html_check and self.html_check.value:
            targets.append("html")
        if self.pptx_check and self.pptx_check.value:
            targets.append("pptx")
        if self.github_check and self.github_check.value:
            targets.append("github")
        return targets

    def _update_step_indicators(self):
        for i, btn in enumerate(self.step_buttons):
            if i < self.current_step:
                if self.step_results.get(i, (True,))[0]:
                    btn.props("color=positive")
                else:
                    btn.props("color=negative")
            elif i == self.current_step:
                btn.props("color=primary")
            else:
                btn.props("color=")

    def _log(self, message):
        if self.log:
            self.log.push(message)

    def _set_progress(self, value, text=""):
        if self.progress_bar:
            self.progress_bar.value = value
        if self.progress_label:
            self.progress_label.text = text or f"{int(value * 100)}%"

    def _set_status(self, text):
        if self.status_label:
            self.status_label.text = text

    def _show_buttons(self, run=False, retry=False, continue_=False):
        if self.run_btn:
            self.run_btn.visible = run
        if self.retry_btn:
            self.retry_btn.visible = retry
        if self.continue_btn:
            self.continue_btn.visible = continue_

    def _schedule(self, fn):
        with self._pending_lock:
            self._pending.append(fn)

    def _drain_pending(self):
        while True:
            with self._pending_lock:
                if not self._pending:
                    return
                batch = self._pending[:]
                self._pending.clear()
            for fn in batch:
                try:
                    fn()
                except Exception:
                    pass

    def _on_provider_change(self, e):
        provider = e.value if e else "ollama"
        local_providers = {"ollama", "lmstudio", "llamacpp"}
        is_local = provider in local_providers
        if self.api_key_row:
            self.api_key_row.visible = not is_local
        if self.base_url_row:
            self.base_url_row.visible = is_local

    def _on_progress(self, message, current=0, total=0):
        self._schedule(
            lambda m=message, c=current, t=total: (
                self._log(m),
                self._set_progress(c / t if t else 0, f"{c}/{t}" if t else ""),
            )
        )

    def _run_prereq(self):
        from folge.pipeline.prerequisites import check

        ok, issues = check(on_progress=self._on_progress)
        self.step_results[0] = (ok, issues)
        return ok

    def _run_provider(self):
        from folge.pipeline.provider import check

        provider = self.provider_select.value if self.provider_select else "ollama"
        api_key = self.api_key_input.value if self.api_key_input else None
        ok, msg = check(
            provider_name=provider, api_key=api_key, on_progress=self._on_progress
        )
        self.step_results[1] = (ok, msg)
        return ok

    def _run_batch(self):
        from folge.pipeline.batch_process import run

        guide = Path(self.guide_input.value)
        images = Path(self.images_input.value)
        output = Path(self.output_input.value)
        provider = self.provider_select.value if self.provider_select else "ollama"
        api_key = self.api_key_input.value if self.api_key_input else None
        model = self.model_input.value if self.model_input else None
        base_url = self.base_url_input.value if self.base_url_input else None
        vision_path = run(
            guide,
            images,
            output / "vision-results.json",
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            on_progress=self._on_progress,
        )
        self.step_results[2] = (True, vision_path)
        return True

    def _run_merge(self):
        from folge.pipeline.merge import run

        guide = Path(self.guide_input.value)
        output = Path(self.output_input.value)
        vision = output / "vision-results.json"
        enriched = run(
            guide, vision, output / "guide.enriched.json", on_progress=self._on_progress
        )
        self.enriched_path = enriched
        self.step_results[3] = (True, enriched)
        return True

    def _run_review(self):
        if not self.enriched_path or not self.enriched_path.exists():
            self._log("ERROR: guide.enriched.json not found")
            return False

        with open(self.enriched_path, "r", encoding="utf-8") as f:
            self.enriched_data = json.load(f)

        self._schedule(lambda: self._show_code_editor(self.enriched_data))
        self._schedule(lambda: self._load_attention_results())

        self.step_results[4] = (True, self.enriched_data)
        return True

    def _show_code_editor(self, data):
        self.codemirror_container.clear()
        with self.codemirror_container:
            ui.label("Edit guide.enriched.json").classes("text-subtext")
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            self.codemirror = (
                ui.codemirror(
                    value=json_str,
                    language="json",
                    theme="githubDark",
                    line_wrapping=True,
                )
                .classes("w-full")
                .style("height: 400px;")
            )

            with ui.row().classes("w-full justify-center gap-4 mt-2"):
                ui.button(
                    "Save Changes", icon="save", on_click=self._save_from_codemirror
                ).props("color=info")
                ui.button(
                    "Continue to Validation",
                    icon="arrow_forward",
                    on_click=self._on_continue,
                ).props("color=positive size=lg")

    def _save_from_codemirror(self):
        if not self.codemirror or not self.enriched_path:
            return
        try:
            content = self.codemirror.value
            self.enriched_data = json.loads(content)
            self._save_enriched()
        except json.JSONDecodeError as ex:
            self._log(f"ERROR: Invalid JSON — {ex}")

    def _load_attention_results(self):
        if not self.output_input:
            return

        output_dir = Path(self.output_input.value)
        attention_file = output_dir / "manual-attention-needed.md"

        self.attention_container.clear()
        with self.attention_container:
            if attention_file.exists():
                with open(attention_file, "r", encoding="utf-8") as f:
                    md_content = f.read()
                ui.markdown(md_content).classes("w-full text-sm")
                ui.label(f"Source: {attention_file}").classes(
                    "text-caption text-subtext mt-2"
                )
            else:
                ui.label("No manual-attention-needed.md found.").classes("text-subtext")
                ui.label(f"Expected at: {output_dir}").classes(
                    "text-caption text-subtext"
                )

    def _save_enriched(self):
        if self.enriched_path and self.enriched_data:
            with open(self.enriched_path, "w", encoding="utf-8") as f:
                json.dump(self.enriched_data, f, indent=2, ensure_ascii=False)
            self._log(f"Saved changes to {self.enriched_path.name}")

    def _run_validate(self):
        from folge.pipeline.validate import run

        output = Path(self.output_input.value)
        confidence = self.confidence_slider.value if self.confidence_slider else 0.8
        ok, issues = run(
            self.enriched_path,
            min_confidence=confidence,
            output_dir=output,
            on_progress=self._on_progress,
        )
        self.step_results[5] = (ok, issues)
        return ok

    def _run_publish(self):
        from folge.pipeline.publish import run

        output = Path(self.output_input.value)
        targets = self._get_targets()
        published = run(
            self.enriched_path, targets, output, on_progress=self._on_progress
        )
        self.step_results[6] = (True, published)
        return True

    STEP_RUNNERS = {
        0: "_run_prereq",
        1: "_run_provider",
        2: "_run_batch",
        3: "_run_merge",
        4: "_run_review",
        5: "_run_validate",
        6: "_run_publish",
    }

    def _execute_step(self, step_index):
        runner_name = self.STEP_RUNNERS.get(step_index)
        if not runner_name:
            return

        runner = getattr(self, runner_name)
        try:
            ok = runner()
            if ok:
                self._schedule(
                    lambda: (
                        self._log(f"Step {step_index} complete"),
                        self._show_buttons(run=False, retry=False, continue_=True),
                        self._set_status(
                            f"Step {step_index + 1}/7 — Waiting for approval"
                        ),
                    )
                )
            else:
                self._schedule(
                    lambda: (
                        self._log(f"Step {step_index} failed"),
                        self._show_buttons(run=False, retry=True, continue_=False),
                        self._set_status(
                            f"Step {step_index + 1}/7 — Failed (click Retry)"
                        ),
                    )
                )
        except Exception as ex:
            error_msg = str(ex)
            self._schedule(
                lambda msg=error_msg: (
                    self._log(f"Step {step_index} error: {msg}"),
                    self._show_buttons(run=False, retry=True, continue_=False),
                    self._set_status(f"Step {step_index + 1}/7 — Error (click Retry)"),
                )
            )

    def _on_run(self):
        if self.current_step == 0 and not self._validate_config():
            self._log("ERROR: Please fill in Guide JSON path")
            return

        self._show_buttons(run=False, retry=False, continue_=False)
        self._set_status(f"Step {self.current_step + 1}/7 — Running...")
        self._log(
            f"--- Starting Step {self.current_step + 1}: {STEPS[self.current_step]['label']} ---"
        )
        self._update_step_indicators()

        thread = threading.Thread(
            target=self._execute_step,
            args=(self.current_step,),
            daemon=True,
        )
        thread.start()

    def _on_retry(self):
        self._show_buttons(run=False, retry=False, continue_=False)
        self._set_status(f"Step {self.current_step + 1}/7 — Retrying...")
        self._log(
            f"--- Retrying Step {self.current_step + 1}: {STEPS[self.current_step]['label']} ---"
        )

        thread = threading.Thread(
            target=self._execute_step,
            args=(self.current_step,),
            daemon=True,
        )
        thread.start()

    def _on_continue(self):
        self.current_step += 1
        if self.current_step >= len(STEPS):
            self._log("=== Pipeline Complete ===")
            self._set_status("Complete")
            self._show_buttons(run=False, retry=False, continue_=False)
            self._set_progress(1.0, "100% — Complete")
            self._update_step_indicators()
            return

        self._log(
            f"\n--- Step {self.current_step + 1}: {STEPS[self.current_step]['label']} ---"
        )
        self._set_status(f"Step {self.current_step + 1}/7 — Ready")
        self._show_buttons(run=True, retry=False, continue_=False)
        self._update_step_indicators()


def main():
    wizard = PipelineWizard()

    @ui.page("/")
    def index():
        wizard.build()

    ui.run(
        dark=True,
        port=8080,
        title="Folge Vision Pipeline",
        favicon="🎨",
        show=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
