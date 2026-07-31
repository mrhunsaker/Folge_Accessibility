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

[Unreleased]: https://github.com/mrhunsaker/Folge_Accessibility/compare/v2026.7.30...HEAD
[2026.7.30]: https://github.com/mrhunsaker/Folge_Accessibility/compare/v2026.7.28...v2026.7.30
[2026.7.28]: https://github.com/mrhunsaker/Folge_Accessibility/compare/v2026.7.25...v2026.7.28
[2026.7.25]: https://github.com/mrhunsaker/Folge_Accessibility/compare/v2026.7.18...v2026.7.25
[2026.7.18]: https://github.com/mrhunsaker/Folge_Accessibility/releases/tag/v2026.7.18
