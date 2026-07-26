#!/usr/bin/env python3
"""Patch nbconvert LaTeX for Chinese TASK6 typography and safe wrapping."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_notebook_tex.py path/to/notebook.tex")
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    text = text.replace(r"\documentclass[11pt]{article}", r"\documentclass[UTF8,zihao=5]{ctexart}", 1)
    text = text.replace(
        r"\usepackage{fancyvrb} % verbatim replacement that allows latex",
        "\\usepackage{fancyvrb} % verbatim replacement that allows latex\n"
        "    \\usepackage{fvextra}\n"
        "    \\usepackage{etoolbox}\n"
        "    \\usepackage{ragged2e}",
        1,
    )
    text = text.replace(
        r"\DefineVerbatimEnvironment{Highlighting}{Verbatim}{commandchars=\\\{\}}",
        r"\DefineVerbatimEnvironment{Highlighting}{Verbatim}{commandchars=\\\{\},breaklines=true,breakanywhere=true,fontsize=\scriptsize}",
        1,
    )
    text = text.replace(
        r"\geometry{verbose,tmargin=1in,bmargin=1in,lmargin=1in,rmargin=1in}",
        "\\geometry{a4paper,tmargin=2.2cm,bmargin=2.2cm,lmargin=2.4cm,rmargin=2.4cm}\n"
        "    \\setmainfont{Times New Roman}\n"
        "    \\setCJKmainfont{Songti SC}\n"
        "    \\setCJKsansfont{Heiti SC}\n"
        "    \\setCJKmonofont{Songti SC}\n"
        "    \\linespread{1.35}\n"
        "    \\setlength{\\parindent}{2em}\n"
        "    \\setlength{\\parskip}{0pt}\n"
        "    \\setcounter{secnumdepth}{0}\n"
        "    \\pagestyle{plain}\n"
        "    \\AtBeginDocument{\\justifying}\n"
        "    \\providecommand{\\pandocbounded}[1]{#1}\n"
        "    \\AtBeginEnvironment{longtable}{\\small}\n"
        "    \\RecustomVerbatimEnvironment{Verbatim}{Verbatim}{breaklines=true,breakanywhere=true,fontsize=\\scriptsize}",
        1,
    )
    text = text.replace(r"\maketitle", "", 1)
    text = text.replace(r"{\def\LTcaptype{none} % do not increment counter", r"{\def\LTcaptype{table} % Pandoc compatibility")
    path.write_text(text, encoding="utf-8")
    print(f"[tex] patched {path}")


if __name__ == "__main__":
    main()
