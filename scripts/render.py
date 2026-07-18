#!/usr/bin/env python3
"""Render Markdown from enriched JSON using Jinja2 templates."""
import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# Set up Jinja2 environment
env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=False
)

def render_markdown(guide_path, template_name="markdown.md",
                   config=None, output_path=None):
    """
    Render Markdown from enriched JSON.

    Args:
        guide_path: Path to guide.enriched.json
        template_name: Template file name
        config: Template configuration dict
        output_path: Output file path (optional)

    Returns:
        Rendered Markdown string
    """

    # Load guide
    with open(guide_path, 'r', encoding='utf-8') as f:
        guide = json.load(f)

    # Load template
    template = env.get_template(template_name)

    # Default configuration
    default_config = {
        "include_long_descriptions": True,
        "include_ocr": False,
        "include_ui_controls": False,
        "newpage_enabled": True
    }

    # Merge configuration
    if config:
        default_config.update(config)

    # Render template
    markdown = template.render(
        **guide,
        **default_config
    )

    # Write to file if output_path provided
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        print(f"Rendered Markdown to {output_path}")

    return markdown

def render_for_target(guide_path, target, output_path):
    """
    Render Markdown optimized for a specific target.

    Args:
        guide_path: Path to guide.enriched.json
        target: One of 'pdf', 'docx', 'html', 'github'
        output_path: Output file path
    """

    # Target-specific configuration
    configs = {
        "pdf": {
            "include_long_descriptions": True,
            "newpage_enabled": True
        },
        "docx": {
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

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python render.py <guide.enriched.json> <output.md>")
        print("       python render.py <guide.enriched.json> <target> <output.md>")
        print("  Target: pdf, docx, html, github")
        sys.exit(1)

    guide_path = Path(sys.argv[1])

    if len(sys.argv) == 3:
        # Simple render with defaults
        render_markdown(guide_path, output_path=Path(sys.argv[2]))
    else:
        # Render for specific target
        target = sys.argv[2]
        output_path = Path(sys.argv[3])
        render_for_target(guide_path, target, output_path)
