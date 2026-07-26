#!/usr/bin/env python3
"""Audit TASK6 markdown for the local Chinese de-AIGC writing requirements."""

from __future__ import annotations

import json
import re
from datetime import datetime

import nbformat

from task6_common import MAIN_METADATA_DIR, TASK_DIR, project_relative, write_json


HIGH_RISK_PHRASES = [
    "综上所述",
    "不言而喻",
    "毫无疑问",
    "显而易见",
    "值得一提的是",
    "总体而言",
    "本文将",
    "本报告首先回答",
    "下面将介绍",
    "而不是",
    "不只是",
    "应该关注",
    "需要关注",
    "值得注意的是",
    "可以看出",
    "我们",
    "recording",
]
FORBIDDEN_HEADINGS = ["tl;dr", "Context & Methods", "## Data", "## Results", "Takeaways", "Key Assumptions"]
CAUTIOUS_WORDS = ["可能", "未必", "不能", "不应", "仅", "受限", "无法", "较短", "不稳定", "不适合"]
RESEARCH_VOICE = ["本作业", "本任务", "本次", "本文", "这里"]


def main() -> None:
    notebook_path = TASK_DIR / "Rebecca+Task6.ipynb"
    notebook = nbformat.read(notebook_path, as_version=4)
    markdown = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "markdown")
    plain = re.sub(r"!\[[^]]*\]\([^)]*\)", "", markdown)
    plain = re.sub(r"[`$#|>*_\\]", "", plain)
    sentences = [item.strip() for item in re.split(r"[\u3002！？!?]", plain) if len(item.strip()) >= 5]
    lengths = [len(item) for item in sentences]
    mean_length = sum(lengths) / len(lengths) if lengths else 0.0
    variance = sum((value - mean_length) ** 2 for value in lengths) / len(lengths) if lengths else 0.0
    std_length = variance**0.5

    phrase_hits = {phrase: markdown.count(phrase) for phrase in HIGH_RISK_PHRASES if phrase in markdown}
    heading_hits = [heading for heading in FORBIDDEN_HEADINGS if heading in markdown]
    number_count = len(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?%?", markdown))
    cautious_count = sum(markdown.count(word) for word in CAUTIOUS_WORDS)
    voice_count = sum(markdown.count(word) for word in RESEARCH_VOICE)
    bold_count = markdown.count("**") // 2
    unicode_dash_count = markdown.count("—") + markdown.count("–")

    specificity = 10 if number_count >= 60 else 9 if number_count >= 35 else 7
    sentence_variation = 9 if std_length >= 18 else 8 if std_length >= 12 else 6
    transition_naturalness = 9 if not phrase_hits and not heading_hits else max(5, 9 - len(phrase_hits) - len(heading_hits))
    cautiousness = 9 if cautious_count >= 12 else 8 if cautious_count >= 8 else 6
    research_voice = 9 if voice_count >= 8 else 8 if voice_count >= 5 else 6
    total = specificity + sentence_variation + transition_naturalness + cautiousness + research_voice

    report = {
        "audited_at": datetime.now().astimezone().isoformat(),
        "source": project_relative(notebook_path),
        "five_step_audit": {
            "1_locate_patterns": {"high_risk_phrase_hits": phrase_hits, "forbidden_heading_hits": heading_hits},
            "2_diagnose_by_section": {
                "scope": "按题目三问和附加题分节检查",
                "bold_count": bold_count,
                "unicode_dash_count": unicode_dash_count,
            },
            "3_rewrite_status": "final_pass" if not phrase_hits and not heading_hits and unicode_dash_count == 0 else "needs_revision",
            "4_five_dimension_score": {
                "content_specificity": specificity,
                "sentence_variation": sentence_variation,
                "transition_naturalness": transition_naturalness,
                "cautious_claims": cautiousness,
                "research_voice": research_voice,
                "total": total,
                "target": 42,
            },
            "5_recheck": {
                "sentence_count": len(sentences),
                "mean_sentence_length": round(mean_length, 2),
                "sentence_length_std": round(std_length, 2),
                "concrete_number_count": number_count,
                "cautious_expression_count": cautious_count,
                "research_voice_count": voice_count,
                "passed": total >= 42 and not phrase_hits and not heading_hits and unicode_dash_count == 0,
            },
        },
    }
    write_json(MAIN_METADATA_DIR / "language_audit.json", report)
    print(json.dumps(report["five_step_audit"]["4_five_dimension_score"], ensure_ascii=False))
    if not report["five_step_audit"]["5_recheck"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
