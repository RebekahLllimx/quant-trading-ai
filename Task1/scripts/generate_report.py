#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 Word 文档：量化交易任务报告
格式要求：宋体、五号字(10.5pt)、1.5倍行距、0倍段间距、两端对齐
"""

import os
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

# ==================== 配置 ====================
OUTPUT_DIR = "/Users/rebecca/Desktop/量化交易"
DOC_FILE = os.path.join(OUTPUT_DIR, "Rebecca+Task1.docx")
CHART_FILE = os.path.join(OUTPUT_DIR, "000001_平安银行_close_price.png")
CSV_FILE = os.path.join(OUTPUT_DIR, "000001_平安银行_daily.csv")
STOCK_CODE = "000001"
STOCK_NAME = "平安银行"

# 常用字号
FONT_SIZE_WUHAO = Pt(10.5)  # 五号 = 10.5pt
FONT_SIZE_TITLE = Pt(16)    # 标题
FONT_SIZE_H1 = Pt(14)       # 一级标题
FONT_SIZE_H2 = Pt(12)       # 二级标题
FONT_SIZE_CAPTION = Pt(9)   # 图/表注

# ==================== 辅助函数 ====================

def set_cell_font(run, font_name='宋体', font_size=FONT_SIZE_WUHAO, bold=False):
    """设置 run 的字体属性"""
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
    run.font.size = font_size
    run.bold = bold


def set_paragraph_format(paragraph, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                          line_spacing=1.5, space_before=0, space_after=0):
    """设置段落格式"""
    paragraph.alignment = alignment
    pf = paragraph.paragraph_format
    pf.line_spacing = line_spacing
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)


def add_heading_custom(doc, text, level=1):
    """添加自定义格式的标题"""
    p = doc.add_paragraph()
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT,
                         line_spacing=1.5, space_before=6, space_after=3)
    run = p.add_run(text)
    if level == 0:
        set_cell_font(run, font_name='宋体', font_size=FONT_SIZE_TITLE, bold=True)
    elif level == 1:
        set_cell_font(run, font_name='宋体', font_size=FONT_SIZE_H1, bold=True)
    elif level == 2:
        set_cell_font(run, font_name='宋体', font_size=FONT_SIZE_H2, bold=True)
    return p


def add_body_paragraph(doc, text, indent_first_line=True, bold=False):
    """添加正文段落（宋体、五号、1.5倍行距、两端对齐）"""
    p = doc.add_paragraph()
    set_paragraph_format(p)
    run = p.add_run(text)
    set_cell_font(run, bold=bold)
    if indent_first_line:
        p.paragraph_format.first_line_indent = Pt(21)  # 两个字符缩进
    return p


def add_code_block(doc, code_text):
    """添加代码块（等宽字体）"""
    p = doc.add_paragraph()
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT)
    p.paragraph_format.first_line_indent = Pt(0)
    run = p.add_run(code_text)
    set_cell_font(run, font_name='Courier New', font_size=Pt(9))
    # 设置浅灰背景
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F5F5F5" w:val="clear"/>')
    p._element.pPr.append(shading)
    return p


def add_bullet_point(doc, text, level=0):
    """添加项目符号段落"""
    p = doc.add_paragraph()
    set_paragraph_format(p)
    p.paragraph_format.first_line_indent = Pt(21 + level * 21)
    p.paragraph_format.left_indent = Pt(21 + level * 21)
    markers = ['● ', '  ○ ', '    ▪ ']
    run = p.add_run(markers[min(level, 2)] + text)
    set_cell_font(run)
    return p


def add_image_with_caption(doc, image_path, caption, width_inches=5.5):
    """添加图表及标题"""
    if os.path.exists(image_path):
        # 图片
        p_img = doc.add_paragraph()
        set_paragraph_format(p_img, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                             line_spacing=1.0, space_after=3)
        run = p_img.add_run()
        run.add_picture(image_path, width=Inches(width_inches))

        # 图表标题
        p_cap = doc.add_paragraph()
        set_paragraph_format(p_cap, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                             line_spacing=1.5, space_before=3, space_after=6)
        run = p_cap.add_run(caption)
        set_cell_font(run, font_name='宋体', font_size=FONT_SIZE_CAPTION, bold=True)
    else:
        add_body_paragraph(doc, f"[图表缺失: {image_path}]")


# ==================== 构建文档 ====================

def build_document():
    doc = Document()

    # ---- 页面设置 ----
    section = doc.sections[0]
    section.page_width = Cm(21.0)   # A4
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(3.17)
    section.right_margin = Cm(3.17)

    # ---- 修改默认样式 ----
    style = doc.styles['Normal']
    style.font.name = '宋体'
    style.font.size = FONT_SIZE_WUHAO
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    pf = style.paragraph_format
    pf.line_spacing = 1.5
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # ==================== 封面/标题 ====================
    p = doc.add_paragraph()
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                         line_spacing=2.0, space_before=60, space_after=30)
    run = p.add_run("量化交易基础任务报告")
    set_cell_font(run, font_name='宋体', font_size=Pt(22), bold=True)

    p = doc.add_paragraph()
    set_paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                         line_spacing=2.0, space_after=6)
    run = p.add_run(f"日期：{datetime.now().strftime('%Y年%m月%d日')}")
    set_cell_font(run, font_name='宋体', font_size=Pt(12))

    # ==================== 任务一 ====================
    add_heading_custom(doc, "任务一：量化交易相较于传统手工操作交易的优势", level=1)

    add_body_paragraph(doc,
        "量化交易是指利用计算机程序、数学模型和统计分析工具，自动化地执行交易策略"
        "的一种交易方式。相较于传统手工操作交易，量化交易具有以下显著优势：")

    # 优势1
    add_heading_custom(doc, "1. 处理更多数据", level=2)
    add_body_paragraph(doc,
        "传统手工交易受限于人的精力和认知能力，交易员通常只能同时关注少数几个市场或品种。"
        "量化交易系统可以借助计算机的强大算力，在毫秒级别内处理海量市场数据——涵盖数百只股票、"
        "期货合约、外汇货币对等多市场、多品种的实时行情数据。此外，量化系统还可以融合宏观经济"
        "指标、财务报表、新闻舆情、社交媒体情绪等非结构化数据，从而构建更全面、多维度的投资决策依据。"
        "这种数据处理的广度和深度，是人工交易难以企及的。")

    # 优势2
    add_heading_custom(doc, "2. 执行更一致", level=2)
    add_body_paragraph(doc,
        "人类交易者在决策过程中不可避免地受到情绪因素（如恐惧、贪婪、过度自信、损失厌恶等）的影响，"
        "导致在实际操作中偏离既定策略。例如，在连续亏损后，交易者可能因恐惧而不敢按信号入场；"
        "在盈利丰厚时，又可能因贪婪而忽视止盈纪律。量化交易则将交易规则固化为程序代码，"
        "计算机严格执行每一条买卖指令，不受任何情绪干扰。无论在何种市场环境下，"
        "量化策略都能保持纪律性和一致性，确保交易行为与策略设计完全吻合。")

    # 优势3
    add_heading_custom(doc, "3. 能历史检验（回测）", level=2)
    add_body_paragraph(doc,
        "量化交易策略在投入实盘之前，可以利用历史数据进行回测（Backtesting），"
        "即在历史行情中模拟策略的运行效果。通过回测，交易者可以评估策略的收益率、"
        "最大回撤、夏普比率、胜率、盈亏比等关键绩效指标，验证策略在不同市场环境下的表现。"
        '这种“先验证、后执行”的模式，使得量化策略在进入实战前就经过了严格的统计检验，'
        "大大降低了策略失效的风险。相比之下，传统手工交易往往只能凭借经验进行主观判断，"
        "难以对交易系统的长期表现做出客观、量化的评估。")

    # 优势4
    add_heading_custom(doc, "4. 风险规则可写入系统", level=2)
    add_body_paragraph(doc,
        "风险管理是交易中至关重要的一环。量化交易可以将复杂的风险控制规则直接编码进交易系统："
        "例如单笔交易最大亏损限制、每日最大回撤熔断机制、投资组合层面的风险敞口控制、"
        "波动率自适应仓位管理等。一旦市场条件触发预设的风控阈值，系统将自动减仓或停止交易，"
        "无需人工干预。这种程序化风控机制反应速度极快，能在市场剧烈波动时第一时间保护资金安全，"
        "有效避免了人工风控中可能出现的犹豫、侥幸心理或操作延迟等问题。")

    # 综合小结
    add_body_paragraph(doc,
        "综上所述，量化交易通过数据驱动、纪律执行、历史验证和系统化风控四大核心优势，"
        "弥补了传统手工交易在信息处理能力、执行一致性和风险管理效率方面的不足。"
        "随着大数据和人工智能技术的发展，量化交易已成为现代金融市场中不可或缺的重要组成部分。")

    # ==================== 任务二 ====================
    add_heading_custom(doc, "任务二：基本概念解释", level=1)

    # K线
    add_heading_custom(doc, "1. K线（K-Line / Candlestick）", level=2)
    add_body_paragraph(doc,
        "K线，又称蜡烛图（Candlestick Chart）或日本线，起源于18世纪日本的大米期货市场，"
        "由日本商人本间宗久发明，是目前金融市场中最常用的价格图表形式之一。")

    add_body_paragraph(doc,
        "一根标准的K线由四个价格要素构成：开盘价（Open）、收盘价（Close）、"
        "最高价（High）和最低价（Low）。K线的实体部分表示开盘价与收盘价之间的价格区间："
        "当收盘价高于开盘价时，实体通常用红色或空心绘制，称为"阳线"，表示价格上涨；"
        "当收盘价低于开盘价时，实体通常用绿色或实心绘制，称为"阴线"，表示价格下跌。"
        "实体上方的细线称为"上影线"，其顶端代表当日最高价；实体下方的细线称为"下影线"，"
        "其底端代表当日最低价。")

    add_body_paragraph(doc,
        "K线图不仅可以展示单一周期的价格信息，更重要的价值在于通过多根K线的组合形态"
        "（如锤子线、吞没形态、十字星、启明星等）来研判市场多空力量对比和潜在的趋势转折。"
        "K线分析是技术分析中最基础、最直观的工具之一。常见的K线周期包括日K线、周K线、月K线，"
        "以及分钟级别的短期K线（如5分钟、15分钟、60分钟等），不同周期的K线适用于不同交易风格的投资者。")

    # 基本面
    add_heading_custom(doc, "2. 基本面（Fundamental Analysis）", level=2)
    add_body_paragraph(doc,
        "基本面分析是一种通过评估经济、行业和公司层面的内在价值来判断证券投资价值的方法论。"
        "其核心思想是：每一只证券都有一个"内在价值"，市场价格围绕内在价值波动；"
        "当市场价格低于内在价值时，是买入时机；当市场价格高于内在价值时，则是卖出时机。")

    add_body_paragraph(doc,
        "基本面分析通常涵盖三个层次：（1）宏观经济分析——考察GDP增长率、通货膨胀率、"
        "利率水平、货币政策、财政政策、就业数据等宏观经济指标，判断整体经济周期所处的阶段；"
        "（2）行业分析——研究行业生命周期、竞争格局、监管政策、技术变革趋势等，"
        "评估特定行业的发展前景和投资吸引力；"
        "（3）公司分析——深入考察企业的财务报表（资产负债表、利润表、现金流量表），"
        "计算市盈率（P/E）、市净率（P/B）、净资产收益率（ROE）、负债率、自由现金流等财务指标，"
        "评估公司的盈利能力、成长性、偿债能力和运营效率。")

    add_body_paragraph(doc,
        "基本面分析的代表人物包括价值投资之父本杰明·格雷厄姆（Benjamin Graham）"
        "和股神沃伦·巴菲特（Warren Buffett）。基本面分析更适合中长期投资者，"
        "其优势在于能够发现被市场低估的优质资产，但缺点是信息获取和分析过程耗时较长，"
        "且市场可能长期偏离基本面判断（即"市场保持非理性的时间可能长于你保持偿债能力的时间"）。")

    # 技术面
    add_heading_custom(doc, "3. 技术面（Technical Analysis）", level=2)
    add_body_paragraph(doc,
        "技术分析是一种通过研究市场交易数据（主要是价格和成交量）来预测未来价格走势的分析方法。"
        "技术分析建立在三个基本假设之上：（1）市场行为包容消化一切信息——所有影响价格的因素"
        "（基本面、政策、心理等）都已反映在价格中；（2）价格以趋势方式演变——价格运动具有惯性，"
        "一旦形成趋势，更可能继续而非反转；（3）历史会重演——人性不变，"
        "过去有效的价格形态和技术指标在未来仍将发挥作用。")

    add_body_paragraph(doc,
        "技术分析的工具和方法非常丰富，主要包括："
        "（1）图表形态分析——识别头肩顶/底、双重顶/底、三角形整理、旗形等经典价格形态；"
        "（2）技术指标——包括趋势跟踪指标（如移动平均线MA、MACD）、"
        "震荡指标（如RSI相对强弱指数、KDJ随机指标、威廉指标）、"
        "成交量指标（如成交量加权平均价VWAP、能量潮OBV）等；"
        "（3）道氏理论、波浪理论和江恩理论等经典技术分析理论框架。")

    add_body_paragraph(doc,
        "技术分析与基本面分析并非互斥，而是互补的。很多成功的投资者会将两者结合使用："
        "用基本面分析筛选投资标的（决定"买什么"），用技术分析选择入场和出场时机"
        "（决定"何时买卖"）。在量化交易领域，技术指标往往被量化为具体的数学模型，"
        "成为交易策略的核心信号来源。")

    # ==================== 任务三 ====================
    add_heading_custom(doc, "任务三：Tushare Pro 平台注册及 Python 数据获取实践", level=1)

    add_heading_custom(doc, "3.1 Tushare Pro 平台注册与 Token 获取", level=2)
    add_body_paragraph(doc,
        "Tushare（https://www.tushare.pro/）是国内知名的免费金融数据开放平台，"
        "提供股票、基金、期货、期权、指数、宏观经济等多类金融数据接口。以下是注册和获取Token的步骤：")

    add_body_paragraph(doc, "注册步骤：", indent_first_line=False, bold=True)

    steps = [
        "访问 Tushare Pro 官网：https://www.tushare.pro/；",
        "点击页面右上角"注册"按钮，填写手机号、邮箱、密码等基本信息完成注册；",
        "注册成功后登录账户，进入"个人主页"或"Token管理"页面；",
        "复制系统生成的 API Token（一串字符），该 Token 是调用 Tushare 接口的凭证；",
        "在 Python 代码中通过 ts.set_token('您的Token') 设置后即可使用。"
    ]
    for i, step in enumerate(steps, 1):
        add_bullet_point(doc, f"第{i}步：{step}")

    add_body_paragraph(doc,
        "注意事项：Tushare Pro 采用积分制度，不同积分等级对应不同的数据访问权限。"
        "新注册用户通常拥有基础积分（如120分），可免费访问大部分常用的行情数据接口。"
        "如需获取更高级的数据（如分钟级行情、龙虎榜数据等），可通过社区贡献、"
        "付费升级等方式获取更高积分。")

    add_heading_custom(doc, "3.2 Python 编程实现", level=2)
    add_body_paragraph(doc,
        "以下 Python 程序实现了三个核心功能："
        "（1）通过 Tushare/AKShare 接口获取沪深A股指定股票过去一年的每日交易数据；"
        "（2）绘制每日收盘价的曲线图（含移动平均线）；"
        "（3）将交易数据保存为 CSV 格式文件。")

    add_body_paragraph(doc,
        "本程序采用双数据源架构设计：优先使用 Tushare Pro API（需配置Token），"
        "当 Tushare 不可用时自动回退到 AKShare（免费、免注册的金融数据接口），"
        "确保程序在各种环境下都能正常运行。以下为示例股票"平安银行（000001）"的核心代码：",
        indent_first_line=True)

    # 插入精简后的代码
    code_snippet = '''import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt

# 1. 设置 Token 并获取数据
ts.set_token("YOUR_TOKEN")          # 替换为您的 Token
pro = ts.pro_api()
df = pro.daily(ts_code="000001.SZ",
               start_date="20250628",
               end_date="20260628")
df = df.sort_values("trade_date")

# 2. 绘制收盘价曲线图
plt.figure(figsize=(14, 7))
plt.plot(df["trade_date"], df["close"],
         color="#1f77b4", linewidth=1.5,
         label="每日收盘价")
plt.title("图1：平安银行（000001）每日收盘价走势图")
plt.xlabel("日期")
plt.ylabel("收盘价（元）")
plt.legend(); plt.grid(True, alpha=0.3)
plt.savefig("close_price.png", dpi=150)

# 3. 保存为 CSV 文件
df.to_csv("stock_daily.csv", index=False,
          encoding="utf-8-sig")
print("数据已保存，共", len(df), "条记录")'''

    add_code_block(doc, code_snippet)

    add_body_paragraph(doc,
        "完整代码文件（含详细注释、多数据源支持、移动平均线、统计标注等功能）"
        "见附带文件：task3_stock_data.py。用户只需修改代码中的 TUSHARE_TOKEN、"
        "STOCK_CODE 和 STOCK_NAME 三个变量，即可获取任意沪深A股的历史交易数据。")

    # ==================== 图表插入 ====================
    add_heading_custom(doc, "3.3 数据可视化结果", level=2)

    add_image_with_caption(doc, CHART_FILE,
        f"图1：{STOCK_NAME}（{STOCK_CODE}）过去一年每日收盘价走势图",
        width_inches=5.5)

    # 图表解读
    add_heading_custom(doc, "3.3.1 图表解读", level=2)

    # 读取数据以得出具体结论
    import pandas as pd
    chart_interpretation = ""
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df['日期'] = pd.to_datetime(df['日期'])
        close = df['收盘价']
        open_price = df['开盘价']
        high = df['最高价']
        low = df['最低价']
        vol = df['成交量(手)']
        amount = df['成交额']

        start_date = df['日期'].min().strftime('%Y年%m月%d日')
        end_date = df['日期'].max().strftime('%Y年%m月%d日')
        days = len(df)

        change_pct = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100
        trend = "上涨" if change_pct > 0 else "下跌"

        max_close = close.max()
        min_close = close.min()
        max_date = df.loc[close.idxmax(), '日期'].strftime('%Y年%m月%d日')
        min_date = df.loc[close.idxmin(), '日期'].strftime('%Y年%m月%d日')
        avg_close = close.mean()
        std_close = close.std()

        # 振幅最大的区间
        df['range'] = high - low
        max_range_idx = df['range'].idxmax()
        max_range_date = df.loc[max_range_idx, '日期'].strftime('%Y年%m月%d日')
        max_range_val = df.loc[max_range_idx, 'range']

        add_body_paragraph(doc,
            f"图1展示了{STOCK_NAME}（股票代码：{STOCK_CODE}）在{start_date}至{end_date}期间"
            f"（共{days}个交易日）的每日收盘价走势。结合图表和数据，可以得出以下关键结论：")

        add_body_paragraph(doc,
            f"第一，整体价格走势呈现{trend}趋势。"
            f"期初（{start_date}）收盘价为 {close.iloc[0]:.2f} 元，"
            f"期末（{end_date}）收盘价为 {close.iloc[-1]:.2f} 元，"
            f"区间累计涨跌幅为 {change_pct:+.2f}%。"
            f"这表明在过去一年中，{STOCK_NAME}的整体股价表现{'强于' if change_pct > 0 else '弱于'}年初水平。")

        add_body_paragraph(doc,
            f"第二，价格波动特征明显。"
            f"区间内最高收盘价出现在{max_date}，达到 {max_close:.2f} 元；"
            f"最低收盘价出现在{min_date}，为 {min_close:.2f} 元。"
            f"收盘价均值为 {avg_close:.2f} 元，标准差为 {std_close:.2f} 元。"
            f"标准差反映了价格的波动幅度——标准差越大，说明股价波动越剧烈，投资风险相对越高。")

        add_body_paragraph(doc,
            f"第三，20日均线（橙色虚线）和60日均线（绿色虚线）提供了趋势跟踪的参考。"
            f"当短期均线（20日）上穿长期均线（60日）形成"金叉"时，通常是看涨信号；"
            f"反之，当短期均线下穿长期均线形成"死叉"时，则是看跌信号。"
            f"此外，收盘价与均线的相对位置也是判断市场多空力量的重要依据——"
            f"价格持续高于均线表明多头占优，反之则空头占优。")

        add_body_paragraph(doc,
            f"第四，成交量分析是验证价格趋势的重要手段。"
            f"统计期间内，日均成交量为 {vol.mean():,.0f} 手，"
            f"日均成交额为 {amount.mean():,.0f} 元。"
            f"通常而言，价格上涨伴随成交量放大，表明上涨动能充足；"
            f"价格上涨但成交量萎缩，则可能是上涨乏力的信号。")

    # ==================== CSV 数据说明 ====================
    add_heading_custom(doc, "3.4 数据保存与后续使用", level=2)

    add_body_paragraph(doc,
        f"交易数据已保存为 CSV 格式文件：{os.path.basename(CSV_FILE)}。"
        f"CSV（Comma-Separated Values）是一种通用、轻量级的数据交换格式，"
        f"可被 Excel、Python（pandas）、R、MATLAB 等几乎所有数据分析工具直接读取。")

    add_body_paragraph(doc,
        f"该 CSV 文件共包含 {days if os.path.exists(CSV_FILE) else 'N'} 条交易记录，每条记录包含以下字段："
        f"日期、股票代码、开盘价、最高价、最低价、收盘价、成交量、成交额、涨跌幅、涨跌额、换手率。"
        f"这些数据为后续的任务（如计算技术指标、构建量化策略、进行回测分析等）提供了坚实的基础数据支撑。")

    add_body_paragraph(doc,
        "在后续任务中，可以基于该数据开展以下量化分析工作："
        "计算各类技术指标（如MACD、RSI、布林带等）；"
        "构建和回测交易策略（如均线交叉策略、动量策略、均值回归策略等）；"
        "进行风险管理分析（如计算VaR在险价值、最大回撤等）；"
        "开发机器学习预测模型（如使用LSTM预测股价走势等）。")

    # ==================== 总结 ====================
    add_heading_custom(doc, "任务总结", level=1)
    add_body_paragraph(doc,
        "本报告完成了量化交易基础阶段的三项核心任务：第一，从数据处理能力、执行纪律性、"
        "历史回测验证和系统化风控四个维度，系统阐述了量化交易相较于传统手工交易的核心优势；"
        "第二，对K线、基本面分析和技术分析这三个金融市场的基础概念进行了详细解释，"
        "包括其定义、构成要素、分析方法和实际应用场景；第三，介绍了Tushare Pro金融数据平台的注册与使用方法，"
        "并通过Python编程实践，成功获取了平安银行（000001）过去一年的真实交易数据，"
        "绘制了收盘价走势图并进行了数据解读，同时将数据保存为CSV文件以备后续使用。")

    add_body_paragraph(doc,
        f"（报告生成日期：{datetime.now().strftime('%Y年%m月%d日')}）")

    # ==================== 保存 ====================
    doc.save(DOC_FILE)
    print(f"文档已保存至: {DOC_FILE}")
    print("完成！")


if __name__ == "__main__":
    build_document()
