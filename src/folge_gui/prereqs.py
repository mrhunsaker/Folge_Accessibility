"""Structured prerequisite and provider-reachability checks for the Setup page.

Mirrors the checks ``folge_cli.pipeline.check_prerequisites()`` and
``check_provider()`` perform, but returns structured results instead of only
printing to stdout, so the GUI can render each result as an accessible
icon+text status row rather than scraping terminal text. This intentionally
duplicates a small amount of *logic* (which external tools matter) rather
than *code* — it does not import or alter anything in ``folge_cli``.
"""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass

from folge_cli.config import LOCAL_PROVIDERS, PROJECT_ROOT, get_env


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    severity: str = "error"  # "error" | "warning" (only meaningful when ok is False)


async def _run(cmd: list[str], timeout: float = 10.0) -> tuple[int, str, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return -1, "", "timed out"
        return proc.returncode or 0, out.decode(errors="replace"), err.decode(errors="replace")
    except FileNotFoundError:
        return 127, "", "not found"
    except Exception as exc:  # pragma: no cover - defensive
        return -1, "", str(exc)


async def check_prerequisites() -> list[CheckResult]:
    """Check for uv, Python (via uv), Pandoc, pdfinfo, and pymupdf.

    Same tool set folge_cli.pipeline checks before running the pipeline or
    publish commands (both shell out to ``uv run ...`` internally).
    """
    results: list[CheckResult] = []

    code, out, _ = await _run(["uv", "--version"])
    results.append(
        CheckResult("uv", code == 0, out.strip().splitlines()[0] if out.strip() else "not found")
    )

    code, out, _ = await _run(["uv", "run", "python", "--version"])
    results.append(
        CheckResult(
            "Python (via uv)", code == 0, out.strip().splitlines()[0] if out.strip() else "not found"
        )
    )

    code, out, _ = await _run(["pandoc", "--version"])
    results.append(
        CheckResult("Pandoc", code == 0, out.strip().splitlines()[0] if out.strip() else "not found")
    )

    pdfinfo_path = shutil.which("pdfinfo")
    if pdfinfo_path:
        code, out, _ = await _run([pdfinfo_path, "-v"])
        detail = out.strip().splitlines()[0] if out.strip() else "found"
        results.append(CheckResult("pdfinfo (poppler-utils)", code == 0, detail, severity="warning"))
    else:
        results.append(
            CheckResult(
                "pdfinfo (poppler-utils)",
                False,
                "not on PATH — PDF validation will use pymupdf only",
                severity="warning",
            )
        )

    venv_python = str(PROJECT_ROOT / ".venv" / "bin" / "python")
    code, out, _ = await _run([venv_python, "-c", "import fitz; print('OK')"])
    results.append(
        CheckResult(
            "pymupdf",
            code == 0 and "OK" in out,
            "importable" if code == 0 and "OK" in out else "not importable",
            severity="warning",
        )
    )

    return results


async def check_provider_reachable(provider_name: str, api_key: str | None = None) -> CheckResult:
    """Check whether the selected vision provider is reachable right now."""
    if provider_name in LOCAL_PROVIDERS:
        prefix = provider_name.upper()
        base_url = get_env(f"{prefix}_BASE_URL", default="http://localhost:11434/v1")
        tags_url = base_url.rstrip("/v1") + "/api/tags"
        code, out, _ = await _run(["curl", "-s", tags_url], timeout=5)
        if code == 0 and out.strip():
            return CheckResult(provider_name, True, f"reachable at {base_url}")
        return CheckResult(
            provider_name, False, f"not responding at {base_url}", severity="warning"
        )

    prefix = provider_name.upper()
    key = api_key or get_env(f"{prefix}_API_KEY")
    if not key:
        return CheckResult(
            provider_name, False, f"{prefix}_API_KEY not set", severity="warning"
        )
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
    return CheckResult(provider_name, True, f"API key present ({masked})")
