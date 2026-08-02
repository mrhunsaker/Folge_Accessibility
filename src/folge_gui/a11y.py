"""Small, reusable accessibility building blocks.

These helpers exist so every page reaches for the *same* correct pattern
(real heading tags, one accessible live region per status area, etc.)
instead of re-deriving it inline. Nothing here is NiceGUI-framework glue for
its own sake — each function maps directly to a WCAG 2.2 success criterion,
noted in its docstring.
"""

from __future__ import annotations

import html as _html
from typing import Literal

from nicegui import ui
from nicegui.element import Element


def heading(text: str, level: int = 1, classes: str = "") -> Element:
    """Render a *real* ``<h1>``–``<h6>`` element.

    NiceGUI's ``ui.label().classes('text-h4')`` only changes appearance — it
    stays a ``<div>``, so screen-reader users navigating by heading (a very
    common technique) never see it. Satisfies WCAG 1.3.1 (Info and
    Relationships) and 2.4.6 (Headings and Labels).
    """
    level = max(1, min(6, level))
    safe = _html.escape(text)
    el = ui.html(f"<h{level}>{safe}</h{level}>")
    if classes:
        el.classes(classes)
    return el


def sr_only(text: str) -> Element:
    """Text that is present for assistive tech but not shown visually.

    Useful for extra context a sighted user can infer visually (e.g. table
    layout) but a screen-reader user needs spelled out.
    """
    safe = _html.escape(text)
    return ui.html(f'<span class="fg-sr-only">{safe}</span>')


def visually_hidden_label(text: str, target_id: str) -> Element:
    """A ``<label>`` associated with ``target_id`` that is visually hidden.

    Use when the visible design doesn't have room for a text label but the
    control still needs an accessible name (WCAG 4.1.2 Name, Role, Value;
    WCAG 3.3.2 Labels or Instructions).
    """
    safe = _html.escape(text)
    return ui.html(f'<label for="{target_id}" class="fg-sr-only">{safe}</label>')


LiveRoutePoliteness = Literal["polite", "assertive"]


class LiveRegion:
    """An ARIA live region that reliably announces short status changes.

    Screen readers announce content added to an element with
    ``aria-live``/``role="status"`` (or ``role="alert"`` for assertive)
    automatically, without the user needing focus to be inside it. This is
    the mechanism used for "Step 3 of 7 — running" style updates (WCAG 4.1.3
    Status Messages). Keep messages short — this is for state changes, not
    for streaming command output (use the console component for that).
    """

    def __init__(self, politeness: LiveRoutePoliteness = "polite") -> None:
        role = "alert" if politeness == "assertive" else "status"
        self.container = (
            ui.element("div")
            .classes("fg-sr-only")
            .props(f'role="{role}" aria-live="{politeness}" aria-atomic="true"')
        )
        self._label = None
        with self.container:
            self._label = ui.label("")

    def announce(self, message: str) -> None:
        """Push a new message. Screen readers speak it automatically."""
        if self._label is None:
            return
        # Re-set even if identical text is sent twice in a row: some screen
        # readers only announce on a genuine DOM mutation, so clear first.
        self._label.set_text("")
        self._label.set_text(message)


def landmark(tag: str, *, label: str | None = None, classes: str = "") -> Element:
    """Create a semantic landmark element (``nav``, ``main``, ``aside`` ...).

    Adds ``aria-label`` when given, since a page can have more than one
    landmark of the same type (e.g. two ``nav`` regions) and each needs a
    distinguishing name (WCAG 1.3.1, 2.4.1 Bypass Blocks support).
    """
    el = ui.element(tag)
    if label:
        el.props(f'aria-label="{_html.escape(label)}"')
    if classes:
        el.classes(classes)
    return el


def icon_with_label(
    icon_name: str,
    text: str,
    *,
    icon_color: str = "",
    text_classes: str = "",
    gap: str = "gap-2",
) -> Element:
    """An icon + text pair where the icon is decorative (``aria-hidden``).

    Meaning always lives in ``text``, never in the icon or color alone
    (WCAG 1.4.1 Use of Color, 1.1.1 Non-text Content — decorative icons are
    hidden from assistive tech rather than given a redundant/awkward name).
    """
    row = ui.row().classes(f"items-center {gap} flex-nowrap")
    with row:
        i = ui.icon(icon_name).props('aria-hidden="true"')
        if icon_color:
            i.style(f"color: {icon_color}")
        ui.label(text).classes(text_classes)
    return row
