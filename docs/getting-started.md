# Getting Started

This guide walks you through installing the pipeline and running it for the first time.

## Prerequisites

### Required Software

| Tool | Version | Purpose | Install |
|------|---------|---------|---------|
| **Python** | 3.10+ | Script execution | [python.org](https://python.org) |
| **uv** | 0.4+ | Package management | [docs.astral.sh/uv](https://docs.astral.sh/uv) |
| **Ollama** | 0.3.0+ | Vision model hosting | [ollama.ai](https://ollama.ai) |
| **Pandoc** | 3.0+ | Document conversion | [pandoc.org](https://pandoc.org) |
| **Git** | Any | Version control | [git-scm.com](https://git-scm.com) |

### Optional but Recommended

| Tool | Purpose | Install |
|------|---------|---------|
| **poppler-utils** | PDF validation (`pdfinfo`) | `sudo apt install poppler-utils` / `brew install poppler` |

### Vision Model

Download the recommended vision model:

```bash
ollama pull qwen2.5vl-8k:latest
```

## Installation

```bash
git clone https://github.com/mrhunsaker/Folge_Accessibility.git
cd Folge_Accessibility
uv sync
```

This installs all Python dependencies including `jsonschema`, `jinja2`, `requests`, `weasyprint`, `pymupdf`, and `mkdocs`.

## Preparing Your Guide

### 1. Export from Folge

- Open your guide in Folge
- Click **Export** > **JSON**
- Save the file as `guide.json` in the project root

### 2. Export Screenshots

- Export all screenshots from Folge
- Save them to the `images/` directory
- Use consistent naming: `001.png`, `002.png`, etc.

!!! warning "Important"
    Do **not** modify `guide.json` after export. It is your source of truth.

## Running the Pipeline

### Full Pipeline (Recommended)

```bash
uv run run_pipeline.py guide.json output/
```

This runs all six stages automatically: vision processing, merge, validation, rendering, and publishing.

### Individual Steps

If you need more control, run each step separately:

```bash
# Step 2: Process images through Ollama Vision
uv run python scripts/batch_process.py guide.json images/ vision-results.json

# Step 3: Merge guide with vision data
uv run python scripts/merge.py guide.json vision-results.json guide.enriched.json

# Step 4: Validate
uv run python scripts/validate_schema.py guide.enriched.json
uv run python scripts/validate_content.py guide.enriched.json 0.8

# Step 5: Render Markdown
uv run python scripts/render.py guide.enriched.json pdf guide.md

# Step 6: Publish
uv run python scripts/publish.py guide.json output/ pdf,docx,html
```

## Checking Output

```bash
ls -la output/
```

You should see:

| File | Description |
|------|-------------|
| `guide.pdf` | Tagged PDF, PDF/UA compliant |
| `guide.docx` | Word document with accessibility metadata |
| `guide.html` | HTML with ARIA attributes |
| `guide.md` | GitHub-compatible Markdown |

### Verify PDF Tagging

```bash
pdfinfo output/guide.pdf | grep -i tagged
# Expected: Tagged: yes
```

Or for detailed validation:

```bash
uv run python scripts/validate_pdf.py output/guide.pdf
```
