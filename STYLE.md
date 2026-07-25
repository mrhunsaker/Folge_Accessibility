<!--
 Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
 SPDX-License-Identifier: Apache-2.0
-->

# Style Guide

This document describes the coding style and patterns used in this project.
Follow these conventions when contributing so that the codebase stays
consistent and accessible.

Automated enforcement is provided by **Ruff** (linting). The guidance here
covers intent, patterns, and project-specific decisions that go beyond what a
linter can check.

---

## Python Version and Type Annotations

- Target **Python 3.10+** in all new code.
- Use the modern union syntax for optional and union types:

  ```python
  # Correct
  def foo(name: str | None = None) -> int | str: ...

  # Wrong
  from typing import Optional, Union
  def foo(name: Optional[str] = None) -> Union[int, str]: ...
  ```

- Use built-in generic types directly (`list[str]`, `dict[str, int]`,
  `tuple[int, ...]`) instead of `List`, `Dict`, `Tuple` from `typing`.

- Annotate all public function parameters and return types.

---

## Formatting

| Setting | Value |
|---------|-------|
| Line length | 100 |
| Linter | Ruff |

Run the linter:

```bash
uv run ruff check src/folge_cli/
uv run ruff check --fix src/folge_cli/   # auto-fix safe issues
```

### Strings

Use double quotes for strings. Ruff normalizes quote style.

### Trailing commas

Use trailing commas in multi-line collections and function signatures:

```python
result = some_function(
    first_argument,
    second_argument,
    third_argument,
)
```

---

## Linting (Ruff)

Active rule sets: `E`, `F`, `W`.

`E501` (line too long) is ignored because the project uses a 100-character
line length with Ruff.

### Common rules to be aware of

| Code | Rule | Notes |
|------|------|-------|
| `F841` | Unused variable | Remove or replace with `_` |
| `E731` | Lambda assignment | Use `def` instead |
| `B006` | Mutable default argument | Use `None` sentinel and assign inside the function |

---

## Naming Conventions

Follow [PEP 8](https://peps.python.org/pep-0008/):

| Construct | Convention | Example |
|-----------|------------|---------|
| Module | `snake_case` | `batch_process.py` |
| Class | `PascalCase` | `StepCounter` |
| Function / method | `snake_case` | `resolve_provider` |
| Variable | `snake_case` | `file_path` |
| Constant | `UPPER_SNAKE_CASE` | `PROVIDERS` |
| Private helper | leading underscore | `_build_auth_headers` |

---

## File and Module Structure

```
src/folge_cli/
├── __init__.py                 # Package metadata
├── __main__.py                 # python -m folge_cli entry point
├── _version.py                 # Dynamic version (CalVer)
├── cli.py                      # folge-cli CLI entry point
├── config.py                   # Centralized configuration loading
├── pipeline.py                 # Full pipeline orchestrator
├── batch_process.py            # Vision API image processing
├── merge.py                    # Deterministic merge
├── render.py                   # Markdown rendering
├── publish.py                  # PDF/UA publishing
├── validate_schema.py          # Schema validation
├── validate_content.py         # Content quality validation
├── validate_pdf.py             # PDF/UA compliance
├── generate_manual_attention.py # Manual attention markdown
└── progress.py                 # Step counters and progress display
```

Rules:

- `config.py` is the single source of truth for configuration — other modules
  import from it, never read `.env` or `config.yaml` directly.
- `cli.py` is the only user-facing entry point; it dispatches to other modules.
- Modules should be importable independently (no circular imports).
- Do not add new top-level modules without discussion.

---

## Configuration Pattern

All settings follow a strict resolution order:

```python
# CLI argument  >  environment variable  >  config.yaml  >  hardcoded default
```

When adding a new setting:

1. Add it to `_PROVIDER_DEFS` in `config.py` (for provider settings) or
   create a new `get_*()` function.
2. Add the env var to `.env` and `envTemplate`.
3. Add the YAML key to `config.yaml`.
4. Document the setting in `README.md`.

---

## Import Order

Ruff enforces this order automatically:

1. Standard library (`import os`, `from pathlib import Path`)
2. Third-party (`import yaml`, `from dotenv import load_dotenv`)
3. Local (`from folge_cli.config import get_env`)

Separate each group with a blank line. Do not mix groups.

---

## Comments and Docstrings

- Write **NumPy-style docstrings** for all public functions and classes.
- Inline comments should explain **why**, not **what**. Avoid restating the code.
- Keep TODO comments short and actionable; link to an issue when possible.

```python
# Good
# pdfinfo uses -v (not --version) on most systems; shutil.which handles
# PATH resolution so we don't hardcode /usr/bin/pdfinfo.

# Bad
# check if pdfinfo exists
```

---

## Docstring Format (NumPy Style)

```python
def function_name(param1, param2=None):
    """Short summary of what the function does.

    Longer description if needed. Can span multiple paragraphs.

    Parameters
    ----------
    param1 : str
        Description of param1.
    param2 : int, optional
        Description of param2. Default is ``None``.

    Returns
    -------
    bool
        Description of return value.

    Raises
    ------
    ValueError
        When something is wrong.
    """
```

---

## Testing

- Tests live in `tests/` and are run with **pytest**.
- Test function names describe the scenario: `test_resolve_provider_defaults_to_ollama`.
- Use `pytest.mark.parametrize` for multiple input cases instead of loops.
- Do not mock the file system unless absolutely necessary; use `tmp_path` fixtures.

Run: `uv run pytest -q`
