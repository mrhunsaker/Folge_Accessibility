<!--
 Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
 SPDX-License-Identifier: Apache-2.0
-->

# Folge Vision Publishing Pipeline

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/mrhunsaker/Folge_Accessibility)](https://github.com/mrhunsaker/Folge_Accessibility/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/mrhunsaker/Folge_Accessibility/release.yml?label=build)](https://github.com/mrhunsaker/Folge_Accessibility/actions/workflows/release.yml)
[![Docs](https://img.shields.io/github/actions/workflow/status/mrhunsaker/Folge_Accessibility/deploy-docs.yml?label=docs)](https://mrhunsaker.github.io/Folge_Accessibility/)
[![Last commit](https://img.shields.io/github/last-commit/mrhunsaker/Folge_Accessibility)](https://github.com/mrhunsaker/Folge_Accessibility/commits/main)
[![Contributors](https://img.shields.io/github/contributors/mrhunsaker/Folge_Accessibility)](https://github.com/mrhunsaker/Folge_Accessibility/graphs/contributors)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://docs.astral.sh/ruff)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

A semi-automated documentation publishing pipeline that enriches
[Folge](https://folge.me) guide exports with Vision AI-generated accessibility
metadata, then publishes to **every format the installed pandoc supports**
(70+ writers) including PDF/UA-compliant PDFs, DOCX, HTML, EPUB, LaTeX,
Typst, and more.

**Documentation:** [mrhunsaker.github.io/Folge_Accessibility](https://mrhunsaker.github.io/Folge_Accessibility/)

---

## Overview

This pipeline transforms **Folge guide exports** into **accessible,
multi-format documentation** through seven stages. It is designed for
[Folge](https://folge.me) JSON exports, but any JSON file with an associated
`images/` folder can be processed.

### Input: `guide.json`

The pipeline accepts guide JSON exports from [Folge](https://folge.me) with
any file name. Each guide lives in its own **project folder** under
`~/Documents/FolgeProjects/<project>/` — the JSON file (any name, it must be
the only top-level JSON), the screenshots in `images/`, and all generated
files in `output/`:

```text
~/Documents/FolgeProjects/
└── my-guide/
    ├── my-export.json              # any name
    ├── images/                     # step-0.png, step-1.png, ...
    └── output/                     # created automatically
```

```json
{
  "guide": {
    "id": "_RIdkNRShXgDsy9_mhwlR",
    "title": "BrailleBlaster: Headings, Lists, and Emphasis",
    "description": ""
  },
  "steps": [
    {
      "id": "QatJX1vxONIm_nySDUIyv",
      "index": 1,
      "parentId": null,
      "title": "Check Heading Levels in Original Document",
      "description": "<p>I click by each of my headings just to see what the reported heading level is in LibreOffice.</p>",
      "screenshotFilename": "step-0.png",
      "indexString": "1.",
      "textblocks": [],
      "includeInToc": true,
      "settings": {
        "forceToANewPage": false,
        "multiImageStep": false,
        "focusedView": true,
        "contentBlock": false,
        "focusedViewSettings": { "scale": 1, "x": 0, "y": 0 },
        "substepBlocksSettings": [
          { "id": "title", "show": false },
          { "id": "image", "show": true },
          { "id": "description", "show": false }
        ],
        "textblocks": []
      },
      "nested": 0,
      "screenshotRelativePath": "images/step-0.png"
    }
  ]
}
```

### Input: `guide.enriched.json`

After Vision AI processing and merge, the enriched format adds a `vision` object
to each step with accessibility metadata:

```json
{
  "schema_version": "1.0",
  "guide_id": "_RIdkNRShXgDsy9_mhwlR",
  "title": "BrailleBlaster: Headings, Lists, and Emphasis",
  "description": "",
  "version": "1.0.0",
  "language": "en",
  "updated_at": "2026-07-25T12:00:00Z",
  "steps": [
    {
      "step_id": "QatJX1vxONIm_nySDUIyv",
      "title": "Check Heading Levels in Original Document",
      "body": "<p>I click by each of my headings just to see what the reported heading level is in LibreOffice.</p>",
      "image": "step-0.png",
      "vision": {
        "alt_text": "LibreOffice heading dropdown showing Heading Level 1",
        "long_description": "The LibreOffice sidebar displays a heading style panel. The current paragraph style is set to 'Heading 1', which is a centered heading at the top of the document.",
        "ocr_text": ["Heading 1", "Paragraph Style", "LibreOffice"],
        "ui_controls": [
          { "type": "dropdown", "label": "Paragraph Style", "action": "select" },
          { "type": "button", "label": "Heading 1", "action": "click" }
        ],
        "important_element": "Paragraph Style dropdown",
        "confidence": 0.92,
        "model": "qwen2.5vl-8k:latest",
        "generated_at": "2026-07-25T12:00:00Z",
        "processing_time_ms": 3450
      }
    }
  ],
  "metadata": {
    "merge_timestamp": "2026-07-25T12:00:00Z",
    "source_guide": "guide.json",
    "source_vision": "vision-results.json",
    "steps_with_vision": 37,
    "steps_with_errors": 0,
    "warnings": []
  }
}
```

During the **merge** step, the vision model's `long_description` is
HTML-escaped before it is written to the enriched JSON. This ensures that any
tags the model embeds in the description — e.g. an `<h4>` in "the last row is
planned as `<h4>`" — are stored as `&lt;h4&gt;` and render as literal text in
Pandoc/WeasyPrint and other HTML intermediaries, rather than being interpreted
as markup (which previously opened an unmatched heading). Only the
`long_description` field is escaped; `alt_text`, `ocr_text`, and
`ui_controls` are stored as authored.

### Pipeline Stages

| Stage | Description | Input | Output |
|-------|-------------|-------|--------|
| **1. Export** | Get your guide and screenshots from Folge | Folge | guide JSON + images |
| **2. Enrich** | Vision AI generates alt text, descriptions, OCR, UI controls | `guide.json` + images | `vision-results.json` |
| **3. Merge** | Combine authored content with vision data deterministically | `guide.json` + `vision-results.json` | `guide.enriched.json` |
| **4. Validate** | Schema compliance, content quality, PDF/UA checks | `guide.enriched.json` | Validation report |
| **5. Review** | Manual operator review (optional re-verify) | Validation report | Approved content |
| **6. Render** | Generate Markdown with embedded accessibility metadata | `guide.enriched.json` | `guide.md` |
| **7. Publish** | Convert to every supported pandoc output format via Pandoc + Lua filters | `guide.md` | PDF, DOCX, HTML, EPUB, LaTeX, Typst, and more |

If a `guide.enriched.json` already exists in the output directory from a
prior run, `folge-cli pipeline` detects it and prompts:

```
Found existing enriched JSON: .../output/guide.enriched.json
  (U)se existing enriched JSON and skip vision processing  or  (R)egenerate vision data from scratch? [U/R]
```

Choosing **U** skips stages 1-3 (vision processing + merge) entirely and
resumes at validation and manual review — useful after fixing something by
hand in the enriched JSON, or after a run that already succeeded at vision
but failed later in the pipeline. Pass `--skip-vision` to do this
non-interactively (errors out if no enriched JSON is present).

**Resume from an arbitrary stage** — `--first-step <stage>` starts the
pipeline from any step instead of the beginning, so you can pick up after a
power outage, regenerate output from a particular stage, or re-run just the
tail of the pipeline without replaying everything before it:

```bash
# Pick up at manual review after losing power mid-run
folge-cli pipeline --project my-guide --first-step 4b

# Re-render Markdown + republish only
folge-cli pipeline --project my-guide --first-step 5
```

Valid values match the stage numbers below: `1` (enrich), `3` (merge),
`4` (validate), `4b` (manual review), `5` (render), `5b` (metadata),
`6` (publish). Every stage before the chosen one is skipped (its
interactive prompts, including the reuse-vision prompt and manual-review
pause, are bypassed). Starting at stage `4` or later requires an existing
`guide.enriched.json`; the pipeline errors out with a clear message if it
is missing.

### Output Formats

Every writer the installed pandoc supports is exported on each run
(`--targets` narrows the list).  Writers unavailable in a given pandoc
version (e.g. `ansi`, `bbcode*`, `djot` on 3.1.x) are skipped with a
warning.  Collision-free filenames follow `guide_<abbrev>.<ext>`; the
primary formats keep plain names.  The registry lives in
`src/folge_cli/formats.py`.

| Format | File Extension | Description |
|--------|---------------|-------------|
| **PDF** | `.pdf` | Tagged PDF, PDF/UA compliant (weasyprint/wkhtmltopdf/xelatex) |
| **DOCX** | `.docx` | Word document with accessibility metadata |
| **HTML** | `.html` | Self-contained HTML with ARIA attributes |
| **PPTX** | `.pptx` | PowerPoint presentation |
| **GitHub Markdown** | `.md` | GitHub-compatible Markdown (minimal, no long descriptions) |
| **Typst** | `.typ` | Typst typesetting format |
| **AsciiDoc** | `.adoc` | AsciiDoc documentation format |
| **Beamer** | `_beamer.pdf` | LaTeX Beamer presentation (PDF) |
| **CommonMark** | `_cm.md` | CommonMark Markdown |
| **GitHub Flavored** | `_gh.md` | GitHub Flavored Markdown (with long descriptions) |
| **MultiMarkdown** | `_mmd.md` | MultiMarkdown format (`markdown_mmd`) |
| **DocBook** | `.xml` | DocBook XML |
| **EPUB** | `.epub` | Electronic publication (self-contained) |
| **ODT** | `.odt` | OpenDocument Text |
| **reStructuredText** | `.rst` | reStructuredText format |
| **LaTeX** | `.tex` | LaTeX source |

Additional markdown/text variants: Markdown (`_md.md`), CommonMark X
(`_cmx.md`), PHP Extra (`_phpextra.md`), Markdown Strict (`_strict.md`),
Markua (`_markua.md`), Plain (`_plain.txt`), Org (`.org`), Textile
(`.textile`), Texinfo (`.texi`), man (`.1`), ms (`.ms`), Djot (`.djot`),
and wiki dialects Dokuwiki, MediaWiki, XWiki, ZimWiki, Jira, Muse,
Haddock, and native AST (all `_<name>.txt`).

HTML family: HTML4 (`_html4.html`), HTML5 (`_html5.html`), and the slide
formats Slideous, Slidy, DZSlides, RevealJS, and S5 (`_<name>.html`),
plus Chunked HTML (`_chunkedhtml.zip`).

XML family: DocBook4, DocBook5, JATS, JATS Archiving, JATS Article
Authoring, JATS Publishing, OpenDocument XML, TEI (all `_<name>.xml`,
except DocBook keeps `.xml`).

Other formats: EPUB2/EPUB3 (`_epub2.epub`/`_epub3.epub`), FB2 (`.fb2`),
ICML (`.icml`), Jupyter Notebook (`.ipynb`), RTF (`.rtf`), OPML
(`.opml`), JSON AST (`.json`), ConTeXt (`_context.tex`), BibTeX (`.bib`),
BibLaTeX (`_biblatex.bib`), AsciiDoc Legacy and Asciidoctor
(`_asciidoc_legacy.adoc`/`_asciidoctor.adoc`), and BBCode variants
(`_<name>.bbcode`).

### Key Features

- **Eight AI providers**: ollama (default, local), lmstudio, jan, llamacpp
  (local), openrouter, openai, gemini, anthropic (cloud)
- **Accessible GUI**: `folge_gui` — a WCAG 2.2 AA NiceGUI front end
  (`uv run folge-gui`) for setup, individual steps, and the full pipeline
- **70+ output formats**: every writer the installed pandoc supports —
  PDF, DOCX, HTML, PPTX, GitHub Markdown, Typst, AsciiDoc, Beamer,
  CommonMark, GFM, MultiMarkdown, DocBook, EPUB, ODT, RST, LaTeX, and more
- **Accessibility-first**: WCAG 2.1 AA, ARIA, PDF/UA, DOCX accessibility
- **Accessible document metadata**: auto-generated title, author, subject,
  keywords, language, structure tags, bookmarks, and copy-permissive security
  settings embedded into every format via `folge-cli metadata`
- **PDF page orientation**: Letter portrait (default) or Letter landscape via
  `--orientation` flag
- **Self-contained output**: HTML and EPUB embed all resources
- **Custom fonts**: Atkinson Hyperlegible Next (text) and AtkynsonMonoNerdFont
  (code/monospace) bundled for accessible typography
- **Deterministic**: Same input always produces same output
- **Separation of concerns**: Authored content stays separate from AI enrichment
- **Progress tracking**: Real-time step counters throughout the pipeline
- **Manual review**: Operator can inspect and re-verify before rendering
- **Pre-built binaries**: single-file executables for Windows,
  macOS, and Linux via
  [GitHub Releases](https://github.com/mrhunsaker/Folge_Accessibility/releases)

---

## Pre-built Binaries

Download the latest release from
[GitHub Releases](https://github.com/mrhunsaker/Folge_Accessibility/releases).
Each release includes single-file executables — no Python installation required:

| Platform | File | Requirements |
|----------|------|--------------|
| **Linux** | `folge-cli-linux-amd64.zip` | Pandoc, poppler-utils (for PDF validation) |
| **macOS** | `folge-cli-macos-arm64.tar.gz` | Pandoc (`brew install pandoc`) |
| **Windows** | `folge-cli-windows-amd64.zip` | Pandoc (install from [pandoc.org](https://pandoc.org)) |

```bash
# Linux
unzip folge-cli-linux-amd64.zip
./folge-cli --help

# macOS
tar xzf folge-cli-macos-arm64.tar.gz
./folge-cli --help

# Windows
# Extract folge-cli.exe and run from Command Prompt or PowerShell
folge-cli.exe --help
```

!!! note "External dependencies"
    The executable bundles all Python dependencies. You still need:

    - **Pandoc** — for document conversion (PDF, DOCX, HTML publishing)
    - **A vision provider** — Ollama (local) or a cloud provider API key
    - **poppler-utils** (optional) — `pdfinfo` for enhanced PDF validation

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/mrhunsaker/Folge_Accessibility.git
cd Folge_Accessibility
uv sync

# Configure provider (edit .env — ollama is the default, no API key needed)
# For cloud providers, set the appropriate API key in .env

# Pull the vision model (if using ollama)
ollama pull qwen2.5vl-8k:latest

# Place your Folge export and screenshots in a project folder
mkdir -p ~/Documents/FolgeProjects/my-guide/images
cp /path/to/guide-export.json ~/Documents/FolgeProjects/my-guide/

# Run the full pipeline
folge-cli pipeline --project my-guide
```

Output files appear in `~/Documents/FolgeProjects/my-guide/output/`: a tagged
PDF/UA-compliant PDF, DOCX, HTML, EPUB, LaTeX, Typst, and more — every format
the installed pandoc supports.

---

## Prerequisites

| Tool | Version | Purpose | Install |
|------|---------|---------|---------|
| **Python** | 3.10+ | Runtime | [python.org](https://python.org) |
| **uv** | 0.4+ | Package management | [docs.astral.sh/uv](https://docs.astral.sh/uv) |
| **Pandoc** | 3.0+ | Document conversion | [pandoc.org](https://pandoc.org) |
| **Git** | Any | Version control | [git-scm.com](https://git-scm.com) |
| **poppler-utils** | Any | PDF validation | `sudo apt install poppler-utils` / `brew install poppler` |
| **Vision provider** | — | Image analysis | See [Providers](#providers) |

---

## Providers

Eight Vision AI providers are supported. Ollama is the default (local, free).
Cloud providers require an API key set in `.env`.

### Provider Table

| Provider | Type | API Key | Default Model | Auth Style |
|----------|------|---------|---------------|------------|
| **ollama** | Local | No | `qwen2.5vl-8k:latest` | None |
| **lmstudio** | Local | No | (user configures) | None |
| **jan** | Local | No | (user configures) | None |
| **llamacpp** | Local | No | (user configures) | None |
| **openrouter** | Cloud | Yes | `qwen/qwen-2.5-vl-72b-instruct` | Bearer token |
| **openai** | Cloud | Yes | `gpt-4o` | Bearer token |
| **gemini** | Cloud | Yes | `gemini-2.5-flash` | Bearer token |
| **anthropic** | Cloud | Yes | `claude-sonnet-4-20250514` | `x-api-key` header |

### Configuration

Resolution order for every setting:

```
CLI argument  >  environment variable  >  config.yaml  >  hardcoded default
```

**`.env`** — Provider selection and API keys:

```bash
PROVIDER=ollama              # ollama (default), lmstudio, jan, llamacpp,
                             # openrouter, openai, gemini, anthropic

# Local providers (no API key needed)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5vl-8k:latest
OLLAMA_TIMEOUT=600

# Cloud providers (set API key)
OPENROUTER_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
```

**`config.yaml`** — Detailed provider settings, targets (informational; the
runtime registry lives in `src/folge_cli/formats.py`), validation thresholds.

---

## CLI Reference

The `folge-cli` command provides eleven subcommands:

```bash
# Full pipeline (all stages with progress tracking)
folge-cli pipeline [guide.json] [output-dir] [--project NAME] [--targets pdf,docx,html,...] [--provider PROVIDER] [--orientation portrait|landscape] [--skip-vision] [--first-step STEP] [--prompt NAME]

# Check version
folge-cli --version

# Individual stages
folge-cli batch-process [guide.json] [images/] [output.json] [--project NAME] [--provider PROVIDER] [--prompt NAME]
folge-cli new-prompt <name> [--force]
folge-cli merge <guide.json> <vision-results.json> <output.json>
folge-cli validate-schema <json-file> [--warnings-out <file>]
folge-cli validate-content <json-file> [min-confidence]
folge-cli validate-pdf <pdf-file>
folge-cli render <guide.enriched.json> <target> <output.md> [--images-dir <dir>]
folge-cli publish [guide.json] [output-dir] [targets] [provider] [--project NAME] [--orientation portrait|landscape]
folge-cli metadata <guide.json> [-o metadata.yaml] [--apply-pdf guide.pdf] [--check] [--strict]
folge-cli generate-manual-attention <json> <images/> <output.md> [warnings.json]
```

Projects live in `~/Documents/FolgeProjects/<project>/`. `--project NAME`
resolves the guide JSON (any name — it must be the only top-level JSON),
`images/`, and `output/` automatically:

```bash
folge-cli pipeline --project my-guide
folge-cli publish --project my-guide pdf,docx,html
```

When `--targets` is not specified, **every format supported by the installed
pandoc** is produced by default (writers absent from that pandoc version are
skipped with a warning).

### Custom Vision Prompts

The prompt sent to the vision model is generated per-step by a prompt module.
By default the built-in prompt in `src/folge_cli/batch_process.py` is used,
but you can select an alternate prompt for the cases that need one:

```bash
# Use the built-in default prompt (no --prompt flag)
folge-cli batch-process --project my-guide --provider ollama

# Use a custom prompt module
folge-cli batch-process --project my-guide --provider ollama --prompt brailleblaster
```

Every prompt module:

- Lives in `src/folge_cli/prompts/<name>.py`.
- Exposes a single function
  `generate_prompt(step, guide_title, previous_step=None, next_step=None)`
  that returns the prompt string.
- Is **auto-registered** — adding a file to that folder immediately makes its
  name a valid `--prompt` choice (the flag's `choices` are discovered
  automatically from the folder contents).

`folge-cli new-prompt <name>` scaffolds a correctly formed prompt module so
you never have to hand-type the function signature:

```bash
folge-cli new-prompt my-special-case
# Creates src/folge_cli/prompts/my_special_case.py with the standard
# generate_prompt() boilerplate and JSON-schema prompt template.
```

The name is normalized to a safe identifier (e.g. `My Special Case` becomes
`my_special_case`). Existing modules are not overwritten unless you pass
`--force`. After scaffolding, edit the function to add your custom
instructions, then run `folge-cli batch-process ... --prompt my_special_case`.

The `pipeline` command forwards the same option:

```bash
folge-cli pipeline --project my-guide --prompt brailleblaster
```

A bundled example, `brailleblaster`, demonstrates a highly customized prompt
that instructs the model to describe the BrailleBlaster editor layout with a
specific opening sentence.

### Available Targets

The full list lives in `src/folge_cli/formats.py`.  Common targets:

```
pdf  docx  html  pptx  github  typst  asciidoc  beamer
commonmark  gfm  markdown_mmd  docbook  epub  odt  rst  latex
```

All pandoc invocations run with `--standalone` (so every file carries the
document metadata) and `--verbose`; their output is appended to
`<output>/pandoc.log`.

### Running Stages Individually

```bash
# Process images through Vision API
folge-cli batch-process --project my-guide --provider ollama
# Use a custom vision prompt instead of the default
folge-cli batch-process --project my-guide --provider ollama --prompt brailleblaster

# Merge guide with vision data
folge-cli merge ~/Documents/FolgeProjects/my-guide/my-export.json \
  ~/Documents/FolgeProjects/my-guide/output/vision-results.json \
  ~/Documents/FolgeProjects/my-guide/output/guide.enriched.json

# Validate schema and content
folge-cli validate-schema ~/Documents/FolgeProjects/my-guide/output/guide.enriched.json
folge-cli validate-content ~/Documents/FolgeProjects/my-guide/output/guide.enriched.json 0.7

# Render Markdown for a specific target
folge-cli render ~/Documents/FolgeProjects/my-guide/output/guide.enriched.json pdf guide.md

# Publish to selected formats (omit --targets for every supported format)
folge-cli publish --project my-guide pdf,docx,html,epub,typst,latex

# Publish with landscape orientation
folge-cli publish --project my-guide pdf --orientation landscape

# Generate accessible-document metadata for all formats
folge-cli metadata ~/Documents/FolgeProjects/my-guide/my-export.json -o metadata.yaml

# Embed metadata into a PDF and allow text copying
folge-cli metadata ~/Documents/FolgeProjects/my-guide/my-export.json --apply-pdf output/guide.pdf

# Verify metadata against accessibility best practices
folge-cli metadata ~/Documents/FolgeProjects/my-guide/my-export.json --check --strict
```

### Accessible Document Metadata

`folge-cli metadata` generates the metadata required for accessible PDFs and
embeds it into **every** output format. It derives values from the guide JSON
and `config.yaml`, and writes a Pandoc-compatible `metadata.yaml`
(`--metadata-file`) so formats like DOCX, ODT, EPUB, and HTML carry the same
title, author, subject, keywords, and language.

| Element | Source | Why it matters |
|---------|--------|----------------|
| **Title** | Guide title (`project.name` fallback) | Screen readers announce it to identify the document |
| **Author** | `project.author`, `--author`, or guide metadata | Names the responsible person, department, or organization |
| **Subject** | Guide description (`project.description` fallback) | Concise summary of the document content |
| **Keywords** | `project.keywords` + terms derived from step titles | Improves searchability |
| **Language** | Guide `language` (default `en`) | Correct pronunciation and intonation in screen readers |
| **Tags** | Pandoc Lua filters + WeasyPrint | Structural tagging for headings, lists, tables, figures |
| **Bookmarks** | Headings (outline) | Interactive navigation for documents of 10+ pages |
| **Security** | `--apply-pdf` (PyMuPDF) | Text copying is always allowed for assistive technology |

With `--apply-pdf`, the PDF Info dictionary (title, author, subject, keywords)
and the document `/Lang` entry are written directly with PyMuPDF, an outline is
generated from headings, and any restrictive security handler is stripped so
text copying is allowed. `--check --strict` exits with status 1 when a
best-practice violation is found (for example, a generic title like
"Document 1").

---

## Building from Source

### Install

```bash
git clone https://github.com/mrhunsaker/Folge_Accessibility.git
cd Folge_Accessibility
uv sync
```

### Build Executable

```bash
# Install build dependencies
uv pip install pyinstaller>=6.0

# Build
uv run pyinstaller pyinstaller/folge-cli.spec

# Output: dist/folge-cli
```

The executable bundles all Python dependencies, Lua filters, templates,
and `config.yaml`. Pandoc and a vision provider are still required at
runtime.

---

## Graphical Interface (folge_gui)

`folge_gui` is an accessible, browser-based front end for the pipeline, built
with [NiceGUI](https://nicegui.io). It lives in `src/folge_gui` and is a
*parallel, additive companion* to `folge-cli` — every command it runs is
launched as a real subprocess (the same `folge-cli` you'd run from a
terminal), and `src/folge_cli` is never modified or imported for execution.
It targets **WCAG 2.2 AA**: real heading levels, skip links, labeled form
controls, ARIA live status announcements, visible focus indicators, and
non-dismissible dialogs for interactive prompts.

### Install and run

```bash
git clone https://github.com/mrhunsaker/Folge_Accessibility.git
cd Folge_Accessibility
uv sync --all-packages   # one-time: pulls in NiceGUI as a workspace member
uv run folge-gui         # opens http://localhost:8765
```

`folge-gui` is registered as a
[uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
member, so it shares one `uv.lock` and one `.venv` with `folge-cli`. The
`folge_gui` console script is kept as an alias — `uv run folge_gui` works
identically. `folge-cli` itself is completely unaffected.

### What it does

| Page | Purpose |
|------|---------|
| **Setup** | Check `uv`, Pandoc, `pdfinfo`, and `pymupdf`; review every provider's resolved settings; edit `.env` and `config.yaml` from the browser |
| **Steps** | Run any `folge-cli` sub-command with its own form, live status, streamed output, and a post-run quality-gate dialog |
| **Full Pipeline** | Run `folge-cli pipeline` end to end behind an 8-stage tracker, swapping the CLI's two terminal prompts for accessible dialogs |

See [docs/gui.md](docs/gui.md) and `src/folge_gui/README.md` for the full
details, including the contrast-ratio table for the Catppuccin Latte theme.

---

```
Folge_Accessibility/
├── pyproject.toml                  # Project metadata, dependencies, entry point
├── config.yaml                     # Provider settings, targets, validation
├── .env                            # Environment variables (provider, API keys)
├── run_pipeline.py                 # Backward-compatible entry point
│
├── src/folge_cli/                  # Installable Python package
│   ├── __init__.py                 # Package metadata
│   ├── __main__.py                 # python -m folge_cli
│   ├── _version.py                 # Dynamic version (CalVer)
│   ├── cli.py                      # folge-cli entry point (10 subcommands)
│   ├── config.py                   # Centralized configuration loading
│   ├── pipeline.py                 # Full pipeline orchestrator
│   ├── batch_process.py            # Vision API image processing
│   ├── merge.py                    # Deterministic merge (guide + vision)
│   ├── render.py                   # Markdown rendering via Jinja2
│   ├── publish.py                  # Standalone publisher with PDF/UA
│   ├── metadata.py                 # Accessible document metadata generator
│   ├── validate_schema.py          # JSON schema validation
│   ├── validate_content.py         # Content quality validation
│   ├── validate_pdf.py             # PDF/UA compliance validation
│   ├── generate_manual_attention.py # Manual attention markdown generation
│   └── progress.py                 # Step counters and progress display
│
├── src/folge_gui/                  # Accessible NiceGUI front end (workspace member)
│   ├── pyproject.toml              # folge-gui package + folge-gui/folge_gui scripts
│   ├── app.py                      # Route registration + ui.run()
│   ├── theme.py                    # Catppuccin Latte tokens, WCAG-safe "ink" variants
│   ├── a11y.py                     # headings, live regions, skip-link landmarks
│   ├── process_runner.py           # async subprocess runner, prompt detection
│   ├── prereqs.py                  # structured prerequisite / provider checks
│   ├── config_io.py                # .env / config.yaml read + write
│   ├── steps.py                    # form <-> argv mapping for each folge-cli command
│   ├── components.py               # step cards, console, status tracker, dialogs
│   └── pages/
│       ├── home.py                 # Landing page
│       ├── setup.py                # Prerequisites, provider settings, config editors
│       ├── steps_page.py           # Individual sub-command runner
│       └── pipeline_page.py        # Full pipeline with 8-stage tracker
│
├── pyinstaller/                    # PyInstaller build configuration
│   └── folge-cli.spec              # Spec file for building executables
│
├── scripts/                        # Backward-compatible thin shims
├── templates/                      # Jinja2 templates, Lua filters, CSS
│   ├── markdown.md                 # Jinja2 Markdown rendering template
│   ├── prompt.txt                  # Vision AI prompt template
│   ├── folge.css                   # @font-face declarations and base styles
│   ├── letter-portrait.css         # PDF @page layout for Letter portrait
│   └── letter-landscape.css        # PDF @page layout for Letter landscape
├── fonts/                          # Bundled accessible fonts
│   ├── Atkinson_Hyperlegible_Next/ # Variable weight text font
│   └── AtkinsonHyperlegibleMono/   # Static OTF monospace font
├── schemas/                        # JSON schemas for validation
├── docs/                           # MkDocs documentation source
│
├── .github/workflows/
│   ├── deploy-docs.yml             # Deploy MkDocs to GitHub Pages
│   └── release.yml                 # Build + release on v* tags
│
├── LICENSE                         # Apache 2.0
├── CHANGES.md                      # Changelog
├── CONTRIBUTING.md                 # How to contribute
├── STYLE.md                        # Code style guide
├── SECURITY.md                     # Security policy
├── GOVERNANCE_ENFORCEMENT.md       # Governance enforcement
└── CODE_OF_CONDUCT.md              # Community standards
```

---

## Configuration Reference

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata, dependencies, `folge-cli` entry point, `[tool.uv.workspace]` members (`src/folge_gui`) |
| `config.yaml` | Provider settings, output targets (informational; registry in `folge_cli.formats`), validation thresholds, `project.author` and `project.keywords` metadata defaults |
| `.env` | Environment variables: provider selection, API keys, paths |
| `templates/prompt.txt` | Vision AI prompt template |
| `templates/markdown.md` | Jinja2 Markdown rendering template |
| `templates/folge.css` | Font declarations and base styles (Atkinson Hyperlegible) |
| `templates/letter-portrait.css` | PDF page layout for Letter portrait |
| `templates/letter-landscape.css` | PDF page layout for Letter landscape |

### Metadata Defaults

| Setting | Default | Description |
|---------|---------|-------------|
| `project.author` | `Michael Ryan Hunsaker, M.Ed., Ph.D.` | Author fallback used by `folge-cli metadata` |
| `project.keywords` | `accessibility, documentation, ...` | Keyword fallbacks used by `folge-cli metadata` |

### Validation Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `MIN_CONFIDENCE` | `0.7` | Minimum confidence threshold for vision results |
| `require_alt_text` | `true` | Require alt text for all images |
| `require_long_description` | `true` | Require long descriptions for images |
| `max_alt_text_length` | `150` | Maximum characters for alt text |

---

## Troubleshooting

### PDF generation fails on Windows: `cannot load library 'libgobject-2.0-0'`

`weasyprint` (the default PDF engine) depends on Pango and its GTK/GLib
dependencies, which aren't installed by `pip`/`uv` on Windows the way they
are on Linux/macOS. If you see:

```
OSError: cannot load library 'libgobject-2.0-0': error 0x7e
```

1. Install [MSYS2](https://www.msys2.org/#installation) (default options).
2. In the MSYS2 shell, run `pacman -S mingw-w64-x86_64-pango`.
3. Point WeasyPrint at the resulting DLLs, either for the current session:
   ```powershell
   set WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin
   ```
   or permanently:
   ```powershell
   setx WEASYPRINT_DLL_DIRECTORIES C:\msys64\mingw64\bin
   ```

See WeasyPrint's own [installation](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation)
and [troubleshooting](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#troubleshooting)
docs for details. If `weasyprint` still fails, the pipeline automatically
falls back to `wkhtmltopdf`, then `xelatex` — check the console output past
the `weasyprint` failure before troubleshooting further; you may already
have a valid PDF from one of the fallback engines. `xelatex` ships with a
MiKTeX install, which most Windows users already have from `pdfinfo`/TeX
tooling.

### Vision step fails with a "no content" or `'NoneType'` error

If a vision request comes back with `finish_reason: "length"` and no
content, it ran out of its token budget before producing an answer.
`batch_process.py` now raises a clear error for this
(`Model returned no content (finish_reason=length); it likely exhausted
max_tokens on internal reasoning before answering`) instead of the
confusing `'NoneType' object has no attribute 'strip'` it used to throw.
This is a known behavior of reasoning models (including the default
OpenRouter model, Kimi K3): reasoning tokens and the final answer share
the same `max_tokens` budget, so a screenshot that needs a longer chain of
thought can consume the whole budget before writing any JSON.
`max_tokens` was raised from `16384` to `32768` in `batch_process.py` to
give more headroom, and the batch processor retries automatically. If it
still happens on a particular step, raise `max_tokens` further or reduce
the model's reasoning effort if your provider exposes that setting.

### Schema validation fails on an unrecognized `ui_controls` type

The `type` field for detected UI controls is a closed vocabulary
(`button`, `text_field`, `dropdown`, `checkbox`, `radio`, `slider`,
`navigation`, `menu`, `tab`, `icon`, `link`, `table`, `other`). If the
vision model returns a label outside this list, it's normalized to
`other` automatically — if you hit a validation error naming a specific
type instead, that type needs to be added to both `VALID_UI_TYPES` in
`batch_process.py` and the schema `enum` in `validate_schema.py` (they
must stay in sync).

---

## Contributing

We welcome contributions! Please see:

- [CONTRIBUTING.md](CONTRIBUTING.md) — How to get started
- [STYLE.md](STYLE.md) — Code conventions and patterns
- [SECURITY.md](SECURITY.md) — Vulnerability reporting process
- [GOVERNANCE_ENFORCEMENT.md](GOVERNANCE_ENFORCEMENT.md) — Enforcement policy
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — Community standards

---

## License

This project is licensed under the **Apache License, Version 2.0** — see the
[LICENSE](LICENSE) file for details.

Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
