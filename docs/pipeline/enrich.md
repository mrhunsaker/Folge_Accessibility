# Step 2: Enrich with Vision AI

**What it does:** Sends each screenshot to Ollama's vision model to generate accessibility metadata.

**Why it matters:** This adds the accessibility metadata that makes your documentation usable by screen readers and compliant with WCAG, ARIA, and PDF/UA.

## Running

Using a project folder (recommended):

```bash
folge-cli batch-process --project my-guide
```

Or with explicit paths (paths default to `<project>/images` and
`<project>/output/vision-results.json` when using `--project`):

```bash
uv run python scripts/batch_process.py guide.json images/ vision-results.json
folge-cli batch-process guide.json images/ vision-results.json
```

## What It Generates

For each step with an image, the vision model produces:

| Field | Type | Description |
|-------|------|-------------|
| `alt_text` | string | Short description for screen readers (max 150 chars) |
| `long_description` | string | Detailed description (2-4 sentences) |
| `ocr_text` | array | Text extracted from the image |
| `ui_controls` | array | Detected UI elements with type and label |
| `important_element` | string | Primary focus element (max 200 chars) |
| `confidence` | number | Model's confidence score (0.0-1.0) |

### UI Control Types

The `ui_controls` array uses these types:

`button`, `text_field`, `dropdown`, `checkbox`, `radio`, `slider`, `navigation`, `menu`, `tab`, `icon`, `link`, `other`

## How It Works

1. Reads `guide.json` to get step information
2. For each step with an image:
    - Loads the image from `images/`
    - Generates a context-aware prompt using the step title, body, and surrounding steps
    - Sends the image and prompt to the Ollama Vision API
    - Parses the JSON response
3. Rate-limits requests (0.5s between calls) to avoid overloading the model
4. Saves all responses to `vision-results.json`

## Custom Vision Prompts

By default, each step sends the built-in prompt from `src/folge_cli/batch_process.py`.
You can select an alternate prompt generator for cases that need a highly
customized instruction (for example, a specific application's editor layout):

```bash
folge-cli batch-process --project my-guide --prompt brailleblaster
folge-cli pipeline --project my-guide --prompt brailleblaster
```

Prompt modules live in `src/folge_cli/prompts/`. Each module exposes a single
function:

```python
def generate_prompt(step, guide_title, previous_step=None, next_step=None):
    ...
```

Adding a new `.py` file to that folder **automatically registers** the prompt:
its module name immediately becomes a valid `--prompt` choice (the flag's
`choices` are discovered from the folder contents).

### Scaffolding a new prompt

Use `folge-cli new-prompt` to generate a correctly formed prompt module
rather than typing the boilerplate by hand:

```bash
folge-cli new-prompt my-special-case
# Creates src/folge_cli/prompts/my_special_case.py with the standard
# generate_prompt() signature and JSON-schema prompt template.
```

- The name is normalized to a safe identifier (e.g. `My Special Case` →
  `my_special_case`) and validated to prevent typos.
- Existing modules are **not** overwritten unless you pass `--force`.
- The created module is immediately available as a `--prompt` choice.

The bundled `brailleblaster` example shows how to give the model a mandatory
opening sentence for a specific tool's window layout.

## Configuration

The vision processing is configured in `.env` and `config.yaml`:

| Setting | Default | Description |
|---------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen2.5vl-8k:latest` | Vision model to use |
| `OLLAMA_TIMEOUT` | `120` | Request timeout in seconds |
| `OLLAMA_RATE_LIMIT` | `0.5` | Seconds between requests |
| `OLLAMA_MAX_WORKERS` | `2` | Parallel request workers |

## Output

**File created:** `vision-results.json` (in `<project>/output/`)

```json
{
  "schema_version": "1.0",
  "guide_id": "...",
  "title": "...",
  "processed_at": "2026-07-18T00:00:00Z",
  "model": "qwen2.5vl-8k:latest",
  "steps": [
    {
      "step_id": 1,
      "vision": {
        "alt_text": "Settings window with sidebar",
        "long_description": "The Settings window displays a navigation sidebar...",
        "ocr_text": ["Settings", "Network", "Privacy"],
        "ui_controls": [{"type": "navigation", "label": "Settings"}],
        "important_element": "Settings category",
        "confidence": 0.96
      }
    }
  ]
}
```

## Prerequisites

- Ollama must be running locally (`ollama serve`)
- The `qwen2.5vl-8k:latest` model must be pulled (`ollama pull qwen2.5vl-8k:latest`)
- Images must be present in `images/`
