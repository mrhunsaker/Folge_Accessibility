"""Catppuccin Latte theme for folge_gui, tuned to pass WCAG 2.2 AA contrast.

Design note — why some colors are "darkened"
----------------------------------------------
The official Catppuccin Latte palette (https://catppuccin.com/palette/) is a
light, pastel theme. Several of its accent colors do not reach the 4.5:1
contrast ratio WCAG 2.2 requires (SC 1.4.3 Contrast (Minimum)) for small text,
or even the 3:1 ratio required for UI components and graphical objects
(SC 1.4.11) when placed on Latte's own light backgrounds. Measured against
``base`` (#eff1f5), for example: green is 2.96:1, yellow 2.31:1, peach 2.64:1,
sapphire 2.78:1, teal 3.31:1, and blue 4.34:1 — none reach 4.5:1.

Rather than abandon the requested Catppuccin Latte scheme, this module keeps
every official Latte color unchanged for large fills, borders, and decorative
use (``LATTE``), and additionally derives an "ink" variant for each
under-contrast accent: the same hue and saturation, with lightness reduced
just enough (verified by binary search against the darkest background these
inks are ever placed on, ``surface0``) to clear 4.6:1 — a small safety margin
above the 4.5:1 AA minimum. These ink colors are used wherever an accent
color carries text or a status icon on a light background. Both palettes are
exposed below so any given use can pick the version appropriate to its role.
All ratios were computed with the standard WCAG relative-luminance formula;
see docs/gui.md for the full contrast table.
"""

from __future__ import annotations

from nicegui import ui

# ---------------------------------------------------------------------------
# Official Catppuccin Latte palette — unmodified.
# https://github.com/catppuccin/catppuccin (Latte flavor)
# ---------------------------------------------------------------------------
LATTE: dict[str, str] = {
    "rosewater": "#dc8a78",
    "flamingo": "#dd7878",
    "pink": "#ea76cb",
    "mauve": "#8839ef",
    "red": "#d20f39",
    "maroon": "#e64553",
    "peach": "#fe640b",
    "yellow": "#df8e1d",
    "green": "#40a02b",
    "teal": "#179299",
    "sky": "#04a5e5",
    "sapphire": "#209fb5",
    "blue": "#1e66f5",
    "lavender": "#7287fd",
    "text": "#4c4f69",
    "subtext1": "#5c5f77",
    "subtext0": "#6c6f85",
    "overlay2": "#7c7f93",
    "overlay1": "#8c8fa1",
    "overlay0": "#9ca0b0",
    "surface2": "#acb0be",
    "surface1": "#bcc0cc",
    "surface0": "#ccd0da",
    "base": "#eff1f5",
    "mantle": "#e6e9ef",
    "crust": "#dce0e8",
}

# AA-safe "ink" variants (see module docstring). red and mauve already pass
# AA as-is and have no ink counterpart.
INK: dict[str, str] = {
    "blue": "#094cd0",
    "green": "#28651b",
    "yellow": "#7b4e10",
    "peach": "#9a3901",
    "teal": "#0f6267",
    "sapphire": "#13616e",
    "sky": "#025f83",
}

# ---------------------------------------------------------------------------
# Semantic roles used throughout the app. Prefer these names in component
# code over reaching into LATTE/INK directly, so the meaning of a color is
# obvious at the call site and stays consistent app-wide.
# ---------------------------------------------------------------------------
COLOR: dict[str, str] = {
    # Surfaces
    "bg": LATTE["base"],
    "bg_raised": LATTE["mantle"],
    "bg_sunken": LATTE["crust"],
    "surface": LATTE["surface0"],
    "surface_strong": LATTE["surface1"],
    # Borders
    "border": LATTE["surface1"],
    "border_strong": LATTE["surface2"],
    # Text
    "text": LATTE["text"],
    "text_muted": LATTE["subtext1"],
    "text_faint": LATTE["overlay1"],
    # Interactive / brand
    "primary": LATTE["blue"],
    "primary_ink": INK["blue"],
    "secondary": LATTE["mauve"],
    "link": LATTE["mauve"],
    "focus_ring": LATTE["blue"],
    # Status semantics — always paired with an icon shape and a text label
    # in the UI, never conveyed by color alone (WCAG 1.4.1 Use of Color).
    "status_pending": LATTE["subtext1"],
    "status_running": INK["blue"],
    "status_waiting": INK["peach"],
    "status_success": INK["green"],
    "status_warning": INK["yellow"],
    "status_error": LATTE["red"],
    "status_info": INK["sky"],
    # Solid fills (verified >=4.5:1 with white text; see docstring)
    "fill_primary": LATTE["blue"],
    "fill_secondary": LATTE["mauve"],
    "fill_success": INK["green"],
    "fill_warning": INK["yellow"],
    "fill_error": LATTE["red"],
    "fill_info": INK["sky"],
}


def apply_theme() -> None:
    """Set the app-wide Quasar color palette and inject supporting CSS.

    Call once, before building any page content (e.g. at the top of the
    ``@ui.page`` handler, or once at module import time in ``app.py``).
    """
    ui.colors(
        primary=LATTE["blue"],
        secondary=LATTE["mauve"],
        accent=INK["teal"],
        positive=INK["green"],
        negative=LATTE["red"],
        info=INK["sky"],
        warning=INK["yellow"],
        dark=LATTE["text"],
        dark_page=LATTE["crust"],
    )

    ui.add_head_html(
        f"""
        <style>
          :root {{
            --fg-bg: {COLOR['bg']};
            --fg-bg-raised: {COLOR['bg_raised']};
            --fg-bg-sunken: {COLOR['bg_sunken']};
            --fg-surface: {COLOR['surface']};
            --fg-border: {COLOR['border']};
            --fg-border-strong: {COLOR['border_strong']};
            --fg-text: {COLOR['text']};
            --fg-text-muted: {COLOR['text_muted']};
            --fg-focus: {COLOR['focus_ring']};
          }}

          html, body {{
            background: var(--fg-bg) !important;
            color: var(--fg-text);
          }}

          /* Base body text size/line-height for readability (WCAG 1.4.8 supportive practice) */
          body {{
            font-size: 16px;
            line-height: 1.5;
          }}

          /* ---------------------------------------------------------------
             Visible focus indicator (WCAG 2.4.7 / 2.4.11). Quasar's default
             focus ring can be subtle; this guarantees a strong, consistent,
             high-contrast indicator on every focusable element, including a
             light halo so it stays visible on both light and colored
             backgrounds.
             --------------------------------------------------------------- */
          a:focus-visible,
          button:focus-visible,
          input:focus-visible,
          select:focus-visible,
          textarea:focus-visible,
          [tabindex]:focus-visible,
          .q-btn:focus-visible,
          .q-field:focus-within .q-field__control {{
            outline: 3px solid {COLOR['focus_ring']} !important;
            outline-offset: 2px !important;
            border-radius: 4px;
            box-shadow: 0 0 0 5px rgba(255, 255, 255, 0.9) !important;
          }}

          /* Respect reduced-motion preference (WCAG 2.3.3) */
          @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{
              animation-duration: 0.001ms !important;
              animation-iteration-count: 1 !important;
              transition-duration: 0.001ms !important;
              scroll-behavior: auto !important;
            }}
          }}

          /* Screen-reader-only utility (Tailwind's sr-only, restated here so
             it always works even if the Tailwind CDN script hasn't parsed
             this class combination yet). */
          .fg-sr-only {{
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
          }}

          .nicegui-skip-link {{
            background: {COLOR['fill_primary']} !important;
            color: #ffffff !important;
            font-weight: 600;
            padding: 0.75rem 1.25rem !important;
            border-radius: 0 0 6px 0;
          }}

          /* Monospace console output */
          .fg-console {{
            font-family: ui-monospace, "Cascadia Code", "Source Code Pro",
              Menlo, Consolas, monospace;
            font-size: 0.85rem;
            line-height: 1.45;
            background: {LATTE['crust']};
            color: {COLOR['text']};
            border: 1px solid {COLOR['border_strong']};
            border-radius: 8px;
          }}

          .fg-card {{
            background: {COLOR['bg_raised']};
            border: 1px solid {COLOR['border']};
            border-radius: 12px;
          }}
        </style>
        """
    )
