"""Publish enriched JSON to PDF, DOCX, HTML, PPTX formats."""

import subprocess
from pathlib import Path
from typing import List

from folge.pipeline.progress import ProgressCallback, banner, ok, error, info

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _run_pandoc(cmd: str, cwd: str) -> tuple:
    """Run a pandoc command. Returns (success, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd,
    )
    return result.returncode == 0, result.stderr


def publish_pdf(output_dir: Path, on_progress: ProgressCallback = None) -> bool:
    """Publish PDF with fallback engines."""
    pdf_file = output_dir / "guide.pdf"

    engines = [
        ("weasyprint", f"pandoc guide.md --lua-filter=../templates/pagebreak.lua "
         f"--lua-filter=../pdf-accessibility.lua --css=../templates/landscape.css "
         f"--pdf-engine=weasyprint --pdf-engine-opt=--presentational-hints "
         f"--metadata=tagged-pdf:true -o guide.pdf"),
        ("wkhtmltopdf", f"pandoc guide.md --lua-filter=../templates/pagebreak.lua "
         f"--lua-filter=../pdf-accessibility.lua --pdf-engine=wkhtmltopdf "
         f"--pdf-engine-opt=--enable-local-file-access --pdf-engine-opt=--tagged-pdf "
         f"--metadata=tagged-pdf:true -o guide.pdf"),
        ("xelatex", f"pandoc guide.md --lua-filter=../templates/pagebreak.lua "
         f"--lua-filter=../pdf-accessibility.lua --pdf-engine=xelatex "
         f"--pdf-engine-opt=-x dvipdfmx -o guide.pdf"),
    ]

    for engine_name, cmd in engines:
        info(on_progress, f"  → PDF ({engine_name})...")
        success, stderr = _run_pandoc(cmd, str(output_dir))
        if success:
            size_kb = pdf_file.stat().st_size / 1024
            ok(on_progress, f"PDF done ({size_kb:.1f} KB) via {engine_name}")
            return True
        else:
            error(on_progress, f"{engine_name} failed: {stderr[:120]}")

    error(on_progress, "All PDF engines failed")
    return False


def publish_docx(output_dir: Path, on_progress: ProgressCallback = None) -> bool:
    """Publish DOCX."""
    info(on_progress, "  → DOCX...")
    cmd = (f"pandoc guide.md --lua-filter=../templates/pagebreak.lua "
           f"--lua-filter=../docx-accessibility.lua -o guide.docx")
    success, stderr = _run_pandoc(cmd, str(output_dir))
    if success:
        docx_file = output_dir / "guide.docx"
        ok(on_progress, f"DOCX done ({docx_file.stat().st_size / 1024:.1f} KB)")
        return True
    error(on_progress, f"DOCX failed: {stderr[:120]}")
    return False


def publish_html(output_dir: Path, on_progress: ProgressCallback = None) -> bool:
    """Publish HTML."""
    info(on_progress, "  → HTML...")
    cmd = f"pandoc guide.md --lua-filter=../accessibility.lua -o guide.html"
    success, stderr = _run_pandoc(cmd, str(output_dir))
    if success:
        html_file = output_dir / "guide.html"
        ok(on_progress, f"HTML done ({html_file.stat().st_size / 1024:.1f} KB)")
        return True
    error(on_progress, f"HTML failed: {stderr[:120]}")
    return False


def publish_pptx(output_dir: Path, on_progress: ProgressCallback = None) -> bool:
    """Publish PPTX."""
    info(on_progress, "  → PPTX...")
    cmd = (f"pandoc guide.md --lua-filter=../templates/pagebreak.lua "
           f"--lua-filter=../docx-accessibility.lua --to pptx -o guide.pptx")
    success, stderr = _run_pandoc(cmd, str(output_dir))
    if success:
        pptx_file = output_dir / "guide.pptx"
        ok(on_progress, f"PPTX done ({pptx_file.stat().st_size / 1024:.1f} KB)")
        return True
    error(on_progress, f"PPTX failed: {stderr[:120]}")
    return False


def run(enriched_path: Path, targets: List[str], output_dir: Path,
        on_progress: ProgressCallback = None) -> List[str]:
    """Run render + publish for all targets. Returns list of published formats."""
    banner(on_progress, "STEP: PUBLISHING TO TARGET FORMATS")

    published = []

    render_path = output_dir / "guide.md"
    from folge.pipeline.render import run as render_run
    render_run(enriched_path, "pdf", render_path, on_progress)

    for target in targets:
        if target == "github":
            github_path = output_dir / "guide.md"
            from folge.pipeline.render import run as render_github
            render_github(enriched_path, "github", github_path, on_progress)
            published.append("github")
            continue

        publishers = {
            "pdf": publish_pdf,
            "docx": publish_docx,
            "html": publish_html,
            "pptx": publish_pptx,
        }
        publisher = publishers.get(target)
        if publisher:
            if publisher(output_dir, on_progress):
                published.append(target)

    return published
