# Contributing

Contributions to the Folge Vision Publishing Pipeline are welcome.

## Getting Started

1. Fork the repository
2. Clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/Folge_Accessibility.git
cd Folge_Accessibility
```

3. Install dependencies:

```bash
uv sync
```

4. Create a feature branch:

```bash
git checkout -b feature/your-feature-name
```

## Development

### Running Tests

```bash
# Validate schema against a test file
uv run python scripts/validate_schema.py test-data/guide.enriched.json

# Run the pipeline with test data
uv run run_pipeline.py test-data/guide.json test-output/
```

### Building Documentation

```bash
# Serve docs locally with hot reload
uv run mkdocs serve

# Build static site
uv run mkdocs build --strict
```

### Code Style

- Python 3.10+ syntax
- Follow existing patterns in the codebase
- Keep scripts focused on single responsibilities
- Use `subprocess.run` with `capture_output=True` for external commands

## Making Changes

### Pipeline Scripts

Each script in `scripts/` should:

- Accept command-line arguments via `sys.argv`
- Print progress to stdout
- Return exit code 0 on success, non-zero on failure
- Handle errors gracefully with informative messages

### Lua Filters

Each filter should:

- Define Pandoc filter functions for the relevant elements
- Be self-contained (no external dependencies)
- Document the attributes it sets

### Documentation

- Keep pages in `docs/` synchronized with script behavior
- Use admonitions for warnings and tips
- Include command examples with expected output

## Submitting

1. Commit your changes with descriptive messages
2. Push to your fork
3. Open a Pull Request against `main`
4. Describe what changed and why

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
