"""Compilation LaTeX (Tectonic) et garde-fous sur les modèles."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import paths


class LatexError(RuntimeError):
    def __init__(self, message: str, log: str = ""):
        super().__init__(message)
        self.log = log


def engine() -> str | None:
    return shutil.which("tectonic")


def preamble(tex: str) -> str:
    """Tout ce qui précède \\begin{document} : la mise en forme validée à l'onboarding."""
    head, sep, _ = tex.partition("\\begin{document}")
    return head.strip() if sep else ""


def same_preamble(generated: str, template: str) -> bool:
    norm = lambda s: "\n".join(line.rstrip() for line in preamble(s).splitlines() if line.strip())
    return norm(generated) == norm(template)


def compile(tex_path: Path) -> Path:
    """Compile `tex_path` dans son dossier ; renvoie le PDF."""
    exe = engine()
    if not exe:
        raise LatexError("Tectonic est introuvable. Installe-le : https://tectonic-typesetting.github.io")
    if paths.SIGNATURE.exists() and not (tex_path.parent / "signature.png").exists():
        shutil.copy(paths.SIGNATURE, tex_path.parent / "signature.png")
    proc = subprocess.run([exe, "--keep-logs", "--chatter", "minimal", tex_path.name],
                          cwd=tex_path.parent, capture_output=True, text=True, timeout=300)
    pdf = tex_path.with_suffix(".pdf")
    if proc.returncode != 0 or not pdf.exists():
        log = (proc.stderr or proc.stdout)[-3000:]
        raise LatexError(f"La compilation de {tex_path.name} a échoué", log)
    return pdf


def page_count(pdf: Path) -> int:
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf))
    try:
        return len(doc)
    finally:
        doc.close()


def install_default_templates(force: bool = False) -> None:
    paths.TEMPLATES.mkdir(parents=True, exist_ok=True)
    for name in ("cv.tex", "letter.tex"):
        dst = paths.TEMPLATES / name
        if force or not dst.exists():
            shutil.copy(paths.DEFAULT_TEMPLATES / name, dst)
