"""Generate the synthetic Alvarez estate: mail (PDF, PNG scans, emails), inbound messages, ground truth.

Everything is fictional. No SSNs, no full account numbers. Deterministic under POSTSCRIPT_SIM_SEED.
Run: python scripts/make_dataset.py [--out data/estate_alvarez]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from postscript.sim.roster import DISTRACTORS, ESTATE, INBOUND, ROSTER, SIM_START, ground_truth


def doc_text(inst: dict | None, doc: dict) -> list[str]:
    head = [inst["name"] if inst else doc["title"], doc["title"]]
    body = []
    if inst:
        body += ["Account holder: Robert Alvarez", f"Account ending in {doc['account']}", "SSN on file, not stored here"]
    body += doc["lines"]
    if inst:
        body += ["", f"Questions: contact {inst['name']} estate services."]
    return head + body


def render_pdf(path: Path, lines: list[str]) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    y = h - 72
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, y, lines[0])
    y -= 22
    c.setFont("Helvetica", 12)
    c.drawString(72, y, lines[1])
    y -= 30
    c.setFont("Helvetica", 11)
    for line in lines[2:]:
        c.drawString(72, y, line)
        y -= 16
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(72, 40, "Synthetic document generated for the Postscript demo. Not a real institution.")
    c.save()


def render_png(path: Path, lines: list[str], rng: random.Random) -> None:
    img = Image.new("L", (1240, 1600), 245)
    draw = ImageDraw.Draw(img)
    try:
        font_h = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except OSError:
        font_h = font = ImageFont.load_default()
    y = 140
    draw.text((120, y), lines[0], fill=20, font=font_h)
    y += 60
    for line in lines[1:]:
        draw.text((120, y), line, fill=35, font=font)
        y += 40
    draw.text((120, 1500), "Synthetic scan for the Postscript demo.", fill=90, font=font)
    img = img.rotate(rng.uniform(-1.5, 1.5), resample=Image.BICUBIC, fillcolor=245)
    px = img.load()
    for _ in range(4000):
        x, yy = rng.randrange(img.width), rng.randrange(img.height)
        px[x, yy] = max(0, px[x, yy] - rng.randint(20, 90))
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    img.save(path)


def render_eml(path: Path, inst: dict, doc: dict, lines: list[str]) -> None:
    body = "\n".join(lines[2:])
    text = (f"From: {inst['name']} <notices@{inst['id']}.example>\nTo: bob.alvarez@example.com\n"
            f"Subject: {doc['title']}\nDate: Sun, 01 Mar 2026 09:12:00 -0800\n\n{lines[0]}\n{lines[1]}\n\n{body}\n")
    path.write_text(text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/estate_alvarez")
    args = ap.parse_args()
    rng = random.Random(int(os.getenv("POSTSCRIPT_SIM_SEED", "7")))
    out = Path(args.out)
    mail = out / "mail"
    inbound = out / "inbound"
    mail.mkdir(parents=True, exist_ok=True)
    inbound.mkdir(parents=True, exist_ok=True)
    for p in list(mail.iterdir()) + list(inbound.iterdir()):
        p.unlink()

    items: list[tuple[dict | None, dict]] = [(inst, d) for inst in ROSTER for d in inst["documents"]]
    items += [(None, d) for d in DISTRACTORS]
    rng.shuffle(items)
    manifest = []
    for i, (inst, doc) in enumerate(items, start=1):
        lines = doc_text(inst, doc)
        stem = f"mail_{i:03d}"
        if doc["render"] == "pdf":
            path = mail / f"{stem}.pdf"
            render_pdf(path, lines)
        elif doc["render"] == "png":
            path = mail / f"{stem}.png"
            render_png(path, lines, rng)
        else:
            path = mail / f"{stem}.eml"
            render_eml(path, inst, doc, lines)
        manifest.append({"file": path.name, "institution_id": inst["id"] if inst else None,
                         "account_last4": doc.get("account"), "kind": doc["type"]})

    for j, msg in enumerate(INBOUND, start=1):
        p = inbound / f"inbound_{j:02d}_day{msg['day']:02d}.eml"
        p.write_text(f"From: {msg['from']} <daniel.alvarez@example.com>\nTo: maya.alvarez@example.com\n"
                     f"Subject: {msg['subject']}\nX-Sim-Day: {msg['day']}\n\n{msg['body']}\n")

    (out / "estate.json").write_text(json.dumps({**ESTATE, "sim_start": SIM_START}, indent=2))
    (out / "ground_truth.json").write_text(json.dumps({**ground_truth(), "mail_manifest": manifest}, indent=2))
    (out / "README.md").write_text(
        "# Synthetic estate: Robert (Bob) Alvarez\n\n"
        "Everything in this folder is invented for the Postscript demo. The institutions do not exist, the "
        "people do not exist, and no document contains a Social Security number or a full account number.\n\n"
        "- `mail/` is the shoebox: statements, bills, notices and emails as PDFs, PNG 'scans' and .eml files. "
        "File names carry no hints. One item is a flyer; one statement is a duplicate mailing.\n"
        "- `inbound/` holds messages the simulator delivers on specific simulated days (an heir objecting, then agreeing).\n"
        "- `ground_truth.json` lists the institutions, the mail manifest, and the decision events an executor "
        "would have to make. The metrics score the agent against it.\n\n"
        "Regenerate with `python scripts/make_dataset.py`.\n"
    )
    print(f"wrote {len(manifest)} mail items, {len(INBOUND)} inbound messages, ground truth with "
          f"{len(ground_truth()['decision_events'])} decision events -> {out}")


if __name__ == "__main__":
    main()
