<!--
 Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
 SPDX-License-Identifier: Apache-2.0
-->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Calendar Versioning](https://calver.org/) (`YYYY.M.D`).

## [Unreleased]

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
- **PyInstaller spec `__file__` error**: replaced `__file__` with `os.getcwd()`
  in `pyinstaller/folge-cli.spec` — PyInstaller executes spec files via `exec()`
  without defining `__file__`.
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

[Unreleased]: https://github.com/mrhunsaker/Folge_Accessibility/compare/v2026.7.25...HEAD
[2026.7.25]: https://github.com/mrhunsaker/Folge_Accessibility/compare/v2026.7.18...v2026.7.25
[2026.7.18]: https://github.com/mrhunsaker/Folge_Accessibility/releases/tag/v2026.7.18
