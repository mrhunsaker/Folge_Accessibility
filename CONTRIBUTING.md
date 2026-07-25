<!--
 Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
 SPDX-License-Identifier: Apache-2.0
-->

# Contributing to Folge Accessibility

Thank you for your interest in contributing. This document explains how to get
started, what is expected from contributors, and how the review process works.

## Code of Conduct

All participants are expected to follow the
[Code of Conduct](CODE_OF_CONDUCT.md). Respectful, professional communication
is required in all project spaces (issues, pull requests, discussions, and
commit messages).

## Security Issues

**Do not open public Issues for security vulnerabilities.** See
[SECURITY.md](SECURITY.md) for the private reporting process.

---

## Getting Started

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Runtime |
| [uv](https://github.com/astral-sh/uv) | 0.4+ | Dependency management |
| Pandoc | 3.0+ | Document conversion (for publishing) |
| Git | Any | Version control |

### Fork and Clone

```bash
# 1. Fork on GitHub, then:
git clone https://github.com/<your-username>/Folge_Accessibility.git
cd Folge_Accessibility

# 2. Add the upstream remote
git remote add upstream https://github.com/mrhunsaker/Folge_Accessibility.git
```

### Install Dependencies

```bash
uv sync
```

This creates `.venv/` with all dependencies.

---

## Workflow

### Branch Naming

Use short, descriptive kebab-case names:

```plaintext
feat/cloud-provider-support
fix/pdfinfo-detection
docs/update-readme
test/validate-schema
```

### Making Changes

1. Create a feature branch from `main`:

   ```bash
   git checkout -b feat/my-feature
   ```

2. Make focused, atomic commits. Each commit should compile and pass lint.

3. Before opening a pull request, run the full validation suite:

   ```bash
   # Lint
   uv run ruff check src/folge_cli/

   # Type check (if configured)
   uv run python -m py_compile src/folge_cli/*.py
   ```

4. If lint checks fail, fix them:

   ```bash
   uv run ruff check --fix src/folge_cli/
   ```

5. Update [README.md](README.md) and docstrings when you change observable
   behavior or add new features.

6. Open a pull request against `main` with a clear description of what changed
   and why.

### Pull Request Checklist

Before marking a PR ready for review:

- [ ] All lint checks pass locally
- [ ] New logic is covered by docstrings where practical
- [ ] Accessibility behavior is preserved (or explicitly improved)
- [ ] Documentation is updated if the change is user-visible
- [ ] Version is **not** bumped in the PR — maintainers handle releases

---

## Project Conventions

### Language and Runtime

- Python **3.10** or newer.
- Type annotations use the modern union syntax (`X | None`, not `Optional[X]`).
- Use built-in generic types (`list[str]`, `dict[str, int]`) instead of
  `typing.List`, `typing.Dict`.

### Linting

Handled by **Ruff**. Configuration in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W"]
ignore = ["E501"]
```

Run:

```bash
uv run ruff check src/folge_cli/
uv run ruff check --fix src/folge_cli/   # auto-fix safe issues
```

### Docstrings

All public functions and classes use **NumPy-style docstrings**:

```python
def resolve_provider(args=None):
    """Resolve the active provider configuration.

    Resolution: CLI ``--provider`` > ``PROVIDER`` env > config.yaml > ``"ollama"``.

    Parameters
    ----------
    args : argparse.Namespace, optional
        CLI argument namespace; ``args.provider`` is checked when present.
        Default is ``None``.

    Returns
    -------
    dict
        Provider configuration dict with keys ``name``, ``base_url``,
        ``model``, ``api_key``, etc.
    """
```

### Dependencies

- Runtime dependencies go in `[project].dependencies` in `pyproject.toml`.
- Pin minimum versions (`>=x.y`), not exact versions.
- Avoid adding dependencies without discussion; keep the runtime footprint small.

### Versioning

This project uses calendar versioning: `YYYY.M.D`.

Do **not** bump the version in contributor PRs. Maintainers handle releases.

### Configuration

Settings follow a strict resolution order:

```
CLI argument  >  environment variable  >  config.yaml  >  hardcoded default
```

When adding new settings, implement all four levels and document the
variable name in the `.env` template and `config.yaml`.

---

## Style Details

See [STYLE.md](STYLE.md) for detailed naming conventions, file structure, and
coding patterns used in this codebase.

---

## Commit Messages

Use the [Conventional Commits](https://www.conventionalcommits.org/) format:

```plaintext
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

Common types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.

Examples:

```plaintext
feat(providers): add anthropic provider support
fix(pdf): use shutil.which for pdfinfo detection
docs(readme): update provider configuration table
test(schema): add tests for enriched JSON validation
```

---

## Releasing (Maintainers Only)

1. Update `CHANGES.md` with the release notes.
2. Tag the commit: `git tag v2026.7.25 && git push origin v2026.7.25`
3. Create a GitHub release from the tag.
