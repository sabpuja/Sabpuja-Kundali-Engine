#!/usr/bin/env python3
"""Developer self-check for the KUN-B6D-REVIEW-001 wording packet.

Documentation tooling only. It reads b6-wording-draft.json and the packet
Markdown in this folder and checks mechanical properties of the *draft*
wording. It does not review language quality and approves nothing.

Checks:
  1. EN/HI placeholder parity for every key.
  2. Every draft string appears verbatim in REVIEW-PACKET.md (the packet
     shows reviewers exactly the strings in the JSON).
  3. Terminology rules from the packet glossary (G-01 .. G-12).
  4. Banned fear-based, predictive or over-claiming vocabulary.
  5. Character lengths (for the design length budget in DESIGN-INTEGRATION.md).
  6. WCAG contrast of the proposed Foundations colour pairs.

Run: python3 -I check_packet.py   (exit status 0 = all checks pass)
"""
import json
import pathlib
import re
import string
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
DRAFT = json.loads((HERE / "b6-wording-draft.json").read_text(encoding="utf-8"))
PACKET = (HERE / "REVIEW-PACKET.md").read_text(encoding="utf-8")
STRINGS = DRAFT["strings"]

problems = []


def fields(s):
    return sorted({f for _, f, _, _ in string.Formatter().parse(s) if f})


# 1. placeholder parity
for key, v in STRINGS.items():
    if set(v) != {"en", "hi"}:
        problems.append(f"{key}: languages {sorted(v)}")
        continue
    if fields(v["en"]) != fields(v["hi"]):
        problems.append(f"{key}: placeholders EN {fields(v['en'])} != HI {fields(v['hi'])}")

# 2. verbatim presence in the packet
for key, v in STRINGS.items():
    for lang in ("en", "hi"):
        s = v[lang]
        if s.strip() and s not in PACKET:
            problems.append(f"{key}.{lang}: not shown verbatim in REVIEW-PACKET.md")

# 3. terminology rules (Hindi side unless stated)
HI_RULES = [
    ("G-05 Moon is चंद्र (catalog form), not चंद्रमा", r"चंद्रमा"),
    ("G-06 Pada is चरण, never पद/पाद", r"(?<![ऀ-ॿ])(पद|पाद)(?![ऀ-ॿ])"),
    ("G-08 'जन्म समय' without hyphen (catalog form)", r"जन्म-समय"),
    ("G-03 Navamsa is नवांश (not नवमांश)", r"नवमांश"),
    ("G-11 no अंश for 'item/part' (means degree in Jyotish)", r"(?<![ऀ-ॿ])अंश(?![ऀ-ॿ])"),
    ("G-10 no Gandanta framing", r"गंड"),
]
EN_RULES = [
    ("G-01 Lagna, not Ascendant, in customer notes", r"\bAscendant\b"),
    ("G-05 Moon, not Chandra, in English notes", r"\bChandra\b"),
    ("G-10 no Gandanta framing", r"(?i)gand"),
]
for key, v in STRINGS.items():
    for label, rx in HI_RULES:
        if re.search(rx, v["hi"]):
            problems.append(f"{key}.hi: {label}")
    for label, rx in EN_RULES:
        if re.search(rx, v["en"]):
            problems.append(f"{key}.en: {label}")

# 4. banned vocabulary (tone and claims)
BANNED_EN = r"(?i)\b(dosha|inauspicious|auspicious|danger|dangerous|unlucky|warning|beware|risk|error|mistake|incorrect|inaccurate|certified|certify|guarantee\w*|precise|exactly correct|rectif\w*|remed\w*|predict\w*)\b"
BANNED_HI = r"(दोष|अशुभ|शुभ|खतरा|ख़तरा|चेतावनी|अनिष्ट|त्रुटि|ग़लती|गलती|प्रमाणित|गारंटी|उपाय|भविष्यवाणी|शोधन)"
for key, v in STRINGS.items():
    m = re.search(BANNED_EN, v["en"])
    if m:
        problems.append(f"{key}.en: banned term {m.group(0)!r}")
    m = re.search(BANNED_HI, v["hi"])
    if m:
        problems.append(f"{key}.hi: banned term {m.group(0)!r}")

# 5. lengths (grapheme-ish: count code points excluding combining marks)
def visible_len(s):
    return sum(1 for ch in s if not unicodedata.category(ch).startswith("M"))


print("== Length table (code points / visible characters)")
print(f"{'key':34} {'EN':>5} {'HI':>5} {'HI vis':>6} {'HI/EN':>6}")
for key, v in STRINGS.items():
    en, hi = len(v["en"]), len(v["hi"])
    ratio = (hi / en) if en else 0
    print(f"{key:34} {en:5} {hi:5} {visible_len(v['hi']):6} {ratio:6.2f}")

# 6. contrast of proposed colour pairs (WCAG 2.x relative luminance)
def lum(hexcol):
    c = [int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


PAIRS = [
    ("Note text: Sacred Brown on Light Cream", "#4E342E", "#FFF8E7", 4.5),
    ("Note text: Deep Brown on Light Cream", "#33241F", "#FFF8E7", 4.5),
    ("Note text: Sacred Brown on Ivory", "#4E342E", "#FFFBEF", 4.5),
    ("Label: Saffron 700 on Light Cream", "#C84700", "#FFF8E7", 4.5),
    ("Label: Saffron on Light Cream (not used for text)", "#D35400", "#FFF8E7", 4.5),
    ("Rule: Temple Gold on Light Cream (non-text, 3:1)", "#F4B400", "#FFF8E7", 3.0),
    ("Rule: Saffron on Light Cream (non-text, 3:1)", "#D35400", "#FFF8E7", 3.0),
]
print("\n== Contrast (WCAG 2.x)")
for label, fg, bg, need in PAIRS:
    r = contrast(fg, bg)
    verdict = "meets" if r >= need else "BELOW"
    print(f"{label:52} {fg} on {bg}: {r:5.2f}:1 ({verdict} {need}:1)")

print(f"\n== {len(STRINGS)} keys checked")
if problems:
    print("PROBLEMS:")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("All mechanical checks pass. (This is not a language or Jyotish review.)")
