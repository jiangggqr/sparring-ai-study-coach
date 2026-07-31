from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "Sparring_Devpost_Judge_Pack.pdf"

PLAN_SCREEN = Path("/private/tmp/sparring-render-real-plan.png")
LESSON_SCREEN = Path("/private/tmp/sparring-render-real-lesson.png")
QUIZ_SCREEN = Path("/private/tmp/sparring-render-real-quiz.png")

PAGE_W, PAGE_H = A4
MARGIN = 46

INK = HexColor("#16231E")
GREEN = HexColor("#0D6B57")
DEEP_GREEN = HexColor("#0B4F40")
MINT = HexColor("#DCEFE9")
PALE_MINT = HexColor("#EFF7F3")
IVORY = HexColor("#FAF7F0")
PAPER = HexColor("#FFFDF8")
RULE = HexColor("#D8D4C9")
MUTED = HexColor("#52615B")
AMBER = HexColor("#F2A65A")
PALE_AMBER = HexColor("#FFF0DA")
PALE_RED = HexColor("#FBE7E4")
RED = HexColor("#9D3B31")

LIVE_URL = "https://sparring-ai-study-coach.onrender.com/"
REPO_URL = "https://github.com/jiangggqr/sparring-ai-study-coach"


def require_assets() -> None:
    missing = [path for path in (PLAN_SCREEN, LESSON_SCREEN, QUIZ_SCREEN) if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing screenshot assets: {missing}")


def rounded_box(pdf: canvas.Canvas, x: float, y: float, w: float, h: float, fill, radius=12):
    pdf.setFillColor(fill)
    pdf.roundRect(x, y, w, h, radius, fill=1, stroke=0)


def draw_wrapped(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    font: str = "Helvetica",
    size: float = 10,
    color=INK,
    leading: float | None = None,
    max_lines: int | None = None,
) -> float:
    leading = leading or size * 1.35
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if stringWidth(candidate, font, size) <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        while stringWidth(lines[-1] + "...", font, size) > width and lines[-1]:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "..."

    pdf.setFont(font, size)
    pdf.setFillColor(color)
    cursor = y
    for line in lines:
        pdf.drawString(x, cursor, line)
        cursor -= leading
    return cursor


def label(pdf: canvas.Canvas, text: str, x: float, y: float, color=GREEN):
    pdf.setFillColor(color)
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawString(x, y, text.upper())


def title(pdf: canvas.Canvas, text: str, y: float) -> float:
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 27)
    return draw_wrapped(pdf, text, MARGIN, y, PAGE_W - 2 * MARGIN, "Helvetica-Bold", 27, INK, 31)


def footer(pdf: canvas.Canvas, page_number: int):
    pdf.setStrokeColor(RULE)
    pdf.setLineWidth(0.6)
    pdf.line(MARGIN, 31, PAGE_W - MARGIN, 31)
    pdf.setFont("Helvetica", 7.5)
    pdf.setFillColor(MUTED)
    pdf.drawString(MARGIN, 18, "SPARRING  |  PROMETHEUS JULY AI CHALLENGE")
    pdf.drawRightString(PAGE_W - MARGIN, 18, str(page_number))


def draw_image_cover(
    pdf: canvas.Canvas,
    image_path: Path,
    x: float,
    y: float,
    w: float,
    h: float,
    position=(0.5, 0.28),
):
    with Image.open(image_path) as source:
        source = source.convert("RGB")
        fitted = ImageOps.fit(
            source,
            (max(1, int(w * 2.2)), max(1, int(h * 2.2))),
            method=Image.Resampling.LANCZOS,
            centering=position,
        )
        buffer = io.BytesIO()
        fitted.save(buffer, format="JPEG", quality=88, optimize=True)
        buffer.seek(0)

        pdf.saveState()
        path = pdf.beginPath()
        path.roundRect(x, y, w, h, 10)
        pdf.clipPath(path, stroke=0, fill=0)
        pdf.drawInlineImage(Image.open(buffer), x, y, w, h)
        pdf.restoreState()
        pdf.setStrokeColor(RULE)
        pdf.setLineWidth(0.8)
        pdf.roundRect(x, y, w, h, 10, fill=0, stroke=1)


def pill(pdf: canvas.Canvas, text: str, x: float, y: float, w: float, fill=MINT, color=DEEP_GREEN):
    rounded_box(pdf, x, y, w, 24, fill, 12)
    pdf.setFillColor(color)
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawCentredString(x + w / 2, y + 8, text.upper())


def numbered_card(
    pdf: canvas.Canvas,
    number: str,
    heading: str,
    body: str,
    x: float,
    y: float,
    w: float,
    h: float,
):
    rounded_box(pdf, x, y, w, h, PAPER, 11)
    pdf.setStrokeColor(RULE)
    pdf.roundRect(x, y, w, h, 11, fill=0, stroke=1)
    rounded_box(pdf, x + 12, y + h - 33, 24, 22, MINT, 8)
    pdf.setFillColor(DEEP_GREEN)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawCentredString(x + 24, y + h - 26, number)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 10.5)
    pdf.drawString(x + 44, y + h - 26, heading)
    draw_wrapped(pdf, body, x + 12, y + h - 47, w - 24, "Helvetica", 8.6, MUTED, 11.3)


def link_button(pdf: canvas.Canvas, text: str, url: str, x: float, y: float, w: float):
    rounded_box(pdf, x, y, w, 30, DEEP_GREEN, 9)
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawCentredString(x + w / 2, y + 10.5, text)
    pdf.linkURL(url, (x, y, x + w, y + 30), relative=0)


def cover_page(pdf: canvas.Canvas):
    pdf.setFillColor(IVORY)
    pdf.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    label(pdf, "Prometheus July AI Challenge", MARGIN, PAGE_H - 52)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 42)
    pdf.drawString(MARGIN, PAGE_H - 105, "Sparring")
    draw_wrapped(
        pdf,
        "The AI study coach that refuses to think for you.",
        MARGIN,
        PAGE_H - 137,
        410,
        "Helvetica-Bold",
        18,
        GREEN,
        22,
    )
    pill(pdf, "Live GPT-5.6-sol demo", MARGIN, PAGE_H - 190, 142)
    pill(pdf, "Source-grounded", MARGIN + 151, PAGE_H - 190, 123, PALE_AMBER, HexColor("#7A4B0F"))
    pill(pdf, "No sign-in", MARGIN + 283, PAGE_H - 190, 82)

    rounded_box(pdf, MARGIN, PAGE_H - 291, PAGE_W - 2 * MARGIN, 79, PAPER, 12)
    pdf.setStrokeColor(RULE)
    pdf.roundRect(MARGIN, PAGE_H - 291, PAGE_W - 2 * MARGIN, 79, 12, fill=0, stroke=1)
    label(pdf, "The problem", MARGIN + 17, PAGE_H - 235, RED)
    draw_wrapped(
        pdf,
        "AI can generate a polished answer before the learner has predicted, retrieved, "
        "judged confidence, or explained the relationship.",
        MARGIN + 17,
        PAGE_H - 254,
        PAGE_W - 2 * MARGIN - 34,
        "Helvetica",
        10.5,
        INK,
        14,
    )

    draw_image_cover(
        pdf,
        PLAN_SCREEN,
        MARGIN,
        105,
        PAGE_W - 2 * MARGIN,
        415,
        position=(0.5, 0.20),
    )
    rounded_box(pdf, MARGIN + 18, 119, PAGE_W - 2 * MARGIN - 36, 52, DEEP_GREEN, 10)
    label(pdf, "Sparring's answer", MARGIN + 33, 151, MINT)
    draw_wrapped(
        pdf,
        "AI structures a three-concept practice map from the learner's PDF. "
        "The learner still performs every meaningful learning action.",
        MARGIN + 33,
        135,
        PAGE_W - 2 * MARGIN - 66,
        "Helvetica-Bold",
        9.5,
        white,
        12.5,
    )
    footer(pdf, 1)
    pdf.showPage()


def learner_loop_page(pdf: canvas.Canvas):
    pdf.setFillColor(IVORY)
    pdf.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    label(pdf, "The learner experience", MARGIN, PAGE_H - 50)
    title(pdf, "A guided loop that keeps the thinking visible", PAGE_H - 80)
    draw_wrapped(
        pdf,
        "Uploaded material is the only source. AI removes preparation work, then asks "
        "for observable attempts before feedback.",
        MARGIN,
        PAGE_H - 150,
        PAGE_W - 2 * MARGIN,
        "Helvetica",
        10.5,
        MUTED,
        14,
    )

    card_w = (PAGE_W - 2 * MARGIN - 12) / 2
    numbered_card(pdf, "1", "Upload", "Text PDF, scanned PDF, or pasted study text.", MARGIN, 570, card_w, 78)
    numbered_card(pdf, "2", "Predict", "Commit a low-stakes idea before seeing the explanation.", MARGIN + card_w + 12, 570, card_w, 78)
    numbered_card(pdf, "3", "Retrieve", "Answer definition, mechanism, and application questions.", MARGIN, 480, card_w, 78)
    numbered_card(pdf, "4", "Judge confidence", "Choose 1-5 before feedback. A sure mistake gets different support.", MARGIN + card_w + 12, 480, card_w, 78)
    numbered_card(pdf, "5", "Teach back", "Explain the relationship and repair one missing connection.", MARGIN, 390, card_w, 78)
    numbered_card(pdf, "6", "Return cold", "Reworded review returns on a transparent 1-3-7 day schedule.", MARGIN + card_w + 12, 390, card_w, 78)

    draw_image_cover(pdf, LESSON_SCREEN, MARGIN, 106, card_w, 244, position=(0.5, 0.25))
    draw_image_cover(pdf, QUIZ_SCREEN, MARGIN + card_w + 12, 106, card_w, 244, position=(0.5, 0.22))
    rounded_box(pdf, MARGIN + 12, 118, 188, 43, PALE_MINT, 8)
    draw_wrapped(
        pdf,
        "One explanation. One verified source anchor.",
        MARGIN + 23,
        144,
        166,
        "Helvetica-Bold",
        8.8,
        DEEP_GREEN,
        11,
    )
    rounded_box(pdf, MARGIN + card_w + 24, 118, 188, 43, PALE_AMBER, 8)
    draw_wrapped(
        pdf,
        "Answer + confidence are locked before feedback.",
        MARGIN + card_w + 35,
        144,
        166,
        "Helvetica-Bold",
        8.8,
        HexColor("#704414"),
        11,
    )
    footer(pdf, 2)
    pdf.showPage()


def architecture_page(pdf: canvas.Canvas):
    pdf.setFillColor(IVORY)
    pdf.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    label(pdf, "AI and technical execution", MARGIN, PAGE_H - 50)
    title(pdf, "Grounded generation, not an open-ended chatbot", PAGE_H - 80)
    draw_wrapped(
        pdf,
        "GPT-5.6-sol is central to the experience, but every model task is bounded by a "
        "schema, the learner's material, and a verifiable source anchor.",
        MARGIN,
        PAGE_H - 150,
        PAGE_W - 2 * MARGIN,
        "Helvetica",
        10.5,
        MUTED,
        14,
    )

    flow_y = 545
    stages = [
        ("1", "Learner PDF", "Text layer or private browser OCR"),
        ("2", "FastAPI", "Server-side key and bounded endpoints"),
        ("3", "GPT-5.6-sol", "Responses API + Structured Outputs"),
        ("4", "Anchor check", "Reject content not matched to source"),
        ("5", "Practice UI", "Prediction, retrieval, confidence, teach-back"),
    ]
    box_w = 92
    gap = 10
    for index, (number, heading, body) in enumerate(stages):
        x = MARGIN + index * (box_w + gap)
        rounded_box(pdf, x, flow_y, box_w, 108, PAPER, 10)
        pdf.setStrokeColor(RULE)
        pdf.roundRect(x, flow_y, box_w, 108, 10, fill=0, stroke=1)
        rounded_box(pdf, x + 10, flow_y + 76, 24, 22, MINT, 8)
        pdf.setFillColor(DEEP_GREEN)
        pdf.setFont("Helvetica-Bold", 9.5)
        pdf.drawCentredString(x + 22, flow_y + 83, number)
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(x + 10, flow_y + 59, heading)
        draw_wrapped(pdf, body, x + 10, flow_y + 44, box_w - 20, "Helvetica", 7.3, MUTED, 9.3)
        if index < len(stages) - 1:
            pdf.setStrokeColor(GREEN)
            pdf.setLineWidth(1.5)
            arrow_x = x + box_w + 2
            pdf.line(arrow_x, flow_y + 54, arrow_x + gap - 4, flow_y + 54)
            pdf.line(arrow_x + gap - 8, flow_y + 58, arrow_x + gap - 4, flow_y + 54)
            pdf.line(arrow_x + gap - 8, flow_y + 50, arrow_x + gap - 4, flow_y + 54)

    left_w = 244
    rounded_box(pdf, MARGIN, 315, left_w, 224, DEEP_GREEN, 14)
    label(pdf, "The AI does", MARGIN + 18, 510, MINT)
    ai_items = [
        "extracts exactly three concepts",
        "writes one focused explanation",
        "generates misconception-oriented items",
        "evaluates a bounded teach-back",
        "rewords the same objective for cold review",
    ]
    y = 484
    for item in ai_items:
        pdf.setFillColor(MINT)
        pdf.circle(MARGIN + 21, y + 3, 2.2, fill=1, stroke=0)
        y = draw_wrapped(pdf, item, MARGIN + 31, y, left_w - 49, "Helvetica", 9.2, white, 12.5) - 8

    right_x = MARGIN + left_w + 15
    right_w = PAGE_W - MARGIN - right_x
    rounded_box(pdf, right_x, 315, right_w, 224, PAPER, 14)
    pdf.setStrokeColor(RULE)
    pdf.roundRect(right_x, 315, right_w, 224, 14, fill=0, stroke=1)
    label(pdf, "The learner does", right_x + 18, 510)
    learner_items = [
        "commits the prediction",
        "retrieves before feedback",
        "rates confidence",
        "explains and revises",
        "returns later without hints",
    ]
    y = 484
    for item in learner_items:
        pdf.setFillColor(GREEN)
        pdf.circle(right_x + 21, y + 3, 2.2, fill=1, stroke=0)
        y = draw_wrapped(pdf, item, right_x + 31, y, right_w - 49, "Helvetica", 9.2, INK, 12.5) - 8

    rounded_box(pdf, MARGIN, 103, PAGE_W - 2 * MARGIN, 178, PALE_MINT, 14)
    label(pdf, "Trust boundaries", MARGIN + 18, 254)
    guardrails = [
        ("Server-side key", "The OpenAI API key never enters client code."),
        ("Source-only", "Sparring does not search the web or add an outside source."),
        ("Verified anchors", "Generated anchors must match the supplied material."),
        ("Minimized evidence", "SQLite stores practice events, not PDFs or learner answers."),
        ("Honest language", "The product reports practice evidence, never permanent mastery."),
    ]
    y = 227
    for heading, body in guardrails:
        pdf.setFont("Helvetica-Bold", 8.9)
        pdf.setFillColor(DEEP_GREEN)
        pdf.drawString(MARGIN + 18, y, heading)
        draw_wrapped(pdf, body, MARGIN + 128, y, PAGE_W - 2 * MARGIN - 146, "Helvetica", 8.6, INK, 11)
        y -= 28
    footer(pdf, 3)
    pdf.showPage()


def judge_page(pdf: canvas.Canvas):
    pdf.setFillColor(IVORY)
    pdf.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    label(pdf, "Judge guide", MARGIN, PAGE_H - 50)
    title(pdf, "The strongest proof path", PAGE_H - 80)
    draw_wrapped(
        pdf,
        "The public demo requires no sign-in. Use a short prose PDF; a pure scanned page "
        "also demonstrates the browser OCR path.",
        MARGIN,
        PAGE_H - 120,
        PAGE_W - 2 * MARGIN,
        "Helvetica",
        10.5,
        MUTED,
        14,
    )

    steps = [
        "Upload a PDF and wait for the source-ready confirmation.",
        "Build the three-concept map and inspect a material anchor.",
        "Commit a prediction before opening the explanation.",
        "Choose a wrong answer with confidence 5 to see mismatch feedback.",
        "Submit a weak teach-back, then repair the missing relationship.",
        "Advance the demo day and open the reworded cold review.",
    ]
    y = 650
    for index, step in enumerate(steps, 1):
        rounded_box(pdf, MARGIN, y - 35, PAGE_W - 2 * MARGIN, 45, PAPER, 9)
        pdf.setStrokeColor(RULE)
        pdf.roundRect(MARGIN, y - 35, PAGE_W - 2 * MARGIN, 45, 9, fill=0, stroke=1)
        rounded_box(pdf, MARGIN + 10, y - 24, 24, 24, MINT, 8)
        pdf.setFillColor(DEEP_GREEN)
        pdf.setFont("Helvetica-Bold", 9.5)
        pdf.drawCentredString(MARGIN + 22, y - 16, str(index))
        draw_wrapped(pdf, step, MARGIN + 46, y - 10, PAGE_W - 2 * MARGIN - 58, "Helvetica", 9, INK, 11)
        y -= 54

    rounded_box(pdf, MARGIN, 210, PAGE_W - 2 * MARGIN, 97, DEEP_GREEN, 13)
    label(pdf, "Validation snapshot", MARGIN + 18, 282, MINT)
    metrics = [
        ("28", "automated tests"),
        ("LIVE", "scanned-PDF E2E"),
        ("AA", "accessibility intent"),
        ("0", "API keys in client"),
    ]
    metric_w = (PAGE_W - 2 * MARGIN - 36) / 4
    for index, (value, caption) in enumerate(metrics):
        x = MARGIN + 18 + index * metric_w
        pdf.setFillColor(white)
        pdf.setFont("Helvetica-Bold", 19)
        pdf.drawString(x, 248, value)
        draw_wrapped(pdf, caption, x, 232, metric_w - 12, "Helvetica", 7.5, MINT, 9)

    rounded_box(pdf, MARGIN, 105, PAGE_W - 2 * MARGIN, 88, PALE_RED, 12)
    label(pdf, "Honest limits", MARGIN + 18, 167, RED)
    draw_wrapped(
        pdf,
        "Complex tables, equations, handwriting, vertical text, and low-resolution scans "
        "may need a clearer export. The prototype has not run a controlled learning-outcome "
        "study and does not claim permanent mastery.",
        MARGIN + 18,
        148,
        PAGE_W - 2 * MARGIN - 36,
        "Helvetica",
        9,
        INK,
        12,
    )

    link_button(pdf, "OPEN LIVE AI DEMO", LIVE_URL, MARGIN, 57, 174)
    link_button(pdf, "VIEW SOURCE CODE", REPO_URL, MARGIN + 186, 57, 160)
    rounded_box(pdf, MARGIN + 358, 57, PAGE_W - MARGIN - (MARGIN + 358), 30, PALE_MINT, 9)
    pdf.setFillColor(DEEP_GREEN)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawCentredString(MARGIN + 358 + (PAGE_W - MARGIN - (MARGIN + 358)) / 2, 67.5, "PDF -> PRACTICE -> REVIEW")
    footer(pdf, 4)
    pdf.showPage()


def build() -> Path:
    require_assets()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(OUTPUT), pagesize=A4, pageCompression=1)
    pdf.setTitle("Sparring - Devpost Judge Pack")
    pdf.setAuthor("Sparring")
    pdf.setSubject("Prometheus July AI Challenge project brief")
    cover_page(pdf)
    learner_loop_page(pdf)
    architecture_page(pdf)
    judge_page(pdf)
    pdf.save()
    return OUTPUT


if __name__ == "__main__":
    print(build())
