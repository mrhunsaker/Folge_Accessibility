# PDF/UA Guarantee

This pipeline guarantees that every PDF it produces is tagged and compliant with PDF/UA-1 (ISO 14289-1).

## The Problem

Standard PDFs lack structure information that screen readers need. Without tags, a screen reader sees a flat stream of text with no understanding of headings, paragraphs, images, or reading order.

**Tagged PDFs** add invisible XML-like tags that define the document structure, making them fully accessible to assistive technologies.

## The Solution

This pipeline uses three layers of PDF/UA compliance:

### Layer 1: Enhanced Lua Filter

The `pdf-accessibility.lua` filter adds explicit PDF tags for all document elements:

| Element | PDF Tag | Description |
|---------|---------|-------------|
| Images | `Figure` | Includes `/Alt` (short) and `/E` (expanded) descriptions |
| Headings | `H1`-`H6` | Proper heading hierarchy |
| Paragraphs | `P` | Text paragraphs |
| Lists | `L` | Bullet and numbered lists |
| Block Quotes | `BlockQuote` | Quoted content |
| Code Blocks | `Code` | Source code |
| Tables | `Table` | Tabular data |

The filter also sets PDF/UA metadata:

```lua
meta["pdf-metadata"] = {
    pdf_version = "1.7",      -- PDF/UA requires 1.7+
    tagged = true,             -- Explicitly request tagged PDF
    conforms_to = "PDF/UA-1"  -- Conformance level
}
```

### Layer 2: PDF Engine with Tagging Support

The pipeline uses Pandoc with a PDF engine that supports tagged output. The recommended engine is **weasyprint**:

```bash
pandoc guide.md \
  --lua-filter=pdf-accessibility.lua \
  --pdf-engine=weasyprint \
  --pdf-engine-opt=--presentational-hints \
  --metadata=tagged-pdf:true \
  -o guide.pdf
```

Key flags:

| Flag | Purpose |
|------|---------|
| `--lua-filter=pdf-accessibility.lua` | Injects PDF tags and metadata |
| `--pdf-engine=weasyprint` | Engine with PDF/UA support |
| `--pdf-engine-opt=--presentational-hints` | Enables structural hints |
| `--metadata=tagged-pdf:true` | Requests tagged output |

### Layer 3: Validation

After generation, the pipeline validates the PDF is actually tagged:

```bash
uv run python scripts/validate_pdf.py output/guide.pdf
```

The validation uses two methods for redundancy:

1. **pdfinfo** (from poppler-utils) -- checks the `Tagged: yes` flag
2. **pymupdf** -- checks `is_tagged`, `is_pdf_ua`, `pdf_version`, and `has_structure`

## PDF/UA Compliance Checklist

| Requirement | Implementation | Verification |
|-------------|----------------|--------------|
| Tagged PDF | Lua filter + engine flags | `pdfinfo` shows "Tagged: yes" |
| Document Language | `language` field in JSON | Check PDF properties |
| Alt Text for Images | `vision.alt_text` | Verify in Tags pane |
| Long Descriptions | `vision.long_description` | Check `/E` entries |
| Logical Reading Order | Markdown structure preserved | Check tag hierarchy |
| Heading Structure | `#`, `##`, `###` in Markdown | Tags show H1, H2, H3 |
| Figure Tags | Enhanced Lua filter | Tags show Figure for images |
| Paragraph Tags | Enhanced Lua filter | Tags show P for paragraphs |
| PDF Version 1.7+ | Default in modern engines | `pdfinfo` shows version |
| PDF/UA Metadata | Enhanced Lua filter | Check PDF properties |

## PDF Engine Comparison

| Engine | Tagging | PDF/UA | Quality | Cost | Notes |
|--------|---------|--------|---------|------|-------|
| **princexml** | Excellent | Full | 5/5 | Paid | Best overall compliance |
| **weasyprint** | Good | Good | 4/5 | Free | Recommended free option |
| **wkhtmltopdf** | Basic | Partial | 3/5 | Free | Use `--tagged-pdf` flag |
| **xelatex** | Good | Good | 4/5 | Free | Requires texlive |

## Verifying Your PDF

### Command Line

```bash
pdfinfo output/guide.pdf | grep -i tagged
# Expected: Tagged: yes
```

### Python Script

```bash
uv run python scripts/validate_pdf.py output/guide.pdf
```

### Visual Inspection

- **Adobe Acrobat**: View > Show/Hide > Navigation Panes > Tags
- **Okular** (Linux): View > Side Panes > Tags
- **PDF Arranger**: View > Tags

The tags pane should show a hierarchy like:

```
Document
  H1: Getting Started with App
  P: A beginner's guide...
  H2: Step 1: Open Settings
  P: Click the Settings button...
  Figure: Settings window...
    Alt: Settings window with sidebar
    E: Long description...
  H2: Step 2: Navigate to Network
```

### Screen Reader Test

Use NVDA or JAWS to navigate the PDF. It should:

- Read headings in order
- Announce images with alt text
- Follow logical reading order

## Resources

- [PDF/UA Standard (ISO 14289-1)](https://www.iso.org/standard/53757.html)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [PDF Accessibility Overview](https://www.adobe.com/accessibility/pdf.html)
- [Pandoc PDF/UA Support](https://pandoc.org/MANUAL.html#producing-pdf)
