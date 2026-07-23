"""Catppuccin theme configuration for NiceGUI."""

from catppuccin import PALETTE

# Macchiato = balanced dark theme
palette = PALETTE.macchiato
colors = palette.colors

CATPPUCCIN_COLORS = {
    "primary": colors.mauve.hex,      # #c6a0f6 — Run buttons, progress
    "secondary": colors.sapphire.hex,  # #74c7ec — Info elements
    "accent": colors.pink.hex,         # #f5bde6 — Highlights
    "positive": colors.green.hex,      # #a6da95 — Success, checkmarks
    "negative": colors.red.hex,        # #ed8796 — Errors, retries
    "warning": colors.yellow.hex,      # #eed49f — Warnings
    "info": colors.sky.hex,            # #91d7e3 — Status info
    "dark": colors.base.hex,           # #24273a — Background
    "surface": colors.surface0.hex,    # #363a4f — Cards, buttons
    "text": colors.text.hex,           # #cad3f5 — Default text
    "subtext": colors.overlay2.hex,    # #6e738d — Status bar
}

# Named colors for direct CSS usage
MAUVE = colors.mauve.hex
SAPPHIRE = colors.sapphire.hex
PINK = colors.pink.hex
GREEN = colors.green.hex
RED = colors.red.hex
YELLOW = colors.yellow.hex
SKY = colors.sky.hex
BASE = colors.base.hex
SURFACE0 = colors.surface0.hex
TEXT = colors.text.hex
OVERLAY2 = colors.overlay2.hex
