"""Read and write the shared ``.env`` and ``config.yaml`` files.

This module only calls *public* ``folge_cli.config`` functions
(``PROJECT_ROOT``, ``PROVIDERS``, ``resolve_provider``, ``load_yaml_config``,
``get_min_confidence``) so the GUI's view of configuration always matches
exactly what the CLI itself would resolve — no logic is duplicated or
reimplemented. Nothing in ``src/folge_cli`` is modified; this is read-only
use of an existing public API, plus writes to the *data* files
(``.env`` / ``config.yaml``) that both the CLI and GUI read at startup.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import yaml
from dotenv import load_dotenv

from folge_cli.config import PROJECT_ROOT, PROVIDERS, load_yaml_config, resolve_provider

ENV_PATH: Path = PROJECT_ROOT / ".env"
ENV_TEMPLATE_PATH: Path = PROJECT_ROOT / "envTemplate"
CONFIG_YAML_PATH: Path = PROJECT_ROOT / "config.yaml"


@dataclass
class FileState:
    """Snapshot of a config file's on-disk content."""

    path: Path
    text: str
    exists: bool


def read_env() -> FileState:
    """Return the current ``.env`` content, falling back to ``envTemplate``."""
    if ENV_PATH.exists():
        return FileState(ENV_PATH, ENV_PATH.read_text(encoding="utf-8"), True)
    if ENV_TEMPLATE_PATH.exists():
        return FileState(ENV_PATH, ENV_TEMPLATE_PATH.read_text(encoding="utf-8"), False)
    return FileState(ENV_PATH, "", False)


def write_env(text: str) -> None:
    """Write ``.env`` and immediately reload it into this process's environment.

    Subprocess-based CLI runs always re-read ``.env`` from disk on their own,
    so this reload only matters for the GUI's own live preview (the
    "Resolved settings" panel on the Setup page).
    """
    ENV_PATH.write_text(text, encoding="utf-8")
    load_dotenv(ENV_PATH, override=True)


def read_config_yaml() -> FileState:
    """Return the current ``config.yaml`` content, if any."""
    if CONFIG_YAML_PATH.exists():
        return FileState(
            CONFIG_YAML_PATH, CONFIG_YAML_PATH.read_text(encoding="utf-8"), True
        )
    return FileState(CONFIG_YAML_PATH, "", False)


class InvalidYamlError(ValueError):
    """Raised when a user attempts to save config.yaml that doesn't parse."""


def write_config_yaml(text: str) -> None:
    """Validate then write ``config.yaml``.

    Raises :class:`InvalidYamlError` (with the parser's message) instead of
    writing anything if the text isn't valid YAML, so a mistake in the
    editor can never leave the file corrupted.
    """
    try:
        yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise InvalidYamlError(str(exc)) from exc
    CONFIG_YAML_PATH.write_text(text, encoding="utf-8")


def mask_secret(value: str | None) -> str:
    """Mask an API key for display, matching folge_cli.pipeline's own convention."""
    if not value:
        return "(not set)"
    if len(value) > 12:
        return f"{value[:8]}...{value[-4:]}"
    return "***"


def all_provider_settings() -> dict[str, dict]:
    """Resolve settings for *every* supported provider, not just the active one.

    Uses ``resolve_provider`` (folge_cli's own public resolution function)
    once per provider by passing a minimal namespace, exactly the way
    ``cli.py`` passes its parsed ``argparse.Namespace``.
    """
    return {name: resolve_provider(SimpleNamespace(provider=name)) for name in PROVIDERS}


def active_provider_name() -> str:
    """The provider that a plain ``folge-cli`` invocation would currently use."""
    return resolve_provider()["name"]


def config_yaml_summary() -> dict:
    """A small read-only summary of config.yaml for display (not the raw text)."""
    cfg = load_yaml_config()
    return {
        "project_version": cfg.get("project", {}).get("version", "unknown"),
        "min_confidence": cfg.get("validation", {}).get("min_confidence", 0.7),
        "raw": cfg,
    }
