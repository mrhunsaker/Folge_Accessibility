# Folge Vision Publishing Pipeline

**Version:** 2026.7.18 | **License:** Apache 2.0 | **Author:** Michael Hunsaker

A complete, automated documentation publishing pipeline that enriches Folge guide exports with Ollama Vision AI-generated accessibility metadata, then publishes to **PDF/UA-compliant PDFs**, DOCX, HTML, and GitHub Markdown formats.

**Documentation:** [mrhunsaker.github.io/Folge_Accessibility](https://mrhunsaker.github.io/Folge_Accessibility/)

---

## Overview

This pipeline transforms **Folge guide exports** into **accessible, multi-format documentation** through six stages:

| Stage | Description | Input | Output |
|-------|-------------|-------|--------|
| **1. Export** | Get your guide and screenshots from Folge | Folge | `guide.json` + images |
| **2. Enrich** | AI generates alt text, descriptions, OCR, UI controls | `guide.json` + images | `vision-results.json` |
| **3. Merge** | Combine authored content with vision data deterministically | `guide.json` + `vision-results.json` | `guide.enriched.json` |
| **4. Validate** | Ensure schema compliance and content quality | `guide.enriched.json` | Validation report |
| **5. Render** | Generate Markdown with embedded accessibility metadata | `guide.enriched.json` | `guide.md` |
| **6. Publish** | Convert to tagged PDF, DOCX, HTML with Pandoc and Lua filters | `guide.md` | PDF, DOCX, HTML |

### Key Features

- **Accessibility-first**: WCAG 2.1 AA, ARIA, **PDF/UA**, DOCX accessibility support
- **Deterministic**: Same input always produces same output
- **Separation of concerns**: Authored content stays separate from AI enrichment
- **Extensible**: Versioned schema supports future metadata additions
- **Multi-format**: Single source publishes to PDF, DOCX, HTML, GitHub Markdown
- **Tagged PDF Guarantee**: All PDFs are PDF/UA compliant with proper structure tags

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/mrhunsaker/Folge_Accessibility.git
cd Folge_Accessibility
uv sync

# Pull the vision model
ollama pull qwen2.5vl-8k:latest

# Place your Folge export and screenshots
# (guide.json in root, images in images/)

# Run the full pipeline
uv run run_pipeline.py guide.json output/
```

Output files appear in `output/`: a tagged PDF/UA-compliant PDF, DOCX, HTML, and Markdown.

---

## Prerequisites

### Required Software

| Tool | Version | Purpose | Install |
|------|---------|---------|---------|
| **Python** | 3.10+ | Script execution | [python.org](https://python.org) |
| **uv** | 0.4+ | Package management | [docs.astral.sh/uv](https://docs.astral.sh/uv) |
| **Ollama** | 0.3.0+ | Vision model hosting | [ollama.ai](https://ollama.ai) |
| **Pandoc** | 3.0+ | Document conversion | [pandoc.org](https://pandoc.org) |
| **Git** | Any | Version control | [git-scm.com](https://git-scm.com) |
| **poppler-utils** | Any | PDF validation | `sudo apt install poppler-utils` / `brew install poppler` |

### Vision Model

```bash
ollama pull qwen2.5vl-8k:latest
```

### Python Dependencies

All Python dependencies are managed by `uv` and installed with `uv sync`:

- `jsonschema` -- Schema validation
- `jinja2` -- Markdown templating
- `requests` -- Ollama API calls
- `weasyprint` -- PDF/UA-compliant PDF generation
- `pymupdf` -- PDF validation
- `mkdocs` + `mkdocs-material` -- Documentation site

---

## Project Structure

```
Folge_Accessibility/
├── pyproject.toml                # Project metadata, dependencies (uv)
├── mkdocs.yml                    # MkDocs documentation config
├── run_pipeline.py               # Master pipeline orchestrator
│
├── accessibility.lua             # Pandoc filter for HTML accessibility
├── docx-accessibility.lua        # Pandoc filter for DOCX accessibility
├── pdf-accessibility.lua         # Pandoc filter for PDF/UA compliance
│
├── templates/
│   ├── prompt.txt                # Template for Ollama vision prompts
│   └── markdown.md               # Jinja2 template for Markdown rendering
│
├── scripts/
│   ├── batch_process.py          # Processes images through Ollama Vision
│   ├── merge.py                  # Merges guide.json + vision-results.json
│   ├── render.py                 # Renders Markdown from enriched JSON
│   ├── publish.py                # Standalone publish with PDF/UA guarantee
│   ├── validate_schema.py        # Validates JSON against canonical schema
│   ├── validate_content.py       # Validates content quality (alt, confidence)
│   └── validate_pdf.py           # Validates PDF tagging and accessibility
│
├── docs/                         # MkDocs documentation source
│   ├── index.md                  # Documentation landing page
│   ├── getting-started.md        # Installation and first run guide
│   ├── pipeline/                 # Step-by-step pipeline docs
│   ├── pdf-ua.md                 # PDF/UA guarantee deep dive
│   ├── configuration.md          # Config file reference
│   ├── reference/                # Script and Lua filter reference
│   ├── contributing.md           # How to contribute
│   └── license.md                # License info
│
├── images/                       # Screenshots from Folge (user-provided)
├── output/                       # Published documents (generated)
├── schemas/                      # JSON schemas for validation
├── config.yaml                   # Pipeline configuration
├── .env                          # Environment variables
├── .github/workflows/
│   └── deploy-docs.yml           # GitHub Actions: deploy docs to Pages
├── LICENSE                       # Apache 2.0
└── README.md                     # This file
```

---

## Documentation

The project includes a full documentation site built with MkDocs and Material for Markdown.

### Viewing Locally

```bash
# Serve with live reload
uv run mkdocs serve

# Opens at http://127.0.0.1:8000
```

### Building Static Site

```bash
uv run mkdocs build --strict
# Output in site/
```

### GitHub Pages

Documentation is automatically deployed to [mrhunsaker.github.io/Folge_Accessibility](https://mrhunsaker.github.io/Folge_Accessibility/) on every push to `main` when `docs/` or `mkdocs.yml` change. The workflow is defined in `.github/workflows/deploy-docs.yml`.

To enable, go to your repo **Settings > Pages** and select **GitHub Actions** as the source.

### Documentation Contents

| Page | Description |
|------|-------------|
| [Getting Started](https://mrhunsaker.github.io/Folge_Accessibility/getting-started/) | Prerequisites, install, first run |
| [Pipeline Overview](https://mrhunsaker.github.io/Folge_Accessibility/pipeline/) | Architecture and design principles |
| Pipeline Steps | [Export](https://mrhunsaker.github.io/Folge_Accessibility/pipeline/export/), [Enrich](https://mrhunsaker.github.io/Folge_Accessibility/pipeline/enrich/), [Merge](https://mrhunsaker.github.io/Folge_Accessibility/pipeline/merge/), [Validate](https://mrhunsaker.github.io/Folge_Accessibility/pipeline/validate/), [Render](https://mrhunsaker.github.io/Folge_Accessibility/pipeline/render/), [Publish](https://mrhunsaker.github.io/Folge_Accessibility/pipeline/publish/) |
| [PDF/UA Guarantee](https://mrhunsaker.github.io/Folge_Accessibility/pdf-ua/) | Three-layer compliance approach |
| [Configuration](https://mrhunsaker.github.io/Folge_Accessibility/configuration/) | config.yaml, .env, pyproject.toml reference |
| [Scripts Reference](https://mrhunsaker.github.io/Folge_Accessibility/reference/scripts/) | CLI reference for all scripts |
| [Lua Filters](https://mrhunsaker.github.io/Folge_Accessibility/reference/lua-filters/) | Filter behavior and attributes |

---

## Pipeline Details

### Running the Full Pipeline

```bash
uv run run_pipeline.py guide.json output/
```

The orchestrator checks prerequisites, runs all six stages, validates the PDF, and prints a summary with file sizes and timing.

### Target Formats

```bash
# Default: PDF, DOCX, HTML
uv run run_pipeline.py guide.json output/

# Specific targets
uv run run_pipeline.py guide.json output/ --targets pdf,html

# Include GitHub Markdown
uv run run_pipeline.py guide.json output/ --targets pdf,docx,html,github
```

### Running Steps Individually

For more control, run each step separately:

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

### Standalone Publish Script

```bash
uv run python scripts/publish.py guide.json output/ pdf,docx,html
```

Runs steps 1-6 (batch process, merge, validate, render, publish, validate PDF).

---

## PDF/UA Tagging Guarantee

Every PDF produced by this pipeline is tagged and compliant with PDF/UA-1 (ISO 14289-1) through three layers:

1. **Enhanced Lua Filter** (`pdf-accessibility.lua`) -- Adds explicit PDF tags for all elements (Figure, H1-H6, P, L, BlockQuote, Code, Table) and sets PDF/UA metadata (version 1.7+, tagged=true, conforms_to=PDF/UA-1)
2. **PDF Engine with Tagging Support** -- Uses weasyprint with `--presentational-hints` and `--metadata=tagged-pdf:true`
3. **Validation Script** (`validate_pdf.py`) -- Dual-method verification via pdfinfo and pymupdf

### Verify PDF Tagging

```bash
pdfinfo output/guide.pdf | grep -i tagged
# Expected: Tagged: yes

uv run python scripts/validate_pdf.py output/guide.pdf
```

### PDF/UA Compliance Checklist

| Requirement | Implementation | Verification |
|-------------|----------------|--------------|
| Tagged PDF | Lua filter + engine flags | `pdfinfo` shows "Tagged: yes" |
| Document Language | `language` field in JSON | Check PDF properties |
| Alt Text for Images | `vision.alt_text` | Verify in Tags pane |
| Long Descriptions | `vision.long_description` | Check `/E` entries |
| Heading Structure | `#`, `##`, `###` in Markdown | Tags show H1, H2, H3 |
| Figure Tags | Enhanced Lua filter | Tags show Figure for images |
| Paragraph Tags | Enhanced Lua filter | Tags show P for paragraphs |
| PDF Version 1.7+ | Default in modern engines | `pdfinfo` shows version |

### PDF Engine Comparison

| Engine | Tagging | PDF/UA | Quality | Cost |
|--------|---------|--------|---------|------|
| **princexml** | Excellent | Full | 5/5 | Paid |
| **weasyprint** | Good | Good | 4/5 | Free |
| **wkhtmltopdf** | Basic | Partial | 3/5 | Free |
| **xelatex** | Good | Good | 4/5 | Free |

---

## Lua Filters

| Filter | Target | Injects | PDF/UA |
|--------|--------|---------|--------|
| `pdf-accessibility.lua` | PDF | `/Alt`, `/E`, `pdf-tag` for all elements, PDF/UA metadata | Full |
| `docx-accessibility.lua` | DOCX | `aria-description`, `accessibility-description`, `aria-label` | Full |
| `accessibility.lua` | HTML | `aria-description`, `aria-level`, `aria-hidden` on notes | Full |

---

## Configuration

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata and dependencies |
| `config.yaml` | Ollama settings, paths, targets, validation thresholds |
| `.env` | Environment variables for Ollama and paths |
| `mkdocs.yml` | Documentation site configuration |
| `templates/prompt.txt` | Ollama vision prompt template |
| `templates/markdown.md` | Jinja2 Markdown rendering template |

---

## Resources

- [PDF/UA Standard (ISO 14289-1)](https://www.iso.org/standard/53757.html)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [PDF Accessibility Overview](https://www.adobe.com/accessibility/pdf.html)
- [Pandoc PDF/UA Support](https://pandoc.org/MANUAL.html#producing-pdf)

---

## License

This project is licensed under the **Apache License 2.0** -- see the [LICENSE](LICENSE) file for details.
