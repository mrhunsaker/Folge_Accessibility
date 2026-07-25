#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""Validate enriched JSON against the canonical schema."""
import json
import sys
import jsonschema
from pathlib import Path

SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://github.com/mhunsaker/folge-vision-spec/schemas/v1.0/guide.enriched.json",
    "title": "Folge Enriched Guide",
    "description": "Canonical schema for Folge guides enriched with Ollama Vision",
    "type": "object",
    "required": ["schema_version", "title", "steps"],
    "properties": {
        "schema_version": {"type": "string", "enum": ["1.0"]},
        "guide_id": {"type": "string"},
        "title": {"type": "string", "minLength": 1, "maxLength": 200},
        "description": {"type": "string", "maxLength": 500},
        "version": {"type": "string"},
        "language": {"type": "string", "default": "en"},
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": "string", "format": "date-time"},
        "processed_at": {"type": "string"},
        "model": {"type": "string"},
        "steps": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "step_id": {"type": ["string", "integer"]},
                    "id": {"type": "string"},
                    "title": {"type": "string", "minLength": 1, "maxLength": 200},
                    "body": {"type": "string"},
                    "description": {"type": "string"},
                    "image": {"type": "string"},
                    "screenshotFilename": {"type": "string"},
                    "order": {"type": "integer", "minimum": 0},
                    "index": {"type": "integer"},
                    "vision": {
                        "type": "object",
                        "properties": {
                            "alt_text": {"type": "string", "maxLength": 150},
                            "long_description": {"type": "string", "maxLength": 1000},
                            "ocr_text": {"type": "array", "items": {"type": "string"}},
                            "ui_controls": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {"type": "string", "enum": ["button", "text_field", "dropdown", "checkbox", "radio", "slider", "navigation", "menu", "tab", "icon", "link", "other"]},
                                        "label": {"type": "string"},
                                        "bounding_box": {"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "width": {"type": "number"}, "height": {"type": "number"}}},
                                        "action": {"type": "string"}
                                    }
                                }
                            },
                            "important_element": {"type": "string", "maxLength": 200},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "model": {"type": "string"},
                            "generated_at": {"type": "string", "format": "date-time"},
                            "processing_time_ms": {"type": "integer"}
                        }
                    },
                    "metadata": {"type": "object"}
                }
            }
        },
        "metadata": {"type": "object"}
    },
    "additionalProperties": True
}


def _is_length_warning(exc):
    """Check if a ValidationError is a maxLength/minLength type (soft violation).

    Parameters
    ----------
    exc : jsonschema.ValidationError
        The validation error to check.

    Returns
    -------
    bool
        True if the error is a length-related soft violation.
    """
    return exc.message and ("is too long" in exc.message or "is too short" in exc.message)


def validate_json(filepath):
    """Validate a JSON file against the schema.

    Returns (is_valid: bool, warnings: list[dict]).

    Parameters
    ----------
    filepath : str or Path
        Path to the JSON file to validate.

    Returns
    -------
    tuple[bool, list[dict]]
        Tuple of (is_valid, warnings) where warnings contains
        length-related soft violations.
    """
    warnings = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        validator = jsonschema.Draft7Validator(SCHEMA)
        errors = sorted(validator.iter_errors(instance=data), key=lambda e: list(e.absolute_path))

        hard = []
        for e in errors:
            path = ".".join(str(p) for p in e.absolute_path)
            if _is_length_warning(e):
                warnings.append({"path": path, "message": e.message})
            else:
                hard.append(e)

        step_count = len(data.get("steps", []))
        if hard:
            print(f"  INVALID: {filepath}")
            for e in hard:
                path = ".".join(str(p) for p in e.absolute_path)
                print(f"    Path: {path}")
                print(f"    Message: {e.message}")
            return False, warnings

        print(f"  Schema valid: {filepath} ({step_count} steps)")
        return True, warnings
    except json.JSONDecodeError as e:
        print(f"  JSON ERROR: {filepath} - {e}")
        return False, warnings


def main():
    """Run CLI validation for enriched JSON schema."""
    if len(sys.argv) < 2:
        print("Usage: folge-cli validate-schema <json-file> [--warnings-out <file>]")
        sys.exit(1)

    files = []
    warnings_out = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--warnings-out":
            i += 1
            if i < len(sys.argv):
                warnings_out = sys.argv[i]
        else:
            files.append(sys.argv[i])
        i += 1

    if not files:
        print("Usage: folge-cli validate-schema <json-file> [--warnings-out <file>]")
        sys.exit(1)

    all_valid = True
    all_warnings = []
    for fp in files:
        ok, warns = validate_json(Path(fp))
        if not ok:
            all_valid = False
        all_warnings.extend(warns)

    if all_warnings:
        print(f"\n  {len(all_warnings)} length warning(s) (not blocking):")
        for w in all_warnings:
            print(f"    - {w['path']}: {w['message']}")

    if warnings_out and all_warnings:
        Path(warnings_out).write_text(
            json.dumps(all_warnings, indent=2), encoding="utf-8"
        )
        print(f"  Warnings written to {warnings_out}")

    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
