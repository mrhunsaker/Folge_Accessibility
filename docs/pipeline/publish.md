# Step 7: Publish

**What it does:** Converts Markdown to every output format the installed
pandoc supports via Pandoc, with Lua filter accessibility metadata injection.

**Why it matters:**

- **PDF**: Tagged PDF with page breaks, PDF/UA compliance from enhanced filter
- **DOCX/PPTX**: Accessibility metadata in OpenXML format
- **HTML**: Self-contained with ARIA attributes, embedded resources
- **EPUB**: Electronic publication with embedded resources
- **Typst, AsciiDoc, LaTeX, RST, DocBook**: Typesetting and documentation formats
- **Markdown variants**: Markdown, CommonMark, GitHub Flavored, MultiMarkdown, and more

## Running

### Via the Pipeline Orchestrator

```bash
folge-cli pipeline --project my-guide --targets pdf,docx,html
# or: folge-cli pipeline guide.json output/ --targets pdf,docx,html
```

### Via the Standalone Publish Script

```bash
folge-cli publish --project my-guide pdf,docx,html
# or: folge-cli publish guide.json output/ --targets pdf,docx,html
```

### With Orientation Flag

```bash
# Letter portrait (default)
folge-cli publish --project my-guide pdf

# Letter landscape
folge-cli publish --project my-guide pdf --orientation landscape
```

### All Targets

Omitting `--targets` produces **every format supported by the installed
pandoc**; writers absent from that pandoc version (e.g. `ansi`, `bbcode*`,
`djot` on 3.1.x) are skipped with a warning.  The registry lives in
`src/folge_cli/formats.py`.  To build everything explicitly:

```bash
folge-cli publish --project my-guide
```

Or a specific subset:

```bash
folge-cli publish --project my-guide pdf,docx,html,pptx,github,typst,asciidoc,beamer,commonmark,gfm,markdown_mmd,docbook,epub,odt,rst,latex
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

# HTML (self-contained)
pandoc guide.md --lua-filter=accessibility.lua --standalone --embed-resources -o guide.html

# EPUB (self-contained)
pandoc guide.md --embed-resources -o guide.epub

# Typst
pandoc guide.md -t typst -o guide.typ

# LaTeX
pandoc guide.md -t latex -o guide.tex
```

## Output Formats

### Primary Formats (with Lua Filters)

| Format | Target | `--to` Value | Lua Filter | Extension | Notes |
|--------|--------|-------------|------------|-----------|-------|
| PDF | `pdf` | `pdf` (weasyprint engine) | `pdf-accessibility.lua` | `.pdf` | Tagged PDF/UA compliant |
| DOCX | `docx` | `docx` | `docx-accessibility.lua` | `.docx` | Accessibility metadata |
| HTML | `html` | `html` | `accessibility.lua` | `.html` | Self-contained, ARIA |
| PPTX | `pptx` | `pptx` | `docx-accessibility.lua` | `.pptx` | Accessibility metadata |
| GitHub | `github` | `gfm` | none | `.md` | Minimal, no long descriptions |

### Markdown Variants

| Format | Target | `--to` Value | Extension | Notes |
|--------|--------|-------------|-----------|-------|
| CommonMark | `commonmark` | `commonmark` | `_cm.md` | Standard CommonMark |
| GitHub Flavored | `gfm` | `gfm` | `_gh.md` | With long descriptions |
| MultiMarkdown | `markdown_mmd` | `markdown_mmd` | `_mmd.md` | MultiMarkdown extensions |

Other markdown/text variants (Markdown `_md.md`, CommonMark X `_cmx.md`,
PHP Extra `_phpextra.md`, Markdown Strict `_strict.md`, Markua `_markua.md`,
Plain `_plain.txt`, Org `.org`, Textile `.textile`, Texinfo `.texi`, man
`.1`, ms `.ms`, Djot `.djot`, wiki dialects, and BBCode variants) follow
the same `guide_<abbrev>.<ext>` convention.

### Typesetting and Document Formats

| Format | Target | `--to` Value | Extension | Notes |
|--------|--------|-------------|-----------|-------|
| Typst | `typst` | `typst` | `.typ` | Modern typesetting |
| LaTeX | `latex` | `latex` | `.tex` | LaTeX source |
| AsciiDoc | `asciidoc` | `asciidoc` | `.adoc` | Documentation format |
| reStructuredText | `rst` | `rst` | `.rst` | Python docs format |
| DocBook XML | `docbook` | `docbook` | `.xml` | Structured documentation |
| Beamer | `beamer` | `beamer` | `_beamer.pdf` | LaTeX presentations |
| ODT | `odt` | `odt` | `.odt` | OpenDocument Text |
| EPUB | `epub` | `epub` | `.epub` | Electronic publication |

## PDF Engine Fallback Order

The publish step tries PDF engines in order:

| Priority | Engine | Notes |
|----------|--------|-------|
| 1 | **weasyprint** | Free, best PDF/UA support |
| 2 | **wkhtmltopdf** | Free, basic tagging |
| 3 | **xelatex** | Free, requires texlive |

If one engine fails, the next is tried automatically.

## Lua Filters

Each primary output format uses a specific Lua filter that injects accessibility metadata:

| Filter | Target | Adds | PDF/UA Support |
|--------|--------|------|----------------|
| `pdf-accessibility.lua` | PDF | `/Alt`, `/E`, explicit tags | Full PDF/UA |
| `docx-accessibility.lua` | DOCX, PPTX | `description` field, alt text | Full |
| `accessibility.lua` | HTML | `aria-description`, `aria-label` | Full |

Markdown variants (markdown, commonmark, gfm, markdown_mmd), Typst, AsciiDoc,
LaTeX, RST, DocBook, ODT, and EPUB do not use Lua filters — Pandoc handles the
conversion natively.

See [Lua Filters Reference](../reference/lua-filters.md) for detailed documentation.

## Self-Contained Output

HTML, EPUB, and slide outputs are self-contained by default:

- **HTML/Slides**: Uses `--standalone --embed-resources` to embed all CSS, fonts, and images
- **EPUB**: Uses `--embed-resources` to embed all resources

## Verbose Logging

Every pandoc invocation runs with `--standalone` (so each file carries the
document metadata from `metadata.yaml`) and `--verbose`.  Its stdout/stderr
is appended to `<output>/pandoc.log` under a header with the timestamp,
command, and exit code.

## Custom Fonts

PDF and HTML outputs use accessible fonts via `templates/folge.css`:

- **Atkinson Hyperlegible Next** (variable weight) — optimized for low vision
- **AtkynsonMonoNerdFont** (static OTF) — monospace font for code blocks

## Output Validation

After publishing, the pipeline validates the PDF:

```bash
# Quick check
pdfinfo output/guide.pdf | grep -i tagged
# Expected: Tagged: yes

# Detailed validation
folge-cli validate-pdf output/guide.pdf
```

See [PDF/UA Guarantee](../pdf-ua.md) for full details on the compliance approach.
