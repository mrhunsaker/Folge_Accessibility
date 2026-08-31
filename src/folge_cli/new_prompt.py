#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""Scaffold a new custom vision prompt module.

Creates a correctly-formed ``generate_prompt`` module in
``src/folge_cli/prompts/`` so a new prompt can be added without typing the
boilerplate by hand.  The generated module is auto-registered as a
``--prompt`` choice by :func:`folge_cli.batch_process.get_available_prompts`.
"""
import re
from pathlib import Path

DEFAULT_PROMPT_TEMPLATE = '''"""Custom vision prompt for {title}."""


def generate_prompt(step, guide_title, previous_step=None, next_step=None):
    """Generate vision prompt for {title} screenshots.

    Parameters
    ----------
    step : dict
        Step dict with 'title', 'body', and 'step_id' keys.
    guide_title : str
        Title of the parent guide.
    previous_step : dict, optional
        Preceding step for context, or None.
    next_step : dict, optional
        Following step for context, or None.

    Returns
    -------
    str
        Formatted prompt string for the vision API.
    """
    prev_title = previous_step["title"] if previous_step else ""
    next_title = next_step["title"] if next_step else ""
    prompt = f"""You are documenting software screenshots for accessibility.

Return ONLY a single JSON object (NOT an array). Use this exact structure:

{{
  "step_id": "{step['step_id']}",
  "vision": {{
    "alt_text": "string (max 150 chars)",
    "long_description": "string (1-2 sentences)",
    "ocr_text": ["array of visible text strings"],
    "ui_controls": [{{"type": "button|text_field|dropdown|...", "label": "string"}}],
    "important_element": "plain text, NOT an object (max 200 chars)",
    "confidence": 0.95
  }}
}}

Guide: {{guide_title}}
Previous: {{prev_title}}
Current: {{step['title']}}
Instruction: {{step['body']}}
Next: {{next_title}}

RULES:
- alt_text: Describe ONLY visible on-screen content, max 150 chars
- long_description: 1-2 sentences, mention important interactive controls
- ocr_text: Only visible text as an array of strings
- ui_controls: Array of {{type, label}} objects for interactive controls
- important_element: Plain text string (NOT an object), max 200 chars
- confidence: 0.0-1.0 reflecting certainty

CRITICAL: Return a single JSON object. NOT an array. Do NOT include any text before or after the JSON. Do NOT wrap in markdown code fences."""
    return prompt
'''


def prompts_dir():
    """Return the absolute path to the prompts package directory.

    Returns
    -------
    Path
        Directory containing prompt modules.
    """
    return Path(__file__).parent / "prompts"


def normalize_prompt_name(name):
    """Normalize a prompt name to a valid, safe Python identifier.

    Converts to lowercase, replaces whitespace and dashes with
    underscores, and strips invalid characters.  Raises ``ValueError``
    if the result is empty or starts with a digit (not importable as a
    module name in this package).

    Parameters
    ----------
    name : str
        Raw prompt name supplied on the command line.

    Returns
    -------
    str
        Cleaned, importable module name.

    Raises
    ------
    ValueError
        If the cleansed name is empty, starts with a digit, or contains
        characters that cannot be cleaned to a valid identifier.
    """
    if not name:
        raise ValueError("Prompt name cannot be empty.")
    cleaned = re.sub(r"[\s\-]+", "_", name).lower()
    cleaned = re.sub(r"[^a-z0-9_]", "", cleaned)
    if not cleaned:
        raise ValueError(
            f"Prompt name {name!r} contains no valid identifier characters."
        )
    if cleaned[0].isdigit():
        raise ValueError(
            f"Prompt name {cleaned!r} starts with a digit; module names cannot."
        )
    return cleaned


def create_prompt_module(name, force=False):
    """Create a new prompt module file.

    Parameters
    ----------
    name : str
        Desired prompt name.  It is normalized to a safe identifier.
    force : bool, optional
        Overwrite an existing module if True.  Default is False.

    Returns
    -------
    Path
        Path to the created module file.

    Raises
    ------
    ValueError
        If the module already exists and ``force`` is False, or the name
        is not a valid identifier.
    """
    module_name = normalize_prompt_name(name)
    title = module_name.replace("_", " ").title()
    target = prompts_dir() / f"{module_name}.py"

    if target.exists() and not force:
        raise ValueError(
            f"Prompt module '{module_name}' already exists at {target}. "
            "Use --force to overwrite."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    content = DEFAULT_PROMPT_TEMPLATE.replace("{title}", title)
    target.write_text(content, encoding="utf-8")
    return target


def main():
    """CLI entry point for the new-prompt command."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="folge-cli new-prompt",
        description="Scaffold a new custom vision prompt module.",
    )
    parser.add_argument("name", help="Name of the new prompt (e.g. brailleblaster)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite an existing prompt module with the same name")
    args = parser.parse_args()

    try:
        target = create_prompt_module(args.name, force=args.force)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Created prompt module: {target}")
    print(f"Customize the generate_prompt() function, then run:")
    print(f"  folge-cli batch-process <guide> <images> <output> --prompt {target.stem}")


if __name__ == "__main__":
    main()
