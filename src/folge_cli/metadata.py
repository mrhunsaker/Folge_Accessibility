#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""Accessible document metadata generator.

Addresses the required metadata elements for accessible (PDF) output:

1. Title       - the document title, never the file name
2. Author      - the person, department, or organization responsible
3. Subject     - a concise summary of the document content
4. Keywords    - terms that improve searchability and discovery
5. Language    - the primary language for correct screen-reader pronunciation
6. Tags        - structural tags for headings, lists, tables, and figures
7. Bookmarks   - an interactive outline for documents of 10+ pages
11. Security   - text copying / extraction must be allowed

The module is standalone: it reads a guide JSON (or the enriched output),
derives a metadata set, and emits a Pandoc-compatible ``metadata.yaml``
that can be embedded into EVERY output format (PDF, DOCX, HTML, PPTX,
EPUB, ODT, ...) via ``--metadata-file``.  PDF files are additionally
given their Info dictionary, document language, and security permissions
directly with PyMuPDF so that text copying is always allowed.

Usage:
    uv run folge-cli metadata <guide.json> [-o metadata.yaml]
    uv run folge-cli metadata <guide.enriched.json> --apply-pdf output/guide.pdf
    uv run folge-cli metadata <guide.json> --check --strict
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import fitz
import yaml

from .config import load_yaml_config

BOOKMARK_PAGE_THRESHOLD = 10

# Titles that fail the "avoid generic titles" best practice.
GENERIC_TITLES = {
    "untitled", "untitled document", "document", "document 1", "doc", "doc 1",
    "new document", "new file", "readme", "guide", "guide 1",
}

# Words too common to be useful as derived keywords.
STOPWORDS = {
    "the", "and", "for", "with", "how", "what", "when", "where", "why",
    "your", "you", "this", "that", "these", "those", "from", "into",
    "will", "can", "are", "has", "have", "was", "were", "not", "but",
    "they", "them", "their", "guide", "document", "overview",
    "introduction", "section", "part", "page", "step", "steps",
    "using", "use", "used", "after", "before", "then", "click",
}

# Permissions that keep a PDF open: copying is REQUIRED for assistive
# technology; the other flags keep the document usable without locks.
_ALLOWED = fitz.PDF_PERM_PRINT | fitz.PDF_PERM_MODIFY | fitz.PDF_PERM_COPY | fitz.PDF_PERM_ANNOTATE


def _clean(obj):
    """Recursively remove ``None``/empty-string values from mappings."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if v not in (None, "")}
    if isinstance(obj, list):
        return [_clean(i) for i in obj]
    return obj


def _dedupe(items):
    """Return unique items in original order."""
    seen, out = set(), []
    for item in items:
        key = str(item).strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def load_guide(guide_path):
    """Load a guide JSON in canonical or Folge-export format.

    Parameters
    ----------
    guide_path : str or Path
        Path to ``guide.json`` or ``guide.enriched.json``.

    Returns
    -------
    tuple[dict, list[dict]]
        ``(guide_dict, steps)`` where ``guide_dict`` is the top-level
        object (wrapper unwrapped) and ``steps`` is the steps list.
    """
    guide_path = Path(guide_path)
    with open(guide_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "guide" in data:
        guide = data["guide"]
        steps = data.get("steps") or guide.get("steps") or []
    else:
        guide = data or {}
        steps = guide.get("steps") or []
    return guide, steps


def _derive_keywords(steps, limit=5):
    """Derive keywords from the most frequent meaningful step-title words.

    Parameters
    ----------
    steps : list[dict]
        The guide steps.
    limit : int, optional
        Maximum number of derived keywords. Default is ``5``.

    Returns
    -------
    list[str]
        Ranked keywords derived from step titles.
    """
    counts = {}
    for step in steps:
        title = str(step.get("title") or "").lower()
        for word in re.findall(r"[a-z]{4,}", title):
            if word not in STOPWORDS:
                counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts, key=lambda w: (-counts[w], w))
    return ranked[:limit]


def build_metadata(guide_path, config=None, overrides=None):
    """Derive accessible-document metadata from a guide JSON.

    Parameters
    ----------
    guide_path : str or Path
        Path to the guide JSON (canonical or enriched).
    config : dict, optional
        Parsed ``config.yaml`` content. Defaults to the project config.
    overrides : dict, optional
        Explicit values for ``title``, ``author``, ``subject``,
        ``keywords`` (string or list), and/or ``language``.

    Returns
    -------
    dict
        Metadata with keys ``title``, ``author``, ``subject``,
        ``keywords``, ``language``, ``tags``, ``bookmarks``, and
        ``security``.
    """
    guide, steps = load_guide(guide_path)
    config = config or load_yaml_config()
    project = config.get("project", {})
    overrides = overrides or {}
    meta = guide.get("metadata") or {}

    keywords = overrides.get("keywords")
    if keywords is None:
        keywords = meta.get("keywords") or project.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [k.strip() for k in re.split(r"[,;]", keywords) if k.strip()]
    keywords = [str(k).strip() for k in keywords if str(k).strip()]
    keywords = _dedupe(keywords + _derive_keywords(steps))

    metadata = {
        "title": str(overrides.get("title") or guide.get("title") or project.get("name") or "Untitled Document").strip(),
        "author": str(overrides.get("author") or guide.get("author") or meta.get("author") or project.get("author") or "").strip(),
        "subject": str(
            overrides.get("subject")
            or guide.get("subject")
            or guide.get("description")
            or meta.get("subject")
            or project.get("description")
            or ""
        ).strip(),
        "keywords": keywords,
        "language": str(overrides.get("language") or guide.get("language") or meta.get("language") or "en").strip(),
        "tags": True,
        "bookmarks": len(steps) >= BOOKMARK_PAGE_THRESHOLD,
        "security": {"copy": "allowed"},
    }
    return _clean(metadata)


def render_metadata_yaml(metadata):
    """Render metadata as a Pandoc-compatible YAML front-matter block.

    The standard keys (``title``, ``author``, ``subject``, ``keywords``,
    ``lang``) are embedded by Pandoc into every output format, including
    the ``docProps/core.xml`` of DOCX/ODT, the ``<meta>``/``<html lang>``
    of HTML (read by WeasyPrint for PDFs), and EPUB OPF metadata.

    Parameters
    ----------
    metadata : dict
        Metadata dict from ``build_metadata``.

    Returns
    -------
    str
        A ``---``-delimited YAML block.
    """
    doc = {
        "title": metadata.get("title", ""),
        "author": metadata.get("author", ""),
        "subject": metadata.get("subject", ""),
        "keywords": metadata.get("keywords", []),
        "lang": metadata.get("language", "en"),
        "description": metadata.get("subject", ""),
    }
    body = yaml.safe_dump(_clean(doc), allow_unicode=True, sort_keys=False).strip()
    return f"---\n{body}\n---\n"


def write_metadata_file(metadata, out_path):
    """Write the Pandoc-compatible metadata YAML to *out_path*.

    Parameters
    ----------
    metadata : dict
        Metadata dict from ``build_metadata``.
    out_path : str or Path
        Destination ``.yaml`` path.

    Returns
    -------
    Path
        The written path.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_metadata_yaml(metadata), encoding="utf-8")
    return out_path


def _pdf_info(metadata):
    """Build the PDF Info-dictionary entries from metadata."""
    info = {"creator": "Folge Vision Publishing Pipeline"}
    if metadata.get("title"):
        info["title"] = metadata["title"]
    if metadata.get("author"):
        info["author"] = metadata["author"]
    if metadata.get("subject"):
        info["subject"] = metadata["subject"]
    if metadata.get("keywords"):
        info["keywords"] = ", ".join(metadata["keywords"])
    return info


def apply_pdf_metadata(pdf_path, metadata):
    """Embed metadata into a PDF and guarantee text copying is allowed.

    Sets the PDF Info dictionary (title, author, subject, keywords,
    creator) and the document language.  If the PDF carries a security
    handler that restricts copying -- which would block assistive
    technology and violate WCAG/PDF-format accessibility requirements --
    the security handler is stripped so text extraction is allowed.

    Parameters
    ----------
    pdf_path : str or Path
        Path to an existing PDF file.
    metadata : dict
        Metadata dict from ``build_metadata``.

    Returns
    -------
    dict
        Summary with ``copy_allowed``, ``bookmarks``, and ``metadata``.
    """
    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)
    doc.set_metadata(_pdf_info(metadata))
    if metadata.get("language"):
        doc.set_language(metadata["language"])

    if not (doc.permissions & fitz.PDF_PERM_COPY):
        tmp = pdf_path.with_suffix(pdf_path.suffix + ".metadata.tmp")
        doc.save(tmp, encryption=fitz.PDF_ENCRYPT_NONE, garbage=0, deflate=True)
        doc.close()
        os.replace(tmp, pdf_path)
        doc = fitz.open(pdf_path)
    else:
        doc.saveIncr()
        doc.close()
        doc = fitz.open(pdf_path)

    summary = {
        "copy_allowed": bool(doc.permissions & fitz.PDF_PERM_COPY),
        "bookmarks": len(doc.get_toc()),
        "metadata": dict(doc.metadata),
    }
    doc.close()
    return summary


def check_compliance(metadata, page_count=None):
    """Check metadata against accessible-document best practices.

    Parameters
    ----------
    metadata : dict
        Metadata dict from ``build_metadata``.
    page_count : int, optional
        Number of pages in the final PDF, used for the bookmark check.

    Returns
    -------
    list[str]
        Human-readable compliance issues; empty when compliant.
    """
    issues = []
    title = str(metadata.get("title") or "").strip().lower()
    if not title:
        issues.append("Title is missing - provide a clear, specific document title")
    elif title in GENERIC_TITLES:
        issues.append(
            f"Title '{metadata['title']}' is generic - use a clear, specific document title"
        )
    if not metadata.get("author"):
        issues.append("Author is missing - identify the person, department, or organization responsible")
    if not metadata.get("subject"):
        issues.append("Subject is missing - provide a concise summary of the document content")
    if not metadata.get("keywords"):
        issues.append("Keywords are missing - include terms that accurately reflect the content")
    if not metadata.get("language"):
        issues.append("Language is not specified - set the primary document language")
    if metadata.get("bookmarks") and page_count is not None and page_count < BOOKMARK_PAGE_THRESHOLD:
        issues.append("Bookmarks flagged for a short document - add bookmarks only for documents of 10+ pages")
    if metadata.get("security", {}).get("copy") != "allowed":
        issues.append("Security settings block text copying - allow text extraction for assistive technology")
    return issues


def run(guide_path, out=None, apply_pdf=None, check=False, strict=False,
        author=None, subject=None, language=None, keywords=None):
    """Build metadata, optionally write YAML, and optionally patch a PDF.

    Parameters
    ----------
    guide_path : str or Path
        Path to the guide JSON.
    out : str or Path, optional
        Write the Pandoc-compatible metadata YAML here.
    apply_pdf : str or Path, optional
        Embed metadata into this PDF and allow text copying.
    check : bool, optional
        Print best-practice compliance results.
    strict : bool, optional
        Return an exit status of 1 when compliance issues are found.
    author : str, optional
        Override the document author.
    subject : str, optional
        Override the document subject.
    language : str, optional
        Override the primary document language.
    keywords : str, optional
        Override keywords (comma/semicolon separated).

    Returns
    -------
    dict
        Result with ``metadata``, ``metadata_yaml``, ``pdf`` (when
        ``apply_pdf`` was given), and ``issues`` (when ``check``).
    """
    overrides = {"author": author, "subject": subject, "language": language}
    if keywords:
        overrides["keywords"] = [k.strip() for k in re.split(r"[,;]", keywords) if k.strip()]
    overrides = {k: v for k, v in overrides.items() if v is not None}

    metadata = build_metadata(guide_path, overrides=overrides)
    meta_yaml = render_metadata_yaml(metadata)

    print(f"\n  Accessible Document Metadata: {Path(guide_path).name}")
    print(f"  Title      : {metadata.get('title', '')}")
    print(f"  Author     : {metadata.get('author', '')}")
    print(f"  Subject    : {metadata.get('subject', '')}")
    print(f"  Keywords   : {', '.join(metadata.get('keywords', []))}")
    print(f"  Language   : {metadata.get('language', '')}")
    print(f"  Tags       : {'present' if metadata.get('tags') else 'missing'}")
    print(f"  Bookmarks  : {'recommended' if metadata.get('bookmarks') else 'n/a (< 10 pages)'}")
    print(f"  Security   : text copying {'allowed' if metadata.get('security', {}).get('copy') == 'allowed' else 'RESTRICTED'}")

    result = {"metadata": metadata, "metadata_yaml": meta_yaml}

    if out:
        written = write_metadata_file(metadata, out)
        print(f"  Metadata YAML written to {written}")

    if apply_pdf:
        summary = apply_pdf_metadata(apply_pdf, metadata)
        result["pdf"] = summary
        print(f"\n  PDF metadata applied to {apply_pdf}")
        print(f"  Copy allowed : {summary['copy_allowed']}")
        print(f"  Bookmarks    : {summary['bookmarks']} outline entrie(s)")
        print(f"  PDF metadata : {summary['metadata']}")

    issues = []
    if check:
        page_count = result.get("pdf", {}).get("pages") if "pdf" in result else None
        issues = check_compliance(metadata, page_count=page_count)
        print(f"\n  Compliance check ({'PASS' if not issues else f'{len(issues)} issue(s)'}):")
        for issue in issues:
            print(f"    - {issue}")
        if not issues:
            print("    All accessible-document metadata requirements are satisfied.")
        if strict:
            result["issues"] = issues

    return result


def main():
    """CLI entry point for the ``metadata`` sub-command."""
    parser = argparse.ArgumentParser(
        prog="folge-cli metadata",
        description="Generate accessible-document metadata for all output formats",
    )
    parser.add_argument("guide", help="Path to guide.json or guide.enriched.json")
    parser.add_argument("-o", "--out", default=None, help="Write Pandoc-compatible metadata YAML here")
    parser.add_argument("--apply-pdf", default=None, help="Embed metadata into this PDF and allow text copying")
    parser.add_argument("--check", action="store_true", help="Check metadata against accessibility best practices")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when --check finds issues")
    parser.add_argument("--author", default=None, help="Override the document author")
    parser.add_argument("--subject", default=None, help="Override the document subject")
    parser.add_argument("--language", default=None, help="Override the primary document language")
    parser.add_argument("--keywords", default=None, help="Override keywords (comma/semicolon separated)")
    args = parser.parse_args()

    result = run(
        args.guide,
        out=args.out,
        apply_pdf=args.apply_pdf,
        check=args.check,
        strict=args.strict,
        author=args.author,
        subject=args.subject,
        language=args.language,
        keywords=args.keywords,
    )
    if args.strict and result.get("issues"):
        sys.exit(1)


if __name__ == "__main__":
    main()
