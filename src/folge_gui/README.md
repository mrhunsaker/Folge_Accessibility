# folge_gui

An accessible [NiceGUI](https://nicegui.io) front end for `folge-cli` — the
Folge Vision Publishing Pipeline. It's a **parallel, additive companion** to
`folge-cli`: every command it runs is the exact same `folge-cli` you'd run
from a terminal, launched as a real subprocess. `src/folge_cli` is never
imported for execution and is never modified by this package.

## What it does

- **Setup** — check that `uv`, Pandoc, `pdfinfo`, and `pymupdf` are
  available; view resolved settings for every vision provider; edit `.env`
  and `config.yaml` from the browser.
- **Steps** — run any individual `folge-cli` sub-command, in the same order
  `pipeline.py` runs them (`batch-process`, `merge`, `validate-schema`,
  `validate-content`, `generate-manual-attention`, `render`, `publish`, then
  `validate-pdf` last since it isn't part of that sequence). Each has its
  own form, a Run/Cancel button, live status, and streamed command output.
  When a step finishes, a non-dismissible dialog asks you to **Re-process
  this step** or **Continue** — a checkpoint to review the result (or fix
  something in your own editor) before it feeds the next step, mirroring
  `pipeline.py`'s own manual-review pause.
- **Full Pipeline** — run `folge-cli pipeline` end to end with a visual,
  8-stage progress tracker. The real `pipeline` command pauses twice for a
  terminal answer (a provider-availability check, and a mandatory
  review-before-rendering gate); this page detects those exact prompts and
  swaps in an accessible dialog for each, so nothing about the underlying
  CLI behavior changes — you just get a button instead of a blinking cursor.

## Accessibility

Built to WCAG 2.2 AA. Some specifics:

- Every heading is a real `<h1>`–`<h6>` element (not a styled `<div>`), so
  screen-reader users can navigate by heading.
- A working "Skip to main content" link on every page (WCAG 2.4.1).
- Every form control has a programmatically associated label, and help text
  is linked with `aria-describedby` (WCAG 1.3.1, 4.1.2, 3.3.2).
- Status (pending/running/waiting/success/error) is always shown as an icon
  *and* text, never color alone (WCAG 1.4.1) — see `theme.py`'s docstring
  for why several stock Catppuccin Latte accent colors were darkened to a
  same-hue "ink" variant to actually clear 4.5:1 contrast on Latte's light
  backgrounds (several of them don't, out of the box).
- State changes ("Batch-process images: running", "Pipeline finished
  successfully") are pushed through an ARIA live region so screen readers
  announce them without needing focus to move (WCAG 4.1.3). The full,
  verbose command log is a separate, focusable `role="log"` region — it's
  available on demand rather than being read aloud line by line.
- A visible, high-contrast focus indicator on every interactive element
  (WCAG 2.4.7 / 2.4.11), and `prefers-reduced-motion` is respected for the
  spinner/status animations (WCAG 2.3.3).
- The two `input()` prompts inside `folge-cli pipeline` are answered through
  a non-dismissible (`persistent`) modal dialog with clearly labeled
  buttons, rather than requiring anyone to find and use a hidden terminal.

See `docs/gui.md` for the full contrast-ratio table and more detail.

## Install and run

`folge_gui` is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
member of the repository — `src/folge_gui/pyproject.toml` declares it, and
the repository root `pyproject.toml` has one small, additive
`[tool.uv.workspace]` entry registering it. Both packages share a single
`uv.lock` and a single `.venv`, so there's one environment for the whole
project.

**One-time setup**, from the repository root:

```bash
uv sync --all-packages
```

`--all-packages` is what pulls `folge-gui`'s own dependencies (NiceGUI,
etc.) into the shared environment alongside `folge-cli`'s — a plain
`uv sync` only installs the root project. You only need to re-run it after
pulling changes that touch either package's dependencies.

**Run it:**

```bash
uv run folge-gui
```

This opens the app at <http://localhost:8765>. `folge-cli` itself is
completely unaffected — `uv run folge-cli --version` (and every other
`folge-cli` command) still works exactly as before.

The `folge_gui` console script is kept as an alias, so `uv run folge_gui`
works identically.

If you ever run `uv run folge-gui` before the one-time setup above, uv will
report `Failed to spawn: folge-gui` (the console script doesn't exist yet in
`.venv/bin/`). Either run the `uv sync --all-packages` step, or use the
self-syncing form, which installs what it needs on demand:

```bash
uv run --package folge-gui folge-gui
```

### Alternative: without the workspace / without touching pyproject.toml

If you'd rather not have `folge_gui` registered as a workspace member at
all, everything in `src/folge_gui` also runs standalone — it only needs
`folge_cli` to be importable and `nicegui` installed:

```bash
uv pip install -r src/folge_gui/requirements.txt
uv run python -m folge_gui
# or, without any editable install at all:
uv run --with nicegui python src/folge_gui/app.py
```

These forms default to port 8080 (NiceGUI's default) unless you edit the
`ui.run(...)` call in `app.py`.

### Where it looks for files

`folge_gui` resolves `.env`, `config.yaml`, `guide.json`, `images/`, and
`output/` the same way `folge-cli` does: relative to the project root
(the repository root, three directories up from `src/folge_cli/config.py`).
Every subprocess it launches runs with that directory as its working
directory, so paths you type into a step's form (e.g. `guide.json`,
`images`, `output/vision-results.json`) behave exactly as they would typed
after `folge-cli` at a terminal in the project root.

## Project layout

```
src/folge_gui/
├── pyproject.toml        # standalone uv workspace member (its own deps + `folge_gui` script)
├── app.py                # route registration + ui.run()
├── theme.py              # Catppuccin Latte tokens, WCAG-safe "ink" variants
├── a11y.py                 # heading(), LiveRegion, skip-link-friendly landmarks
├── process_runner.py        # async subprocess runner, prompt detection
├── prereqs.py                 # structured prerequisite / provider checks
├── config_io.py                 # .env / config.yaml read+write (via folge_cli.config)
├── steps.py                       # form <-> argv mapping for each folge-cli command
├── components.py                    # step cards, console, status tracker, dialogs
└── pages/
    ├── home.py
    ├── setup.py
    ├── steps_page.py
    └── pipeline_page.py
```

## Notes

- `src/folge_cli` is never modified and never imported for execution — see
  above for how every command actually runs.
- The **only** change outside `src/folge_gui` and `docs/` is a 3-line,
  purely additive `[tool.uv.workspace]` block in the repository root
  `pyproject.toml`, which is what makes `uv run folge-gui` resolvable from
  the repository root. It adds no new dependency to the root project and
  changes no existing line. If you'd rather not have even that, see
  "Alternative" above — everything still runs without it.
- `.env` and `config.yaml` are user data files at the repository root, not
  project source; `folge_gui`'s Setup page can read and write them the same
  way `folge-cli` does. See `docs/gui.md` for details.
- Versioned independently from `folge_cli` (`folge_gui/_version.py`).
