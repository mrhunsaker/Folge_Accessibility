# Configuration

The pipeline is configured through several files.

## pyproject.toml

Project metadata and Python dependencies managed by `uv`.

```toml
[project]
name = "folge-vision-pipeline"
version = "2026.7.18"
requires-python = ">=3.10"
dependencies = [
    "jsonschema>=4.17.0",
    "jinja2>=3.1.0",
    "requests>=2.28.0",
    "weasyprint>=60.0",
    "pymupdf>=1.23.0",
    "mkdocs>=1.6",
    "mkdocs-material>=9.5",
    "pymdown-extensions>=10.0",
]
```

To install all dependencies:

```bash
uv sync
```

## config.yaml

Pipeline configuration for Ollama, paths, output targets, and validation thresholds.

```yaml
project:
  name: "Folge Vision Publishing"
  version: "1.0.0"

ollama:
  base_url: "http://localhost:11434/v1"
  model: "qwen2.5vl:7b"
  timeout: 120
  rate_limit: 0.5
  max_workers: 2

paths:
  input_dir: "./input"
  output_dir: "./output"
  images_dir: "./images"
  templates_dir: "./templates"
  scripts_dir: "./scripts"

targets:
  - name: "pdf"
    lua_filter: "pdf-accessibility.lua"
  - name: "docx"
    lua_filter: "docx-accessibility.lua"
  - name: "html"
    lua_filter: "accessibility.lua"
  - name: "github"
    lua_filter: null

validation:
  min_confidence: 0.8
  max_alt_text_length: 150
```

## .env

Environment variables for Ollama connection and project paths.

```bash
# Ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5vl:7b
OLLAMA_TIMEOUT=120
OLLAMA_RATE_LIMIT=0.5
OLLAMA_MAX_WORKERS=2

# Paths
INPUT_DIR=./input
OUTPUT_DIR=./output
IMAGES_DIR=./images

# Validation
MIN_CONFIDENCE=0.8
MAX_ALT_TEXT_LENGTH=150
```

## mkdocs.yml

Documentation site configuration for MkDocs with Material theme. Controls navigation, theme, and Markdown extensions.

## Templates

### templates/prompt.txt

Jinja2 template for the Ollama vision prompt. Defines the schema the vision model should return and the rules for generating accessibility metadata.

### templates/markdown.md

Jinja2 template for rendering the enriched JSON into Markdown. Controls how steps, images, long descriptions, and page breaks are formatted.

## Customizing Behavior

### Change Vision Model

Edit `.env` or `config.yaml`:

```bash
OLLAMA_MODEL=llava:13b
```

### Adjust Validation Thresholds

Edit `config.yaml`:

```yaml
validation:
  min_confidence: 0.9  # More strict
```

Or pass as a command-line argument:

```bash
uv run python scripts/validate_content.py guide.enriched.json 0.9
```

### Change PDF Engine

Edit `scripts/publish.py` or `run_pipeline.py` to modify the engine fallback order. The default order is:

1. weasyprint
2. wkhtmltopdf
3. xelatex
