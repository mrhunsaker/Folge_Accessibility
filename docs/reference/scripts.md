# Scripts Reference

All scripts live in the `scripts/` directory and are run via `uv run`.

## run_pipeline.py

**Location:** `run_pipeline.py` (project root)

Master orchestrator that runs the full pipeline.

```bash
uv run run_pipeline.py <guide.json> [output-dir] [--targets pdf,docx,html]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `guide` | (required) | Path to `guide.json` |
| `output` | `output/` | Output directory |
| `--targets` | `pdf,docx,html` | Comma-separated target formats |

**Additional targets:** `github` (generates clean Markdown)

### What It Does

1. Checks prerequisites (Python, uv, Pandoc, Ollama)
2. Creates required directories (`images/`, `output/`, `schemas/`)
3. Runs all 6 pipeline stages
4. Validates the PDF output
5. Prints a summary with file sizes and timing

---

## scripts/batch_process.py

Processes all images through the Ollama Vision API.

```bash
uv run python scripts/batch_process.py <guide.json> <images-dir> <output.json>
```

| Argument | Description |
|----------|-------------|
| `guide.json` | Folge export file |
| `images-dir` | Directory containing screenshots |
| `output.json` | Where to save vision results |

**Key behaviors:**

- Uses `qwen2.5vl:7b` model (configurable via env)
- Rate-limits requests (0.5s between calls)
- Parallel workers (default: 2)
- Handles JSON parse errors gracefully
- Returns error objects for failed steps instead of crashing

---

## scripts/merge.py

Merges guide content with vision results using `step_id` as the primary key.

```bash
uv run python scripts/merge.py <guide.json> <vision-results.json> <output.json>
```

| Argument | Description |
|----------|-------------|
| `guide.json` | Original Folge export |
| `vision-results.json` | Output from batch_process.py |
| `output.json` | Enriched output file |

**Key behaviors:**

- Never modifies `guide.json`
- Adds only the `vision` field to each step
- Logs warnings for unmatched step IDs
- Preserves all original authored fields

---

## scripts/render.py

Renders Markdown from enriched JSON using Jinja2 templates.

```bash
uv run python scripts/render.py <guide.enriched.json> [target] <output.md>
```

| Argument | Description |
|----------|-------------|
| `guide.enriched.json` | Enriched guide file |
| `target` | `pdf`, `docx`, `html`, or `github` |
| `output.md` | Output Markdown file |

**Target-specific behavior:**

| Target | Long Descriptions | Page Breaks | OCR/Controls |
|--------|-------------------|-------------|--------------|
| `pdf` | Yes | Yes | No |
| `docx` | Yes | Yes | No |
| `html` | Yes | No | Yes |
| `github` | No | No | No |

---

## scripts/validate_schema.py

Validates JSON against the canonical enriched guide schema.

```bash
uv run python scripts/validate_schema.py <json-file> [json-file2 ...]
```

Validates one or more JSON files. Uses an embedded schema (no external schema file needed).

**Checks:**

- Required fields: `schema_version`, `guide_id`, `title`, `steps`
- Data types and constraints
- No extra fields (strict mode)

---

## scripts/validate_content.py

Validates content quality of enriched JSON.

```bash
uv run python scripts/validate_content.py <json-file> [min-confidence]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `json-file` | (required) | Enriched JSON to validate |
| `min-confidence` | `0.8` | Minimum confidence threshold |

**Checks:**

- `alt_text` <= 150 characters
- `long_description` is 2-4 sentences
- `confidence` >= threshold
- Required vision fields present
- Unique `step_id` values

---

## scripts/publish.py

Standalone publish script with PDF/UA guarantee. Runs steps 1-6.

```bash
uv run python scripts/publish.py <guide.json> <output-dir> [targets]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `guide.json` | (required) | Folge export file |
| `output-dir` | `output/` | Output directory |
| `targets` | `pdf,docx,html` | Comma-separated formats |

---

## scripts/validate_pdf.py

Validates PDF for PDF/UA compliance and tagging.

```bash
uv run python scripts/validate_pdf.py <pdf-file>
```

Uses two validation methods:

1. **pdfinfo** (if poppler-utils installed) -- checks tagged status, PDF version, metadata
2. **pymupdf** -- checks `is_tagged`, `is_pdf_ua`, `pdf_version`, `has_structure`
