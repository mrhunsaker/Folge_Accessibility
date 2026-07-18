# Step 5: Render Markdown

**What it does:** Converts `guide.enriched.json` into Markdown with embedded accessibility metadata and page breaks.

**Why it matters:**

- Creates human-readable Markdown
- Embeds `longdesc` attributes for Pandoc Lua filters
- Adds `\newpage` directives for PDF and DOCX page breaks
- Can include or exclude long descriptions based on target format

## Running

```bash
# For PDF (includes long descriptions and page breaks)
uv run python scripts/render.py guide.enriched.json pdf guide.md

# For DOCX
uv run python scripts/render.py guide.enriched.json docx guide.md

# For HTML (includes all accessibility metadata)
uv run python scripts/render.py guide.enriched.json html guide.md

# For GitHub (minimal, no long descriptions)
uv run python scripts/render.py guide.enriched.json github guide.md
```

## Target Configurations

Each target gets different rendering options:

| Target | Long Descriptions | Page Breaks | OCR/UI Controls |
|--------|-------------------|-------------|-----------------|
| `pdf` | Included | `\newpage` | No |
| `docx` | Included | `\newpage` | No |
| `html` | Included | No | Included |
| `github` | Excluded | No | No |

## How It Works

1. Loads `guide.enriched.json`
2. Loads the Jinja2 template from `templates/markdown.md`
3. Renders each step with:
    - Step title and body
    - Image with `alt_text` and `longdesc` attribute
    - Optional long description div
    - `\newpage` after each step (except last)
4. Applies target-specific configuration

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
