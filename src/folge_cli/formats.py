#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""
Unified pandoc output-format registry and helpers.

This module is the single source of truth for every format ``folge-cli``
can produce.  It is used by both ``pipeline.py`` and ``publish.py``.

Entry schema
------------
``to`` : str or None
    Pandoc writer name (``--to``).  When ``None`` the writer is inferred
    by pandoc from the output file extension (``docx``, ``html``).
``ext`` : str
    Output file extension.
``abbrev`` : str or None
    Short tag used for collision-free filenames.  When ``None`` the
    output file keeps the plain name ``guide<ext>``.
``lua``, ``css``, ``embed`` : bool
    Attach accessibility Lua filters, Folge CSS, and ``--embed-resources``.
``engine`` : str or None
    Optional ``--pdf-engine`` (e.g. ``xelatex`` for beamer).
``extra`` : str or None
    Optional extra CLI arguments.

The ``pdf`` and ``github`` targets are handled by special-case logic and
are NOT part of the registry.
"""
from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from .config import get_bundled_path

# Target keys handled outside the generic pandoc registry.
SPECIAL_TARGETS = ("pdf", "github")

# The complete registry of pandoc writers.
FORMATS: dict[str, dict] = {
    # ── Markdown / text family ───────────────────────────────────────
    "markdown":             {"to": "markdown",             "ext": ".md",        "abbrev": "md"},
    "commonmark":           {"to": "commonmark",           "ext": ".md",        "abbrev": "cm"},
    "commonmark_x":         {"to": "commonmark_x",         "ext": ".md",        "abbrev": "cmx"},
    "gfm":                  {"to": "gfm",                  "ext": ".md",        "abbrev": "gh"},
    "markdown_mmd":         {"to": "markdown_mmd",         "ext": ".md",        "abbrev": "mmd"},
    "markdown_phpextra":    {"to": "markdown_phpextra",    "ext": ".md",        "abbrev": "phpextra"},
    "markdown_strict":      {"to": "markdown_strict",      "ext": ".md",        "abbrev": "strict"},
    "markua":               {"to": "markua",               "ext": ".md",        "abbrev": "markua"},
    "plain":                {"to": "plain",                "ext": ".txt",       "abbrev": "plain"},
    "ansi":                 {"to": "ansi",                 "ext": ".txt",       "abbrev": "ansi"},
    "dokuwiki":             {"to": "dokuwiki",             "ext": ".txt",       "abbrev": "dokuwiki"},
    "haddock":              {"to": "haddock",              "ext": ".txt",       "abbrev": "haddock"},
    "jira":                 {"to": "jira",                 "ext": ".txt",       "abbrev": "jira"},
    "mediawiki":            {"to": "mediawiki",            "ext": ".txt",       "abbrev": "mediawiki"},
    "muse":                 {"to": "muse",                 "ext": ".txt",       "abbrev": "muse"},
    "native":               {"to": "native",               "ext": ".txt",       "abbrev": "native"},
    "xwiki":                {"to": "xwiki",                "ext": ".txt",       "abbrev": "xwiki"},
    "zimwiki":              {"to": "zimwiki",              "ext": ".txt",       "abbrev": "zimwiki"},
    "org":                  {"to": "org",                  "ext": ".org",       "abbrev": None},
    "rst":                  {"to": "rst",                  "ext": ".rst",       "abbrev": None},
    "textile":              {"to": "textile",              "ext": ".textile",   "abbrev": None},
    "texinfo":              {"to": "texinfo",              "ext": ".texi",      "abbrev": None},
    "t2t":                  {"to": "t2t",                  "ext": ".t2t",       "abbrev": None},
    "vimdoc":               {"to": "vimdoc",               "ext": ".vimdoc",    "abbrev": None},
    # ── HTML family ─────────────────────────────────────────────────
    "html":                 {"to": None,                   "ext": ".html",      "abbrev": None,
                             "lua": True, "css": True, "embed": True},
    "html4":                {"to": "html4",                "ext": ".html",      "abbrev": "html4", "embed": True},
    "html5":                {"to": "html5",                "ext": ".html",      "abbrev": "html5", "embed": True},
    "chunkedhtml":          {"to": "chunkedhtml",          "ext": ".zip",       "abbrev": "chunkedhtml"},
    "slideous":             {"to": "slideous",             "ext": ".html",      "abbrev": "slideous", "embed": True},
    "slidy":                {"to": "slidy",                "ext": ".html",      "abbrev": "slidy", "embed": True},
    "dzslides":             {"to": "dzslides",             "ext": ".html",      "abbrev": "dzslides", "embed": True},
    "revealjs":             {"to": "revealjs",             "ext": ".html",      "abbrev": "revealjs", "embed": True},
    "s5":                   {"to": "s5",                   "ext": ".html",      "abbrev": "s5", "embed": True},
    # ── XML family ──────────────────────────────────────────────────
    "docbook":              {"to": "docbook",              "ext": ".xml",       "abbrev": None},
    "docbook4":             {"to": "docbook4",             "ext": ".xml",       "abbrev": "docbook4"},
    "docbook5":             {"to": "docbook5",             "ext": ".xml",       "abbrev": "docbook5"},
    "jats":                 {"to": "jats",                 "ext": ".xml",       "abbrev": "jats"},
    "jats_archiving":       {"to": "jats_archiving",       "ext": ".xml",       "abbrev": "jats_archiving"},
    "jats_articleauthoring": {"to": "jats_articleauthoring",
                             "ext": ".xml",                "abbrev": "jats_articleauthoring"},
    "jats_publishing":      {"to": "jats_publishing",      "ext": ".xml",       "abbrev": "jats_publishing"},
    "opendocument":         {"to": "opendocument",         "ext": ".xml",       "abbrev": "opendocument"},
    "tei":                  {"to": "tei",                  "ext": ".xml",       "abbrev": "tei"},
    "xml":                  {"to": "xml",                  "ext": ".xml",       "abbrev": "xml"},
    # ── Office / docs ───────────────────────────────────────────────
    "docx":                 {"to": None,                   "ext": ".docx",      "abbrev": None, "lua": True},
    "pptx":                 {"to": "pptx",                 "ext": ".pptx",      "abbrev": None, "lua": True},
    "odt":                  {"to": "odt",                  "ext": ".odt",       "abbrev": None},
    "epub":                 {"to": "epub",                 "ext": ".epub",      "abbrev": None,
                             "embed": True},
    "epub2":                {"to": "epub2",                "ext": ".epub",      "abbrev": "epub2",
                             "embed": True},
    "epub3":                {"to": "epub3",                "ext": ".epub",      "abbrev": "epub3",
                             "embed": True},
    "fb2":                  {"to": "fb2",                  "ext": ".fb2",       "abbrev": None},
    "icml":                 {"to": "icml",                 "ext": ".icml",      "abbrev": None},
    "ipynb":                {"to": "ipynb",                "ext": ".ipynb",     "abbrev": None},
    "rtf":                  {"to": "rtf",                  "ext": ".rtf",       "abbrev": None},
    "opml":                 {"to": "opml",                 "ext": ".opml",      "abbrev": None},
    "json":                 {"to": "json",                 "ext": ".json",      "abbrev": None},
    # ── TeX / PDF ───────────────────────────────────────────────────
    "latex":                {"to": "latex",                "ext": ".tex",       "abbrev": None},
    "context":              {"to": "context",              "ext": ".tex",       "abbrev": "context"},
    "beamer":               {"to": "beamer",               "ext": ".pdf",       "abbrev": "beamer",
                             "lua": True, "css": True, "engine": "xelatex"},
    "typst":                {"to": "typst",                "ext": ".typ",       "abbrev": None},
    # ── Bibliography ────────────────────────────────────────────────
    "bibtex":               {"to": "bibtex",               "ext": ".bib",       "abbrev": None},
    "biblatex":             {"to": "biblatex",             "ext": ".bib",       "abbrev": "biblatex"},
    # ── AsciiDoc ────────────────────────────────────────────────────
    "asciidoc":             {"to": "asciidoc",             "ext": ".adoc",      "abbrev": None},
    "asciidoc_legacy":      {"to": "asciidoc_legacy",      "ext": ".adoc",      "abbrev": "asciidoc_legacy"},
    "asciidoctor":          {"to": "asciidoctor",          "ext": ".adoc",      "abbrev": "asciidoctor"},
    # ── BBCode ──────────────────────────────────────────────────────
    "bbcode":               {"to": "bbcode",               "ext": ".bbcode",    "abbrev": "bbcode"},
    "bbcode_fluxbb":        {"to": "bbcode_fluxbb",        "ext": ".bbcode",    "abbrev": "bbcode_fluxbb"},
    "bbcode_phpbb":         {"to": "bbcode_phpbb",         "ext": ".bbcode",    "abbrev": "bbcode_phpbb"},
    "bbcode_steam":         {"to": "bbcode_steam",         "ext": ".bbcode",    "abbrev": "bbcode_steam"},
    "bbcode_hubzilla":      {"to": "bbcode_hubzilla",      "ext": ".bbcode",    "abbrev": "bbcode_hubzilla"},
    "bbcode_xenforo":       {"to": "bbcode_xenforo",       "ext": ".bbcode",    "abbrev": "bbcode_xenforo"},
    # ── Misc ────────────────────────────────────────────────────────
    "djot":                 {"to": "djot",                 "ext": ".djot",      "abbrev": None},
    "man":                  {"to": "man",                  "ext": ".1",         "abbrev": None},
    "ms":                   {"to": "ms",                   "ext": ".ms",        "abbrev": None},
}

# Everything producible: all generic writers plus the two special targets.
ALL_TARGETS = list(FORMATS) + list(SPECIAL_TARGETS)

_supported_cache: frozenset[str] | None = None


def output_name(target_name: str) -> str:
    """Return the output filename for a registry target.

    Targets without an ``abbrev`` keep the plain name ``guide<ext>``;
    everything else is disambiguated as ``guide_<abbrev><ext>``.
    """
    cfg = FORMATS[target_name]
    abbrev = cfg.get("abbrev")
    if abbrev:
        return f"guide_{abbrev}{cfg['ext']}"
    return f"guide{cfg['ext']}"


def pandoc_args(target_name: str, orientation: str = "portrait") -> str:
    """Build pandoc CLI arguments for a registry target.

    Parameters
    ----------
    target_name : str
        Key into ``FORMATS`` (e.g. ``"docx"``, ``"epub"``).
    orientation : str, optional
        Page orientation for CSS selection. Default is ``"portrait"``.

    Returns
    -------
    str
        A space-separated string of Pandoc arguments.
    """
    cfg = FORMATS[target_name]
    parts = []
    if cfg.get("to"):
        parts.append(f"--to {cfg['to']}")
    if cfg.get("lua"):
        for lua in ("pdf-accessibility.lua", "docx-accessibility.lua", "accessibility.lua"):
            lua_path = get_bundled_path(lua)
            if lua_path.exists():
                parts.append(f"--lua-filter={lua_path}")
        pagebreak = get_bundled_path("templates", "pagebreak.lua")
        if pagebreak.exists():
            parts.append(f"--lua-filter={pagebreak}")
    if cfg.get("css"):
        folge_css = get_bundled_path("templates", "folge.css")
        if folge_css.exists():
            parts.append(f"--css={folge_css}")
        page_css_name = "letter-portrait.css" if orientation != "landscape" else "letter-landscape.css"
        page_css = get_bundled_path("templates", page_css_name)
        if page_css.exists():
            parts.append(f"--css={page_css}")
    if cfg.get("embed"):
        parts.append("--embed-resources")
    parts.append("--standalone")
    if cfg.get("extra"):
        parts.append(cfg["extra"])
    return " ".join(parts)


def supported_formats() -> frozenset[str]:
    """Return the set of writers supported by the installed pandoc.

    The result is cached after the first call.
    """
    global _supported_cache
    if _supported_cache is None:
        result = subprocess.run(
            ["pandoc", "--list-output-formats"],
            capture_output=True, text=True, check=False,
        )
        names: set[str] = set()
        if result.returncode == 0:
            names = {line.strip() for line in result.stdout.splitlines() if line.strip()}
        _supported_cache = frozenset(names)
    return _supported_cache


def resolve_targets(requested: list[str] | tuple[str, ...] | None):
    """Resolve a requested target list against the installed pandoc.

    Parameters
    ----------
    requested : list of str or tuple of str or None
        Comma-split target names.  ``None`` means *all* formats supported
        by the installed pandoc (plus the special ``pdf``/``github``
        targets).

    Returns
    -------
    tuple of (list of str, list of str)
        ``(selected, skipped)`` where ``skipped`` names are unknown or
        unsupported by the installed pandoc and were warned about.
    """
    supported = supported_formats()
    if requested is None:
        requested = list(ALL_TARGETS)
    selected: list[str] = []
    skipped: list[str] = []
    for name in requested:
        name = (name or "").strip()
        if not name:
            continue
        if name in SPECIAL_TARGETS:
            selected.append(name)
        elif name in FORMATS:
            writer = FORMATS[name].get("to") or name
            if writer not in supported:
                skipped.append(name)
            else:
                selected.append(name)
        else:
            skipped.append(name)
    return selected, skipped


def run_pandoc(cmd: str, log_dir):
    """Run a pandoc shell command, capturing and logging its output.

    The command is echoed, executed with ``capture_output``, and its
    stdout/stderr are appended to ``<log_dir>/pandoc.log`` under a header
    with the timestamp, command, and exit code.  The working directory is
    ``log_dir`` (the folder holding the source ``guide.md``).

    Returns
    -------
    subprocess.CompletedProcess
        The captured result (``returncode``, ``stdout``, ``stderr``).
    """
    print(f"  -> {cmd}")
    result = subprocess.run(
        cmd,
        shell=True, capture_output=True, text=True,
        cwd=str(log_dir),
    )
    _append_log(cmd, result, log_dir)
    return result


def _append_log(cmd: str, result: subprocess.CompletedProcess, log_dir):
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "pandoc.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = (
        f"\n{'=' * 70}\n"
        f"[{timestamp}] exit={result.returncode}\n"
        f"  $ {cmd}\n"
        f"{'-' * 70}"
    )
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(header + "\n")
        if result.stdout:
            f.write(result.stdout)
        if result.stderr:
            f.write(result.stderr)
        if not result.stdout and not result.stderr:
            f.write("(no output)\n")
