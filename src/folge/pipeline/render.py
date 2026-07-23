"""Render enriched JSON to Markdown."""

import json
from pathlib import Path
from typing import Optional

from folge.pipeline.progress import ProgressCallback, banner, ok, error

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def render_for_target(guide_path: Path, target: str, output_path: Path,
                      on_progress: ProgressCallback = None) -> bool:
    """Render Markdown optimized for a specific target."""
    templates_dir = PROJECT_ROOT / "templates"
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        error(on_progress, "jinja2 not installed")
        return False

    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template_name = "markdown.md"
    template = env.get_template(template_name)

    with open(guide_path, "r", encoding="utf-8") as f:
        guide = json.load(f)

    rendered = template.render(guide=guide, target=target)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    return True


def run(enriched_path: Path, target: str, output_path: Path,
        on_progress: ProgressCallback = None) -> Path:
    """Run the render step. Returns path to rendered markdown."""
    banner(on_progress, "STEP: RENDERING MARKDOWN")

    ok_flag = render_for_target(enriched_path, target, output_path, on_progress)
    if ok_flag:
        ok(on_progress, f"Rendered {target} markdown → {output_path.name}")
    else:
        error(on_progress, f"Failed to render {target} markdown")

    return output_path
