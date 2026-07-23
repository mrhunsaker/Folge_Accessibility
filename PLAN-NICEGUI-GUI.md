# Plan: NiceGUI GUI with Catppuccin Theme — Step-by-Step Wizard

## Problem

The CLI pipeline requires typing commands and reading terminal output. A GUI
would make it accessible to non-technical users and provide visual progress
feedback with manual approval gates.

## Goal

A step-by-step wizard GUI that runs each pipeline phase independently,
requires manual approval before proceeding, and provides a JSON editor for
reviewing and editing `guide.enriched.json` before validation. All in a
Catppuccin-themed dark interface.

## Dependencies

Add to `pyproject.toml`:
```
"nicegui>=3.14",
"catppuccin>=2.5",
```

Install with: `uv add nicegui catppuccin`

## Project Structure

```
Folge_Accessibility/
├── src/
│   └── folge/
│       ├── __init__.py          # __version__ + package exports
│       ├── _version.py          # date-based version (YYYY.M.D)
│       ├── pipeline/
│       │   ├── __init__.py      # exports all step functions
│       │   ├── prerequisites.py # check_prerequisites()
│       │   ├── provider.py      # check_provider()
│       │   ├── batch_process.py # run_batch()
│       │   ├── merge.py         # run_merge()
│       │   ├── validate.py      # run_validate()
│       │   ├── render.py        # run_render()
│       │   ├── publish.py       # run_publish()
│       │   └── progress.py      # callback-based progress
│       └── gui/
│           ├── __init__.py
│           ├── app.py           # main NiceGUI application
│           └── theme.py         # Catppuccin color mapping
├── run_pipeline.py              # CLI entry point (thin wrapper)
├── gui.py                       # GUI entry point (thin wrapper)
├── templates/                   # pandoc templates (unchanged)
├── *.lua                        # Lua filters (unchanged)
├── config.yaml
├── mkdocs.yml
├── pyproject.toml               # hatchling build backend
└── src/folge/_version.py        # version source
```

## Build System — Hatchling

Migrated from setuptools to hatchling for better PEP 621 support and
built-in dynamic versioning.

```toml
[build-system]
requires = ["hatchling>=1.31"]
build-backend = "hatchling.build"

[tool.hatch.version]
path = "src/folge/_version.py"

[project.scripts]
folge-pipeline = "folge.pipeline.orchestrator:main"
folge-gui = "folge.gui.app:main"
```

## Pipeline API — Step Functions

Each step is an importable function with a progress callback signature:

```python
from typing import Callable
ProgressCallback = Callable[[str, int, int], None]  # (message, current, total)
```

| Module | Function | Returns |
|--------|----------|---------|
| `prerequisites.py` | `check(on_progress) → tuple[bool, list[str]]` | (ok, issues) |
| `provider.py` | `check(provider, api_key, on_progress) → tuple[bool, str]` | (ok, message) |
| `batch_process.py` | `run(guide, images, output, provider, api_key, on_progress) → Path` | vision_results |
| `merge.py` | `run(guide, vision, output, on_progress) → Path` | enriched path |
| `validate.py` | `run(enriched, min_confidence, output, on_progress) → tuple[bool, list]` | (ok, warnings) |
| `render.py` | `run(enriched, targets, output, on_progress) → list[str]` | published formats |
| `publish.py` | `run(md_file, targets, output, templates_dir, on_progress) → list[str]` | published formats |

## Step-by-Step Wizard

### Pipeline Steps with Mandatory Gates

| # | Step | Action | Gate | Retry |
|---|------|--------|------|-------|
| 0 | Configure | User fills form | — | — |
| 1 | Prerequisites | `check()` | Yes | Yes |
| 2 | Provider | `check(provider)` | Yes | Yes |
| 3 | Batch Process | `run_batch()` | Yes | Yes |
| 4 | Merge | `run_merge()` | Yes | Yes |
| 5 | Manual Review | JSON editor (autosave) | Yes | — |
| 6 | Validate | `run_validate()` | Yes | Yes |
| 7 | Render & Publish | `run_render()` + `run_publish()` | Yes | Yes |

### State Machine

```
IDLE → CONFIGURED → PREREQ_CHECK → PROVIDER_CHECK → BATCH_PROCESSING
  → MERGING → MANUAL_REVIEW → VALIDATING → RENDERING → COMPLETE
```

Each transition requires user clicking "Continue to Next Step".
Failed steps show "Retry" button instead of "Continue".

## Layout

```
┌──────────────────────────────────────────────────────┐
│  Folge Vision Pipeline                               │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Step 0: Configure                                   │
│  ┌─────────────────────────────────────────────────┐ │
│  │ Guide JSON:   [________________________] [Browse]│ │
│  │ Images Dir:   [________________________] [Browse]│ │
│  │ Output Dir:   [________________________] [Browse]│ │
│  │                                                  │ │
│  │ Target Formats:                                  │ │
│  │   [✓] PDF   [✓] DOCX   [✓] HTML   [ ] GitHub   │ │
│  │                                                  │ │
│  │ Min Confidence: [0.8 ]                           │ │
│  │ Vision Provider: ( ) Ollama  ( ) OpenRouter      │ │
│  └─────────────────────────────────────────────────┘ │
│                                                      │
│  Steps: [✓ Prereq] [✓ Provider] [→ Batch]           │
│          [ ] Merge] [ ] Review] [ ] Validate]        │
│          [ ] Publish]                                │
│                                                      │
│  Progress Bar: ████████████████░░░░░░░░░░  58%       │
│  Status: Step 3/7 — Processing image 15/37           │
│                                                      │
│  Log:                                                │
│  ✓ Prerequisites OK                                  │
│  ✓ Ollama running (qwen2.5vl)                       │
│  → Processing 37 images...                           │
│    [  1/37] ✓ 3.2s                                  │
│    [ 15/37] processing...                            │
│                                                      │
│  [▶ Run Next Step]  [🔄 Retry Step]  [⏭ Skip]       │
├──────────────────────────────────────────────────────┤
│  (After Step 4 — Review Step)                        │
│  ┌─────────────────────────────────────────────────┐ │
│  │  JSON Editor: guide.enriched.json                │ │
│  │  {                                               │ │
│  │    "title": "...",                               │ │
│  │    "steps": [                                    │ │
│  │      {                                           │ │
│  │        "instruction": "...",                     │ │
│  │        "vision_description": "..."  ← edit this  │ │
│  │      },                                          │ │
│  │      ...                                         │ │
│  │    ]                                             │ │
│  │  }                                               │ │
│  │                                                  │ │
│  │  [💾 Save Changes]  [▶ Continue to Validation]   │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

## Catppuccin Theme

### Palette Selection

```python
from catppuccin import Flavour

palette = Flavour.macchiato()  # balanced dark theme
```

### NiceGUI Color Mapping

```python
CATPPUCCIN_COLORS = {
    "primary": palette.mauve.hex,      # #b4befe — Run buttons, progress
    "secondary": palette.sapphire.hex,  # #74c7ec — Info elements
    "accent": palette.pink.hex,         # #f5c2e7 — Highlights
    "positive": palette.green.hex,      # #a6e3a1 — Success, checkmarks
    "negative": palette.red.hex,        # #f38ba8 — Errors, retries
    "warning": palette.yellow.hex,      # #f9e2af — Warnings
    "info": palette.sky.hex,            # #89dceb — Status info
    "dark": palette.base.hex,           # #1e1e2e — Background
    "surface": palette.surface0.hex,    # #313244 — Cards, buttons
    "text": palette.text.hex,           # #cdd6f4 — Default text
    "subtext": palette.overlay2.hex,    # #6c7086 — Status bar
}
```

### UI Element Styling

| Element | Catppuccin Color | Usage |
|---------|-----------------|-------|
| Run button | Mauve (primary) | Main action |
| Retry button | Yellow (warning) | Retry failed step |
| Success messages | Green (positive) | Checkmarks, "done" |
| Error messages | Red (negative) | Failures, warnings |
| Progress bar fill | Mauve (primary) | Progress indicator |
| Log background | Base (#1e1e2e) | Dark log area |
| Log text | Text (#cdd6f4) | Default text |
| Status bar | Overlay2 (#6c7086) | Secondary text |
| File picker buttons | Surface0 (#313244) | Secondary buttons |
| JSON editor | Surface + Text | Code editing area |

## Components

### File/Folder Selection

```python
with ui.row().classes('w-full'):
    guide_input = ui.input(label='Guide JSON', placeholder='guide.json').classes('flex-grow')
    ui.button('Browse', on_click=lambda: pick_file(guide_input))

with ui.row().classes('w-full'):
    images_input = ui.input(label='Images Directory', placeholder='images/').classes('flex-grow')
    ui.button('Browse', on_click=lambda: pick_folder(images_input))

with ui.row().classes('w-full'):
    output_input = ui.input(label='Output Directory', placeholder='output/').classes('flex-grow')
    ui.button('Browse', on_click=lambda: pick_folder(output_input))
```

### Target Format Checkboxes

```python
with ui.row():
    pdf_check = ui.checkbox('PDF', value=True)
    docx_check = ui.checkbox('DOCX', value=True)
    html_check = ui.checkbox('HTML', value=True)
    github_check = ui.checkbox('GitHub', value=False)
```

### JSON Editor (Step 5 — Manual Review)

```python
json_editor = ui.json_editor(
    {'content': {'json': enriched_data}},
    on_change=lambda e: autosave_changes(e),
    schema=enriched_schema,
)
```

- **Autosave**: Every edit triggers `on_change` which writes to disk
- **Schema validation**: Red highlights for invalid fields
- **View modes**: Tree, code, table views for different editing styles
- **Continue button**: Only enabled after autosave completes

### Progress Bar

```python
progress = ui.linear_progress(value=0, show_value=False).classes('w-full')
progress_label = ui.label('Ready').classes('text-center')
```

### Log Area

```python
log = ui.log(max_lines=200).classes('w-full bg-base text-text font-mono')
```

### Step Indicator

```python
steps = ['Prereq', 'Provider', 'Batch', 'Merge', 'Review', 'Validate', 'Publish']
step_buttons = []
for i, name in enumerate(steps):
    btn = ui.button(name).classes('step-btn')
    step_buttons.append(btn)
```

### Retry Button

```python
retry_btn = ui.button('Retry', icon='refresh', on_click=retry_current_step)
retry_btn.props('color=warning').classes('hidden')  # shown only on failure
```

## GUI Flow

1. **Startup**: Show empty form with all defaults. Status: "Idle"
2. **Configure**: Browse buttons open native file/folder dialogs
3. **Run clicked**:
   - Validate inputs (all three paths filled, guide.json exists)
   - Disable Run button, change to "Running..."
   - Start Step 1 (Prerequisites)
4. **During each step**:
   - Log updates scroll in real-time
   - Progress bar advances
   - Status bar shows current phase + elapsed time
5. **Step complete**:
   - Show results in log
   - Enable "Continue to Next Step" button
   - If failed: show "Retry" button in yellow
6. **Manual Review (Step 5)**:
   - JSON editor opens with `guide.enriched.json`
   - Autosave on every edit
   - User edits vision descriptions, adds manual annotations
   - Click "Continue to Validation" to proceed
7. **Final publish (Step 7)**:
   - Runs render + publish as single batch
   - Shows format-by-format progress
8. **Complete**:
   - Re-enable all buttons
   - Show completion summary in log
   - Status: "Complete — 142.3s"
9. **Error**:
   - Highlight error in red in log
   - Show "Retry" button
   - Status: "Failed at Step X"

## Threading Model

```
Main Thread (GUI)          Background Thread (Pipeline)
─────────── ────────────────────────────────
User clicks "Continue"
  → disable button
  → start Thread ───────→ run_step()
  → show progress bar       ↓
                            check_prerequisites()
  ← update log ───────────  on_progress("Prerequisites OK")
  ← enable Continue ──────  on_progress("Step complete")
                            ... waits for user ...
User clicks "Continue"
  → start Thread ───────→ run_next_step()
  ... continues ...
```

## NiceGUI v3 Notes

- `ui.navigate.to()` replaces deprecated `ui.open()`
- `ui.json_editor` supports schema validation (v2.8.0+)
- `ui.codemirror` for code editing with 140+ language support
- `ui.run_on_thread()` for updating UI from background threads
- `dark=True` in `ui.run()` enables dark mode globally

## Implementation Order

1. Update `PLAN-NICEGUI-GUI.md` with current versions and step-by-step workflow
2. Create `src/folge/` directory structure with `__init__.py` files
3. Move `_version.py` → `src/folge/_version.py`
4. Refactor pipeline scripts → `src/folge/pipeline/` modules with step functions
5. Create `src/folge/gui/theme.py` (Catppuccin colors)
6. Create `src/folge/gui/app.py` (step-by-step wizard UI)
7. Update `pyproject.toml` (hatchling, deps, entry points)
8. Create thin entry points (`gui.py`, `run_pipeline.py` at root)
9. Delete old `scripts/` directory
10. Run `uv sync` + test CLI
11. Run `uv run gui.py` + test GUI

## Running

```bash
# CLI (backward compatible)
uv run run_pipeline.py guide.json

# GUI
uv run gui.py

# The GUI opens at http://localhost:8080
```

## Future Enhancements

- Save/load pipeline configurations (JSON presets)
- Export/import enriched guides
- Batch mode for multiple guides
- Custom themes beyond Catppuccin
- Docker support for headless environments
