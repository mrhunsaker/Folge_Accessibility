# Getting Started

This guide walks you through installing the pipeline and running it for the first time.

## Installation Options

### Option A: Pre-built Binary (Coming Soon)

!!! note "Not yet available"
    Pre-built binaries are not yet released. The PyInstaller build pipeline is
    functional but releases have not been published yet. Use the source
    installation below in the meantime.

Download the latest release from
[GitHub Releases](https://github.com/mrhunsaker/Folge_Accessibility/releases):

| Platform | File |
|----------|------|
| **Linux** | `folge-cli-linux-amd64.zip` |
| **macOS** | `folge-cli-macos-arm64.tar.gz` |
| **Windows** | `folge-cli-windows-amd64.zip` |

```bash
# Linux
unzip folge-cli-linux-amd64.zip
chmod +x folge-cli
./folge-cli --help

# macOS
tar xzf folge-cli-macos-arm64.tar.gz
chmod +x folge-cli
./folge-cli --help

# Windows — extract and run from Command Prompt
folge-cli.exe --help
```

!!! note "External dependencies"
    You still need:

    - **Pandoc** — for document conversion (PDF, DOCX, HTML publishing)
    - **A vision provider** — Ollama (local) or a cloud provider API key in `.env`
    - **poppler-utils** (optional) — `pdfinfo` for enhanced PDF validation

### Option B: Source Installation (Full Pipeline)

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv).

```bash
git clone https://github.com/mrhunsaker/Folge_Accessibility.git
cd Folge_Accessibility
uv sync
```

This installs all Python dependencies including `jsonschema`, `jinja2`, `requests`, `weasyprint`, `pymupdf`, and `mkdocs`.

## Prerequisites

### Required Software

| Tool | Version | Purpose | Install |
|------|---------|---------|---------|
| **Python** | 3.10+ | Runtime (source install only) | [python.org](https://python.org) |
| **uv** | 0.4+ | Package management (source install only) | [docs.astral.sh/uv](https://docs.astral.sh/uv) |
| **Pandoc** | 3.0+ | Document conversion | [pandoc.org](https://pandoc.org) |
| **Vision provider** | — | Image analysis | See [Providers](#vision-providers) |

### Optional but Recommended

| Tool | Purpose | Install |
|------|---------|---------|
| **poppler-utils** | PDF validation (`pdfinfo`) | `sudo apt install poppler-utils` / `brew install poppler` |

### Vision Providers

Eight providers are supported. Ollama is the default (local, free).

| Provider | Type | API Key Required | Default Model |
|----------|------|------------------|---------------|
| **ollama** | Local | No | `qwen2.5vl-8k:latest` |
| **lmstudio** | Local | No | (user configures) |
| **jan** | Local | No | (user configures) |
| **llamacpp** | Local | No | (user configures) |
| **openrouter** | Cloud | Yes | `qwen/qwen-2.5-vl-72b-instruct` |
| **openai** | Cloud | Yes | `gpt-4o` |
| **gemini** | Cloud | Yes | `gemini-2.5-flash` |
| **anthropic** | Cloud | Yes | `claude-sonnet-4-20250514` |

Configure in `.env`:

```bash
PROVIDER=ollama
# For cloud providers, set the API key:
OPENAI_API_KEY=your-key-here
```

## Preparing Your Guide

Each guide lives in its own **project folder** under `~/Documents/FolgeProjects/`.
The folder holds the guide JSON (any file name — it must be the **only**
top-level JSON file), the screenshots in `images/`, and all generated files in
`output/`:

```text
~/Documents/FolgeProjects/
└── my-first-guide/
    ├── braille-blaster-export.json   # any name; the only JSON at this level
    ├── images/                      # screenshots (step-0.png, step-1.png, ...)
    └── output/                      # created automatically (all generated files)
```

### 1. Create a project folder

```bash
mkdir -p ~/Documents/FolgeProjects/my-first-guide/images
```

!!! tip "Where is this folder?"
    The default is `~/Documents/FolgeProjects`, but you can point the pipeline
    anywhere with the `FOLGE_PROJECTS_DIR` environment variable or
    `paths.projects_dir` in `config.yaml` (see
    [Configuration](configuration.md)).

### 2. Export from Folge

- Open your guide in [Folge](https://folge.me)
- Click **Export** > **JSON**
- Save the file into `~/Documents/FolgeProjects/my-first-guide/` — it can keep
  any name (e.g. `braille-blaster-export.json`). Just make sure it is the only
  JSON file at the top level of the project folder.

### 3. Export Screenshots

- Export all screenshots from Folge
- Save them to the project's `images/` directory
- Folge exports use names like `step-0.png`, `step-1.png`, etc.

!!! warning "Important"
    Do **not** modify the exported guide JSON after saving it. It is your
    source of truth.

## Running the Pipeline

### Full Pipeline (Source Installation Only)

```bash
folge-cli pipeline --project my-first-guide
```

`--project` finds the guide JSON automatically. This runs all seven stages
automatically with progress tracking and produces **all 16 output formats** by
default into `~/Documents/FolgeProjects/my-first-guide/output/`.

You can also pass explicit paths instead of `--project` (useful outside the
default layout):

```bash
folge-cli pipeline /path/to/any-export.json /some/output-dir
```

### Individual Steps (Works with Binary or Source)

```bash
# Step 1: Process images through Vision AI
folge-cli batch-process --project my-first-guide --provider ollama
# or: folge-cli batch-process guide.json images/ vision-results.json --provider ollama

# Step 2: Merge guide with vision data
folge-cli merge ~/Documents/FolgeProjects/my-first-guide/any-export.json \
  ~/Documents/FolgeProjects/my-first-guide/output/vision-results.json \
  ~/Documents/FolgeProjects/my-first-guide/output/guide.enriched.json

# Step 3: Validate
folge-cli validate-schema ~/Documents/FolgeProjects/my-first-guide/output/guide.enriched.json
folge-cli validate-content ~/Documents/FolgeProjects/my-first-guide/output/guide.enriched.json 0.7

# Step 4: Render Markdown
folge-cli render ~/Documents/FolgeProjects/my-first-guide/output/guide.enriched.json pdf guide.md

# Step 5: Publish (requires Pandoc)
folge-cli publish --project my-first-guide pdf,docx,html
```

### Output Formats

Every format the installed pandoc supports is produced by default
(`--targets` narrows the list; writers missing from that pandoc version are
skipped with a warning).  The full registry lives in
`src/folge_cli/formats.py`.

```bash
# Publish to all supported formats
folge-cli publish --project my-first-guide

# Or select specific formats
folge-cli publish --project my-first-guide pdf,docx,epub,typst
```

| Format | Target Name | File Extension |
|--------|-------------|---------------|
| PDF (tagged, PDF/UA) | `pdf` | `.pdf` |
| Word Document | `docx` | `.docx` |
| HTML (self-contained) | `html` | `.html` |
| PowerPoint | `pptx` | `.pptx` |
| GitHub Markdown | `github` | `.md` |
| Typst | `typst` | `.typ` |
| AsciiDoc | `asciidoc` | `.adoc` |
| Beamer (PDF) | `beamer` | `_beamer.pdf` |
| CommonMark | `commonmark` | `_cm.md` |
| GitHub Flavored MD | `gfm` | `_gh.md` |
| MultiMarkdown | `markdown_mmd` | `_mmd.md` |
| DocBook XML | `docbook` | `.xml` |
| EPUB | `epub` | `.epub` |
| OpenDocument | `odt` | `.odt` |
| reStructuredText | `rst` | `.rst` |
| LaTeX | `latex` | `.tex` |

The rest (markdown dialects, HTML4/5, slides, XML variants, EPUB2/3, FB2,
ICML, IPYNB, RTF, OPML, JSON, ConTeXt, BibTeX/BibLaTeX, AsciiDoc Legacy,
Asciidoctor, BBCode, and more) are named `guide_<abbrev>.<ext>` following the
same convention.  All pandoc conversions run with `--standalone` (document
metadata from `metadata.yaml`) and `--verbose`, with output appended to
`<output>/pandoc.log`.

## Running the GUI

Instead of (or alongside) the terminal, you can drive the pipeline from an
accessible, browser-based interface:

```bash
uv sync --all-packages   # one-time: installs NiceGUI as a workspace member
uv run folge-gui         # opens http://localhost:8765
```

`folge-gui` is a WCAG 2.2 AA [NiceGUI](https://nicegui.io) front end with
pages for Setup (prerequisites, provider settings, `.env`/`config.yaml`
editors), Steps (each `folge-cli` sub-command with a quality gate), and the
Full Pipeline (8-stage progress tracker). It launches the exact same
`folge-cli` commands you'd type at a terminal — see the
[Graphical Interface guide](gui.md) for details.

## Checking Output

```bash
ls -la ~/Documents/FolgeProjects/my-first-guide/output/
```

You should see files for each target you specified, e.g.:

| File | Description |
|------|-------------|
| `guide.pdf` | Tagged PDF, PDF/UA compliant |
| `guide.docx` | Word document with accessibility metadata |
| `guide.html` | Self-contained HTML with ARIA attributes |
| `guide.typ` | Typst typesetting source |
| `guide.epub` | Electronic publication |
| `guide.tex` | LaTeX source |
| `guide.md` | GitHub-compatible Markdown |

### Verify PDF Tagging

```bash
pdfinfo ~/Documents/FolgeProjects/my-first-guide/output/guide.pdf | grep -i tagged
# Expected: Tagged: yes
```

Or for detailed validation:

```bash
folge-cli validate-pdf ~/Documents/FolgeProjects/my-first-guide/output/guide.pdf
```
