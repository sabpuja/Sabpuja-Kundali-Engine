"""Private visual review package for the Phase 2A report (synthetic scenarios only).

Renders every page of real generator output and writes, to an output directory outside Git:
complete sample PDFs, all-page contact sheets, old/new comparisons against the Phase 1
renderer, a palette A/B comparison, high-resolution chart previews and a page-metrics table.

    python report/phase1/tools/visual_review.py OUT_DIR [--case s11-afternoon]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

import fitz
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

PHASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PHASE))
import generate_report as phase1  # noqa: E402
import premium_report as premium  # noqa: E402

FIXTURES = PHASE / 'tests/fixtures/premium'
INK, PAPER, RULE = (47, 41, 38), (255, 255, 255), (210, 200, 190)


def font(size, weight='600'):
    t = TTFont(str(premium.FONT_DIR / f'inter-latin-{weight}-normal.woff2'))
    t.flavor = None
    buf = io.BytesIO()
    t.save(buf)
    buf.seek(0)
    return ImageFont.truetype(buf, size)


def pages(pdf_bytes, dpi):
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    out = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        out.append(Image.frombytes('RGB', (pix.width, pix.height), pix.samples))
    return out


def framed(images, labels, title, cols=None, gap=28, pad=40):
    cols = cols or len(images)
    w, h = images[0].size
    rows = (len(images) + cols - 1) // cols
    head = 70
    sheet = Image.new('RGB', (pad * 2 + cols * w + (cols - 1) * gap, head + pad + rows * (h + 44) + (rows - 1) * gap), PAPER)
    draw = ImageDraw.Draw(sheet)
    draw.text((pad, 24), title, fill=INK, font=font(26))
    for i, (im, label) in enumerate(zip(images, labels)):
        x = pad + (i % cols) * (w + gap)
        y = head + (i // cols) * (h + 44 + gap)
        draw.text((x, y), label, fill=INK, font=font(17, '500'))
        sheet.paste(im, (x, y + 30))
        draw.rectangle([x - 1, y + 29, x + w, y + 30 + h], outline=RULE)
    return sheet


def page_metrics(pdf_bytes):
    """Per page: smallest text, text extent, and the largest empty vertical band in the content area."""
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    rows = []
    for number, page in enumerate(doc, 1):
        sizes, boxes = [], []
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                for span in line['spans']:
                    if span['text'].strip():
                        sizes.append(span['size'])
                        boxes.append(fitz.Rect(span['bbox']))
        for d in page.get_drawings():
            r = d['rect']
            if r.width < page.rect.width * 0.95:  # ignore full-page backgrounds
                boxes.append(r)
        top, bottom = 80, page.rect.height - 60
        covered = sorted((max(b.y0, top), min(b.y1, bottom)) for b in boxes if b.y1 > top and b.y0 < bottom)
        gap, cursor = 0.0, top
        for y0, y1 in covered:
            gap = max(gap, y0 - cursor)
            cursor = max(cursor, y1)
        gap = max(gap, bottom - cursor)
        rows.append({'page': number, 'min_text_pt': round(min(sizes), 2), 'spans': len(sizes),
                     'largest_empty_band_pt': round(gap, 1),
                     'largest_empty_band_pct': round(100 * gap / (bottom - top), 1)})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--case', default='s11-afternoon')
    args = ap.parse_args()
    out = Path(args.out)
    for sub in ('pdf/candidate', 'pdf/baseline', 'pdf/phase1', 'contact', 'compare', 'charts'):
        (out / sub).mkdir(parents=True, exist_ok=True)
    manifest = json.loads((FIXTURES / 'manifest.json').read_text())
    checksums, metrics = {}, {}
    for case in manifest['cases']:
        data = json.loads((FIXTURES / f'{case["id"]}.json').read_text())
        for pal, folder in (('od10-candidate', 'candidate'), ('baseline', 'baseline')):
            pdf = premium.generate(data, synthetic=True, palette=pal)
            path = out / 'pdf' / folder / f'{case["id"]}-{folder}.pdf'
            path.write_bytes(pdf)
            checksums[str(path.relative_to(out))] = hashlib.sha256(pdf).hexdigest()
            metrics[f'{case["id"]}/{folder}'] = page_metrics(pdf)
    data = json.loads((FIXTURES / f'{args.case}.json').read_text())
    new = premium.generate(data, synthetic=True, palette='od10-candidate')
    base = premium.generate(data, synthetic=True, palette='baseline')
    old = phase1.generate(data, synthetic=True)
    (out / 'pdf/phase1' / f'{args.case}-phase1.pdf').write_bytes(old)
    checksums[f'pdf/phase1/{args.case}-phase1.pdf'] = hashlib.sha256(old).hexdigest()
    metrics[f'{args.case}/phase1'] = page_metrics(old)
    for name, pdf in (('candidate', new), ('baseline', base)):
        imgs = pages(pdf, 60)
        framed(imgs, [f'{i + 1}. {t}' for i, (_, t, _) in enumerate(premium.PAGES)],
               f'Phase 2A premium report, all pages ({name} palette, synthetic {args.case})', cols=5) \
            .save(out / 'contact' / f'contact-sheet-{name}.png')
    old_imgs = pages(old, 60)
    framed(old_imgs, [f'{i + 1}' for i in range(len(old_imgs))], 'Phase 1 baseline report, all pages', cols=4) \
        .save(out / 'contact' / 'contact-sheet-phase1.png')
    oi, ni, bi = pages(old, 90), pages(new, 90), pages(base, 90)
    P = premium.PAGE_OF
    pairs = [('cover', [oi[0], ni[0]], ['Phase 1 cover', 'Phase 2A cover']),
             ('d1-chart', [oi[2], ni[P['d1'] - 1]], ['Phase 1 D1', 'Phase 2A D1']),
             ('d9-chart', [oi[3], ni[P['d9'] - 1]], ['Phase 1 D9', 'Phase 2A D9']),
             ('planetary-table', [oi[4], ni[P['positions'] - 1]], ['Phase 1 positions', 'Phase 2A positions']),
             ('d9-table', [oi[5], ni[P['navamsa'] - 1]], ['Phase 1 D9 placements', 'Phase 2A Navamsa placements']),
             ('house-directory', [oi[6], ni[P['houses'] - 1]], ['Phase 1 houses', 'Phase 2A house directory']),
             ('methodology', [oi[7], ni[P['method'] - 1]], ['Phase 1 methodology', 'Phase 2A methodology'])]
    for name, imgs, labels in pairs:
        framed(imgs, labels, f'Old / new: {name.replace("-", " ")}').save(out / 'compare' / f'old-new-{name}.png')
    picks = [0, P['d1'] - 1, P['positions'] - 1, P['houses'] - 1]
    framed([bi[i] for i in picks] + [ni[i] for i in picks],
           [f'A baseline: {premium.PAGES[i][1]}' for i in picks] + [f'B OD-10 candidate: {premium.PAGES[i][1]}' for i in picks],
           'Palette A/B: existing tokens (A) vs proposed maroon / ivory / gold (B, not approved)', cols=4) \
        .save(out / 'compare' / 'palette-a-b.png')
    for name, pdf in (('candidate', new), ('baseline', base)):
        doc = fitz.open(stream=pdf, filetype='pdf')
        for key in ('d1', 'd9'):
            doc[P[key] - 1].get_pixmap(dpi=220, clip=fitz.Rect(70, 150, premium.W - 70, 640)) \
                .save(str(out / 'charts' / f'{key}-chart-{name}-220dpi.png'))
    (out / 'checksums.json').write_text(json.dumps(checksums, indent=1) + '\n')
    (out / 'page-metrics.json').write_text(json.dumps(metrics, indent=1) + '\n')
    print(json.dumps({'pdfs': len(checksums), 'case': args.case}))


if __name__ == '__main__':
    main()
