# Configuration

The pipeline is configured through several files. Settings follow a strict resolution order:

```
CLI argument  >  environment variable  >  config.yaml  >  hardcoded default
```

## pyproject.toml

Project metadata and Python dependencies managed by `uv`.

```toml
[project]
name = "folge-vision-pipeline"
dynamic = ["version"]
requires-python = ">=3.10"
dependencies = [
    "jsonschema>=4.17.0",
    "jinja2>=3.1.0",
    "requests>=2.28.0",
    "weasyprint>=60.0",
    "pymupdf>=1.23.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0",
]

[project.scripts]
folge-cli = "folge_cli.cli:main"

[project.optional-dependencies]
build = ["pyinstaller>=6.0"]
```

To install all dependencies:

```bash
uv sync
```

## config.yaml

Pipeline configuration for providers, paths, output targets, and validation thresholds.

```yaml
project:
  name: "Folge Vision Publishing"
  version: "2026.7.25"

provider: "ollama"  # Default provider

ollama:
  base_url: "http://localhost:11434/v1"
  model: "qwen2.5vl-8k:latest"
  timeout: 600
  max_workers: 2

openrouter:
  base_url: "https://openrouter.ai/api/v1"
  model: "qwen/qwen-2.5-vl-72b-instruct"
  timeout: 60
  max_workers: 4

# ... (see full config.yaml for all providers)

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
  min_confidence: 0.7
  max_alt_text_length: 150
```

## .env

Environment variables for provider selection, API keys, and paths.

```bash
# Provider selection (ollama is default)
PROVIDER=ollama

# Local providers (no API key needed)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5vl-8k:latest
OLLAMA_TIMEOUT=600

# Cloud providers (set API key)
OPENROUTER_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here

# Validation
MIN_CONFIDENCE=0.7
```

!!! warning "Security"
    Never commit `.env` to version control. It is already in `.gitignore`.

## Templates

### templates/prompt.txt

Jinja2 template for the Vision AI prompt. Defines the schema the vision model should return and the rules for generating accessibility metadata.

### templates/markdown.md

Jinja2 template for rendering the enriched JSON into Markdown. Controls how steps, images, long descriptions, and page breaks are formatted.

## Customizing Behavior

### Change Vision Provider

Edit `.env`:

```bash
PROVIDER=openrouter
OPENROUTER_API_KEY=your-key-here
OPENROUTER_MODEL=qwen/qwen-2.5-vl-72b-instruct
```

### Adjust Validation Thresholds

Edit `config.yaml`:

```yaml
validation:
  min_confidence: 0.9  # More strict
```

Or pass as a CLI argument:

```bash
folge-cli validate-content guide.enriched.json 0.9
```

### Change PDF Engine

The publish step tries PDF engines in this fallback order:

1. **weasyprint** (default, best PDF/UA support)
2. **wkhtmltopdf** (fallback)
3. **xelatex** (fallback)

All require Pandoc to be installed.
