from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output" / "pdf"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENT_TITLE = "OPC创客申请"
PDF_PATH = OUT_DIR / "OPC_Maker_Application_CN.pdf"

ASSET = ROOT / "website" / "assets" / "project-flow-canvas.png"

FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
]


def register_fonts() -> tuple[str, str]:
    base = "Helvetica"
    bold = "Helvetica-Bold"
    for font_path in FONT_CANDIDATES:
        if font_path.exists():
            pdfmetrics.registerFont(TTFont("CN", str(font_path)))
            base = "CN"
            break
    bold_path = Path(r"C:\Windows\Fonts\msyhbd.ttc")
    if bold_path.exists():
        pdfmetrics.registerFont(TTFont("CN-Bold", str(bold_path)))
        bold = "CN-Bold"
    else:
        bold = base
    return base, bold


FONT, FONT_BOLD = register_fonts()

INK = colors.HexColor("#102033")
MUTED = colors.HexColor("#5A6678")
BLUE = colors.HexColor("#2563EB")
GREEN = colors.HexColor("#16A34A")
PALE_BLUE = colors.HexColor("#EFF6FF")
PALE_GREEN = colors.HexColor("#ECFDF5")
LINE = colors.HexColor("#D8E0EA")
LIGHT = colors.HexColor("#F7F9FC")
WHITE = colors.white


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="CoverTitle",
        fontName=FONT_BOLD,
        fontSize=30,
        leading=38,
        textColor=INK,
        alignment=TA_LEFT,
        spaceAfter=14,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverSub",
        fontName=FONT,
        fontSize=12.5,
        leading=21,
        textColor=MUTED,
        alignment=TA_LEFT,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="H1CN",
        fontName=FONT_BOLD,
        fontSize=18,
        leading=24,
        textColor=INK,
        spaceBefore=12,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="H2CN",
        fontName=FONT_BOLD,
        fontSize=12.5,
        leading=18,
        textColor=INK,
        spaceBefore=8,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="BodyCN",
        fontName=FONT,
        fontSize=9.8,
        leading=16,
        textColor=INK,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="SmallCN",
        fontName=FONT,
        fontSize=8.4,
        leading=13,
        textColor=MUTED,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="CellCN",
        fontName=FONT,
        fontSize=8,
        leading=12,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        name="CellBoldCN",
        fontName=FONT_BOLD,
        fontSize=8.2,
        leading=12.5,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        name="Metric",
        fontName=FONT_BOLD,
        fontSize=17,
        leading=21,
        textColor=BLUE,
        alignment=TA_CENTER,
    )
)
styles.add(
    ParagraphStyle(
        name="MetricLabel",
        fontName=FONT,
        fontSize=7.8,
        leading=11,
        textColor=MUTED,
        alignment=TA_CENTER,
    )
)


def p(text: str, style: str = "BodyCN") -> Paragraph:
    return Paragraph(text, styles[style])


def bullet(text: str) -> Paragraph:
    return Paragraph("• " + text, styles["BodyCN"])


def cell(text: str, bold: bool = False) -> Paragraph:
    return Paragraph(text, styles["CellBoldCN" if bold else "CellCN"])


class Rule(Flowable):
    def __init__(self, color=LINE, width=1):
        super().__init__()
        self.color = color
        self.width = width
        self.height = 1

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.width)
        self.canv.line(0, 0, self.width_available, 0)

    def wrap(self, availWidth, availHeight):
        self.width_available = availWidth
        return availWidth, self.height


class BarChart(Flowable):
    def __init__(self, rows: list[tuple[str, int, str]], width=150 * mm, height=44 * mm):
        super().__init__()
        self.rows = rows
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return min(self.width, availWidth), self.height

    def draw(self):
        c = self.canv
        w = min(self.width, getattr(self, "_availWidth", self.width))
        max_value = max(v for _, v, _ in self.rows)
        row_h = self.height / len(self.rows)
        for i, (label, value, color) in enumerate(self.rows):
            y = self.height - (i + 1) * row_h + 6
            c.setFont(FONT, 7.5)
            c.setFillColor(MUTED)
            c.drawString(0, y + 7, label)
            x = 45 * mm
            bar_w = (w - x - 28 * mm) * value / max_value
            c.setFillColor(colors.HexColor(color))
            c.roundRect(x, y + 5, bar_w, 7, 3, fill=1, stroke=0)
            c.setFillColor(INK)
            c.setFont(FONT_BOLD, 7.5)
            c.drawRightString(w, y + 6, f"{value}%")


class Timeline(Flowable):
    def __init__(self, items: list[tuple[str, str]], width=160 * mm, height=35 * mm):
        super().__init__()
        self.items = items
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return min(self.width, availWidth), self.height

    def draw(self):
        c = self.canv
        w = self.width
        y = self.height - 15
        c.setStrokeColor(LINE)
        c.setLineWidth(1.2)
        c.line(10, y, w - 10, y)
        gap = (w - 20) / (len(self.items) - 1)
        for i, (label, desc) in enumerate(self.items):
            x = 10 + i * gap
            c.setFillColor(BLUE if i < 2 else GREEN)
            c.circle(x, y, 4.2, fill=1, stroke=0)
            c.setFillColor(INK)
            c.setFont(FONT_BOLD, 7.3)
            c.drawCentredString(x, y - 13, label)
            c.setFillColor(MUTED)
            c.setFont(FONT, 6.5)
            c.drawCentredString(x, y - 23, desc)


def make_table(data, widths, header=True, pale=False):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        style.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ]
        )
    if pale:
        for row in range(1 if header else 0, len(data)):
            if row % 2 == 1:
                style.append(("BACKGROUND", (0, row), (-1, row), LIGHT))
    t.setStyle(TableStyle(style))
    return t


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT, 7.5)
    canvas.drawString(doc.leftMargin, 12 * mm, DOCUMENT_TITLE)
    canvas.drawRightString(A4[0] - doc.rightMargin, 12 * mm, f"{doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(doc.leftMargin, 17 * mm, A4[0] - doc.rightMargin, 17 * mm)
    canvas.restoreState()


def cover_metrics():
    rows = [
        [
            p("5", "Metric"),
            p("30 天", "Metric"),
            p("US$1.99", "Metric"),
            p("2 条", "Metric"),
        ],
        [
            p("产品/项目管线", "MetricLabel"),
            p("Project Flow 免费试用", "MetricLabel"),
            p("当前永久访问定价", "MetricLabel"),
            p("网页端 + 桌面端路径", "MetricLabel"),
        ],
    ]
    table = Table(rows, colWidths=[38 * mm] * 4, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def build_story():
    story = []

    story += [
        Spacer(1, 20 * mm),
        p(DOCUMENT_TITLE, "CoverTitle"),
        p("面向个人创作者、学生、开发者与小团队的效率软件产品组合", "CoverSub"),
        p("版本：2026 年 7 月｜官网：https://pmpro.com.cn｜联系邮箱：postmaster@pmpro.com.cn｜GitHub：https://github.com/adkinsbai", "SmallCN"),
        Spacer(1, 7 * mm),
        cover_metrics(),
        Spacer(1, 12 * mm),
        p(
            "本文件用于说明当前产品方向、商业化路径与作品能力边界。当前主推商业产品为 Project Flow；TypeUp/语音键盘、VibeBoard、Digital Life 和 PPT 学习分析工具作为正在开发或产品化中的项目管线展示。本文不包含 Wan Studio 视频训练审核工具，也不包含光子芯片版图设计辅助工具。",
            "BodyCN",
        ),
    ]
    if ASSET.exists():
        story += [
            Spacer(1, 8 * mm),
            Image(str(ASSET), width=158 * mm, height=92 * mm),
            p("图：Project Flow 可视化项目时间线界面示意", "SmallCN"),
        ]
    story.append(PageBreak())

    story += [
        p("1. 执行摘要", "H1CN"),
        p(
            "PMPro 正在构建一组围绕“个人生产力、项目执行、语音输入、AI 辅助学习与本地智能伴侣”的软件产品。核心思路不是单纯包装 AI 模型，而是把真实用户工作流拆成可操作、可验证、可持续使用的工具：任务从想法进入结构化时间线，输入从键盘扩展到语音，学习材料从 PPT 变成可引用的知识单元，长期陪伴型应用通过本地优先架构保护用户数据。",
            "BodyCN",
        ),
        p(
            "当前商业化优先级最高的是 Project Flow：一款可视化项目时间线工具，提供网页端与 Windows 桌面端，面向创作者、学生、独立开发者和小团队。产品采用 30 天免费试用 + 低门槛永久访问的模式，当前价格为 US$1.99，并预留 Creem 支付与 License Key 解锁流程。",
            "BodyCN",
        ),
        p("核心商业判断", "H2CN"),
        bullet("用户已经不缺普通 Todo List，缺的是能表达项目分支、继续推进、完成收尾和历史脉络的工作空间。"),
        bullet("早期商业化应以轻量一次性付费、低摩擦试用和个人创作者传播为主，而不是一开始做复杂企业销售。"),
        bullet("多项目管线可以共享账号、支付、桌面打包、官网合规、更新分发和用户支持体系，形成统一的个人软件品牌。"),
        Spacer(1, 4 * mm),
        p("2. 产品组合矩阵", "H1CN"),
    ]

    product_table = [
        [cell("项目", True), cell("定位", True), cell("目标用户", True), cell("阶段", True), cell("商业化方式", True)],
        [
            cell("Project Flow", True),
            cell("可视化项目时间线与分支管理工具"),
            cell("学生、创作者、独立开发者、小团队"),
            cell("主推商业产品，已具备官网、下载、试用/付费文案和合规条款"),
            cell("30 天免费试用 + US$1.99 永久访问 + License Key"),
        ],
        [
            cell("TypeUp / 语音键盘"),
            cell("Windows 语音输入、个人词典、备忘记忆和本地桥接能力"),
            cell("高频写作用户、办公用户、需要语音转写的人群"),
            cell("产品化中，已做桌面集成、服务状态页、诊断与本地数据能力"),
            cell("桌面应用授权、Pro 功能、后续可接入订阅或永久许可"),
        ],
        [
            cell("VibeBoard"),
            cell("AI Agent 硬件执行与验证工作台"),
            cell("嵌入式开发者、硬件团队、AI 编程工具用户"),
            cell("技术展示与原型验证阶段"),
            cell("开发者工具、硬件板卡工作流、团队版服务"),
        ],
        [
            cell("Digital Life"),
            cell("本地优先的数字生命/个人陪伴运行时"),
            cell("需要长期记忆、情绪陪伴、个人日志和本地隐私的人群"),
            cell("原型与架构验证阶段"),
            cell("本地桌面应用、插件生态、隐私优先个人版"),
        ],
        [
            cell("PPT 学习分析工具"),
            cell("把 PPT/PPTX 转为章节讲解、题目、答案、公式和复习重点"),
            cell("学生、自学者、培训场景、考试复习用户"),
            cell("本地 Web 工具原型，具备上传解析与证据链输出"),
            cell("按次分析、学习工具包、校园/培训机构授权"),
        ],
    ]
    story.append(make_table(product_table, [28 * mm, 38 * mm, 34 * mm, 48 * mm, 34 * mm], pale=True))
    story.append(PageBreak())

    story += [
        p("3. 主推产品：Project Flow", "H1CN"),
        p(
            "Project Flow 的核心价值是把项目推进过程可视化。用户不是只记录一条待办，而是把一个项目从 Setup 到 Continue，再到 Done 的路径放到时间线上；每一次继续推进都可以形成分支，用户可以看到任务之间的关系、当前日期、逾期状态、完成状态和后续方向。",
            "BodyCN",
        ),
        p("典型使用流程", "H2CN"),
        Timeline(
            [
                ("Setup", "建立项目"),
                ("Continue", "继续推进"),
                ("Branch", "形成分支"),
                ("Today", "关注今日"),
                ("Done", "完成收尾"),
            ]
        ),
        Spacer(1, 5 * mm),
        p("关键功能", "H2CN"),
        bullet("节点式项目管理：每个项目、任务、分支都可以作为节点存在，适合表达真实推进路径。"),
        bullet("时间线视图：让用户看到今天、日期、历史节点和未来安排之间的关系。"),
        bullet("Continue 语义：每次继续工作时可以保留上下文，不把项目进展压扁成一条普通清单。"),
        bullet("Done 标记：完成后明确收尾，帮助用户从“持续拖延”转为“闭环记录”。"),
        bullet("网页端 + Windows 桌面端：便于用户先试用，再作为日常工具长期使用。"),
        p("商业化设计", "H2CN"),
    ]

    model_table = [
        [cell("项目", True), cell("设计", True), cell("原因", True)],
        [cell("免费试用"), cell("新用户 30 天免费试用"), cell("降低首次使用门槛，让用户在真实项目中验证价值。")],
        [cell("付费方式"), cell("当前永久访问价格 US$1.99"), cell("适合早期冷启动和海外支付审核，降低用户决策成本。")],
        [cell("License Key"), cell("通过支付后发放激活码解锁"), cell("兼容桌面端、本地化应用和未来多设备账号同步。")],
        [cell("支付服务"), cell("计划通过 Creem 处理 checkout 与 key 分发"), cell("减少自建支付系统的复杂度，便于合规审核。")],
        [cell("合规页面"), cell("官网展示隐私政策、服务条款、退款规则和联系方式"), cell("满足支付平台、用户信任和公开销售的基本要求。")],
    ]
    story += [make_table(model_table, [30 * mm, 55 * mm, 90 * mm], pale=True), Spacer(1, 4 * mm)]

    story += [
        p("4. 其它产品管线", "H1CN"),
        p("4.1 TypeUp / 语音键盘", "H2CN"),
        p(
            "TypeUp / 语音键盘面向 Windows 桌面使用场景，重点解决语音输入、状态可见、本地服务桥接、个人词典和常用备忘等需求。它的价值在于让语音输入不只是一个录音按钮，而是和用户的词汇、上下文、输入习惯、诊断状态形成可管理的本地系统。",
            "BodyCN",
        ),
        bullet("产品能力：语音输入、服务状态、诊断面板、个人词典、备忘记忆、云桥接公开状态。"),
        bullet("目标用户：写作者、学生、办公人群、需要高频输入或不方便长时间打字的人。"),
        bullet("产品化方向：Windows 桌面安装包、试用/Pro 授权、本地优先数据保存、后续接入统一账号体系。"),
        p("4.2 VibeBoard", "H2CN"),
        p(
            "VibeBoard 是面向 AI Agent 和硬件开发的执行/验证工作台。它的长期方向不是普通 AI 聊天工具，而是让 AI 编程工具在真实板卡上完成构建、烧录、日志回读和证据验证，从而减少嵌入式开发中“代码看起来对，但设备没有真正跑起来”的问题。",
            "BodyCN",
        ),
        bullet("产品能力：板卡上下文、编译构建、USB/OTA/Bridge 烧录、日志读取、Build/Flash/Device Evidence。"),
        bullet("目标用户：嵌入式开发者、硬件团队、AI 编程工具用户、需要自动化验证的教育/实验场景。"),
        bullet("商业化方向：开发者工具、硬件工作流服务、团队版验证平台或板卡生态合作。"),
        p("4.3 Digital Life", "H2CN"),
        p(
            "Digital Life 是本地优先的个人陪伴与长期记忆运行时。它强调可解释的状态、记忆、日志、反思和自主运行循环，同时在没有云模型时保留确定性离线回退能力。它适合承载未来的个人 AI 伴侣、桌面宠物、日志整理和情绪支持类产品。",
            "BodyCN",
        ),
        bullet("产品能力：本地状态、消息、记忆、日记、反思、行动循环、离线回退。"),
        bullet("目标用户：重视隐私的个人用户、需要长期陪伴和自我记录的人群。"),
        bullet("产品化方向：本地桌面伴侣、会员制插件、与 Project Flow/TypeUp 共享本地数据能力。"),
        p("4.4 PPT 学习分析工具", "H2CN"),
        p(
            "PPT 学习分析工具面向课程资料和考试复习。它把 PPT/PPTX 文件解析为章节讲解、问题、答案、公式和复习重点，并强调内容必须基于原始 PPT 证据，避免生成没有依据的学习材料。",
            "BodyCN",
        ),
        bullet("产品能力：PPTX 解析、幻灯片文本/备注/公式提取、图片 OCR、章节化学习内容、证据链与质量摘要。"),
        bullet("目标用户：学生、自学者、培训机构、需要快速消化课件的人。"),
        bullet("商业化方向：按次分析、考试复习包、校园工具、培训机构内部工具。"),
        PageBreak(),
    ]

    story += [
        p("5. 市场与用户", "H1CN"),
        p(
            "PMPro 产品组合的共同用户不是大型企业采购方，而是对工具敏感、愿意尝试新软件、希望把学习和项目执行效率提高的个人用户与小团队。早期应优先服务一批真实使用者，通过低价、快速迭代和公开演示获得反馈。",
            "BodyCN",
        ),
        BarChart(
            [
                ("个人创作者/独立开发者", 90, "#2563EB"),
                ("学生与自学者", 80, "#16A34A"),
                ("小团队/工作室", 65, "#2563EB"),
                ("硬件开发者", 45, "#16A34A"),
                ("培训/教育机构", 40, "#2563EB"),
            ]
        ),
        p("图：早期目标用户优先级示意", "SmallCN"),
        p("6. 商业模式", "H1CN"),
        p(
            "短期以 Project Flow 的一次性低价授权作为商业化起点，中期把 TypeUp 和 PPT 学习工具纳入同一账号/支付/授权体系，长期再根据验证结果发展为多产品会员或工具包销售。",
            "BodyCN",
        ),
    ]

    revenue_table = [
        [cell("阶段", True), cell("收入来源", True), cell("重点动作", True), cell("衡量指标", True)],
        [cell("0-3 个月"), cell("Project Flow 永久访问"), cell("完善官网、支付、License Key、桌面下载、用户指南"), cell("访问量、注册数、试用转化、激活成功率")],
        [cell("3-6 个月"), cell("Project Flow + TypeUp Pro"), cell("统一账号、桌面更新、语音输入核心体验打磨"), cell("留存率、日活、桌面安装量、退款率")],
        [cell("6-12 个月"), cell("学习工具包 / 多产品会员"), cell("PPT 学习工具产品化，探索打包销售"), cell("付费用户数、复购率、分析次数")],
        [cell("12 个月+"), cell("开发者工具 / 团队版"), cell("VibeBoard 验证工作流和 Digital Life 插件化"), cell("团队试点数、合作机会、ARPU")],
    ]
    story += [make_table(revenue_table, [25 * mm, 40 * mm, 72 * mm, 45 * mm], pale=True)]

    story += [
        p("7. 技术路线与资产复用", "H1CN"),
        p(
            "这些项目虽然面向不同使用场景，但底层可以复用同一套商业基础设施：账号、试用期、授权、支付、隐私政策、服务条款、桌面打包、官网下载、用户支持邮箱、版本更新和日志诊断。",
            "BodyCN",
        ),
    ]
    tech_table = [
        [cell("公共能力", True), cell("Project Flow", True), cell("TypeUp", True), cell("PPT 工具", True), cell("Digital Life / VibeBoard", True)],
        [cell("账号/授权"), cell("试用、永久访问、License Key"), cell("Pro 功能解锁"), cell("分析额度/会员"), cell("插件或开发者版授权")],
        [cell("桌面端"), cell("Windows 安装包"), cell("Windows 托盘/桥接"), cell("可封装为本地工具"), cell("本地运行时/硬件代理")],
        [cell("本地数据"), cell("项目时间线"), cell("词典、备忘、历史"), cell("课件解析缓存"), cell("记忆、日志、运行证据")],
        [cell("云服务"), cell("账号同步、支付校验"), cell("可选云桥接"), cell("可选模型 OCR/分析"), cell("可选模型推理/远程验证")],
    ]
    story += [make_table(tech_table, [32 * mm, 38 * mm, 34 * mm, 34 * mm, 44 * mm], pale=True), PageBreak()]

    story += [
        p("8. 合规与上线准备", "H1CN"),
        p(
            "当前官网已经围绕公开销售所需的基础内容进行整理：包含产品说明、定价、退款规则、隐私政策、服务条款、公开联系邮箱和 ICP 状态说明。由于网站当前计划托管在 Vercel，在未使用中国内地服务器时不应展示虚假的 ICP 备案号；若未来迁回中国内地服务器，必须在页脚展示真实有效的 ICP 备案号。",
            "BodyCN",
        ),
    ]
    compliance = [
        [cell("事项", True), cell("当前状态", True), cell("后续动作", True)],
        [cell("公开官网"), cell("pmpro.com.cn 已用于 Project Flow 对外展示"), cell("持续保持英文默认、中文可切换和下载入口稳定")],
        [cell("隐私政策"), cell("已公开说明数据收集、使用、存储和联系渠道"), cell("后续根据真实后端和支付服务商更新")],
        [cell("服务条款"), cell("已公开说明试用、付费、License Key、退款和责任限制"), cell("正式上线前再人工法务校对")],
        [cell("支付"), cell("计划使用 Creem，当前需完成平台审核与企业/身份资料"), cell("审核通过后接入正式 checkout 与 webhook")],
        [cell("ICP"), cell("Vercel 托管时不展示虚假备案号"), cell("若使用中国内地服务器，先完成真实备案")],
        [cell("用户支持"), cell("公开邮箱 postmaster@pmpro.com.cn"), cell("建立退款、激活失败、数据请求处理流程")],
    ]
    story += [make_table(compliance, [34 * mm, 72 * mm, 74 * mm], pale=True)]

    story += [
        p("9. 12 个月里程碑", "H1CN"),
        Timeline(
            [
                ("M1", "支付闭环"),
                ("M3", "首批用户"),
                ("M6", "多产品授权"),
                ("M9", "学习工具"),
                ("M12", "开发者版"),
            ]
        ),
        Spacer(1, 5 * mm),
    ]
    milestones = [
        [cell("时间", True), cell("目标", True), cell("交付物", True)],
        [cell("第 1 个月"), cell("Project Flow 可售卖闭环"), cell("Creem checkout、License Key、退款/支持流程、桌面下载页")],
        [cell("第 2-3 个月"), cell("验证真实用户使用"), cell("用户指南、反馈入口、数据备份、常见问题、稳定版本")],
        [cell("第 4-6 个月"), cell("TypeUp 产品化"), cell("安装包、诊断、词典/备忘体验、Pro 权限设计")],
        [cell("第 7-9 个月"), cell("PPT 学习工具上线试验"), cell("上传解析、章节输出、证据链、按次/会员定价测试")],
        [cell("第 10-12 个月"), cell("VibeBoard/Digital Life 选择商业方向"), cell("根据用户反馈决定开发者工具或个人陪伴产品优先级")],
    ]
    story += [make_table(milestones, [28 * mm, 50 * mm, 104 * mm], pale=True)]

    story += [
        p("10. 风险与应对", "H1CN"),
    ]
    risks = [
        [cell("风险", True), cell("影响", True), cell("应对策略", True)],
        [cell("支付平台审核延迟"), cell("影响正式收费"), cell("先保持免费试用与人工 License Key 流程，审核通过后再自动化。")],
        [cell("合规材料不完整"), cell("影响支付和公开销售"), cell("保持官网条款、隐私、退款、联系方式清晰，并避免虚假宣传。")],
        [cell("产品线过多"), cell("开发资源分散"), cell("以 Project Flow 为商业主线，其它项目作为管线分阶段推进。")],
        [cell("用户留存不足"), cell("低价转化后增长慢"), cell("重点优化首次登录指南、真实案例模板、桌面端日常使用体验。")],
        [cell("AI 生成内容可信度"), cell("学习工具可能输出不准确"), cell("保留证据链、引用来源，不足时明确提示没有依据。")],
    ]
    story += [
        make_table(risks, [38 * mm, 42 * mm, 102 * mm], pale=True),
        Spacer(1, 6 * mm),
        p("结论", "H1CN"),
        p(
            "PMPro 的近期重点应是把 Project Flow 打磨成真正可购买、可试用、可下载、可支持的商业产品。它承担品牌和收入起点；TypeUp、PPT 学习工具、Digital Life 与 VibeBoard 则作为后续产品管线，围绕个人生产力、本地智能和开发者验证能力逐步扩展。这个组合的优势在于：每个项目都有明确使用场景，同时又能共享账号、支付、桌面、合规和用户支持基础设施。",
            "BodyCN",
        ),
    ]
    return story


def main():
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=22 * mm,
        title=DOCUMENT_TITLE,
        author="PMPro",
    )
    story = build_story()
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(PDF_PATH)


if __name__ == "__main__":
    main()
