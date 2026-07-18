#!/usr/bin/env python3
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
    "required": ["schema_version", "guide_id", "title", "steps"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "string", "enum": ["1.0"]},
        "guide_id": {"type": "string"},
        "title": {"type": "string", "minLength": 1, "maxLength": 200},
        "description": {"type": "string", "maxLength": 500},
        "version": {"type": "string"},
        "language": {"type": "string", "default": "en"},
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": "string", "format": "date-time"},
        "steps": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["step_id", "title", "body"],
                "additionalProperties": False,
                "properties": {
                    "step_id": {"type": "integer", "minimum": 1},
                    "title": {"type": "string", "minLength": 1, "maxLength": 200},
                    "body": {"type": "string", "minLength": 1},
                    "image": {"type": "string"},
                    "order": {"type": "integer", "minimum": 0},
                    "vision": {
                        "type": "object",
                        "required": ["alt_text", "long_description", "confidence", "model", "generated_at"],
                        "additionalProperties": False,
                        "properties": {
                            "alt_text": {"type": "string", "maxLength": 150},
                            "long_description": {"type": "string", "maxLength": 1000},
                            "ocr_text": {"type": "array", "items": {"type": "string"}},
                            "ui_controls": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["type", "label"],
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
                    "metadata": {"type": "object", "additionalProperties": True}
                }
            }
        },
        "metadata": {"type": "object", "additionalProperties": True}
    }
}

def validate_json(filepath):
    """Validate a JSON file against the schema."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        jsonschema.validate(instance=data, schema=SCHEMA)
        print(f"VALID: {filepath}")
        return True
    except jsonschema.ValidationError as e:
        print(f"INVALID: {filepath}")
        print(f"  Path: {'.'.join(str(p) for p in e.absolute_path)}")
        print(f"  Message: {e.message}")
        return False
    except json.JSONDecodeError as e:
        print(f"JSON ERROR: {filepath} - {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_schema.py <json-file> [json-file2 ...]")
        sys.exit(1)
    all_valid = all(validate_json(Path(fp)) for fp in sys.argv[1:])
    sys.exit(0 if all_valid else 1)
