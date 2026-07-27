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

Pipeline configuration for providers, paths, output targets (16 formats), and validation thresholds.

The `project.version` field is injected dynamically from `_version.py` — you do not need to set it manually.

```yaml
project:
  name: "Folge Vision Publishing"
  description: "Automated documentation publishing with vision enrichment"

provider: "ollama"  # Default provider

ollama:
  base_url: "http://localhost:11434/v1"
  model: "qwen2.5vl-8k:latest"
  timeout: 600
  max_workers: 2
  retries: 3
  retry_delay: 5
  image_max_width: 1024
  warmup: true

openrouter:
  base_url: "https://openrouter.ai/api/v1"
  model: "qwen/qwen-2.5-vl-72b-instruct"
  timeout: 60
  max_workers: 4
  retries: 2
  retry_delay: 2
  image_max_width: 1024

# ... (see full config.yaml for all 7 providers)

targets:
  - name: "pdf"
    enabled: true
    include_long_descriptions: true
    lua_filter: "pdf-accessibility.lua"
    output_extension: ".pdf"
    orientation: "portrait"         # portrait or landscape

  - name: "docx"
    enabled: true
    include_long_descriptions: true
    lua_filter: "docx-accessibility.lua"
    output_extension: ".docx"

  - name: "html"
    enabled: true
    include_long_descriptions: true
    include_ocr: true
    include_ui_controls: true
    lua_filter: "accessibility.lua"
    output_extension: ".html"

  - name: "pptx"
    enabled: true
    include_long_descriptions: true
    lua_filter: "docx-accessibility.lua"
    output_extension: ".pptx"

  - name: "github"
    enabled: true
    include_long_descriptions: false
    lua_filter: null
    output_extension: ".md"

  - name: "typst"
    enabled: true
    include_long_descriptions: true
    output_extension: ".typ"

  - name: "asciidoc"
    enabled: true
    include_long_descriptions: true
    output_extension: ".adoc"

  - name: "beamer"
    enabled: true
    include_long_descriptions: true
    output_extension: "_beamer.pdf"

  - name: "commonmark"
    enabled: true
    include_long_descriptions: true
    output_extension: "_cm.md"

  - name: "gfm"
    enabled: true
    include_long_descriptions: true
    output_extension: "_gh.md"

  - name: "multimarkdown"
    enabled: true
    include_long_descriptions: true
    output_extension: "_mmd.md"

  - name: "docbook"
    enabled: true
    include_long_descriptions: true
    output_extension: ".xml"

  - name: "epub"
    enabled: true
    include_long_descriptions: true
    output_extension: ".epub"

  - name: "odt"
    enabled: true
    include_long_descriptions: true
    output_extension: ".odt"

  - name: "rst"
    enabled: true
    include_long_descriptions: true
    output_extension: ".rst"

  - name: "latex"
    enabled: true
    include_long_descriptions: true
    output_extension: ".tex"

validation:
  min_confidence: 0.7
  require_alt_text: true
  require_long_description: true
  max_alt_text_length: 150

qa:
  flag_low_confidence: true
  low_confidence_threshold: 0.7
  flag_missing_ui_elements: true
  required_ui_types: ["button", "text_field", "dropdown"]
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

### templates/folge.css

Base CSS with `@font-face` declarations for accessible typography:

- **Atkinson Hyperlegible Next** (variable weight) — body text
- **AtkynsonMonoNerdFont** (static OTF) — code blocks and monospace

### templates/letter-portrait.css

PDF `@page` rules for Letter Portrait layout (default).

### templates/letter-landscape.css

PDF `@page` rules for Letter Landscape layout (used with `--orientation landscape`).

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

```bash
validation:
  min_confidence: 0.9  # More strict
```

Or pass as a CLI argument:

```bash
folge-cli validate-content guide.enriched.json 0.9
```

### Change PDF Orientation

Use the `--orientation` flag:

```bash
# Letter portrait (default)
folge-cli publish guide.json output/ pdf

# Letter landscape
folge-cli publish guide.json output/ pdf --orientation landscape

# Or set in config.yaml per target
targets:
  - name: "pdf"
    orientation: "landscape"
```

### Change PDF Engine

The publish step tries PDF engines in this fallback order:

1. **weasyprint** (default, best PDF/UA support)
2. **wkhtmltopdf** (fallback)
3. **xelatex** (fallback)

All require Pandoc to be installed.
