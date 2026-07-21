#!/usr/bin/env python3
"""Shared progress reporting utilities for the Folge pipeline.

Thread-safe helpers for printing per-step and per-phase progress.
All output is flushed immediately so it streams to the terminal.
"""
import sys
import threading
import time

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


def banner(text, char="=", width=60):
    """Print a section banner."""
    _write(f"\n{char * width}")
    _write(f"  {text}")
    _write(f"{char * width}")


def phase(name):
    """Print a phase header."""
    banner(name)


def step_start(cur, total, label, detail=""):
    """Print [cur/total] label — processing..."""
    tag = f"[{cur:>{len(str(total))}}/{total}]"
    msg = f"  {tag} {label}"
    if detail:
        msg += f" \u2014 {detail}"
    _write(f"{msg}")


def step_ok(cur, total, label, elapsed=None):
    """Print [cur/total] label \u2713 done."""
    tag = f"[{cur:>{len(str(total))}}/{total}]"
    suffix = f" ({elapsed:.1f}s)" if elapsed is not None else ""
    _write(f"  {tag} {GREEN}\u2713{RESET} {label}{suffix}")


def step_error(cur, total, label, error=""):
    """Print [cur/total] label \u2717 error."""
    tag = f"[{cur:>{len(str(total))}}/{total}]"
    short_err = (error[:60] + "...") if len(error) > 63 else error
    _write(f"  {tag} {RED}\u2717{RESET} {label}: {short_err}")


def info(text):
    """Print an informational line."""
    _write(f"  {DIM}{text}{RESET}")


def ok(text):
    """Print a success line."""
    _write(f"  {GREEN}\u2713{RESET} {text}")


def warn(text):
    """Print a warning line."""
    _write(f"  {YELLOW}[WARN]{RESET} {text}")


def error(text):
    """Print an error line."""
    _write(f"  {RED}[ERROR]{RESET} {text}")


def summary(label, count, total, path=None, extra=None):
    """Print a summary line like 'Processed 36/37 steps ...'"""
    msg = f"  {label} {count}/{total}"
    if path:
        msg += f" to {path}"
    if extra:
        msg += f" \u2014 {extra}"
    _write(msg)


def elapsed_str(seconds):
    """Format seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.0f}s"


class Timer:
    """Context manager that prints elapsed time on exit."""

    def __init__(self, label=""):
        self.label = label
        self.start = None
        self.elapsed = 0

    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *_):
        self.elapsed = time.monotonic() - self.start
        if self.label:
            ok(f"{self.label} ({elapsed_str(self.elapsed)})")
