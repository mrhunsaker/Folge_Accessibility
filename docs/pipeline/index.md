# Pipeline Overview

The Folge Vision Publishing Pipeline transforms [Folge](https://folge.me) guide exports into accessible, multi-format documentation through seven stages.

## Architecture

Each guide lives in its own **project folder** under
`~/Documents/FolgeProjects/<project>/`. The folder holds the guide JSON
(any name — it must be the only top-level JSON), `images/` with the
screenshots, and `output/` where every generated file is written:

```text
~/Documents/FolgeProjects/my-guide/
├── my-export.json      # guide export from Folge (any name, only JSON here)
├── images/             # screenshots (step-0.png, step-1.png, ...)
└── output/             # created automatically
    ├── vision-results.json
    ├── guide.enriched.json
    ├── guide.md
    ├── guide.pdf
    └── ...
```

```text
guide.json + images/  (inside the project folder)
        |
        v
  [1] Batch Process  -->  vision-results.json
        |
        v
  [2] Merge          -->  guide.enriched.json
        |
        v
  [3] Validate           (schema + content quality)
        |
        v
  [3b] Manual Review     (operator review, optional re-verify)
        |
        v
  [4] Render         -->  guide.md
        |
        v
  [5] Publish        -->  16 output formats
        |                    |
        |                    +--> guide.pdf       (PDF/UA tagged PDF)
        |                    +--> guide.docx      (Word document)
        |                    +--> guide.html      (self-contained HTML)
        |                    +--> guide.pptx      (PowerPoint)
        |                    +--> guide.md        (GitHub Markdown)
        |                    +--> guide.typ       (Typst)
        |                    +--> guide.adoc      (AsciiDoc)
        |                    +--> guide_beamer.pdf (Beamer)
        |                    +--> guide_cm.md     (CommonMark)
        |                    +--> guide_gh.md     (GFM)
        |                    +--> guide_mmd.md    (MultiMarkdown)
        |                    +--> guide.xml       (DocBook)
        |                    +--> guide.epub      (EPUB)
        |                    +--> guide.odt       (OpenDocument)
        |                    +--> guide.rst       (reStructuredText)
        |                    +--> guide.tex       (LaTeX)
        |                    +--> ...             (every other format the
        |                                          installed pandoc supports)
        v
  [6] Validate PDF       (PDF/UA compliance check)
```

## Design Principles

### Deterministic

Same input always produces the same output. The merge step uses `step_id` as the primary key, not filenames, so renaming images or re-exporting does not break the pipeline.

### Non-Destructive

The original `guide.json` is never modified. Only a new `vision` field is added during the merge step. Your authored content is always preserved exactly.

### Separation of Concerns

Authored content (`guide.json`) and AI-generated enrichment (`vision-results.json`) are kept separate until the deterministic merge step. This makes it easy to re-run vision processing without losing manual edits.

### Extensible

The enriched JSON uses a versioned schema (`schema_version: "1.0"`). Future versions can add new fields without breaking existing tools. The `TARGETS` registry makes adding new output formats trivial.

## Running the Pipeline

### Full Pipeline (Source Installation)

```bash
folge-cli pipeline --project my-guide
```

`--project` looks up the guide JSON automatically in
`~/Documents/FolgeProjects/my-guide/`. The orchestrator handles all stages
with progress tracking, checks prerequisites, and validates the output.

You can also pass explicit paths instead of `--project`:

```bash
folge-cli pipeline /path/to/my-export.json /some/output-dir
```

### Individual Steps (Binary or Source)

Chain the individual subcommands for a lightweight workflow. `batch-process`,
`pipeline`, and `publish` accept `--project NAME`; the other stages take
explicit paths:

```bash
folge-cli batch-process --project my-guide
folge-cli merge ~/Documents/FolgeProjects/my-guide/my-export.json \
  ~/Documents/FolgeProjects/my-guide/output/vision-results.json \
  ~/Documents/FolgeProjects/my-guide/output/guide.enriched.json
folge-cli validate-schema ~/Documents/FolgeProjects/my-guide/output/guide.enriched.json
folge-cli validate-content ~/Documents/FolgeProjects/my-guide/output/guide.enriched.json 0.7
folge-cli render ~/Documents/FolgeProjects/my-guide/output/guide.enriched.json pdf guide.md
folge-cli publish --project my-guide pdf,docx,html,epub,typst
```

### Check Version

```bash
folge-cli --version
```

### Orientation Control

```bash
# Letter portrait (default)
folge-cli publish --project my-guide pdf

# Letter landscape
folge-cli publish --project my-guide pdf --orientation landscape
```

## Stage Details

Each stage is documented in detail in its own page:

1. [Export from Folge](export.md) -- Get your guide and screenshots
2. [Enrich with Vision AI](enrich.md) -- Generate accessibility metadata
3. [Deterministic Merge](merge.md) -- Combine content with enrichment
4. [Validate](validate.md) -- Ensure data quality
5. [Render Markdown](render.md) -- Generate intermediate Markdown
6. [Publish](publish.md) -- Convert to 16 output formats with PDF/UA guarantee
