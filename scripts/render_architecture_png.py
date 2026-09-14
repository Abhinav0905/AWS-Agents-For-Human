"""Render docs/img/architecture.png with Pillow (same layout as docs/img/architecture.svg). No browser needed."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

S = 2  # scale: 680x560 design -> 1360x1120 px
OUT = Path(__file__).resolve().parents[1] / "docs" / "img" / "architecture.png"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

INK, MUTED, RULE = "#2c2c2a", "#5f5e5a", "#b4b2a9"
TEAL = ("#e1f5ee", "#0f6e56", "#085041")
CORAL = ("#faece7", "#993c1d", "#712b13")
NEUTRAL = ("#f7f6f2", "#b4b2a9", "#2c2c2a")


def f(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_B if bold else FONT, size * S)
    except OSError:
        return ImageFont.load_default()


def box(d: ImageDraw.ImageDraw, x, y, w, h, title, sub, colors, r=8):
    fill, stroke, text = colors
    d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=r * S, fill=fill, outline=stroke, width=1)
    d.text(((x + w / 2) * S, (y + 18) * S), title, font=f(13, True), fill=text, anchor="mm")
    d.text(((x + w / 2) * S, (y + 38) * S), sub, font=f(11), fill=stroke if colors is not NEUTRAL else MUTED, anchor="mm")


def arrow(d, x1, y1, x2, y2, both=False):
    d.line([x1 * S, y1 * S, x2 * S, y2 * S], fill=MUTED, width=max(1, S))
    def head(px, py, dx, dy):
        n = (dx * dx + dy * dy) ** 0.5 or 1
        ux, uy = dx / n, dy / n
        L, W = 7 * S, 4 * S
        base = (px * S - ux * L, py * S - uy * L)
        d.polygon([(px * S, py * S), (base[0] + uy * W, base[1] - ux * W), (base[0] - uy * W, base[1] + ux * W)], fill=MUTED)
    head(x2, y2, x2 - x1, y2 - y1)
    if both:
        head(x1, y1, x1 - x2, y1 - y2)


def main() -> None:
    img = Image.new("RGB", (680 * S, 560 * S), "white")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([220 * S, 40 * S, 460 * S, 512 * S], radius=20 * S, fill="#fbfaf7", outline=RULE, width=1)
    d.text((340 * S, 62 * S), "Postscript on AgentCore", font=f(14, True), fill=INK, anchor="mm")
    d.text((340 * S, 80 * S), "Strands Agents SDK", font=f(11), fill=MUTED, anchor="mm")
    box(d, 240, 100, 200, 56, "Intake agent", "Mail to ledger entries", TEAL)
    box(d, 240, 184, 200, 56, "Runner agent", "One task per tick", TEAL)
    box(d, 240, 268, 200, 56, "Interruption governor", "Cedar via Interventions", TEAL)
    box(d, 240, 352, 200, 56, "Receipt hooks", "Hash-chained tool calls", TEAL)
    box(d, 240, 436, 200, 56, "Stores", "Ledger in S3, AgentCore Memory", NEUTRAL)
    for y1, y2 in ((156, 182), (240, 266), (324, 350)):
        arrow(d, 340, y1, 340, y2)
    d.rounded_rectangle([40 * S, 236 * S, 196 * S, 426 * S], radius=12 * S, outline=RULE, width=1)
    d.text((118 * S, 254 * S), "Executor (human)", font=f(13, True), fill=INK, anchor="mm")
    box(d, 48, 268, 140, 56, "Decision inbox", "Web and SMS", CORAL)
    box(d, 48, 352, 140, 56, "Accounting PDF", "Verified receipts", CORAL)
    box(d, 490, 100, 150, 56, "Estate mail", "Scans, PDFs, emails", NEUTRAL)
    box(d, 490, 184, 150, 56, "EventBridge tick", "Runs daily", NEUTRAL)
    box(d, 490, 268, 150, 56, "Institutions", "Simulated via MCP", NEUTRAL)
    arrow(d, 490, 128, 442, 128)
    arrow(d, 490, 212, 442, 212)
    arrow(d, 442, 296, 488, 296, both=True)
    arrow(d, 238, 296, 190, 296)
    arrow(d, 238, 380, 190, 380)
    d.rounded_rectangle([220 * S, 522 * S, 232 * S, 534 * S], radius=2 * S, fill=TEAL[0], outline=TEAL[1])
    d.text((240 * S, 528 * S), "Agents on AgentCore", font=f(11), fill=MUTED, anchor="lm")
    d.rounded_rectangle([380 * S, 522 * S, 392 * S, 534 * S], radius=2 * S, fill=CORAL[0], outline=CORAL[1])
    d.text((400 * S, 528 * S), "What the executor sees", font=f(11), fill=MUTED, anchor="lm")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"wrote {OUT} {img.size}")


if __name__ == "__main__":
    main()
