#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""Render Markdown from enriched JSON using Jinja2 templates."""
import json
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from folge_cli.config import get_bundled_path

env = Environment(
    loader=FileSystemLoader(str(get_bundled_path("templates"))),
    autoescape=False
)


def render_markdown(guide_path, template_name="markdown.md",
                    config=None, output_path=None, images_dir=None):
    """Render Markdown from enriched JSON using a Jinja2 template.

    Parameters
    ----------
    guide_path : str or Path
        Path to the enriched JSON file.
    template_name : str, optional
        Name of the Jinja2 template file. Default is "markdown.md".
    config : dict, optional
        Template configuration overrides.
    output_path : str or Path, optional
        If provided, write the rendered Markdown to this path.
    images_dir : str or Path, optional
        Directory containing the guide's screenshots, used to compute the
        relative ``image_prefix`` for the rendered Markdown. Defaults to
        ``<guide dir>/images``.

    Returns
    -------
    str
        The rendered Markdown content.
    """
    guide_path = Path(guide_path)

    with open(guide_path, "r", encoding="utf-8") as f:
        guide = json.load(f)

    template = env.get_template(template_name)

    default_config = {
        "include_long_descriptions": True,
        "include_ocr": False,
        "include_ui_controls": False,
        "newpage_enabled": True,
        "image_prefix": "",
    }

    if output_path:
        output_dir = Path(output_path).resolve().parent
        if images_dir is None:
            images_dir = guide_path.resolve().parent / "images"
        images_dir = Path(images_dir).resolve()
        try:
            rel = os.path.relpath(images_dir, output_dir)
            default_config["image_prefix"] = rel + "/"
        except ValueError:
            default_config["image_prefix"] = "images/"

    if config:
        default_config.update(config)

    markdown = template.render(**guide, **default_config)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(markdown)
        size = out.stat().st_size
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024*1024):.1f} MB"
        print(f"  Rendered to {out} ({size_str})")

    return markdown


def render_for_target(guide_path, target, output_path, images_dir=None):
    """Render Markdown optimized for a specific target format.

    Parameters
    ----------
    guide_path : str or Path
        Path to the enriched JSON file.
    target : str
        Any format key, e.g. ``'pdf'``, ``'docx'``, ``'pptx'``,
        ``'html'``, ``'github'``.  Unknown targets fall back to the
        ``'pdf'`` configuration.
    output_path : str or Path
        Destination file path for the rendered Markdown.
    images_dir : str or Path, optional
        Directory containing the guide's screenshots (see
        :func:`render_markdown`). Defaults to ``<guide dir>/images``.
    """
    configs = {
        "pdf": {
            "include_long_descriptions": True,
            "newpage_enabled": True
        },
        "docx": {
            "include_long_descriptions": True,
            "newpage_enabled": True
        },
        "pptx": {
            "include_long_descriptions": True,
            "newpage_enabled": True
        },
        "html": {
            "include_long_descriptions": True,
            "include_ocr": True,
            "include_ui_controls": True,
            "newpage_enabled": False
        },
        "github": {
            "include_long_descriptions": False,
            "newpage_enabled": False
        },
        "typst": {
            "include_long_descriptions": True,
            "newpage_enabled": True
        },
        "asciidoc": {
            "include_long_descriptions": True,
            "newpage_enabled": True
        },
        "beamer": {
            "include_long_descriptions": True,
            "newpage_enabled": True
        },
        "commonmark": {
            "include_long_descriptions": True,
            "newpage_enabled": False
        },
        "gfm": {
            "include_long_descriptions": True,
            "newpage_enabled": False
        },
        "markdown": {
            "include_long_descriptions": True,
            "newpage_enabled": False
        },
        "markdown_mmd": {
            "include_long_descriptions": True,
            "newpage_enabled": False
        },
        "markdown_phpextra": {
            "include_long_descriptions": True,
            "newpage_enabled": False
        },
        "markdown_strict": {
            "include_long_descriptions": True,
            "newpage_enabled": False
        },
        "markua": {
            "include_long_descriptions": True,
            "newpage_enabled": False
        },
        "commonmark_x": {
            "include_long_descriptions": True,
            "newpage_enabled": False
        },
        "docbook": {
            "include_long_descriptions": True,
            "newpage_enabled": True
        },
        "epub": {
            "include_long_descriptions": True,
            "newpage_enabled": True
        },
        "odt": {
            "include_long_descriptions": True,
            "newpage_enabled": True
        },
        "rst": {
            "include_long_descriptions": True,
            "newpage_enabled": True
        },
        "latex": {
            "include_long_descriptions": True,
            "newpage_enabled": True
        },
    }

    config = configs.get(target, configs["pdf"])
    render_markdown(guide_path, "markdown.md", config, output_path, images_dir)


def main():
    """CLI entry point for the render sub-command."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="folge-cli render",
        description="Render Markdown from an enriched guide JSON.",
    )
    parser.add_argument("--images-dir", default=None,
                        help="Guide's images directory (default: <guide dir>/images)")
    parser.add_argument("targets", nargs="*",
                        help="<guide.json> [<target>] <output.md>")
    args, _ = parser.parse_known_args()
    remaining = args.targets

    if len(remaining) < 2 or len(remaining) > 3:
        parser.error("usage: folge-cli render <guide.json> [<target>] <output.md>")
    guide_path = Path(remaining[0])

    if len(remaining) == 2:
        render_markdown(guide_path, output_path=Path(remaining[1]),
                        images_dir=args.images_dir)
    else:
        render_for_target(guide_path, remaining[1], Path(remaining[2]),
                          images_dir=args.images_dir)


if __name__ == "__main__":
    main()
