from __future__ import annotations

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
PDF_PATH = OUT_DIR / "OPC_Maker_Application_CN.pdf"
SCREENSHOT = ROOT / "website" / "assets" / "project-flow-canvas.png"

TITLE = "OPC创客申请"
SUBTITLE = "PMPro 多产品软件作品与商业化说明"
CONTACT = "postmaster@pmpro.com.cn"
WEBSITE = "https://pmpro.com.cn"
GITHUB = "https://github.com/adkinsbai"

FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
]


def register_fonts() -> tuple[str, str]:
    base = "Helvetica"
    bold = "Helvetica-Bold"
    for font in FONT_CANDIDATES:
        if font.exists():
            pdfmetrics.registerFont(TTFont("CN", str(font)))
            base = "CN"
            break
    bold_font = Path(r"C:\Windows\Fonts\msyhbd.ttc")
    if bold_font.exists():
        pdfmetrics.registerFont(TTFont("CN-Bold", str(bold_font)))
        bold = "CN-Bold"
    else:
        bold = base
    return base, bold


FONT, FONT_BOLD = register_fonts()

INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#667085")
BLUE = colors.HexColor("#2563EB")
GREEN = colors.HexColor("#13A86B")
CYAN = colors.HexColor("#0891B2")
VIOLET = colors.HexColor("#7C3AED")
ORANGE = colors.HexColor("#EA580C")
LINE = colors.HexColor("#DFE7F1")
PANEL = colors.HexColor("#F7FAFC")
SOFT_BLUE = colors.HexColor("#EFF6FF")
SOFT_GREEN = colors.HexColor("#ECFDF3")
SOFT_CYAN = colors.HexColor("#ECFEFF")
WHITE = colors.white

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("CoverTitle", fontName=FONT_BOLD, fontSize=36, leading=44, textColor=INK, spaceAfter=10))
styles.add(ParagraphStyle("CoverSub", fontName=FONT, fontSize=13.5, leading=21, textColor=MUTED, spaceAfter=6))
styles.add(ParagraphStyle("Meta", fontName=FONT, fontSize=8.5, leading=13, textColor=MUTED))
styles.add(ParagraphStyle("H1", fontName=FONT_BOLD, fontSize=18, leading=24, textColor=INK, spaceBefore=8, spaceAfter=8))
styles.add(ParagraphStyle("H2", fontName=FONT_BOLD, fontSize=12.5, leading=17, textColor=INK, spaceBefore=4, spaceAfter=4))
styles.add(ParagraphStyle("Body", fontName=FONT, fontSize=9.3, leading=15.5, textColor=INK, spaceAfter=5))
styles.add(ParagraphStyle("Small", fontName=FONT, fontSize=7.8, leading=11.5, textColor=MUTED))
styles.add(ParagraphStyle("CardTitle", fontName=FONT_BOLD, fontSize=11.2, leading=15, textColor=INK))
styles.add(ParagraphStyle("CardText", fontName=FONT, fontSize=8.0, leading=12, textColor=INK))
styles.add(ParagraphStyle("Chip", fontName=FONT_BOLD, fontSize=6.7, leading=8.5, textColor=WHITE, alignment=TA_CENTER))
styles.add(ParagraphStyle("MetricValue", fontName=FONT_BOLD, fontSize=18, leading=22, textColor=BLUE, alignment=TA_CENTER))
styles.add(ParagraphStyle("MetricLabel", fontName=FONT, fontSize=7.2, leading=10, textColor=MUTED, alignment=TA_CENTER))
styles.add(ParagraphStyle("Callout", fontName=FONT_BOLD, fontSize=12, leading=18, textColor=INK, alignment=TA_LEFT))


def p(text: str, style: str = "Body") -> Paragraph:
    return Paragraph(text, styles[style])


def chip(text: str, color=BLUE, width=26 * mm):
    t = Table([[p(text, "Chip")]], colWidths=[width])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("BOX", (0, 0), (-1, -1), 0, color),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


class AccentRule(Flowable):
    def __init__(self, color=BLUE, height=2):
        super().__init__()
        self.color = color
        self.height = height

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        return availWidth, self.height

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.roundRect(0, 0, self.width, self.height, 1.2, fill=1, stroke=0)


def soft_card(items, width, bg=PANEL, stroke=LINE, pad=8):
    t = Table([[items]], colWidths=[width], hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 0.55, stroke),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), pad),
                ("RIGHTPADDING", (0, 0), (-1, -1), pad),
                ("TOPPADDING", (0, 0), (-1, -1), pad),
                ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
            ]
        )
    )
    return t


def metric_card(value, label, width=38 * mm):
    inner = [p(value, "MetricValue"), Spacer(1, 1.5 * mm), p(label, "MetricLabel")]
    return soft_card(inner, width, bg=WHITE)


def product_card(name, stage, body, bullets, accent, width=86 * mm):
    chip_row = Table([[chip(stage, accent, width=26 * mm)]], colWidths=[28 * mm])
    chip_row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0)]))
    content = [
        AccentRule(accent, 2.2),
        Spacer(1, 3 * mm),
        p(name, "CardTitle"),
        Spacer(1, 1.5 * mm),
        chip_row,
        Spacer(1, 2.5 * mm),
        p(body, "CardText"),
        Spacer(1, 2 * mm),
    ]
    for item in bullets:
        content.append(p("• " + item, "CardText"))
    return soft_card(content, width, bg=WHITE)


def info_pair(label, value, color=BLUE, width=84 * mm):
    content = [
        p(label, "Small"),
        Spacer(1, 1.2 * mm),
        p(value, "CardTitle"),
    ]
    return soft_card(content, width, bg=SOFT_BLUE if color == BLUE else SOFT_GREEN, stroke=colors.HexColor("#D6E4FF"))


def card_grid(cards, col_width=86 * mm, gap=6 * mm):
    rows = []
    for i in range(0, len(cards), 2):
        left = cards[i]
        right = cards[i + 1] if i + 1 < len(cards) else ""
        rows.append([left, "", right])
    t = Table(rows, colWidths=[col_width, gap, col_width], hAlign="LEFT")
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return t


def card_grid_three(cards, col_width=56 * mm, gap=5 * mm):
    rows = []
    for i in range(0, len(cards), 3):
        row = []
        for j in range(3):
            if i + j < len(cards):
                row.append(cards[i + j])
            else:
                row.append("")
            if j < 2:
                row.append("")
        rows.append(row)
    t = Table(rows, colWidths=[col_width, gap, col_width, gap, col_width], hAlign="LEFT")
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def simple_status_card(title, lines, accent=BLUE, width=56 * mm):
    content = [AccentRule(accent, 2), Spacer(1, 2.5 * mm), p(title, "CardTitle")]
    for line in lines:
        content.append(Spacer(1, 1.5 * mm))
        content.append(p(line, "Small" if len(line) > 22 else "CardText"))
    return soft_card(content, width, bg=WHITE)


def timeline(items):
    rows = []
    for label, title, text, color in items:
        rows.append([chip(label, color, width=18 * mm), p(title, "CardTitle"), p(text, "CardText")])
    t = Table(rows, colWidths=[23 * mm, 38 * mm, 111 * mm], hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -2), 0.45, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return t


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(doc.leftMargin, 17 * mm, A4[0] - doc.rightMargin, 17 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT, 7.5)
    canvas.drawString(doc.leftMargin, 12 * mm, TITLE)
    canvas.drawRightString(A4[0] - doc.rightMargin, 12 * mm, str(doc.page))
    canvas.restoreState()


def section(title):
    return [Spacer(1, 4 * mm), p(title, "H1"), AccentRule(BLUE, 1.4), Spacer(1, 5 * mm)]


def build_story():
    story = []

    story += [
        Spacer(1, 16 * mm),
        p(TITLE, "CoverTitle"),
        p(SUBTITLE, "CoverSub"),
        p(f"版本：2026 年 7 月｜官网：{WEBSITE}｜邮箱：{CONTACT}｜GitHub：{GITHUB}", "Meta"),
        Spacer(1, 9 * mm),
    ]

    metrics = Table(
        [[metric_card("5", "产品/项目管线"), metric_card("30 天", "Project Flow 免费试用"), metric_card("US$1.99", "当前永久访问定价"), metric_card("2 条", "网页端 + Windows 桌面端")]],
        colWidths=[42 * mm, 42 * mm, 42 * mm, 42 * mm],
    )
    metrics.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(metrics)
    story += [
        Spacer(1, 8 * mm),
        soft_card(
            [
                p("申请定位", "CardTitle"),
                p("PMPro 是一个面向个人创作者、学生、开发者和小团队的轻量生产力软件项目组合。本申请以 Project Flow 为当前主推商业产品，同时展示 TypeUp / 语音键盘、VibeBoard、Digital Life 和 PPT 学习分析工具作为产品管线。", "Body"),
                p("本文明确排除 Wan Studio 视频训练审核工具与光子芯片版图设计辅助工具。", "Small"),
            ],
            174 * mm,
            bg=SOFT_BLUE,
            stroke=colors.HexColor("#C7D7FE"),
        ),
        Spacer(1, 7 * mm),
    ]
    if SCREENSHOT.exists():
        story += [Image(str(SCREENSHOT), width=160 * mm, height=93 * mm), p("Project Flow 可视化项目时间线界面", "Small")]
    story.append(PageBreak())

    story += section("1. 申请概览")
    story += [
        p("本申请材料面向 OPC 创客入驻审核，重点说明：申请人正在开发的产品是真实软件项目，已有可展示的官网、产品页面、Windows 桌面下载与公开联系邮箱；当前商业化优先级集中在 Project Flow，其它项目以产品管线和技术能力展示为主。", "Body"),
        Spacer(1, 4 * mm),
        Table(
            [[
                info_pair("公开官网", WEBSITE),
                "",
                info_pair("联系邮箱", CONTACT, color=GREEN),
            ]],
            colWidths=[84 * mm, 6 * mm, 84 * mm],
        ),
        Spacer(1, 5 * mm),
        Table(
            [[
                info_pair("代码与作品入口", GITHUB),
                "",
                info_pair("主推产品", "Project Flow - 可视化项目时间线", color=GREEN),
            ]],
            colWidths=[84 * mm, 6 * mm, 84 * mm],
        ),
    ]

    story += section("2. 产品组合")
    cards = [
        product_card(
            "Project Flow",
            "主推商业产品",
            "可视化项目时间线与工作流规划工具，帮助用户把真实项目拆成节点、分支、日期、进度和 Done 状态。",
            ["网页端与 Windows 桌面端", "30 天免费试用，当前永久访问价 US$1.99", "计划使用 Creem / License Key 完成付费解锁"],
            BLUE,
        ),
        product_card(
            "TypeUp / 语音键盘",
            "产品化中",
            "Windows 语音输入与个人效率工具，围绕语音转写、本地服务状态、诊断、个人词典和备忘记忆构建。",
            ["面向高频输入、写作和办公人群", "本地桥接与公开状态页", "后续可接入统一授权体系"],
            GREEN,
        ),
        product_card(
            "VibeBoard",
            "原型验证",
            "面向 AI Agent 和硬件开发的执行验证工作台，强调构建、烧录、日志回读和设备证据。",
            ["服务嵌入式开发者和硬件团队", "不是普通聊天工具，而是执行/验证工作流", "后续可发展为开发者工具"],
            CYAN,
        ),
        product_card(
            "Digital Life",
            "架构验证",
            "本地优先的个人陪伴与长期记忆运行时，包含状态、消息、记忆、日记、反思和自主循环。",
            ["隐私优先、本地数据优先", "支持离线回退", "可作为未来桌面伴侣或插件化产品"],
            VIOLET,
        ),
        product_card(
            "PPT 学习分析工具",
            "本地 Web 原型",
            "把 PPT/PPTX 课件转换为章节讲解、题目、答案、公式和复习重点，并保留证据链。",
            ["面向学生、自学者和培训场景", "强调基于原始 PPT，不凭空生成", "可探索按次分析或学习工具包"],
            ORANGE,
        ),
    ]
    story.append(card_grid(cards[:4], col_width=84 * mm))
    story.append(
        product_card(
            "PPT 学习分析工具",
            "本地 Web 原型",
            "把 PPT/PPTX 课件转换为章节讲解、题目、答案、公式和复习重点，并保留证据链。",
            ["面向学生、自学者和培训场景", "强调基于原始 PPT，不凭空生成", "可探索按次分析或学习工具包"],
            ORANGE,
            width=174 * mm,
        )
    )

    story += section("3. 主推产品 Project Flow")
    story += [
        p("Project Flow 是当前最适合公开销售和平台审核的主产品。它解决的是普通 Todo List 难以表达真实项目上下文的问题：一个项目往往不是一条线，而是会继续推进、产生分支、回到今天、最后收尾。Project Flow 用时间线和节点关系把这个过程呈现出来。", "Body"),
        Spacer(1, 3 * mm),
        card_grid(
            [
                simple_status_card("Setup", ["建立项目主线", "记录项目起点和目标"], BLUE),
                simple_status_card("Continue", ["继续推进时保留上下文", "分支代表新的行动路径"], GREEN),
                simple_status_card("Today", ["日期列帮助用户定位今日", "减少项目散落和遗忘"], CYAN),
                simple_status_card("Done", ["完成后明确收尾", "形成可回顾的执行记录"], VIOLET),
            ],
            col_width=84 * mm,
        ),
        Spacer(1, 4 * mm),
        soft_card(
            [
                p("商业化方式", "CardTitle"),
                p("新用户可免费试用 30 天。试用结束后，用户可通过付费获得授权账号的永久访问权限，当前价格为 US$1.99。支付和激活流程计划由 Creem 或同类 checkout 服务处理，购买后通过 License Key 或账号解锁完成交付。", "Body"),
            ],
            174 * mm,
            bg=SOFT_GREEN,
            stroke=colors.HexColor("#B7E4C7"),
        ),
    ]

    story += section("4. 交付、支持与合规")
    story += [
        card_grid_three(
            [
                simple_status_card("产品交付", ["网页端访问", "Windows 安装包", "账号或 Key 解锁"], BLUE),
                simple_status_card("用户支持", [CONTACT, "处理激活、退款、隐私和账号问题"], GREEN),
                simple_status_card("支付边界", ["前端不保存完整卡信息", "支付由 checkout 服务商处理"], CYAN),
                simple_status_card("公开政策", ["Privacy Policy", "Terms of Service", "退款和定价说明"], VIOLET),
                simple_status_card("数据边界", ["避免收集高敏个人数据", "本地数据优先"], ORANGE),
                simple_status_card("ICP备案", ["不用虚假备案号", "内地服务器上线前完成备案"], BLUE),
            ],
            col_width=56 * mm,
        ),
        Spacer(1, 3 * mm),
        soft_card(
            [
                p("风险控制声明", "CardTitle"),
                p("PMPro 不把 Project Flow 宣传为法律、金融、医疗、数据恢复、企业 SLA 或安全认证产品。用户购买的是项目规划与时间线可视化工具的访问权限。若未来使用中国内地服务器公开访问，将在取得真实有效 ICP 备案后展示备案号；当前不展示虚假备案信息。", "Body"),
            ],
            174 * mm,
            bg=PANEL,
        ),
    ]

    story += section("5. 商业化路径")
    story += [
        timeline(
            [
                ("M1", "支付闭环", "完成 Creem / checkout、License Key、退款与人工支持流程，保证用户购买后能顺利解锁。", BLUE),
                ("M2", "用户指南", "完善首次登录指南、Help 入口、真实截图案例和 Setup / Continue / Done 流程说明。", GREEN),
                ("M3", "桌面端稳定", "保持 Windows 安装包、网页端和账号授权体验一致，修复高频使用中的布局和同步问题。", CYAN),
                ("M6", "多产品授权", "将 TypeUp 和 PPT 学习分析工具纳入统一账号、授权和支持体系。", VIOLET),
                ("M12", "产品管线选择", "根据真实用户反馈决定 VibeBoard 或 Digital Life 的商业化优先级。", ORANGE),
            ]
        )
    ]

    story += section("6. 申请材料总结")
    story += [
        soft_card(
            [
                p("为什么适合 OPC 创客申请", "Callout"),
                p("本项目不是单一概念展示，而是围绕个人生产力软件形成的持续产品组合。Project Flow 已具备公开展示、定价、桌面交付、用户支持和基础合规说明；其它项目体现了申请人在桌面软件、本地数据、AI 辅助学习、硬件验证和长期记忆运行时方面的持续开发能力。", "Body"),
                p("当前申请重点是获得平台侧的创客/产品展示与商业化支持，而不是声称已有大规模收入或企业客户。所有商业化、定价、退款和产品阶段均按当前真实状态说明。", "Body"),
            ],
            174 * mm,
            bg=SOFT_BLUE,
            stroke=colors.HexColor("#C7D7FE"),
        ),
    ]
    return story


def main():
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=22 * mm,
        title=TITLE,
        author="PMPro",
    )
    doc.build(build_story(), onFirstPage=header_footer, onLaterPages=header_footer)
    print(PDF_PATH)


if __name__ == "__main__":
    main()
