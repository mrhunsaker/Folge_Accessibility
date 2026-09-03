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
  [5] Publish        -->  every supported output format
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

### Resume from a Stage

By default the pipeline always starts at the beginning. If a run is
interrupted (e.g. by a power outage) or you only need to regenerate part of
the output, use `--first-step` to start from a specific stage and skip
everything before it:

```bash
# Pick up mid-pipeline after an interruption
folge-cli pipeline --project my-guide --first-step 5

# Re-run only validation + manual review
folge-cli pipeline --project my-guide --first-step 4
```

Valid `--first-step` values map to the stage numbers below:

| `--first-step` | Stage | Requires existing |
|----------------|-------|-------------------|
| `1` | Batch vision processing (stages 1-2) | `guide.json` + images |
| `3` | Merge | `vision-results.json` (reused from disk) |
| `4` | Validate | `guide.enriched.json` |
| `4b` | Manual review | `guide.enriched.json` |
| `5` | Render | `guide.enriched.json` |
| `5b` | Metadata | `guide.enriched.json` |
| `6` | Publish | `guide.enriched.json` + `guide.md` |

Starting at `4` or later errors out with a clear message if
`guide.enriched.json` is missing, so you cannot accidentally resume from a
point with no prerequisite data. Every skipped stage's interactive prompts
(the reuse-vision prompt and the manual-review pause, for example) are
bypassed as well.

When resuming, the pipeline **discovers the intermediate files by their
on-disk names** in the output directory rather than assuming they were
created on the current date. A project last run on an earlier day (e.g.
files named `Headings-2026-08-28.enriched.json`) is therefore resumed
correctly. In particular, `--first-step 3` **reuses** the existing
`*-vision-results.json` (it does not regenerate vision data) and errors if
that file is missing.

## Stage Details

Each stage is documented in detail in its own page:

1. [Export from Folge](export.md) -- Get your guide and screenshots
2. [Enrich with Vision AI](enrich.md) -- Generate accessibility metadata
3. [Deterministic Merge](merge.md) -- Combine content with enrichment
4. [Validate](validate.md) -- Ensure data quality
5. [Render Markdown](render.md) -- Generate intermediate Markdown
6. [Publish](publish.md) -- Convert to every format the installed pandoc supports with PDF/UA guarantee
