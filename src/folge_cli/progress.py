#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""Shared progress reporting utilities for the Folge pipeline.

Thread-safe helpers for printing per-step and per-phase progress.
All output is flushed immediately so it streams to the terminal.
"""
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
    """Write text to stdout in a thread-safe manner.

    Parameters
    ----------
    text : str
        The text to print.
    """
    with _lock:
        print(text, flush=True)


def banner(text, char="=", width=60):
    """Print a section banner delimited by repeated characters.

    Parameters
    ----------
    text : str
        The banner title text.
    char : str, optional
        Character used for the border lines. Default is ``"="``.
    width : int, optional
        Total width of the border line. Default is ``60``.
    """
    _write(f"\n{char * width}")
    _write(f"  {text}")
    _write(f"{char * width}")


def phase(name):
    """Print a phase header using a banner.

    Parameters
    ----------
    name : str
        The name of the phase.
    """
    banner(name)


def step_start(cur, total, label, detail=""):
    """Print a step-in-progress line.

    Parameters
    ----------
    cur : int
        The current step number (1-indexed).
    total : int
        The total number of steps.
    label : str
        Short label describing the step.
    detail : str, optional
        Additional detail shown after an em-dash. Default is ``""``.
    """
    tag = f"[{cur:>{len(str(total))}}/{total}]"
    msg = f"  {tag} {label}"
    if detail:
        msg += f" \u2014 {detail}"
    _write(f"{msg}")


def step_ok(cur, total, label, elapsed=None):
    """Print a completed step line with a green check mark.

    Parameters
    ----------
    cur : int
        The current step number (1-indexed).
    total : int
        The total number of steps.
    label : str
        Short label describing the step.
    elapsed : float, optional
        Elapsed time in seconds. Default is ``None`` (omitted).
    """
    tag = f"[{cur:>{len(str(total))}}/{total}]"
    suffix = f" ({elapsed:.1f}s)" if elapsed is not None else ""
    _write(f"  {tag} {GREEN}\u2713{RESET} {label}{suffix}")


def step_error(cur, total, label, error=""):
    """Print a failed step line with a red cross mark.

    Parameters
    ----------
    cur : int
        The current step number (1-indexed).
    total : int
        The total number of steps.
    label : str
        Short label describing the step.
    error : str, optional
        Error message, truncated to 60 characters. Default is ``""``.
    """
    tag = f"[{cur:>{len(str(total))}}/{total}]"
    short_err = (error[:60] + "...") if len(error) > 63 else error
    _write(f"  {tag} {RED}\u2717{RESET} {label}: {short_err}")


def info(text):
    """Print an informational line in dim text.

    Parameters
    ----------
    text : str
        The informational message.
    """
    _write(f"  {DIM}{text}{RESET}")


def ok(text):
    """Print a success line with a green check mark.

    Parameters
    ----------
    text : str
        The success message.
    """
    _write(f"  {GREEN}\u2713{RESET} {text}")


def warn(text):
    """Print a warning line with a [WARN] prefix.

    Parameters
    ----------
    text : str
        The warning message.
    """
    _write(f"  {YELLOW}[WARN]{RESET} {text}")


def error(text):
    """Print an error line with an [ERROR] prefix.

    Parameters
    ----------
    text : str
        The error message.
    """
    _write(f"  {RED}[ERROR]{RESET} {text}")


def summary(label, count, total, path=None, extra=None):
    """Print a summary line showing progress counts.

    Parameters
    ----------
    label : str
        Descriptive label (e.g. ``"Processed"``).
    count : int
        Number of completed items.
    total : int
        Total number of items.
    path : str, optional
        Output path appended after ``"to"``. Default is ``None``.
    extra : str, optional
        Additional info appended after an em-dash. Default is ``None``.
    """
    msg = f"  {label} {count}/{total}"
    if path:
        msg += f" to {path}"
    if extra:
        msg += f" \u2014 {extra}"
    _write(msg)


def elapsed_str(seconds):
    """Format seconds into a human-readable string.

    Parameters
    ----------
    seconds : float
        Time in seconds.

    Returns
    -------
    str
        Formatted string such as ``"12.3s"`` or ``"2m 15s"``.
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.0f}s"


class Timer:
    """Context manager that measures and prints elapsed time.

    Parameters
    ----------
    label : str, optional
        Label printed on exit. Default is ``""`` (silent).

    Attributes
    ----------
    elapsed : float
        Elapsed wall-clock seconds after exiting the context.
    """

    def __init__(self, label=""):
        self.label = label
        self.start = None
        self.elapsed = 0

    def __enter__(self):
        """Start the timer.

        Returns
        -------
        Timer
            This instance.
        """
        self.start = time.monotonic()
        return self

    def __exit__(self, *_):
        """Stop the timer and print the result if a label was given."""
        self.elapsed = time.monotonic() - self.start
        if self.label:
            ok(f"{self.label} ({elapsed_str(self.elapsed)})")


class StepCounter:
    """Thread-safe counter for tracking batch progress.

    Parameters
    ----------
    total : int
        Total number of steps in the batch.

    Attributes
    ----------
    done : int
        Number of steps completed so far.
    errors : int
        Number of failed steps so far.
    """

    def __init__(self, total):
        self.total = total
        self.done = 0
        self.errors = 0
        self._lock = threading.Lock()

    def tick(self, success=True):
        """Record one completed step.

        Parameters
        ----------
        success : bool, optional
            Whether the step succeeded. Default is ``True``.

        Returns
        -------
        tuple[int, int]
            ``(done, errors)`` counts after the update.
        """
        with self._lock:
            self.done += 1
            if not success:
                self.errors += 1
            return self.done, self.errors
