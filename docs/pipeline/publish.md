# Step 6: Publish

**What it does:** Converts Markdown to final formats (PDF, DOCX, HTML) with PDF/UA compliance and accessibility metadata injected by Lua filters.

**Why it matters:**

- **PDF**: Tagged PDF with page breaks, PDF/UA compliance from enhanced filter
- **DOCX**: Accessibility metadata in OpenXML format
- **HTML**: `aria-description` and other ARIA attributes

## Running

### Via the Pipeline Orchestrator

```bash
uv run run_pipeline.py guide.json output/ --targets pdf,docx,html
```

### Via the Standalone Publish Script

```bash
uv run python scripts/publish.py guide.json output/ pdf,docx,html
```

### Via Pandoc Directly

```bash
# PDF with weasyprint (recommended, free)
pandoc guide.md \
  --lua-filter=pdf-accessibility.lua \
  --pdf-engine=weasyprint \
  --pdf-engine-opt=--presentational-hints \
  --metadata=tagged-pdf:true \
  -o guide.pdf

# DOCX
pandoc guide.md --lua-filter=docx-accessibility.lua -o guide.docx

# HTML
pandoc guide.md --lua-filter=accessibility.lua -o guide.html
```

## PDF Engine Fallback Order

The publish step tries PDF engines in order:

| Priority | Engine | Notes |
|----------|--------|-------|
| 1 | **weasyprint** | Free, best PDF/UA support |
| 2 | **wkhtmltopdf** | Free, basic tagging |
| 3 | **xelatex** | Free, requires texlive |

If one engine fails, the next is tried automatically.

## Lua Filters

Each output format uses a specific Lua filter that injects accessibility metadata:

| Filter | Target | Adds | PDF/UA Support |
|--------|--------|------|----------------|
| `pdf-accessibility.lua` | PDF | `/Alt`, `/E`, explicit tags | Full PDF/UA |
| `docx-accessibility.lua` | DOCX | `description` field, alt text | Full |
| `accessibility.lua` | HTML | `aria-description`, `aria-label` | Full |

See [Lua Filters Reference](../reference/lua-filters.md) for detailed documentation.

## Output Validation

After publishing, the pipeline validates the PDF:

```bash
# Quick check
pdfinfo output/guide.pdf | grep -i tagged
# Expected: Tagged: yes

# Detailed validation
uv run python scripts/validate_pdf.py output/guide.pdf
```

See [PDF/UA Guarantee](../pdf-ua.md) for full details on the compliance approach.
