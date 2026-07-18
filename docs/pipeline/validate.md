# Step 4: Validate

**What it does:** Ensures `guide.enriched.json` conforms to the canonical schema and content quality standards.

**Why it matters:** Catches data errors before publishing and ensures accessibility metadata meets quality standards.

## Running

```bash
# Schema validation
uv run python scripts/validate_schema.py guide.enriched.json

# Content quality validation
uv run python scripts/validate_content.py guide.enriched.json 0.8
```

## Schema Validation

`validate_schema.py` checks structural compliance against the canonical JSON schema:

| Check | Description |
|-------|-------------|
| Required fields | `schema_version`, `guide_id`, `title`, `steps` must be present |
| Data types | Strings, integers, arrays, objects match expected types |
| Value constraints | String lengths, number ranges, enums are respected |
| Extra fields | No unexpected fields are allowed (strict schema) |

## Content Validation

`validate_content.py` checks accessibility metadata quality:

| Check | Threshold |
|-------|-----------|
| `alt_text` length | <= 150 characters |
| `long_description` sentences | 2-4 sentences |
| `confidence` | >= minimum threshold (default: 0.8) |
| Required vision fields | `alt_text`, `long_description`, `confidence` present |
| Unique `step_id` | No duplicate step IDs |

### Custom Threshold

You can specify a minimum confidence threshold:

```bash
# Require 0.9 confidence
uv run python scripts/validate_content.py guide.enriched.json 0.9

# Use default (0.8)
uv run python scripts/validate_content.py guide.enriched.json
```

## Expected Output

```
VALID: guide.enriched.json
All 12 steps passed content validation (min_confidence=0.8)!
```

## Troubleshooting

If validation fails, the scripts print specific issues:

```
INVALID: guide.enriched.json
  - step_id=3: alt_text exceeds 150 chars (187 chars)
  - step_id=7: confidence 0.65 below threshold 0.8
```

Fix the issues in your `vision-results.json` and re-run the merge step, or adjust the vision model's output.
