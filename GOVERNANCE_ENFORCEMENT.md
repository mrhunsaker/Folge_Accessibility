<!--
 Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
 SPDX-License-Identifier: Apache-2.0
-->

# Governance & Code Quality Enforcement

This document explains how the Folge Accessibility project enforces code
quality, accessibility standards, and governance through multiple layers.

## Enforcement Strategy

### Layer 1: Local Development (Pre-Commit Checks)

**When**: Run manually before committing
**Tools**: Ruff (linting)
**Enforcement Level**: Blocks commit if issues found

#### How it works:

1. Run the linter on your staged changes:

   ```bash
   uv run ruff check src/folge_cli/
   ```

2. Auto-fix safe issues:

   ```bash
   uv run ruff check --fix src/folge_cli/
   ```

3. Verify Python files compile:

   ```bash
   uv run python -m py_compile src/folge_cli/*.py
   ```

4. If all checks pass, commit your changes.

#### Expected workflow:

```bash
# Make changes
# ...

# Run lint checks
uv run ruff check src/folge_cli/

# If issues found, auto-fix
uv run ruff check --fix src/folge_cli/

# Stage and commit
git add .
git commit -m "feat(providers): add new provider"
# Checks passed → commit succeeds
```

---

### Layer 2: CI/CD on Every Push/PR (GitHub Actions)

**When**: Automatically when code is pushed or PR is created
**Enforcement Level**: Blocks merge if required checks fail

#### Required checks (block merge):

- Lint check (Ruff)
- Python compilation check

#### Non-blocking checks (warn but don't block):

- Security audit (dependency CVEs)

---

### Layer 3: Documentation & Standards

**When**: Developer reads before contributing
**Files**: Governance and style guides
**Enforcement Level**: Documented expectations

#### Key files:

| File | Purpose | Audience |
|------|---------|----------|
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Community standards | All contributors |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute | Developers |
| [STYLE.md](STYLE.md) | Code conventions | Developers |
| [SECURITY.md](SECURITY.md) | Security practices | Security-aware users |
| [CHANGES.md](CHANGES.md) | Changelog | All |

---

## Enforcement Summary

| Layer | Tool | Timing | Strictness | Bypass Possible? |
|-------|------|--------|------------|------------------|
| **Local** | Ruff lint | Before commit | Blocks | `git commit --no-verify` (not recommended) |
| **CI/CD** | GitHub Actions | On push/PR | Blocks merge | PR approval override (requires maintainer) |
| **Docs** | Style/contributing guides | Before contributing | Expected | N/A |

---

## Getting Started as a Contributor

### First Time Setup

```bash
# Clone the repo
git clone https://github.com/mrhunsaker/Folge_Accessibility.git
cd Folge_Accessibility

# Install dependencies
uv sync

# Verify setup
uv run ruff check src/folge_cli/    # Should pass with no output
```

### Normal Contribution Workflow

```bash
# Create feature branch
git checkout -b feat/my-feature

# Make changes
# ... edit files ...

# Run lint checks
uv run ruff check src/folge_cli/

# Stage and commit
git add .
git commit -m "feat(scope): description"
# → Commit succeeds if checks pass

# Push to GitHub
git push origin feat/my-feature

# Create Pull Request on GitHub
# CI/CD checks run automatically
# → If all pass, ready for review and merge
```

### If Lint Checks Fail

```bash
# Lint found issues. Fix them:
uv run ruff check --fix src/folge_cli/

# Or manually edit the files

# Try committing again
git add .
git commit -m "feat(scope): description"
# ✅ This time it should pass
```

---

## Verification

To verify enforcement is working:

### Test lint check (local)

```bash
# Introduce a lint error (e.g., unused import)
echo "import os" >> src/folge_cli/config.py
uv run ruff check src/folge_cli/
# → Should report F401 (unused import)

# Fix it
uv run ruff check --fix src/folge_cli/
# → Auto-removes the unused import
```

### Test CI checks (on GitHub)

```bash
# Make a PR with lint errors
# → CI workflow runs automatically
# → Check Actions tab to see results
```

---

## References

- [CONTRIBUTING.md](CONTRIBUTING.md) — How to contribute
- [STYLE.md](STYLE.md) — Code conventions
- [SECURITY.md](SECURITY.md) — Security practices
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — Community standards
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Keep a Changelog](https://keepachangelog.com/)
