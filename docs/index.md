---
hide:
  - navigation
---

# Folge Vision Publishing Pipeline

**Version:** 2026.7.18 | **License:** Apache 2.0 | **Author:** Michael Hunsaker

---

An automated documentation publishing pipeline that enriches Folge guide exports with Ollama Vision AI-generated accessibility metadata, then publishes to **PDF/UA-compliant PDFs**, DOCX, HTML, and GitHub Markdown.

## What It Does

<div class="grid cards" markdown>

- :material-export:{ .lg .middle } **Export**

    ---

    Take your guide and screenshots from Folge

    [:octicons-arrow-right-24: Learn more](pipeline/export.md)

- :material-eye:{ .lg .middle } **Enrich**

    ---

    AI generates alt text, descriptions, OCR, and UI control detection

    [:octicons-arrow-right-24: Learn more](pipeline/enrich.md)

- :material-call-merge:{ .lg .middle } **Merge**

    ---

    Combine authored content with vision data deterministically

    [:octicons-arrow-right-24: Learn more](pipeline/merge.md)

- :material-check-all:{ .lg .middle } **Validate**

    ---

    Ensure schema compliance and content quality

    [:octicons-arrow-right-24: Learn more](pipeline/validate.md)

- :material-text-box-outline:{ .lg .middle } **Render**

    ---

    Generate Markdown with embedded accessibility metadata

    [:octicons-arrow-right-24: Learn more](pipeline/render.md)

- :material-file-document-outline:{ .lg .middle } **Publish**

    ---

    Convert to tagged PDF, DOCX, HTML with Pandoc and Lua filters

    [:octicons-arrow-right-24: Learn more](pipeline/publish.md)

</div>

## Key Features

- **Accessibility-first** -- WCAG 2.1 AA, ARIA, PDF/UA, DOCX accessibility support
- **Deterministic** -- Same input always produces same output
- **Separation of concerns** -- Authored content stays separate from AI enrichment
- **Extensible** -- Versioned schema supports future metadata additions
- **Multi-format** -- Single source publishes to PDF, DOCX, HTML, GitHub Markdown
- **Tagged PDF Guarantee** -- All PDFs are PDF/UA compliant with proper structure tags

## Quick Start

```bash
# Clone and install
git clone https://github.com/mrhunsaker/Folge_Accessibility.git
cd Folge_Accessibility
uv sync

# Pull the vision model
ollama pull qwen2.5vl:7b

# Place your Folge export and screenshots
# (guide.json in root, images in images/)

# Run the full pipeline
uv run run_pipeline.py guide.json output/
```

Output files appear in `output/`: a tagged PDF/UA-compliant PDF, DOCX, HTML, and Markdown.

[:octicons-arrow-right-24: Full getting started guide](getting-started.md)
