#!/usr/bin/env python3
"""Apply Chinese typography and safer code wrapping to nbconvert LaTeX output."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_notebook_tex.py path/to/notebook.tex")
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        r"\documentclass[11pt]{article}",
        r"\documentclass[UTF8,zihao=5]{ctexart}",
        1,
    )
    text = text.replace(
        r"\usepackage{fancyvrb} % verbatim replacement that allows latex",
        "\\usepackage{fancyvrb} % verbatim replacement that allows latex\n"
        "    \\usepackage{fvextra} % wrap long code and output lines\n"
        "    \\usepackage{etoolbox}\n"
        "    \\usepackage{titlesec}\n"
        "    \\usepackage{indentfirst}",
        1,
    )
    text = text.replace(
        r"\DefineVerbatimEnvironment{Highlighting}{Verbatim}{commandchars=\\\{\}}",
        r"\DefineVerbatimEnvironment{Highlighting}{Verbatim}{commandchars=\\\{\},breaklines=true,breakanywhere=true,fontsize=\scriptsize}",
        1,
    )
    text = text.replace(
        r"\geometry{verbose,tmargin=1in,bmargin=1in,lmargin=1in,rmargin=1in}",
        "\\geometry{a4paper,tmargin=2.2cm,bmargin=2.2cm,lmargin=2.5cm,rmargin=2.5cm}\n"
        "    \\setmainfont{Times New Roman}\n"
        "    \\setCJKmainfont{Songti SC}\n"
        "    \\setCJKsansfont{Heiti SC}\n"
        "    \\setCJKmonofont{Songti SC}\n"
        "    \\linespread{1.35}\n"
        "    \\setlength{\\parindent}{2em}\n"
        "    \\setlength{\\parskip}{0pt}\n"
        "    \\setcounter{secnumdepth}{0}\n"
        "    \\pagestyle{plain}\n"
        "    \\titleformat{\\paragraph}[block]{\\normalfont\\normalsize\\bfseries}{}{0pt}{}\n"
        "    \\titlespacing{\\section}{0pt}{0pt}{1.2em}\n"
        "    \\titlespacing{\\subsection}{0pt}{1.4em}{0.9em}\n"
        "    \\titlespacing{\\subsubsection}{0pt}{1.2em}{0.95em}\n"
        "    \\titlespacing{\\paragraph}{0pt}{1.25em}{1.35em}\n"
        "    \\AtBeginEnvironment{longtable}{\\small}\n"
        "    \\RecustomVerbatimEnvironment{Verbatim}{Verbatim}{breaklines=true,breakanywhere=true,fontsize=\\scriptsize}",
        1,
    )
    text = text.replace(
        r"\begin{tcolorbox}[breakable, size=fbox, boxrule=1pt, pad at break*=1mm,colback=cellbackground, colframe=cellborder]",
        r"\begin{tcolorbox}[breakable, boxrule=0.6pt, left=2mm, right=2mm, top=2.8mm, bottom=2mm, before skip=0.9em, after skip=0.9em, pad at break*=2.8mm, colback=cellbackground, colframe=cellborder]",
    )
    text = text.replace(r"\maketitle", "", 1)
    text = text.replace(
        r"{\def\LTcaptype{none} % do not increment counter",
        r"{\def\LTcaptype{table} % Pandoc 3 compatibility",
    )
    # Keep the short closing paragraph with its heading instead of creating an
    # almost empty final page. This only extends the current page into the
    # existing bottom margin; it does not change the body line spacing.
    text = text.replace(
        r"\subsection{五、总结}",
        "\\enlargethispage{4\\baselineskip}\n\\subsection{五、总结}",
        1,
    )
    path.write_text(text, encoding="utf-8")
    print(f"[done] patched {path}")


if __name__ == "__main__":
    main()
