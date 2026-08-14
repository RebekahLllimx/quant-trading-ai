#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Word OMML 公式工具 — 在 python-docx 中插入专业数学公式

用法:
    from src.equation_utils import add_equation, rsi_formula, macd_formulas, ...

    for line in macd_formulas():
        add_equation(doc, line)
"""

from lxml import etree

OMML = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
NSMAP = {'m': OMML}


def _elem(tag, parent=None, text=None, **attrs):
    """创建一个 OMML 命名空间元素"""
    el = etree.SubElement(parent, f'{{{OMML}}}{tag}') if parent is not None \
        else etree.Element(f'{{{OMML}}}{tag}', nsmap=NSMAP)
    if text is not None:
        el.text = text
    for k, v in attrs.items():
        el.set(k, v)
    return el


def _r(text):
    """<m:r><m:t>text</m:t></m:r>"""
    r = etree.Element(f'{{{OMML}}}r')
    t = etree.SubElement(r, f'{{{OMML}}}t')
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = text
    return r


def _fraction(num_els, den_els):
    """<m:f><m:num>...</m:num><m:den>...</m:den></m:f>"""
    f = etree.Element(f'{{{OMML}}}f')
    num = etree.SubElement(f, f'{{{OMML}}}num')
    for el in num_els:
        num.append(el)
    den = etree.SubElement(f, f'{{{OMML}}}den')
    for el in den_els:
        den.append(el)
    return f


def add_equation(doc, parts):
    """
    在文档中插入一个居中的公式段落。

    parts: lxml 元素列表（_r() 和 _fraction() 的返回值）。

    示例:
        add_equation(doc, [
            _r("RSI = 100 − "),
            _fraction([_r("100")], [_r("1 + RS")]),
        ])
    """
    oMathPara = etree.Element(f'{{{OMML}}}oMathPara', nsmap=NSMAP)

    for item in parts:
        oMath = etree.SubElement(oMathPara, f'{{{OMML}}}oMath')
        if isinstance(item, list):
            for sub in item:
                oMath.append(sub)
        else:
            oMath.append(item)

    p = doc.add_paragraph()
    p.alignment = 1  # CENTER
    p._element.append(oMathPara)
    return p


# ═══════════════════════════════════════════════════════════════
# 预定义公式
# ═══════════════════════════════════════════════════════════════

def rsi_formula():
    return [
        [
            _r("RSI = 100 − "),
            _fraction([_r("100")], [_r("1 + RS")]),
        ],
        [_r("RS = AvgGain / AvgLoss")],
    ]


def macd_formulas():
    return [
        [_r("DIF = EMA(Close, 12) − EMA(Close, 26)")],
        [_r("DEA = EMA(DIF, 9)")],
        [_r("BAR = 2 × (DIF − DEA)")],
    ]


def bollinger_formulas():
    return [
        [_r("MID = SMA(Close, 20)")],
        [_r("UP = MID + k × σ    DN = MID − k × σ")],
        [_r("%b = (Close − DN) / (UP − DN)")],
        [_r("BandWidth = (UP − DN) / MID × 100%")],
    ]


def atr_formula():
    return [
        [_r("TR = max(High − Low, |High − C_{t−1}|, |Low − C_{t−1}|)")],
        [_r("ATR = WilderSmooth(TR, N),    α = 1/N")],
    ]


def kdj_formulas():
    return [
        [_r("RSV = (C − L₉) / (H₉ − L₉) × 100")],
        [_r("K = SMA(RSV, 3)    D = SMA(K, 3)    J = 3K − 2D")],
    ]


def ma_formulas():
    return [
        [_r("SMA(N) = (P₁ + P₂ + ... + P_N) / N")],
        [
            _r("EMA(N) = P_t × "),
            _fraction([_r("2")], [_r("N + 1")]),
            _r(" + EMA_{t−1} × "),
            _fraction([_r("N − 1")], [_r("N + 1")]),
        ],
    ]


def cci_formula():
    return [
        [_r("TP = (High + Low + Close) / 3")],
        [_r("CCI = (TP − SMA(TP, N)) / (0.015 × MD)")],
        [_r("MD = Mean(|TP − SMA(TP, N)|)  (平均绝对偏差)")],
    ]


def adx_formulas():
    return [
        [_r("+DM = max(High_t − High_{t−1}, 0)")],
        [_r("−DM = max(Low_{t−1} − Low_t, 0)")],
        [_r("+DI = WilderSmooth(+DM, N) / ATR × 100")],
        [_r("−DI = WilderSmooth(−DM, N) / ATR × 100")],
        [_r("DX = |+DI − −DI| / (+DI + −DI) × 100")],
        [_r("ADX = WilderSmooth(DX, N)")],
    ]
