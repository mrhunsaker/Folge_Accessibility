<!--
 Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
 SPDX-License-Identifier: Apache-2.0
-->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Calendar Versioning](https://calver.org/) (`YYYY.M.D`).

## [Unreleased]

### Added

- **Manual step numbering** — each step in `guide.enriched.json` carries a
  `step_label` field that controls the rendered "Step X" heading. It is a
  **merge-managed** field independent of `guide.json`: the merge step seeds
  every step with its auto-number (`"Step 1"`, `"Step 2"`, ...) and preserves
  any hand-edited values across re-merges by `step_id`. Set
  `"step_label": "Step 1"` to manually number a step, `"step_label": ""`
  (empty string) for no step prefix, or any custom text. The `##` heading
  level stays in the render template, so label values contain only the text
  (e.g. `"Step 1"`, not `"## Step 1"`).
- **Custom vision prompts** — `folge-cli batch-process` (and `folge-cli
  pipeline`) accept `--prompt <name>` to select an alternate prompt generator
  for the vision model. Prompt modules live in `src/folge_cli/prompts/` and
  each exposes `generate_prompt(step, guide_title, previous_step=None,
  next_step=None)`. Available names are auto-discovered and offered as
  `choices`, so any new module added to that folder automatically becomes a
  valid `--prompt`. Without the flag, the built-in default prompt from
  `batch_process.py` is used unchanged.
- **`folge-cli new-prompt <name>`** — scaffolds a new custom vision prompt
  module into `src/folge_cli/prompts/<name>.py` with the correct
  `generate_prompt` signature and the standard JSON-schema prompt template,
  so a new prompt can be added without hand-typing boilerplate (and without
  misspelling the function name). The name is validated/normalized to a safe
  identifier, existing modules are not overwritten unless `--force` is passed,
  and the created module is immediately auto-registered as a `--prompt` choice.
  Bundled example: `brailleblaster`.
- **`--skip-vision` / reuse existing enriched JSON** — `folge-cli pipeline`
  now detects an existing `<guide>.enriched.json` in the output directory
  and prompts to reuse it, skipping vision processing and merge (stages
  1-3) entirely and resuming at validation and manual review. Pass
  `--skip-vision` to do this non-interactively; useful after fixing
  something by hand in the enriched JSON, or after a run that succeeded at
  vision but failed later in the pipeline.
- **`--first-step <stage>`** — `folge-cli pipeline` can now start from any
  step instead of the beginning, so you can pick up where an interrupted
  run left off (e.g. after a power outage) or regenerate output from a
  given stage without replaying everything before it. Valid values match
  the stage numbers shown in the pipeline's step headers: `1` (batch
  vision, stages 1-2), `3` (merge), `4` (validate), `4b` (manual review),
  `5` (render), `5b` (metadata), `6` (publish). Every earlier stage and its
  interactive prompts are skipped and the step counter is adjusted to
  account for the skipped phases. Starting at `4` or later requires an
  existing `<guide>.enriched.json` and errors out with a clear message if
  it is missing, so you cannot accidentally resume without prerequisite
  data.
- **Resume discovers artifacts from disk** — when `--first-step` is used,
  the pipeline locates its intermediate files (enriched JSON, vision
  results, Markdown, metadata YAML) by their **on-disk names** in the
  output directory rather than assuming they were created on the current
  date. This means a project last run on an earlier day (e.g.
  `Headings-2026-08-28.enriched.json`) resumes correctly. In particular,
  `--first-step 3` **reuses** an existing `vision-results.json` (it does
  not regenerate vision data) and errors with a clear message if that file
  is missing.
- **`table` UI control type** — `ui_controls[].type` now accepts `table`
  (alongside the existing `button`, `text_field`, `dropdown`, `checkbox`,
  `radio`, `slider`, `navigation`, `menu`, `tab`, `icon`, `link`, `other`)
  in both `VALID_UI_TYPES` (`batch_process.py`) and the JSON Schema `enum`
  (`validate_schema.py`) — the vision model was correctly identifying
  tables in "Review Heading Plan" screenshots but had no valid slot to put
  that classification in.
- **Troubleshooting section in README** — covers the WeasyPrint-on-Windows
  library error, vision-model token-truncation errors, and unrecognized
  `ui_controls` types.
- **Unified format registry** — `src/folge_cli/formats.py` is now the single
  source of truth for output formats, replacing the duplicated `TARGETS`
  dicts in `pipeline.py` and `publish.py`.
- **Every pandoc writer supported** — `pipeline`/`publish` now export *all*
  formats the installed pandoc supports by default (70+ writers), not just 16.
  Writers missing from that pandoc version (e.g. `ansi`, `bbcode*`, `djot`,
  `t2t`, `vimdoc`, `xml` on 3.1.x) are skipped with a warning.  Use
  `--targets`/the `targets` positional to narrow the list.
- **`multimarkdown` → `markdown_mmd`** — the old target errored ("Unknown
  output format"); the correct pandoc writer is `markdown_mmd` (output
  `guide_mmd.md`, unchanged).
- **Collision-free filenames** — new/colliding formats are written as
  `guide_<abbrev>.<ext>` (e.g. `guide_cmx.md`, `guide_epub2.epub`,
  `guide_docbook4.xml`); primary formats keep `guide.docx`-style names.
- **`--standalone` everywhere** — every pandoc invocation now emits a full
  standalone document, so all formats carry the `metadata.yaml` document
  metadata (also now generated by `pipeline.py`).
- **`--verbose` + `pandoc.log`** — all pandoc runs pass `--verbose` and their
  stdout/stderr is appended to `<output>/pandoc.log` under per-format headers
  (timestamp, command, exit code).

### Fixed

- **Crash on steps with no screenshot** — a step with no `image` (e.g. a
  text-only closing summary) resolved `image_dir / ""` to the images
  *directory itself*, which `PIL.Image.open()` then tried to open as a
  file, raising `PermissionError` on Windows (`IsADirectoryError` on
  Linux/macOS) and aborting the whole batch. `process_single_step` now
  checks for a missing/empty `image` up front and returns a `vision_error`
  for that step instead of processing it.
- **Empty vision result bypassed the `vision_error` exemption** — the fix
  above initially returned a bare result with no `vision_error` key, which
  `merge.py` then wrote out as an *empty but present* `vision: {}` object.
  `validate_content.py`'s existing `vision_error` skip-check never
  triggered, so it flagged missing `alt_text`/`long_description`/
  `confidence` as hard errors. The no-image guard now sets `vision_error`
  explicitly so both `merge.py` and `validate_content.py` handle it via
  their existing exemption path.
- **One failing vision step could discard an entire successful batch** —
  `process_guide`'s `as_completed` loop called `future.result()`
  unguarded, so any unexpected exception from a worker thread (including
  ones raised before a step's own retry loop, e.g. in image decoding)
  propagated and crashed `process_guide` before results were ever written
  to disk — discarding every already-completed step in the process. Each
  future's result is now resolved inside a `try/except`, degrading a
  single unexpected failure to a `vision_error` on that one step.
- **`generate-manual-attention` flagged text-only steps as needing manual
  alt text** — after the fix above, any step with no image legitimately
  carries a `vision_error`, but `generate_manual_attention.py` listed
  every `vision_error` step as needing a manually-written `alt_text`/
  `long_description`. It now also checks `step.get("image")`, so only
  steps that have a real screenshot but failed vision processing show up
  on the manual-review list.
- **Confusing `'NoneType' object has no attribute 'strip'` on vision
  responses** — reasoning models (e.g. Kimi K3, the OpenRouter default)
  can return `finish_reason: "length"` with `message.content: null` when
  they exhaust `max_tokens` on internal reasoning before writing an
  answer. `parse_json_response()` assumed a string and crashed with an
  opaque `AttributeError`. The response handler now checks for `None`
  content immediately after extraction and raises a clear error
  referencing `finish_reason` instead.

### Changed

- **HTML-escape `long_description` in `guide.enriched.json`** — the merge
  step now HTML-escapes the vision model's `long_description` (via
  `html.escape(..., quote=True)`) before writing the enriched JSON, so tags
  embedded in the description — e.g. `<h4>` — render as literal text in
  Pandoc/WeasyPrint and other HTML intermediaries instead of being interpreted
  as markup (which previously opened an unmatched `<h3>`/`<h4>` heading).
  Only the `long_description` field is escaped; `alt_text`, `ocr_text`, and
  `ui_controls` are left untouched.
- **Default vision `max_tokens` raised from `16384` to `32768`** — gives
  reasoning models more headroom to finish internal reasoning and still
  produce an answer on complex screenshots, reducing truncated/empty
  responses.
- **Image-path existence check uses `is_file()` instead of `exists()`** —
  defense-in-depth so that if a step's `image` path ever resolves to a
  directory again, it fails safely as "Image not found" instead of
  reaching `PIL.Image.open()`.

### Removed

- **Docker/Podman documentation** — the `## Container Usage` section
  (`### Docker`, `### Podman`) and the "Container workflow only"
  directory-tree notes have been removed from `README.md`. The
  `docker-compose.yml`, `podman-compose.yml`, `Containerfile`, and
  `Dockerfile` themselves are untouched — say the word if you want those
  removed from the repo too.

## [2026.8.2] - 2026-08-02

### Added

- **`folge_gui`** — an accessible, browser-based front end for the pipeline,
  built with [NiceGUI](https://nicegui.io) in a Catppuccin Latte color scheme,
  living in `src/folge_gui` alongside `src/folge_cli`. It is a *parallel,
  additive companion* to `folge-cli`: every command it runs is launched as a
  real subprocess (the same `folge-cli` you'd run at a terminal) and
  `src/folge_cli` is never imported for execution and never modified.
  Three pages: **Setup** (prerequisite/provider checks, `.env` and
  `config.yaml` editors), **Steps** (one card per `folge-cli` sub-command with
  a post-run quality gate), and **Full Pipeline** (8-stage progress tracker
  that swaps the CLI's two terminal prompts for accessible dialogs).
- **`uv run folge-gui`** — new `folge-gui` console script entry point in
  `src/folge_gui/pyproject.toml`, alongside the existing `folge_gui` script.
  Both now launch `folge_gui.app:main` on port 8765.
- **uv workspace member** — `src/folge_gui` is registered in
  `[tool.uv.workspace]` in the repository root `pyproject.toml`, so it shares
  one `uv.lock` and one `.venv` with `folge-cli` (install with
  `uv sync --all-packages`).
- **GUI documentation** — `docs/gui.md` (MkDocs page), `src/folge_gui/README.md`,
  and a "Graphical Interface" section in the top-level `README.md`.
- **WCAG 2.2 AA accessibility** — real heading levels, skip link, labeled
  form controls, ARIA live status announcements, `role="log"` command output,
  visible focus indicators, `prefers-reduced-motion` support, and
  non-dismissible modal dialogs for interactive prompts. Contrast-safe "ink"
  variants of the Catppuccin Latte accents that fall short of 4.5:1.

## [2026.7.31] - 2026-07-31

### Added

- **`jan` provider** — Jan (local, OpenAI-compatible) is now supported as a
  local LLM provider, using the same settings shape as `lmstudio` and serving
  at `http://localhost:1337/v1`.
- **`metadata` subcommand** — `folge-cli metadata` derives accessible-document
  metadata (title, author, subject, keywords, language, structure tags,
  bookmarks, and security settings) from the guide JSON and writes a
  Pandoc-compatible `metadata.yaml` that is embedded into every output format
  via `--metadata-file`.
- **PDF metadata and security hardening** — `--apply-pdf` embeds the PDF Info
  dictionary (title, author, subject, keywords, creator) and document language
  with PyMuPDF, and strips restrictive security handlers so text copying and
  extraction are always allowed for assistive technology.
- **Metadata compliance check** — `--check --strict` validates metadata against
  accessible-PDF best practices (no generic titles, author, subject, keywords,
  language, bookmarks for 10+ page documents) and exits with status 1 on
  violations.
- **New `config.yaml` defaults** — `project.author` and `project.keywords`
  provide the author and keyword fallbacks used by `folge-cli metadata`.

### Changed

- **`publish`** now generates `metadata.yaml` during the pipeline and passes it
  to every Pandoc target; generated PDFs are post-processed to embed the
  metadata and guarantee text copying is allowed.
- **Local LLM API key handling** — `lmstudio`, `jan`, and `llamacpp` are probed
  through their OpenAI-compatible `/v1` endpoints (`/chat/completions`,
  `/v1/models`) instead of Ollama-only routes, so they run with no API key. An
  optional `*_API_KEY` is sent only when configured, for servers that have API
  auth enabled.

## [2026.7.30] - 2026-07-30

### Added

- **HTML cleaning** — `_clean_html()` strips HTML tags and decodes entities from
  step body text in exported guides.
- **Robust JSON parsing** — `parse_json_response()` now handles markdown fences,
  wrapped arrays, trailing commas, unquoted keys, single-quoted strings, and
  truncated JSON with missing closing delimiters.
- **Debug logging** of failed API responses to
  `output/debug_responses/failed_{step_id}_attempt{N}.txt`.
- **Temperature cycling** across retries (0.1 → 0.5 → 0.7) to improve parsing
  success on subsequent attempts.
- **`finish_reason` tracking** in step results.
- **Warn logging** on retry attempts for visible feedback during processing.

### Changed

- **`config.yaml` Ollama timeout** increased from 600s to 1800s.
- **`max_tokens`** increased from 8192 to 16384 for richer model output.
- **`num_predict`** set to 16384 for local providers.
- **Vision prompt** rewritten with explicit JSON structure example, clearer
  rules, and instruction to return a single JSON object without code fences.

## [2026.7.28] - 2026-07-28

### Added

- **`--version` flag** on `folge-cli` and all standalone scripts (`pipeline.py`,
  `batch_process.py`, `publish.py`) — prints version and exits, matching standard
  Linux CLI conventions.
- **`--orientation portrait|landscape` flag** for PDF page orientation (default:
  portrait). Switches between Letter Portrait and Letter Landscape page sizes.
- **11 new output formats** via Pandoc: typst (`.typ`), asciidoc (`.adoc`),
  beamer (`_beamer.pdf`), commonmark (`_cm.md`), GitHub-flavored Markdown
  (`_gh.md`), MultiMarkdown (`_mmd.md`), DocBook (`.xml`), EPUB (`.epub`),
  ODT (`.odt`), reStructuredText (`.rst`), and LaTeX (`.tex`).
- **Data-driven `TARGETS` registry** in `pipeline.py` and `publish.py` for
  output format configuration — replaces repetitive if-blocks and makes adding
  new formats trivial.
- **Self-contained HTML output** via `--standalone --embed-resources` Pandoc flags.
- **Self-contained EPUB output** via `--epub-embed-resources=true` Pandoc flag.
- **`@font-face` CSS** for Atkinson Hyperlegible Next (text) and
  AtkynsonMonoNerdFont (code/monospace) in `templates/folge.css`.
- **Page orientation CSS files**: `templates/letter-portrait.css` and
  `templates/letter-landscape.css` for PDF page layout control.
- **Font files bundled** in `fonts/` directory (Atkinson Hyperlegible Next
  variable weight, AtkinsonHyperlegibleMono static OTF).

### Changed

- **PDF default orientation** is now Letter Portrait (was Letter Landscape).
- **`config.yaml` `project.version`** is now derived dynamically from
  `_version.py` via `load_yaml_config()` — removed hardcoded value.
- **Subprocess output** in `run_cmd()` streams to terminal in real-time
  (removed `capture_output=True` from `pipeline.py` and `publish.py`).
- **Publish section refactored** to use `TARGETS` registry loop instead of
  individual if-blocks for each output format.
- **CLI help text** updated to list all 16 output formats in `--targets`.
- **Default targets** now include all 16 output formats when `--targets` is
  not specified (was `pdf,docx,html,pptx`).

### Fixed

- **Beamer output extension** corrected from Cyrillic characters
  (`_beamер.pdf`) to ASCII (`_beamer.pdf`) in TARGETS registry and config.yaml.

### Removed

- **`templates/landscape.css`** — replaced by `letter-landscape.css` and
  `letter-portrait.css` for explicit orientation control.

## [2026.7.25] - 2026-07-25

### Added

- **Seven provider support**: ollama (default), lmstudio, llamacpp, openrouter,
  openai, gemini, and anthropic — all fully wired through `.env`, `config.yaml`,
  and CLI `--provider` flags.
- **Unified CLI entry point** (`folge-cli`): single command with nine subcommands
  (`pipeline`, `batch-process`, `merge`, `validate-schema`, `validate-content`,
  `validate-pdf`, `render`, `publish`, `generate-manual-attention`).
- **`src/folge_cli/` Python package**: proper installable package with
  `pyproject.toml`, `[project.scripts]` entry point, and `src` layout.
- **NumPy-style docstrings** on all public functions and classes across every
  module in the package.
- **Progress counters** (`StepCounter`) in both `batch_process.py` and
  `pipeline.py` showing running "X/Y steps complete" status.
- **Manual review pause** in the pipeline after validation — prompts operator
  to `(C)ontinue` or `(R)eVerify` before rendering.
- **Seven-phase pipeline progress** tracking: prerequisites, provider check,
  batch vision, merge, validate, manual review, render+publish.
- **PyInstaller build configuration** (`pyinstaller/folge-cli.spec`): builds a
  single-file executable for Windows, macOS, and Linux. Bundles Lua filters,
  templates, config.yaml, and schemas. Individual subcommands are available
  as standalone executables (not the full `pipeline` command).
- **GitHub Actions release workflow** (`.github/workflows/release.yml`):
  triggers on `v*` tags, builds on all three platforms, creates a GitHub
  release with platform-specific artifacts (`.zip` for Windows/Linux,
  `.tar.gz` for macOS).
- **`BUNDLED_DIR` and `get_bundled_path()`** in `config.py`: supports
  PyInstaller-frozen executables by resolving data file paths via
  `sys._MEIPASS`.
- **Dynamic Lua filter path resolution** in `pipeline.py`: Pandoc commands
  resolve `--lua-filter` and `--css` paths via `get_bundled_path()` instead
  of hardcoded relative paths, working in both source and bundled modes.
- **CHANGES.md** — this changelog file.
- **Community governance documentation**: updated CONTRIBUTING.md, STYLE.md,
  SECURITY.md, GOVERNANCE_ENFORCEMENT.md, and CODE_OF_CONDUCT.md for this project.
- **Apache 2.0 license headers** on all `.py` files for file-level license clarity.

### Changed

- **`PROVIDER` env var** now accepts all seven provider names (was ollama-only).
- **`OLLAMA_TIMEOUT`** changed from empty/default 300 to 600 seconds.
- **`MIN_CONFIDENCE`** set to `0.7` (replaced per-provider `*_CONFIDENCE` env vars).
- **`pdfinfo` detection** uses `shutil.which()` instead of hardcoded
  `/usr/bin/pdfinfo`, and passes `-v` (not `--version`).
- **Anthropic auth** uses `x-api-key` header + `anthropic-version` header
  (not Bearer token).
- **Gemini endpoint** uses OpenAI-compatible
  `https://generativelanguage.googleapis.com/v1beta/openai` URL.
- **`envTemplate`** simplified to API key placeholders only.
- **Pipeline `check_provider()`** now handles all seven providers (local via curl
  check, cloud via API key presence).
- **`publish.py`** forwards API keys for all cloud providers (not just openrouter).
- **`pyproject.toml`** updated with `python-dotenv>=1.0` dependency, `src` layout
  discovery, and `folge-cli` entry point.
- README.md fully rewritten to reflect current project architecture and providers.

### Fixed

- **`pdfinfo` path detection** on systems where `pdfinfo` is not at
  `/usr/bin/pdfinfo` (uses `shutil.which`).
- **`pdfinfo` flag** corrected from `--version` to `-v`.
- **PyInstaller spec path resolution**: PyInstaller changes `cwd` to the
  spec file's directory before executing it.  All paths in the spec now use
  `PROJECT_ROOT = os.path.dirname(os.getcwd())` to resolve source files,
  data files, and schema directories correctly.
- **MkDocs icon rendering**: added `pymdownx.emoji` extension to
  `mkdocs.yml` — `:material-*:` and `:octicons-*:` shortcodes now render as
  inline SVGs instead of broken links.

## [2026.7.18] - 2026-07-18

### Added

- Initial pipeline with Ollama Vision AI enrichment.
- Schema validation, content validation, PDF/UA validation.
- Markdown rendering via Jinja2 templates.
- Multi-format publishing (PDF, DOCX, HTML) via Pandoc with Lua filters.
- MkDocs documentation site.

[Unreleased]: https://github.com/mrhunsaker/Folge_Accessibility/compare/v2026.8.2...HEAD
[2026.8.2]: https://github.com/mrhunsaker/Folge_Accessibility/compare/v2026.7.31...v2026.8.2
[2026.7.31]: https://github.com/mrhunsaker/Folge_Accessibility/compare/v2026.7.30...v2026.7.31
[2026.7.30]: https://github.com/mrhunsaker/Folge_Accessibility/compare/v2026.7.28...v2026.7.30
[2026.7.28]: https://github.com/mrhunsaker/Folge_Accessibility/compare/v2026.7.25...v2026.7.28
[2026.7.25]: https://github.com/mrhunsaker/Folge_Accessibility/compare/v2026.7.18...v2026.7.25
[2026.7.18]: https://github.com/mrhunsaker/Folge_Accessibility/releases/tag/v2026.7.18
