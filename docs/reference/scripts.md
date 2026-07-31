# CLI Reference

The `folge-cli` command provides ten subcommands. It can be installed as a
Python package or used as a pre-built executable.

## folge-cli (installed)

```bash
folge-cli <subcommand> [arguments]
```

## folge-cli (pre-built binary)

Download from [GitHub Releases](https://github.com/mrhunsaker/Folge_Accessibility/releases).
The binary bundles all Python dependencies. Pandoc and a vision provider are
still required at runtime.

---

## pipeline

Full end-to-end pipeline with progress tracking (source installation only).

```bash
folge-cli pipeline <guide.json> [output-dir] [--targets pdf,docx,html] [--provider PROVIDER]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `guide` | (required) | Path to `guide.json` |
| `output` | `output/` | Output directory |
| `--targets` | `pdf,docx,html,pptx` | Comma-separated target formats |
| `--provider` | `ollama` | Vision AI provider |

!!! note
    The `pipeline` subcommand requires `uv` and Python because it spawns
    subprocess calls. Use the pre-built binary with individual subcommands
    for a lightweight workflow.

---

## batch-process

Process all images through the Vision AI API.

```bash
folge-cli batch-process <guide.json> <images-dir> <output.json> [--provider PROVIDER]
```

| Argument | Description |
|----------|-------------|
| `guide.json` | Folge export file |
| `images-dir` | Directory containing screenshots |
| `output.json` | Where to save vision results |
| `--provider` | Vision backend (default: from `.env`) |
| `--api-key` | API key for cloud providers |

**Key behaviors:**

- Configurable model via provider settings
- Parallel workers (default: 2 for local, 4 for cloud)
- Handles JSON parse errors gracefully
- Returns error objects for failed steps instead of crashing
- Progress counter shows completion status

---

## merge

Merges guide content with vision results using `step_id` as the primary key.

```bash
folge-cli merge <guide.json> <vision-results.json> <output.json>
```

| Argument | Description |
|----------|-------------|
| `guide.json` | Original Folge export |
| `vision-results.json` | Output from batch-process |
| `output.json` | Enriched output file |

**Key behaviors:**

- Never modifies `guide.json`
- Adds only the `vision` field to each step
- Logs warnings for unmatched step IDs
- Preserves all original authored fields

---

## render

Renders Markdown from enriched JSON using Jinja2 templates.

```bash
folge-cli render <guide.enriched.json> [target] <output.md>
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

## validate-schema

Validates JSON against the canonical enriched guide schema.

```bash
folge-cli validate-schema <json-file> [json-file2 ...] [--warnings-out <file>]
```

Validates one or more JSON files. Uses an embedded schema.

**Checks:**

- Required fields: `schema_version`, `guide_id`, `title`, `steps`
- Data types and constraints
- Length warnings (non-blocking)

---

## validate-content

Validates content quality of enriched JSON.

```bash
folge-cli validate-content <json-file> [min-confidence]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `json-file` | (required) | Enriched JSON to validate |
| `min-confidence` | `0.7` (from env/config) | Minimum confidence threshold |

**Checks:**

- `alt_text` <= 150 characters
- `long_description` is 2-4 sentences
- `confidence` >= threshold
- Required vision fields present
- Unique `step_id` values

---

## validate-pdf

Validates PDF for PDF/UA compliance and tagging.

```bash
folge-cli validate-pdf <pdf-file>
```

Uses two validation methods:

1. **pdfinfo** (if poppler-utils installed) — checks tagged status, PDF version, metadata
2. **pymupdf** — checks `is_tagged`, `is_pdf_ua`, `pdf_version`, `has_structure`

---

## publish

Publishes guide to target formats with PDF/UA guarantee.

```bash
folge-cli publish <guide.json> [output-dir] [targets] [provider]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `guide.json` | (required) | Folge export file |
| `output-dir` | `output/` | Output directory |
| `targets` | `pdf,docx,html` | Comma-separated formats |
| `provider` | `ollama` | Vision provider |

---

## metadata

Generates accessible-document metadata (title, author, subject, keywords,
language, structure tags, bookmarks, and security) for all output formats.

```bash
folge-cli metadata <guide.json> [-o metadata.yaml] [--apply-pdf guide.pdf] [--check] [--strict]
```

| Argument | Description |
|----------|-------------|
| `guide.json` | Folge export or enriched guide file |
| `-o, --out` | Write a Pandoc-compatible `metadata.yaml` to this path |
| `--apply-pdf` | Embed metadata into this PDF and allow text copying |
| `--check` | Check metadata against accessibility best practices |
| `--strict` | Exit 1 when `--check` finds issues |
| `--author` | Override the document author |
| `--subject` | Override the document subject |
| `--language` | Override the primary document language |
| `--keywords` | Override keywords (comma/semicolon separated) |

**Key behaviors:**

- Emits a Pandoc-compatible `metadata.yaml` that is embedded into every
  output format via `--metadata-file` (DOCX/ODT core properties, HTML
  `<meta>` and `<html lang>`, EPUB OPF, and more)
- `--apply-pdf` writes the PDF Info dictionary and `/Lang` entry with
  PyMuPDF, generates an outline from headings, and strips restrictive
  security handlers so text copying is always allowed
- `--check --strict` flags violations such as generic titles ("Document 1"),
  missing author/subject/keywords, and unset language

See [Accessible Document Metadata](../accessibility-metadata.md) for the full
standard and examples.

---

## generate-manual-attention

Generates a markdown file listing items that need manual review.

```bash
folge-cli generate-manual-attention <enriched.json> <images-dir> <output.md> [warnings.json]
```

| Argument | Description |
|----------|-------------|
| `enriched.json` | Enriched guide file |
| `images-dir` | Directory containing screenshots |
| `output.md` | Output markdown file |
| `warnings.json` | Optional warnings from schema validation |
