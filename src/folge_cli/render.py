#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""Render Markdown from enriched JSON using Jinja2 templates."""
import json
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from folge_cli.config import get_bundled_path, BUNDLED_DIR

env = Environment(
    loader=FileSystemLoader(str(get_bundled_path("templates"))),
    autoescape=False
)


def render_markdown(guide_path, template_name="markdown.md",
                    config=None, output_path=None):
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
        images_dir = (BUNDLED_DIR / "images").resolve()
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


def render_for_target(guide_path, target, output_path):
    """Render Markdown optimized for a specific target format.

    Parameters
    ----------
    guide_path : str or Path
        Path to the enriched JSON file.
    target : str
        One of ``'pdf'``, ``'docx'``, ``'pptx'``, ``'html'``, ``'github'``.
    output_path : str or Path
        Destination file path for the rendered Markdown.
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
        }
    }

    config = configs.get(target, configs["pdf"])
    render_markdown(guide_path, "markdown.md", config, output_path)


def main():
    """CLI entry point for the render sub-command."""
    import sys
    if len(sys.argv) < 3:
        print("Usage: folge-cli render <guide.enriched.json> <target> <output.md>")
        print("  Target: pdf, docx, pptx, html, github")
        sys.exit(1)

    guide_path = Path(sys.argv[1])

    if len(sys.argv) == 3:
        render_markdown(guide_path, output_path=Path(sys.argv[2]))
    else:
        target = sys.argv[2]
        output_path = Path(sys.argv[3])
        render_for_target(guide_path, target, output_path)


if __name__ == "__main__":
    main()
