# Pipeline Overview

The Folge Vision Publishing Pipeline transforms Folge guide exports into accessible, multi-format documentation through seven stages.

## Architecture

```
guide.json + images/
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
  [5] Publish        -->  guide.pdf / guide.docx / guide.html
        |
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

The enriched JSON uses a versioned schema (`schema_version: "1.0"`). Future versions can add new fields without breaking existing tools.

## Running the Pipeline

### Full Pipeline (Source Installation)

```bash
folge-cli pipeline guide.json output/
```

The orchestrator handles all stages with progress tracking, checks prerequisites, and validates the output.

### Individual Steps (Binary or Source)

Chain the individual subcommands for a lightweight workflow:

```bash
folge-cli batch-process guide.json images/ vision-results.json
folge-cli merge guide.json vision-results.json guide.enriched.json
folge-cli validate-schema guide.enriched.json
folge-cli validate-content guide.enriched.json 0.7
folge-cli render guide.enriched.json pdf guide.md
folge-cli publish guide.json output/ pdf,docx,html
```

## Stage Details

Each stage is documented in detail in its own page:

1. [Export from Folge](export.md) -- Get your guide and screenshots
2. [Enrich with Vision AI](enrich.md) -- Generate accessibility metadata
3. [Deterministic Merge](merge.md) -- Combine content with enrichment
4. [Validate](validate.md) -- Ensure data quality
5. [Render Markdown](render.md) -- Generate intermediate Markdown
6. [Publish](publish.md) -- Convert to final formats with PDF/UA guarantee
