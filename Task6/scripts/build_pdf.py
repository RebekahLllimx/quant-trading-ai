#!/usr/bin/env python3
"""Render the executed TASK6 notebook to the required Chinese A4 PDF."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from task6_common import PDF_OUTPUT_DIR, ROOT, TASK_DIR, TMP_PDF_DIR


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def main() -> None:
    TMP_PDF_DIR.mkdir(parents=True, exist_ok=True)
    notebook = TASK_DIR / "Rebecca+Task6.ipynb"
    run(["jupyter", "nbconvert", "--to", "latex", "--output-dir", str(TMP_PDF_DIR), str(notebook)], ROOT)
    tex_path = TMP_PDF_DIR / "Rebecca+Task6.tex"
    tex = tex_path.read_text(encoding="utf-8")
    tex = tex.replace("\\usepackage{parskip} % Stop auto-indenting (to mimic markdown behaviour)", "")
    tex = tex.replace("\\documentclass[11pt]{article}", "\\documentclass[UTF8,zihao=5]{ctexart}")
    tex = tex.replace("\\documentclass{article}", "\\documentclass[UTF8,zihao=5]{ctexart}")
    additions = r"""
    \geometry{a4paper,tmargin=2.2cm,bmargin=2.0cm,lmargin=2.4cm,rmargin=2.4cm}
    \usepackage{setspace}
    \usepackage{fvextra}
    \usepackage{ragged2e}
    \usepackage{indentfirst}
    \setmainfont{Times New Roman}
    \setCJKmainfont{Songti SC}
    \setCJKsansfont{Heiti SC}
    \setCJKmonofont{Songti SC}
    \onehalfspacing
    \setlength{\parindent}{2em}
    \setlength{\parskip}{0pt}
    \setcounter{secnumdepth}{0}
    \pagestyle{plain}
    \AtBeginDocument{\setlength{\parindent}{2em}\setlength{\parskip}{0pt}\justifying}
    \providecommand{\pandocbounded}[1]{#1}
    \AtBeginEnvironment{longtable}{\small}
    \RecustomVerbatimEnvironment{Verbatim}{Verbatim}{breaklines=true,breakanywhere=true,fontsize=\scriptsize}
    """
    tex = tex.replace("\\begin{document}", additions + "\n\\begin{document}", 1)
    tex = tex.replace("\\maketitle", "")
    tex = tex.replace("\\def\\LTcaptype{none}", "\\def\\LTcaptype{table}")
    tex_path.write_text(tex, encoding="utf-8")
    for pass_number in (1, 2):
        with (TMP_PDF_DIR / f"xelatex-pass{pass_number}.log").open("wb") as log:
            subprocess.run(
                ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", str(TMP_PDF_DIR), str(tex_path)],
                cwd=TASK_DIR, check=True, stdout=log, stderr=subprocess.STDOUT,
            )
    built = TMP_PDF_DIR / "Rebecca+Task6.pdf"
    for destination in (TASK_DIR / "Rebecca+Task6.pdf", PDF_OUTPUT_DIR / "Rebecca+Task6.pdf"):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(built, destination)
    print(f"built {built}")


if __name__ == "__main__":
    main()
