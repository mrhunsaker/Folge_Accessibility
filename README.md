<!--
 Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
 SPDX-License-Identifier: Apache-2.0
-->

# Folge Vision Publishing Pipeline

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/mrhunsaker/Folge_Accessibility)](https://github.com/mrhunsaker/Folge_Accessibility/releases)

A semi-automated documentation publishing pipeline that enriches
[Folge](https://folge.me) guide exports with Vision AI-generated accessibility
metadata, then publishes to **16 output formats** including PDF/UA-compliant
PDFs, DOCX, HTML, EPUB, LaTeX, Typst, and more.

**Documentation:** [mrhunsaker.github.io/Folge_Accessibility](https://mrhunsaker.github.io/Folge_Accessibility/)

---

## Overview

This pipeline transforms **Folge guide exports** into **accessible,
multi-format documentation** through seven stages. It is designed for
[Folge](https://folge.me) JSON exports, but any JSON file with an associated
`images/` folder can be processed.

### Input: `guide.json`

The pipeline accepts `guide.json` exports from [Folge](https://folge.me).
Place the file in the project root with screenshots in `images/`:

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

### Pipeline Stages

| Stage | Description | Input | Output |
|-------|-------------|-------|--------|
| **1. Export** | Get your guide and screenshots from Folge | Folge | `guide.json` + images |
| **2. Enrich** | Vision AI generates alt text, descriptions, OCR, UI controls | `guide.json` + images | `vision-results.json` |
| **3. Merge** | Combine authored content with vision data deterministically | `guide.json` + `vision-results.json` | `guide.enriched.json` |
| **4. Validate** | Schema compliance, content quality, PDF/UA checks | `guide.enriched.json` | Validation report |
| **5. Review** | Manual operator review (optional re-verify) | Validation report | Approved content |
| **6. Render** | Generate Markdown with embedded accessibility metadata | `guide.enriched.json` | `guide.md` |
| **7. Publish** | Convert to 16 output formats via Pandoc + Lua filters | `guide.md` | PDF, DOCX, HTML, EPUB, LaTeX, Typst, and more |

### Output Formats

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
| **MultiMarkdown** | `_mmd.md` | MultiMarkdown format |
| **DocBook** | `.xml` | DocBook XML |
| **EPUB** | `.epub` | Electronic publication (self-contained) |
| **ODT** | `.odt` | OpenDocument Text |
| **reStructuredText** | `.rst` | reStructuredText format |
| **LaTeX** | `.tex` | LaTeX source |

### Key Features

- **Seven AI providers**: ollama (default, local), lmstudio, llamacpp (local),
  openrouter, openai, gemini, anthropic (cloud)
- **16 output formats**: PDF, DOCX, HTML, PPTX, GitHub Markdown, Typst,
  AsciiDoc, Beamer, CommonMark, GFM, MultiMarkdown, DocBook, EPUB, ODT, RST,
  LaTeX
- **Accessibility-first**: WCAG 2.1 AA, ARIA, PDF/UA, DOCX accessibility
- **PDF page orientation**: Letter portrait (default) or Letter landscape via
  `--orientation` flag
- **Self-contained output**: HTML and EPUB embed all resources
- **Custom fonts**: Atkinson Hyperlegible Next (text) and AtkynsonMonoNerdFont
  (code/monospace) bundled for accessible typography
- **Deterministic**: Same input always produces same output
- **Separation of concerns**: Authored content stays separate from AI enrichment
- **Progress tracking**: Real-time step counters throughout the pipeline
- **Manual review**: Operator can inspect and re-verify before rendering
- **Pre-built binaries**: Coming Soon — single-file executables for Windows,
  macOS, and Linux via
  [GitHub Releases](https://github.com/mrhunsaker/Folge_Accessibility/releases)

---

## Pre-built Binaries

!!! note "Coming Soon"
    Pre-built binaries are not yet available. The PyInstaller build pipeline is
    functional but releases have not been published yet. Use the source
    installation below in the meantime.

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

# Place your Folge export and screenshots
# (guide.json in root, images in images/)

# Run the full pipeline
folge-cli pipeline guide.json output/
```

Output files appear in `output/`: a tagged PDF/UA-compliant PDF, DOCX, HTML,
EPUB, LaTeX, Typst, and more — all 16 supported formats.

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

Seven Vision AI providers are supported. Ollama is the default (local, free).
Cloud providers require an API key set in `.env`.

### Provider Table

| Provider | Type | API Key | Default Model | Auth Style |
|----------|------|---------|---------------|------------|
| **ollama** | Local | No | `qwen2.5vl-8k:latest` | None |
| **lmstudio** | Local | No | (user configures) | None |
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
PROVIDER=ollama              # ollama (default), lmstudio, llamacpp,
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

**`config.yaml`** — Detailed provider settings, targets (16 output formats), validation thresholds.

---

## CLI Reference

The `folge-cli` command provides nine subcommands:

```bash
# Full pipeline (all stages with progress tracking)
folge-cli pipeline <guide.json> [output-dir] [--targets pdf,docx,html,...] [--provider PROVIDER] [--orientation portrait|landscape]

# Check version
folge-cli --version

# Individual stages
folge-cli batch-process <guide.json> <images/> <output.json> [--provider PROVIDER]
folge-cli merge <guide.json> <vision-results.json> <output.json>
folge-cli validate-schema <json-file> [--warnings-out <file>]
folge-cli validate-content <json-file> [min-confidence]
folge-cli validate-pdf <pdf-file>
folge-cli render <guide.enriched.json> <target> <output.md>
folge-cli publish <guide.json> [output-dir] [--targets pdf,docx,html,...] [--orientation portrait|landscape]
folge-cli generate-manual-attention <json> <images/> <output.md> [warnings.json]
```

When `--targets` is not specified, **all 16 formats** are produced by default.

### Available Targets

```
pdf  docx  html  pptx  github  typst  asciidoc  beamer
commonmark  gfm  multimarkdown  docbook  epub  odt  rst  latex
```

### Running Stages Individually

```bash
# Process images through Vision API
folge-cli batch-process guide.json images/ vision-results.json --provider ollama

# Merge guide with vision data
folge-cli merge guide.json vision-results.json guide.enriched.json

# Validate schema and content
folge-cli validate-schema guide.enriched.json
folge-cli validate-content guide.enriched.json 0.7

# Render Markdown for a specific target
folge-cli render guide.enriched.json pdf guide.md

# Publish to multiple formats (all 16 supported)
folge-cli publish guide.json output/ pdf,docx,html,epub,typst,latex

# Publish with landscape orientation
folge-cli publish guide.json output/ pdf --orientation landscape
```

!!! tip "Pre-built binaries"
    Pre-built executables (Coming Soon from
    [GitHub Releases](https://github.com/mrhunsaker/Folge_Accessibility/releases))
    will include all individual subcommands. The `pipeline` subcommand (which chains
    all steps together) requires the source installation with `uv` because it
    spawns subprocess calls. For the full automated pipeline, use the source
    installation or chain the individual commands manually.

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

## Project Structure

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
│   ├── cli.py                      # folge-cli entry point (9 subcommands)
│   ├── config.py                   # Centralized configuration loading
│   ├── pipeline.py                 # Full pipeline orchestrator
│   ├── batch_process.py            # Vision API image processing
│   ├── merge.py                    # Deterministic merge (guide + vision)
│   ├── render.py                   # Markdown rendering via Jinja2
│   ├── publish.py                  # Standalone publisher with PDF/UA
│   ├── validate_schema.py          # JSON schema validation
│   ├── validate_content.py         # Content quality validation
│   ├── validate_pdf.py             # PDF/UA compliance validation
│   ├── generate_manual_attention.py # Manual attention markdown generation
│   └── progress.py                 # Step counters and progress display
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
├── images/                         # Screenshots from Folge (user-provided)
├── output/                         # Published documents (generated)
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
| `pyproject.toml` | Project metadata, dependencies, `folge-cli` entry point |
| `config.yaml` | Provider settings, 16 output targets, validation thresholds |
| `.env` | Environment variables: provider selection, API keys, paths |
| `templates/prompt.txt` | Vision AI prompt template |
| `templates/markdown.md` | Jinja2 Markdown rendering template |
| `templates/folge.css` | Font declarations and base styles (Atkinson Hyperlegible) |
| `templates/letter-portrait.css` | PDF page layout for Letter portrait |
| `templates/letter-landscape.css` | PDF page layout for Letter landscape |

### Validation Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `MIN_CONFIDENCE` | `0.7` | Minimum confidence threshold for vision results |
| `require_alt_text` | `true` | Require alt text for all images |
| `require_long_description` | `true` | Require long descriptions for images |
| `max_alt_text_length` | `150` | Maximum characters for alt text |

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
