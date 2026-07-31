---
hide:
  - navigation
---

# Folge Vision Publishing Pipeline

**Version:** 2026.7.25 | **License:** Apache 2.0 | **Author:** Michael Hunsaker

---

An automated documentation publishing pipeline that enriches
[Folge](https://folge.me) guide exports with Vision AI-generated accessibility
metadata, then publishes to **16 output formats** including PDF/UA-compliant
PDFs, DOCX, HTML, EPUB, LaTeX, Typst, and more.

## What It Does

<div class="grid cards" markdown>

- :material-export:{ .lg .middle } **Export**

    ---

    Take your guide and screenshots from [Folge](https://folge.me)

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

- :material-tag-text-outline:{ .lg .middle } **Metadata**

    ---

    Embed title, author, subject, keywords, language, and security settings into every format

    [:octicons-arrow-right-24: Learn more](accessibility-metadata.md)

- :material-file-document-outline:{ .lg .middle } **Publish**

    ---

    Convert to 16 output formats with PDF/UA compliance

    [:octicons-arrow-right-24: Learn more](pipeline/publish.md)

</div>

## Key Features

- **Seven AI providers** -- ollama (default), lmstudio, llamacpp, openrouter, openai, gemini, anthropic
- **16 output formats** -- PDF, DOCX, HTML, PPTX, GitHub Markdown, Typst, AsciiDoc, Beamer, CommonMark, GFM, MultiMarkdown, DocBook, EPUB, ODT, RST, LaTeX
- **Accessibility-first** -- WCAG 2.1 AA, ARIA, PDF/UA, DOCX accessibility support
- **Accessible document metadata** -- auto-generated title, author, subject, keywords, language, tags, bookmarks, and copy-permissive security embedded into all formats
- **PDF page orientation** -- Letter portrait (default) or Letter landscape
- **Self-contained output** -- HTML and EPUB embed all resources
- **Custom fonts** -- Atkinson Hyperlegible Next (text) and AtkynsonMonoNerdFont (code/monospace)
- **Deterministic** -- Same input always produces same output
- **Separation of concerns** -- Authored content stays separate from AI enrichment
- **Pre-built binaries** -- Coming Soon (single-file executables for Windows, macOS, and Linux)

## Quick Start

=== "Source Installation"

    ```bash
    git clone https://github.com/mrhunsaker/Folge_Accessibility.git
    cd Folge_Accessibility
    uv sync

    # Pull the vision model (if using ollama)
    ollama pull qwen2.5vl-8k:latest

    # Run the full pipeline (all 16 formats)
    folge-cli pipeline guide.json output/

    # Or publish specific formats
    folge-cli publish guide.json output/ pdf,docx,html,epub,typst
    ```

=== "Pre-built Binary (Coming Soon)"

    !!! note "Not yet available"
        Pre-built binaries are not yet released. Use the source installation
        in the meantime. Check
        [GitHub Releases](https://github.com/mrhunsaker/Folge_Accessibility/releases)
        for updates.

[:octicons-arrow-right-24: Full getting started guide](getting-started.md)
