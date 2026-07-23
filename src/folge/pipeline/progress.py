"""Progress reporting utilities for the Folge pipeline.

Provides a callback-based progress system that works for both CLI and GUI modes.
All functions accept an optional on_progress callback; if None, prints to stdout.
"""
import sys
import threading
import time
from typing import Callable, Optional

ProgressCallback = Optional[Callable[[str, int, int], None]]

_lock = threading.Lock()

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"


def _write(text):
    """Thread-safe write to stdout with immediate flush."""
    with _lock:
        print(text, flush=True)


def _report(on_progress: ProgressCallback, message: str, current: int = 0, total: int = 0):
    """Report progress via callback or stdout."""
    if on_progress is not None:
        on_progress(message, current, total)
    else:
        _write(f"  {message}")


def banner(on_progress: ProgressCallback, text, char="=", width=60):
    """Print a section banner."""
    _report(on_progress, f"\n{char * width}")
    _report(on_progress, f"  {text}")
    _report(on_progress, f"{char * width}")


def phase(on_progress: ProgressCallback, name):
    """Print a phase header."""
    banner(on_progress, name)


def step_start(on_progress: ProgressCallback, cur, total, label, detail=""):
    """Report step start."""
    tag = f"[{cur:>{len(str(total))}}/{total}]"
    msg = f"  {tag} {label}"
    if detail:
        msg += f" — {detail}"
    _report(on_progress, msg, cur, total)


def step_ok(on_progress: ProgressCallback, cur, total, label, elapsed=None):
    """Report step completion."""
    tag = f"[{cur:>{len(str(total))}}/{total}]"
    suffix = f" ({elapsed:.1f}s)" if elapsed is not None else ""
    _report(on_progress, f"  {tag} ✓ {label}{suffix}", cur, total)


def step_error(on_progress: ProgressCallback, cur, total, label, error=""):
    """Report step failure."""
    tag = f"[{cur:>{len(str(total))}}/{total}]"
    short_err = (error[:60] + "...") if len(error) > 63 else error
    _report(on_progress, f"  {tag} ✗ {label}: {short_err}", cur, total)


def info(on_progress: ProgressCallback, text):
    """Report informational line."""
    _report(on_progress, f"  {text}")


def ok(on_progress: ProgressCallback, text):
    """Report success."""
    _report(on_progress, f"  ✓ {text}")


def warn(on_progress: ProgressCallback, text):
    """Report warning."""
    _report(on_progress, f"  [WARN] {text}")


def error(on_progress: ProgressCallback, text):
    """Report error."""
    _report(on_progress, f"  [ERROR] {text}")


def summary(on_progress: ProgressCallback, label, count, total, path=None, extra=None):
    """Report summary line."""
    msg = f"  {label} {count}/{total}"
    if path:
        msg += f" to {path}"
    if extra:
        msg += f" — {extra}"
    _report(on_progress, msg)


def elapsed_str(seconds):
    """Format seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.0f}s"


class Timer:
    """Context manager that measures elapsed time."""

    def __init__(self):
        self.start = None
        self.elapsed = 0

    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *_):
        self.elapsed = time.monotonic() - self.start
