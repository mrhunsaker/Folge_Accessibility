"""Runs ``folge_cli`` commands as real subprocesses and streams their output.

Design principle: folge_gui never imports folge_cli's step implementations
(``batch_process.main()``, ``pipeline.run_pipeline()``, ...) to execute work
in-process. Every step is launched exactly the way a person at a terminal
would launch it — ``sys.executable -m folge_cli <command> ...`` — using the
same Python interpreter/environment the GUI itself is running under. This
keeps folge_cli completely unmodified and behaviorally identical whether it's
driven from a terminal or from this GUI.

The trickiest part is ``folge_cli pipeline``: it calls the builtin
``input()`` twice (a provider-availability confirmation, and a mandatory
"review the enriched JSON before rendering" pause). ``input()`` writes its
prompt to stdout *without* a trailing newline and then blocks reading stdin.
A naive ``readline()``-based reader would therefore hang forever: the prompt
bytes sit in the pipe with no newline to complete the read, and we can't
know to answer a prompt we can't see yet. To avoid that, output is read in
raw chunks and scanned for known prompt strings as soon as they arrive,
independent of line boundaries.
"""

from __future__ import annotations

import asyncio
import re
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# ANSI SGR escape sequences (folge_cli's progress.py prints color codes
# unconditionally, regardless of whether stdout is a real terminal).
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI color escape codes so captured output reads cleanly."""
    return _ANSI_RE.sub("", text)


class StepStatus(str, Enum):
    """Lifecycle of one command run, used to drive both visuals and ARIA state."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


# Known input() prompts printed by folge_cli.pipeline.run_pipeline(). Matched
# against the *stripped* trailing content of the not-yet-newline-terminated
# buffer. Kept here (rather than in pipeline_page.py) because recognizing
# them is a property of how the subprocess's stdout behaves, not of the page.
PROVIDER_CONFIRM_PROMPT = "Continue anyway? [y/N]"
REVIEW_PROMPT = "(C)ontinue to rendering  or  (R)eVerify enriched JSON? [C/R]"
KNOWN_PROMPTS: tuple[str, ...] = (PROVIDER_CONFIRM_PROMPT, REVIEW_PROMPT)


@dataclass
class ProcessRun:
    """One launch of ``python -m folge_cli <args>`` with streaming I/O.

    Attach listeners with :meth:`on_line`, :meth:`on_status`, and (only
    needed for the interactive ``pipeline`` command) :meth:`on_prompt`
    *before* calling :meth:`start`.
    """

    args: list[str]
    cwd: Path
    process: asyncio.subprocess.Process | None = field(default=None, init=False)
    status: StepStatus = field(default=StepStatus.PENDING, init=False)
    return_code: int | None = field(default=None, init=False)
    _line_listeners: list[Callable[[str], Awaitable[None] | None]] = field(
        default_factory=list, init=False
    )
    _status_listeners: list[Callable[[StepStatus], Awaitable[None] | None]] = field(
        default_factory=list, init=False
    )
    _prompt_listeners: list[Callable[[str], Awaitable[None] | None]] = field(
        default_factory=list, init=False
    )
    _cancelled: bool = field(default=False, init=False)

    def on_line(self, callback: Callable[[str], Awaitable[None] | None]) -> None:
        """Register a callback invoked with each output line (ANSI stripped)."""
        self._line_listeners.append(callback)

    def on_status(self, callback: Callable[[StepStatus], Awaitable[None] | None]) -> None:
        """Register a callback invoked whenever :attr:`status` changes."""
        self._status_listeners.append(callback)

    def on_prompt(self, callback: Callable[[str], Awaitable[None] | None]) -> None:
        """Register a callback invoked when a known interactive prompt is seen.

        The callback receives the matched prompt constant (e.g.
        :data:`REVIEW_PROMPT`). It should eventually call :meth:`send_input`.
        """
        self._prompt_listeners.append(callback)

    async def _emit(self, listeners, value) -> None:
        for cb in list(listeners):
            result = cb(value)
            if asyncio.iscoroutine(result):
                await result

    async def _emit_line(self, line: str) -> None:
        await self._emit(self._line_listeners, strip_ansi(line))

    async def _set_status(self, status: StepStatus) -> None:
        self.status = status
        await self._emit(self._status_listeners, status)

    async def start(self) -> int:
        """Launch the subprocess and stream its output until it exits.

        Returns the process's exit code. Safe to await from a NiceGUI
        ``on_click`` async handler.
        """
        await self._set_status(StepStatus.RUNNING)
        self.process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "folge_cli",
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(self.cwd),
        )
        assert self.process.stdout is not None

        buffer = ""
        try:
            while True:
                chunk = await self.process.stdout.read(4096)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    await self._emit_line(line.rstrip("\r"))

                matched = _match_prompt(buffer)
                if matched is not None:
                    # Flush the still-unterminated prompt text as a line so
                    # it's visible in the console, then hand off control.
                    await self._emit_line(buffer)
                    buffer = ""
                    await self._set_status(StepStatus.WAITING_INPUT)
                    await self._emit(self._prompt_listeners, matched)
        except asyncio.CancelledError:
            self.cancel()
            raise
        finally:
            if buffer:
                await self._emit_line(buffer)

        self.return_code = await self.process.wait()
        if self._cancelled:
            await self._set_status(StepStatus.CANCELLED)
        elif self.return_code == 0:
            await self._set_status(StepStatus.SUCCESS)
        else:
            await self._set_status(StepStatus.ERROR)
        return self.return_code

    async def send_input(self, text: str) -> None:
        """Write a line to the subprocess's stdin (e.g. answering a prompt)."""
        if not self.process or not self.process.stdin:
            return
        try:
            self.process.stdin.write((text + "\n").encode("utf-8"))
            await self.process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        await self._set_status(StepStatus.RUNNING)

    def cancel(self) -> None:
        """Terminate the subprocess (e.g. user pressed a Cancel button)."""
        self._cancelled = True
        if self.process and self.process.returncode is None:
            try:
                self.process.terminate()
            except ProcessLookupError:
                pass


def _match_prompt(buffer: str) -> str | None:
    stripped = buffer.rstrip()
    for prompt in KNOWN_PROMPTS:
        if stripped.endswith(prompt):
            return prompt
    return None
