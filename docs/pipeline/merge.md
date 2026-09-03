# Step 3: Deterministic Merge

**What it does:** Combines `guide.json` (your authored content) with `vision-results.json` (AI-generated enrichment) into a single, enriched JSON file.

**Why it matters:**

- **Deterministic**: Uses `step_id` as the primary key, not filenames
- **Non-destructive**: Original authored content is preserved exactly
- **Single source of truth**: `guide.enriched.json` becomes your publishing source

## Running

```bash
folge-cli merge ~/Documents/FolgeProjects/my-guide/my-export.json \
  ~/Documents/FolgeProjects/my-guide/output/vision-results.json \
  ~/Documents/FolgeProjects/my-guide/output/guide.enriched.json
# or: uv run python scripts/merge.py guide.json vision-results.json guide.enriched.json
```

## How It Works

1. Loads both input files
2. Creates a lookup table from vision results by `step_id`
3. For each step in the guide:
    - Creates a copy (never modifies the original)
    - Finds matching vision data by `step_id`
    - Adds the `vision` field with all AI-generated content
    - Ensures a `step_label` is present (preserving any prior value, else seeding the auto-number)
    - Preserves all original fields
4. Logs warnings for any mismatches
5. Saves to `guide.enriched.json`

## Merge Rules

| Rule | Description |
|------|-------------|
| Primary key | `step_id` (never filenames) |
| Only replaces | The `vision` field |
| Preserves | All authored fields from `guide.json` |
| On missing data | Continues with warnings |

## Manual Step Labels

`step_label` is a **merge-managed** field that is independent of `guide.json`
(which never provides one). The merge step guarantees every output step carries
a `step_label`:

- **Seeded by default** — steps without an existing label get the auto-number
  (`"Step 1"`, `"Step 2"`, ...) matching their position, so output is unchanged
  until you edit it.
- **Preserved on re-merge** — hand-edited values are carried forward by
  `step_id` from the existing `guide.enriched.json`, so manual labels survive
  recomputes.

Edit `step_label` directly in `guide.enriched.json`. You never need to touch
`guide.json` to control step numbering:

| `step_label` value | Rendered heading |
|---|---|
| `"Step 1"` (default seed) | `## Step 1 Title` |
| `"Step 2"` | `## Step 2 Title` |
| `""` (empty) | `## Title` (no step prefix) |
| `"Phase A"` | `## Phase A Title` (any custom text) |

For a description of how `step_label` affects rendering, see the
[Render step](render.md#manual-step-numbering).

## HTML Escaping of `long_description`

When writing `guide.enriched.json`, the merge step **HTML-escapes** the vision
model's `long_description` field using `html.escape(..., quote=True)`.

!!! note "Why"
    The vision model sometimes embeds literal HTML tags in its descriptions —
    for example a screenshot may be described as "planned as `<h4>`". If those
    tags are not escaped, an HTML intermediary (WeasyPrint, pandoc's HTML
    output, etc.) interprets them as real markup and opens an unmatched
    heading (`<h3>`/`<h4>`), hiding the surrounding text instead of showing
    it.

With escaping, the stored value becomes `planned as &lt;h4&gt;`, which renders
as literal text.

Only the `long_description` field is escaped. `alt_text`, `ocr_text`, and
`ui_controls` are stored exactly as the model returned them.

## Output

**File created:** `guide.enriched.json` (in `<project>/output/`)

This is your **source of truth for publishing**. It contains the original guide content plus the vision enrichment data, ready for validation and rendering.

!!! info
    If you re-run the vision processing (e.g., with a different model), you can re-run the merge step to update `guide.enriched.json` without touching `guide.json`.
