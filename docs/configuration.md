# Configuration

The pipeline is configured through several files. Settings follow a strict resolution order:

```
CLI argument  >  environment variable  >  config.yaml  >  hardcoded default
```

## Project Folders

Each guide lives in its own folder under `~/Documents/FolgeProjects/<project>/`:

```text
~/Documents/FolgeProjects/
└── my-guide/
    ├── my-export.json      # guide export — any name, the only top-level JSON
    ├── images/             # screenshots (step-0.png, ...)
    └── output/             # all generated files (created automatically)
```

`folge-cli pipeline --project my-guide`, `folge-cli publish --project my-guide`,
and `folge-cli batch-process --project my-guide` look up these paths
automatically. All other sub-commands take explicit paths (the GUI's project
selector pre-fills them for you).

### Choosing the projects directory

The base directory resolves in this order:

1. `FOLGE_PROJECTS_DIR` environment variable
2. `paths.projects_dir` in `config.yaml`
3. `~/Documents/FolgeProjects` (default)

Example:

```bash
FOLGE_PROJECTS_DIR=/srv/folge folge-cli pipeline --project my-guide
```

or in `config.yaml`:

```yaml
paths:
  projects_dir: "/srv/folge"
```

### Guide JSON discovery

A project folder must contain **exactly one** top-level JSON file — the guide
export, which may have any name. All generated JSON files
(`vision-results.json`, `guide.enriched.json`, schema warnings, ...) live in
`output/`, so discovery stays unambiguous. `folge-cli` fails with a clear
message if a project has zero or more than one JSON file.

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

Pipeline configuration for providers, paths, output targets (informational;
the runtime registry lives in `src/folge_cli/formats.py`), and validation
thresholds.

The `project.version` field is injected dynamically from `_version.py` — you do not need to set it manually.

```yaml
project:
  name: "Folge Vision Publishing"
  description: "Automated documentation publishing with vision enrichment"
  author: "Michael Ryan Hunsaker, M.Ed., Ph.D."   # Used by folge-cli metadata
  keywords: ["accessibility", "documentation", "publishing", "pipeline"]  # Used by folge-cli metadata

provider: "ollama"  # Default provider

paths:
  projects_dir: ""   # Where project folders live (default: ~/Documents/FolgeProjects)

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

# ... (see full config.yaml for all 8 providers)

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

  - name: "markdown_mmd"
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

Environment variables for provider selection, API keys, and the projects
directory.

```bash
# Provider selection (ollama is default)
PROVIDER=ollama

# Local providers (no API key needed)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5vl-8k:latest
OLLAMA_TIMEOUT=600
JAN_BASE_URL=http://localhost:1337/v1
JAN_MODEL=

# Cloud providers (set API key)
OPENROUTER_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here

# Where project folders live (default: ~/Documents/FolgeProjects)
FOLGE_PROJECTS_DIR=

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
folge-cli publish --project my-guide pdf

# Letter landscape
folge-cli publish --project my-guide pdf --orientation landscape

# Or set in config.yaml per target
targets:
  - name: "pdf"
    orientation: "landscape"
```

### Selecting Specific Targets

By default, every format supported by the installed pandoc is produced.
To build only specific formats:

```bash
# Only PDF and DOCX
folge-cli pipeline --project my-guide --targets pdf,docx

# All formats (explicit)
folge-cli pipeline --project my-guide --targets pdf,docx,html,pptx,github,typst,asciidoc,beamer,commonmark,gfm,markdown_mmd,docbook,epub,odt,rst,latex
```

The runtime target registry lives in `src/folge_cli/formats.py` (the
`targets:` block in this YAML is informational only).  Writers absent from
the installed pandoc are skipped with a warning.  Every pandoc call runs
with `--standalone` and `--verbose`; its output is appended to
`<output>/pandoc.log`.

### Change PDF Engine

The publish step tries PDF engines in this fallback order:

1. **weasyprint** (default, best PDF/UA support)
2. **wkhtmltopdf** (fallback)
3. **xelatex** (fallback)

All require Pandoc to be installed.
