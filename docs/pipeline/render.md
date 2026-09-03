# Step 6: Render Markdown

**What it does:** Converts `guide.enriched.json` into Markdown with embedded accessibility metadata and page breaks.

**Why it matters:**

- Creates human-readable Markdown
- Embeds `longdesc` attributes for Pandoc Lua filters
- Adds `\newpage` directives for PDF and DOCX page breaks
- Can include or exclude long descriptions based on target format

## Running

```bash
# For PDF (includes long descriptions and page breaks)
folge-cli render guide.enriched.json pdf guide.md

# For DOCX
folge-cli render guide.enriched.json docx guide.md

# For HTML (includes all accessibility metadata)
folge-cli render guide.enriched.json html guide.md

# For GitHub (minimal, no long descriptions)
folge-cli render guide.enriched.json github guide.md

# For Typst
folge-cli render guide.enriched.json typst guide.md

# For any of the 16 supported targets
folge-cli render guide.enriched.json <target> guide.md
```

## Target Configurations

Each target gets different rendering options. The `include_long_descriptions`
setting controls whether the `<div class="image-description">` block appears
in the output, which the Pandoc Lua filters use to inject accessibility metadata.

| Target | Long Descriptions | Page Breaks | OCR/UI Controls | Notes |
|--------|-------------------|-------------|-----------------|-------|
| `pdf` | Included | `\newpage` | No | Tagged PDF via Lua filter |
| `docx` | Included | `\newpage` | No | DOCX accessibility via Lua filter |
| `html` | Included | No | Included | ARIA attributes via Lua filter |
| `pptx` | Included | `\newpage` | No | PowerPoint via Lua filter |
| `github` | Excluded | No | No | Minimal Markdown, no long descriptions |
| `typst` | Included | No | No | Typst typesetting format |
| `asciidoc` | Included | No | No | AsciiDoc documentation |
| `beamer` | Included | `\newpage` | No | LaTeX Beamer presentations |
| `commonmark` | Included | No | No | CommonMark standard |
| `gfm` | Included | No | No | GitHub Flavored Markdown |
| `markdown_mmd` | Included | No | No | MultiMarkdown extensions |
| `markdown` | Included | No | No | Pandoc Markdown |
| `docbook` | Included | No | No | DocBook XML |
| `epub` | Included | No | No | Electronic publication |
| `odt` | Included | No | No | OpenDocument Text |
| `rst` | Included | No | No | reStructuredText |
| `latex` | Included | No | No | LaTeX source |

## How It Works

1. Loads `guide.enriched.json`
2. Loads the Jinja2 template from `templates/markdown.md`
3. Renders each step with:
    - Step title and body
    - Image with `alt_text` and `longdesc` attribute
    - Optional long description div
    - `\newpage` after each step (except last)
4. Applies target-specific configuration from the `TARGETS` registry

## Template

The Markdown template (`templates/markdown.md`) produces output like:

```markdown
# Guide Title

## Step 1: Open Settings

Click the Settings button in the sidebar.

![Settings window with sidebar](images/001.png){longdesc="The Settings window displays..."}

<div class="image-description">
**Image Description:** The Settings window displays a navigation sidebar on the left.
</div>

\newpage
```

The `longdesc` attribute is what the Pandoc Lua filters use to inject accessibility metadata into the final output formats.

### Manual Step Numbering

Each step carries a `step_label` field that controls its rendered heading.
The **merge** step seeds every step with the auto-number (`"Step 1"`,
`"Step 2"`, ...) and preserves hand-edited values, so by default output is
auto-numbered by position. Edit `step_label` in `guide.enriched.json` to
override it:

| `step_label` value | Rendered heading |
|---|---|
| `"Step 1"` (default seed) | `## Step 1 Title` |
| `"Step 2"` | `## Step 2 Title` |
| `""` (empty) | `## Title` (no step prefix) |
| `"Phase A"` | `## Phase A Title` (any custom text) |

The `##` heading level is always supplied by the template — only the text
(e.g. `"Step 1"`) goes in the JSON field, not `"## Step 1"`.

Because the label is stored verbatim per step, you control the sequence
directly — set `"Step 1"` to restart numbering at any slide, or set `""` to
skip a step prefix entirely. This is useful when different sections of a guide
have independent step sequences.

Example: a guide with two independent step sequences.

```json
"steps": [
  { "step_label": "Step 1", "title": "Open the app" },
  { "step_label": "Step 2", "title": "Configure the connection" },
  { "step_label": "Step 3", "title": "Save the profile" },
  { "step_label": "Step 1", "title": "Sync the device" },
  { "step_label": "Step 2", "title": "Verify sync status" }
]
```

## Data-Driven Targets

The rendering pipeline uses a data-driven `TARGETS` registry rather than
individual if-blocks for each format. This makes adding new output formats
trivial — just add an entry to the registry with the target name and
configuration options.
