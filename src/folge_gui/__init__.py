"""folge_gui — an accessible NiceGUI front end for the Folge Vision Publishing Pipeline.

This package is a *parallel*, additive interface to ``folge_cli``. It never
imports private/internal ``folge_cli`` step implementations to execute work;
every pipeline step is launched the same way a person would from a terminal
(``python -m folge_cli <command> ...``) so ``folge_cli`` itself is used
completely unmodified. The only ``folge_cli`` symbols this package touches
are public, read-only configuration helpers (``folge_cli.config``), used to
show setup/status information consistently with the CLI.

See ``src/folge_gui/README.md`` and ``docs/gui.md`` for usage.
"""

from folge_gui._version import __version__

__all__ = ["__version__"]
