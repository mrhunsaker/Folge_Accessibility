"""Registry describing each ``folge_cli`` sub-command as a GUI form.

Each :class:`StepSpec` mirrors one ``argparse`` sub-parser in
``folge_cli/cli.py`` exactly (same positionals in the same order, same
flags) — see that file's docstring/definitions if you need to cross-check.
``build_args`` turns the values a person entered into the exact argv list
that would be typed at a terminal after ``folge-cli``.

This module only *describes* commands; it never calls folge_cli itself.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from folge_cli.config import (
    PROJECTS_DIR,
    PROVIDERS,
    project_base,
    project_images,
    project_output,
    resolve_guide,
)
from folge_cli.formats import ALL_TARGETS

#: Every format folge_cli knows how to produce, from the shared registry
#: in ``folge_cli.formats`` (single source of truth).
TARGET_FORMATS: list[str] = list(ALL_TARGETS)

RENDER_TARGETS: list[str] = ["pdf", "docx", "pptx", "html", "github"]

ORIENTATIONS: list[str] = ["portrait", "landscape"]


@dataclass
class FieldSpec:
    """One form field on a step card."""

    key: str
    label: str
    kind: str = "text"  # text | password | number | select | multiselect | checkbox | paths
    default: str = ""
    required: bool = False
    help: str = ""
    options: list[str] = field(default_factory=list)
    placeholder: str = ""
    project_key: str = ""  # set to override `default` from the active project


def project_defaults(project: str) -> dict[str, str]:
    """Resolve absolute default paths for a project folder.

    Returns a mapping from ``FieldSpec.project_key`` to an absolute path,
    or ``""`` when the guide JSON cannot be discovered.  An empty dict is
    returned when no project is selected.  Keys:

    - ``guide``: the project's single JSON file (any name)
    - ``images``: ``<project>/images``
    - ``output``: ``<project>/output``
    - ``vision`` / ``enriched`` / ``schema_warnings`` / ``manual`` /
      ``md`` / ``pdf``: generated files inside ``output/``
    """
    if not project:
        return {}
    try:
        guide = resolve_guide(project=project)
    except (FileNotFoundError, ValueError):
        guide = None
    base = project_base(guide) if guide else PROJECTS_DIR / project
    images = project_images(guide) if guide else base / "images"
    output = project_output(guide) if guide else base / "output"
    return {
        "guide": str(guide) if guide else "",
        "images": str(images),
        "output": str(output),
        "vision": str(output / "vision-results.json"),
        "enriched": str(output / "guide.enriched.json"),
        "schema_warnings": str(output / "schema-warnings.json"),
        "manual": str(output / "manual-attention-needed.md"),
        "md": str(output / "guide.md"),
        "pdf": str(output / "guide.pdf"),
    }


@dataclass
class StepSpec:
    """A single ``folge_cli`` sub-command, described for the Steps page."""

    id: str
    title: str
    icon: str
    description: str
    fields: list[FieldSpec]
    build_args: Callable[[dict], list[str]]
    notes: str = ""


def _paths(text: str) -> list[str]:
    """Split a free-form "one or more paths" field on whitespace/commas/newlines."""
    if not text:
        return []
    normalized = text.replace(",", "\n")
    return [line.strip() for line in normalized.splitlines() if line.strip()]


def _bp_args(v: dict) -> list[str]:
    args = ["batch-process", v["guide"], v["image_dir"], v["output"]]
    if v.get("provider"):
        args += ["--provider", v["provider"]]
    if v.get("api_key"):
        args += ["--api-key", v["api_key"]]
    if v.get("model"):
        args += ["--model", v["model"]]
    if v.get("sequential"):
        args += ["--sequential"]
    return args


def _merge_args(v: dict) -> list[str]:
    return ["merge", v["guide"], v["vision"], v["output"]]


def _validate_schema_args(v: dict) -> list[str]:
    args = ["validate-schema", *_paths(v["files"])]
    if v.get("warnings_out"):
        args += ["--warnings-out", v["warnings_out"]]
    return args


def _validate_content_args(v: dict) -> list[str]:
    args = ["validate-content", v["file"]]
    if v.get("min_confidence"):
        args += [str(v["min_confidence"])]
    return args


def _validate_pdf_args(v: dict) -> list[str]:
    return ["validate-pdf", v["pdf"]]


def _render_args(v: dict) -> list[str]:
    args = ["render", v["guide"], v["target"], v["output"]]
    if v.get("images_dir"):
        args += ["--images-dir", v["images_dir"]]
    return args


def _publish_args(v: dict) -> list[str]:
    args = ["publish", v["guide"], v["output"], v["targets"], v["provider"]]
    if v.get("orientation"):
        args += ["--orientation", v["orientation"]]
    return args


def _manual_attention_args(v: dict) -> list[str]:
    args = ["generate-manual-attention", v["enriched"], v["images_dir"], v["output"]]
    if v.get("warnings"):
        args += [v["warnings"]]
    return args


STEPS: list[StepSpec] = [
    StepSpec(
        id="batch-process",
        title="Batch-process images",
        icon="smart_toy",
        description=(
            "Send every image referenced in the guide through the configured "
            "vision provider and save the raw results."
        ),
        fields=[
            FieldSpec("guide", "Guide JSON", default="guide.json", required=True,
                       project_key="guide",
                       help="Path to the guide exported from Folge (any name)."),
            FieldSpec("image_dir", "Images directory", default="images", required=True,
                       project_key="images"),
            FieldSpec("output", "Output file", default="output/vision-results.json", required=True,
                       project_key="vision"),
            FieldSpec("provider", "Provider", kind="select", options=[""] + PROVIDERS,
                       help="Leave blank to use the provider configured in Setup."),
            FieldSpec("api_key", "API key override", kind="password",
                       help="Optional — overrides the key from .env for this run only."),
            FieldSpec("model", "Model override", help="Optional — overrides the configured model."),
            FieldSpec("sequential", "Process sequentially", kind="checkbox",
                       help="Disable concurrent workers (slower, easier to debug)."),
        ],
        build_args=_bp_args,
        notes="Calls the vision provider for every image — this is the step most likely to cost time or money on cloud providers.",
    ),
    StepSpec(
        id="merge",
        title="Merge guide + vision results",
        icon="merge",
        description="Deterministically combine the original guide with vision results into an enriched JSON file.",
        fields=[
            FieldSpec("guide", "Guide JSON", default="guide.json", required=True,
                       project_key="guide"),
            FieldSpec("vision", "Vision results JSON", default="output/vision-results.json", required=True,
                       project_key="vision"),
            FieldSpec("output", "Output file", default="output/guide.enriched.json", required=True,
                       project_key="enriched"),
        ],
        build_args=_merge_args,
    ),
    StepSpec(
        id="validate-schema",
        title="Validate schema",
        icon="fact_check",
        description="Check one or more JSON files against the enriched-guide schema.",
        fields=[
            FieldSpec("files", "File(s) to validate", kind="paths",
                       default="output/guide.enriched.json", required=True,
                       project_key="enriched",
                       help="One path per line (or comma/space separated)."),
            FieldSpec("warnings_out", "Warnings output file", default="output/schema-warnings.json",
                       project_key="schema_warnings"),
        ],
        build_args=_validate_schema_args,
    ),
    StepSpec(
        id="validate-content",
        title="Validate content quality",
        icon="rule",
        description="Check enriched content against the minimum-confidence threshold.",
        fields=[
            FieldSpec("file", "File to validate", default="output/guide.enriched.json", required=True,
                       project_key="enriched"),
            FieldSpec("min_confidence", "Minimum confidence", kind="number",
                       placeholder="e.g. 0.7",
                       help="Optional — leave blank to use the value from Setup / config.yaml."),
        ],
        build_args=_validate_content_args,
    ),
    StepSpec(
        id="generate-manual-attention",
        title="Generate manual-attention report",
        icon="flag",
        description=(
            "Matches pipeline.py's Step 4b manual-review pause: list enriched steps "
            "that likely need a human look, then review output/guide.enriched.json "
            "(and this report) before moving on to rendering."
        ),
        fields=[
            FieldSpec("enriched", "Enriched guide JSON", default="output/guide.enriched.json", required=True,
                       project_key="enriched"),
            FieldSpec("images_dir", "Images directory", default="images", required=True,
                       project_key="images"),
            FieldSpec("output", "Output Markdown file", default="output/manual-attention-needed.md", required=True,
                       project_key="manual"),
            FieldSpec("warnings", "Schema warnings JSON", default="output/schema-warnings.json",
                       project_key="schema_warnings",
                       help="Optional — include schema warnings in the report."),
        ],
        build_args=_manual_attention_args,
        notes="This is your quality gate. Review the enriched JSON and this report now — it's much cheaper to fix here than after rendering and publishing.",
    ),
    StepSpec(
        id="render",
        title="Render Markdown",
        icon="description",
        description="Render the enriched guide to an accessible Markdown file for a specific target.",
        fields=[
            FieldSpec("guide", "Enriched guide JSON", default="output/guide.enriched.json", required=True,
                       project_key="enriched"),
            FieldSpec("target", "Target", kind="select", options=RENDER_TARGETS,
                       default="pdf", required=True),
            FieldSpec("output", "Output Markdown file", default="output/guide.md", required=True,
                       project_key="md"),
            FieldSpec("images_dir", "Images directory", default="images",
                       project_key="images",
                       help="Used to compute relative image paths in the rendered Markdown."),
        ],
        build_args=_render_args,
    ),
    StepSpec(
        id="publish",
        title="Publish to target formats",
        icon="publish",
        description=(
            "Run the batch-process, merge, validate, render, and format-conversion stages "
            "in one go and publish the selected output formats."
        ),
        fields=[
            FieldSpec("guide", "Guide JSON", default="guide.json", required=True,
                       project_key="guide"),
            FieldSpec("output", "Output directory", default="output", required=True,
                       project_key="output"),
            FieldSpec("targets", "Target formats", kind="multiselect", options=TARGET_FORMATS,
                       default=",".join(TARGET_FORMATS), required=True),
            FieldSpec("provider", "Provider", kind="select", options=PROVIDERS,
                       default="ollama", required=True),
            FieldSpec("orientation", "PDF orientation", kind="select", options=ORIENTATIONS,
                       default="portrait"),
        ],
        build_args=_publish_args,
        notes="Requires `uv` on PATH — this step shells out to `uv run` internally, same as folge-cli itself.",
    ),
    StepSpec(
        id="validate-pdf",
        title="Validate PDF/UA compliance",
        icon="picture_as_pdf",
        description=(
            "Check a generated PDF for tagging and PDF/UA accessibility compliance. "
            "Not part of pipeline.py's numbered steps — run this afterward, once Publish "
            "has produced a PDF."
        ),
        fields=[
            FieldSpec("pdf", "PDF file", default="output/guide.pdf", required=True,
                       project_key="pdf"),
        ],
        build_args=_validate_pdf_args,
    ),
]

STEPS_BY_ID: dict[str, StepSpec] = {s.id: s for s in STEPS}
