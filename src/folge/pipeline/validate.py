"""Schema and content validation for enriched JSON."""

import json
import re
from pathlib import Path
from typing import Tuple, List, Optional

from folge.pipeline.progress import ProgressCallback, banner, ok, warn, error, info

# Schema from original validate_schema.py
SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["title", "steps"],
    "properties": {
        "title": {"type": "string", "minLength": 1},
        "id": {"type": "string"},
        "steps": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["instruction"],
                "properties": {
                    "instruction": {"type": "string", "minLength": 1},
                    "id": {"type": "string"},
                    "step_id": {"type": "string"},
                    "index": {"type": "integer"},
                    "title": {"type": "string"},
                    "notes": {"type": "string"},
                    "vision": {
                        "type": "object",
                        "properties": {
                            "alt_text": {"type": "string"},
                            "long_description": {"type": "string"},
                            "ocr_text": {"type": ["string", "array"]},
                            "ui_controls": {"type": ["string", "array"]},
                            "important_element": {"type": "string"},
                            "confidence": {"type": ["number", "string"]},
                            "vision_error": {"type": "string"},
                        },
                    },
                },
            },
        },
        "metadata": {"type": "object"},
    },
}


def _is_length_warning(exc):
    return any(kw in exc.message for kw in ("minLength", "maxLength"))


def validate_schema(filepath: Path) -> Tuple[bool, List[str]]:
    """Validate JSON against schema. Returns (is_valid, warnings)."""
    try:
        import jsonschema
    except ImportError:
        return True, ["jsonschema not installed — skipping schema validation"]

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    errors = []
    warnings = []
    validator = jsonschema.Draft7Validator(SCHEMA)
    for exc in validator.iter_errors(data):
        if _is_length_warning(exc):
            warnings.append(f"Warning: {exc.message}")
        else:
            errors.append(f"Error: {exc.message}")

    return len(errors) == 0, warnings + errors


REQUIRED_VISION_FIELDS = ["alt_text", "long_description", "confidence"]


def count_sentences(text):
    if not text:
        return 0
    return len(re.findall(r'[.!?]+', str(text)))


def validate_step(step, min_confidence=0.8):
    errors = []
    warnings = []

    instruction = step.get("instruction", "")
    if not instruction or not instruction.strip():
        errors.append(f"Step {step.get('id', '?')}: empty instruction")

    vision = step.get("vision", {})
    if not vision:
        warnings.append(f"Step {step.get('id', '?')}: no vision data")
        return errors, warnings

    if vision.get("vision_error"):
        warnings.append(f"Step {step.get('id', '?')}: vision_error — {vision['vision_error']}")
        return errors, warnings

    for field in REQUIRED_VISION_FIELDS:
        val = vision.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            warnings.append(f"Step {step.get('id', '?')}: missing {field}")

    alt_text = vision.get("alt_text", "")
    if alt_text and count_sentences(alt_text) > 3:
        warnings.append(f"Step {step.get('id', '?')}: alt_text is long ({count_sentences(alt_text)} sentences)")

    long_desc = vision.get("long_description", "")
    if long_desc and count_sentences(long_desc) < 1:
        warnings.append(f"Step {step.get('id', '?')}: long_description has no sentences")

    try:
        conf = float(vision.get("confidence", 0))
        if conf < min_confidence:
            warnings.append(f"Step {step.get('id', '?')}: confidence {conf:.2f} < {min_confidence}")
    except (ValueError, TypeError):
        warnings.append(f"Step {step.get('id', '?')}: non-numeric confidence")

    return errors, warnings


def validate_content(filepath: Path, min_confidence: float = 0.8) -> Tuple[bool, List[str]]:
    """Validate content quality. Returns (is_valid, issues)."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_errors = []
    all_warnings = []
    steps = data.get("steps", [])

    for step in steps:
        errors, warnings = validate_step(step, min_confidence)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    issues = all_warnings + all_errors
    return len(all_errors) == 0, issues


def run(enriched_path: Path, min_confidence: float = 0.8, output_dir: Path = None,
        on_progress: ProgressCallback = None) -> Tuple[bool, List[str]]:
    """Run validation (schema + content). Returns (ok, all_issues)."""
    banner(on_progress, "STEP: VALIDATING ENRICHED JSON")

    schema_ok, schema_issues = validate_schema(enriched_path)
    if schema_ok:
        ok(on_progress, "Schema validation passed")
    else:
        for issue in schema_issues:
            warn(on_progress, issue)

    content_ok, content_issues = validate_content(enriched_path, min_confidence)
    if content_ok:
        ok(on_progress, "Content validation passed")
    else:
        for issue in content_issues:
            warn(on_progress, issue)

    all_ok = schema_ok and content_ok
    all_issues = schema_issues + content_issues

    if output_dir and all_issues:
        warnings_path = output_dir / "schema-warnings.json"
        with open(warnings_path, "w", encoding="utf-8") as f:
            json.dump(all_issues, f, indent=2)
        info(on_progress, f"Wrote {len(all_issues)} warnings to {warnings_path.name}")

    return all_ok, all_issues
