# Folge GUI

`folge_gui` is an accessible, browser-based companion to `folge-cli`, built
with [NiceGUI](https://nicegui.io) in a Catppuccin Latte color scheme. It
lives in `src/folge_gui` alongside `src/folge_cli` and never modifies or
imports `folge_cli`'s step implementations to do work — every command it
runs is launched as a real subprocess, exactly the same `folge-cli` you'd
run at a terminal.

!!! note "Companion, not a replacement"
    Everything in this page describes an additional interface. The
    terminal workflow documented on [Getting Started](getting-started.md)
    is unchanged and works exactly as before.

## Install and run

`folge_gui` is registered as a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
member, so it shares one `uv.lock` and one `.venv` with `folge-cli`:

```bash
git clone https://github.com/mrhunsaker/Folge_Accessibility.git
cd Folge_Accessibility
uv sync --all-packages   # one-time: pulls in NiceGUI alongside folge-cli's own deps
uv run folge-gui
```

This opens the app at `http://localhost:8765`. `folge-cli` itself is
unaffected — every existing command still works exactly as documented on
[Getting Started](getting-started.md). The `folge_gui` console script is
kept as an alias, so `uv run folge_gui` works identically.

!!! tip "Forgot the one-time setup?"
    `uv sync` on its own only installs the root project. If `uv run
    folge-gui` reports `Failed to spawn: folge-gui`, either run `uv sync
    --all-packages` once, or use the self-syncing form:
    `uv run --package folge-gui folge-gui`.

If you'd rather not have `folge_gui` registered as a workspace member at
all, `src/folge_gui` also runs standalone (see `src/folge_gui/README.md`
for the non-workspace commands, on the default NiceGUI port 8080).

## What's on each page

### Setup

- **Prerequisites** — checks for `uv`, Pandoc, `pdfinfo`, and `pymupdf`
  (the same tools `folge-cli pipeline` checks before it starts).
- **Vision provider settings** — a table of every supported provider's
  resolved base URL, model, and (masked) API key, and a button to test
  whether the currently selected provider is reachable.
- **`.env` and `config.yaml` editors** — load, edit, and save both files
  from the browser. `config.yaml` is checked for valid YAML before it's
  written; an invalid save is rejected with the parser's error message and
  the file on disk is left untouched.

!!! warning ".env holds secrets"
    The `.env` editor shows API keys in plain text, the same way any text
    editor would. Don't leave the Setup page open on a shared screen while
    it's loaded.

### Steps

One card per `folge-cli` sub-command, in the same order `pipeline.py` runs
them — `batch-process`, `merge`, `validate-schema`, `validate-content`,
`generate-manual-attention`, `render`, `publish` — with `validate-pdf` last,
since it isn't part of `pipeline.py`'s numbered steps (it checks a PDF that
`publish` has to produce first). Each card has its own form, a Run/Cancel
button, a status indicator, and the command's live output. Paths are
relative to the project root, same as running `folge-cli` from a terminal
there.

**Quality gate.** When a step finishes — success or failure — a
non-dismissible dialog asks you to choose **Re-process this step** or
**Continue**, before you can act on anything else on the page. This mirrors
`pipeline.py`'s own Step 4b manual-review pause (the `(C)ontinue to
rendering or (R)eVerify enriched JSON?` prompt), applied to every step
instead of only that one: it's a deliberate checkpoint to review a step's
output — or fix something in your own editor — *before* it feeds into the
next step, rather than discovering a problem only after a final PDF has
already been generated. "Re-process this step" simply re-runs the same
command with the form's current values, so you can go make an external fix
and then choose it to check that the fix took, as many times as you need.

### Full Pipeline

Runs `folge-cli pipeline` end to end behind an 8-stage visual tracker
(prerequisites, provider check, vision processing, merge, validation,
manual review, render, publish).

The real `pipeline` command pauses twice for a terminal answer:

1. A confirmation if the selected provider doesn't appear reachable.
2. A mandatory pause after validation, asking you to review
   `output/guide.enriched.json` (and `output/manual-attention-needed.md`,
   if generated) before rendering continues.

This page watches the command's output for those exact prompts and opens an
accessible, non-dismissible dialog for each instead — the underlying CLI
behavior is unchanged, you just get a labeled button instead of a blinking
cursor in a terminal you may not have open.

## Accessibility

Built against WCAG 2.2 AA and WAI-ARIA 1.2. Specifics:

- **Real headings.** Every heading is an actual `<h1>`–`<h6>` element, not a
  `<div>` styled to look like one, so screen-reader users can navigate by
  heading (WCAG 1.3.1, 2.4.6).
- **Skip link.** Every page starts with a "Skip to main content" link,
  visible on keyboard focus (WCAG 2.4.1).
- **Labeled everything.** Every form control has a programmatically
  associated label; fields with extra guidance link it with
  `aria-describedby`; required fields carry `aria-required` in addition to
  a visible "(required)" marker (WCAG 1.3.1, 3.3.2, 4.1.2).
- **Status is never color-only.** Pending/running/waiting/success/error
  states are always an icon *and* a text word, never color alone
  (WCAG 1.4.1). Decorative icons are marked `aria-hidden`.
- **Live announcements without a wall of noise.** Short state changes
  ("Merge guide + vision results: completed successfully") go through an
  ARIA live region (`role="status"`, `aria-live="polite"`) so a screen
  reader announces them without focus needing to move (WCAG 4.1.3). The
  full, verbose command output is a separate `role="log"` region — it's
  there to read on demand, not narrated line by line.
- **Visible focus.** A high-contrast, consistent focus outline is enforced
  on every interactive element (WCAG 2.4.7 / 2.4.11).
- **Motion respects preference.** `prefers-reduced-motion` disables the
  spinner/status animations for anyone who has that OS setting on
  (WCAG 2.3.3).
- **Modal dialogs.** The pipeline's two interactive prompts, and every
  step's post-run quality-gate prompt, use the same pattern: a
  `role="alertdialog"` modal with `aria-labelledby` pointing at its heading,
  marked `persistent` so it can't be dismissed by an accidental click or
  Escape press — the same way a real terminal prompt can't be either.
- **`lang` attribute.** The page is served with `<html lang="en-US">`
  (WCAG 3.1.1).

### Why some Catppuccin Latte colors were darkened

The official [Catppuccin Latte](https://catppuccin.com/palette/) palette is
a light, pastel theme. Measured with the standard WCAG relative-luminance
formula against Latte's own `base` background (`#eff1f5`), several of its
accent colors fall short of the 4.5:1 ratio WCAG 2.2 requires for small text
(SC 1.4.3) — some even fall short of the 3:1 floor for UI components and
graphical objects (SC 1.4.11):

| Color | Role | Hex | Contrast on base (#eff1f5) | Passes AA text (4.5:1)? |
|---|---|---|---|---|
| Latte `text` | as-is | `#4c4f69` | 7.06:1 | Yes |
| Latte `subtext1` | as-is | `#5c5f77` | 5.53:1 | Yes |
| Latte `red` | as-is | `#d20f39` | 4.80:1 | Yes |
| Latte `mauve` | as-is | `#8839ef` | 4.79:1 | Yes |
| Latte `blue` | as-is | `#1e66f5` | 4.34:1 | No |
| Latte `green` | as-is | `#40a02b` | 2.96:1 | No |
| Latte `yellow` | as-is | `#df8e1d` | 2.31:1 | No |
| Latte `peach` | as-is | `#fe640b` | 2.64:1 | No |
| Latte `teal` | as-is | `#179299` | 3.31:1 | No |
| Latte `sapphire` | as-is | `#209fb5` | 2.78:1 | No |
| Latte `sky` | as-is | `#04a5e5` | 2.47:1 | No |
| `blue` ink | darkened | `#094cd0` | 6.28:1 | Yes |
| `green` ink | darkened | `#28651b` | 6.26:1 | Yes |
| `yellow` ink | darkened | `#7b4e10` | 6.32:1 | Yes |
| `peach` ink | darkened | `#9a3901` | 6.27:1 | Yes |
| `teal` ink | darkened | `#0f6267` | 6.27:1 | Yes |
| `sapphire` ink | darkened | `#13616e` | 6.27:1 | Yes |
| `sky` ink | darkened | `#025f83` | 6.26:1 | Yes |

`red`, `mauve`, `text`, and `subtext1` are used unchanged. For every other
accent, an "ink" variant — same hue and saturation, reduced lightness,
verified against the darkest surface color it's ever placed on
(`surface0`) with a small safety margin — is used anywhere the color
carries text or a status icon. The original, brighter Latte colors are kept
for large decorative fills, borders, and anything that isn't required to
carry a contrast ratio on its own. Full token definitions are in
`src/folge_gui/theme.py`.

## Where files live

`folge_gui` resolves `.env`, `config.yaml`, `guide.json`, `images/`, and
`output/` the same way `folge-cli` does — relative to the project root — by
reading `folge_cli.config.PROJECT_ROOT` directly rather than recomputing
it. Every subprocess it launches uses that directory as its working
directory, so a path typed into any form (`guide.json`, `images`,
`output/vision-results.json`, ...) behaves exactly as it would typed after
`folge-cli` at a terminal in the project root.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `ModuleNotFoundError: No module named 'folge_cli'` | Run from the project root after `uv sync`, or set `PYTHONPATH` to include `src`. |
| Setup page shows `uv` / Pandoc as missing | Install them and make sure they're on `PATH` for the same shell/user running `python -m folge_gui`. |
| Full Pipeline never gets past "Provider check" | The selected provider isn't reachable — for local providers (Ollama, LM Studio, llama.cpp) make sure the server is running; for cloud providers, add the API key on the Setup page. |
| A step fails immediately with a usage error | Check the command echoed at the top of that card's output against the path values in its form — a missing required field is the most common cause. |
