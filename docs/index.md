---
hide:
  - navigation
---

# Folge Vision Publishing Pipeline

**Version:** 2026.7.25 | **License:** Apache 2.0 | **Author:** Michael Hunsaker

---

An automated documentation publishing pipeline that enriches Folge guide exports with Vision AI-generated accessibility metadata, then publishes to **PDF/UA-compliant PDFs**, DOCX, HTML, and GitHub Markdown.

## What It Does

<div class="grid cards" markdown>

- :material-export:{ .lg .middle } **Export**

    ---

    Take your guide and screenshots from Folge

    [:octicons-arrow-right-24: Learn more](pipeline/export.md)

- :material-eye:{ .lg .middle } **Enrich**

    ---

    Vision AI generates alt text, descriptions, OCR, and UI control detection

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

- **Seven AI providers** -- ollama (default), lmstudio, llamacpp, openrouter, openai, gemini, anthropic
- **Accessibility-first** -- WCAG 2.1 AA, ARIA, PDF/UA, DOCX accessibility support
- **Deterministic** -- Same input always produces same output
- **Separation of concerns** -- Authored content stays separate from AI enrichment
- **Pre-built binaries** -- Single-file executables for Windows, macOS, and Linux

## Quick Start

=== "Pre-built Binary"

    Download from [GitHub Releases](https://github.com/mrhunsaker/Folge_Accessibility/releases):

    ```bash
    # Linux
    unzip folge-cli-linux-amd64.zip
    ./folge-cli batch-process guide.json images/ vision-results.json
    ./folge-cli merge guide.json vision-results.json guide.enriched.json
    ./folge-cli render guide.enriched.json pdf guide.md
    ```

=== "Source Installation"

    ```bash
    git clone https://github.com/mrhunsaker/Folge_Accessibility.git
    cd Folge_Accessibility
    uv sync

    # Pull the vision model (if using ollama)
    ollama pull qwen2.5vl-8k:latest

    # Run the full pipeline
    folge-cli pipeline guide.json output/
    ```

[:octicons-arrow-right-24: Full getting started guide](getting-started.md)
