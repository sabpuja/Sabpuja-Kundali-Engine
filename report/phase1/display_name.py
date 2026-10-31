"""Optional report name (KUN-UX-NAME-001): one validation rule for the HTTP route and the PDF.

The name is presentation data only. It is validated here, before and separately from the
birth details, and it never reaches the chart request, the engine, the calculation metadata
or any log. This module has no I/O and no dependencies beyond the standard library.

    normalize(value) -> str | None     # None: no name (absent, empty or only spaces)
    DisplayNameError                   # status, code, fixed message; never carries the input

Accepted, after Unicode NFC and trimming outer spaces:
  * Latin letters that every bundled Poppins and Inter weight can draw (A-Z, a-z, the
    Latin-1 letters and most Latin Extended-A, plus Ș ș Ț ț Ə ə), so accents such as
    é, ñ, ü, ā, ī, ū are kept as typed;
  * Devanagari letters, vowel signs, virama, nukta, anusvara, candrabindu and visarga
    that the bundled Poppins Devanagari can draw (no digits, danda or Om sign), and a
    ZWJ or ZWNJ directly after a virama, as used for explicit half forms;
  * single spaces, and the apostrophe (' or ’), hyphen and full stop between or after letters.
Everything else is refused, never dropped or transliterated: control and format
characters (newline, tab, bidi overrides, zero-width space), symbols, digits, markup
characters such as < > & " / : ; = ( ), emoji and other scripts.

Length: at most 80 visible characters. A visible character is any accepted character that
is not a combining sign (Unicode categories Mn, Mc, Me) or a joiner, so a Devanagari
vowel sign or virama does not count but each consonant does. Before any other work the
raw string is bounded to 320 code points.
"""
from __future__ import annotations

import unicodedata

MAX_VISIBLE = 80
MAX_RAW_CODEPOINTS = 320

VIRAMA = 0x094D
ZWNJ, ZWJ = 0x200C, 0x200D
SPACE = 0x20
APOSTROPHES = frozenset({0x27, 0x2019})
HYPHEN = 0x2D
FULL_STOP = 0x2E
SEPARATORS = APOSTROPHES | {HYPHEN, FULL_STOP, SPACE}


def _ranges(*pairs):
    return frozenset(c for lo, hi in pairs for c in range(lo, hi + 1))


# Latin letters drawn by every bundled weight: Inter 400/500/600 and Poppins 500/600/700,
# latin + latin-ext subsets (checked in report/phase1/tests/test_display_name.py).
LATIN = _ranges((0x41, 0x5A), (0x61, 0x7A), (0xC0, 0xD6), (0xD8, 0xF6), (0xF8, 0x107),
                (0x10A, 0x11B), (0x11E, 0x123), (0x128, 0x130), (0x136, 0x137), (0x139, 0x148),
                (0x14C, 0x15B), (0x15E, 0x165), (0x168, 0x17E), (0x18F, 0x18F), (0x218, 0x21B),
                (0x259, 0x259))
# Devanagari letters and signs drawn by Poppins Devanagari 500/600/700 (same test).
DEVANAGARI = _ranges((0x901, 0x903), (0x905, 0x90D), (0x90F, 0x911), (0x913, 0x928),
                     (0x92A, 0x933), (0x935, 0x939), (0x93C, 0x945), (0x947, 0x949),
                     (0x94B, 0x94D), (0x960, 0x963), (0x972, 0x972))
LETTERS = LATIN | DEVANAGARI
ALLOWED = LETTERS | SEPARATORS | {ZWJ, ZWNJ}

# Outer characters removed by the trim: spaces only (controls are refused, not trimmed).
# Every Unicode space separator (category Zs), as listed in Unicode 15.
_TRIM = ' \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f\u3000'


class DisplayNameError(ValueError):
    """A refused name. The message is fixed and never contains the submitted text."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(code)
        self.status, self.code, self.message = status, code, message


def _invalid():
    return DisplayNameError(422, 'DISPLAY_NAME_INVALID',
                            'the name for the report may use letters (English or Hindi), single spaces, '
                            'apostrophes, hyphens and full stops')


def is_mark(cp: int) -> bool:
    return unicodedata.category(chr(cp)) in ('Mn', 'Mc', 'Me')


def is_devanagari(cp: int) -> bool:
    return 0x0900 <= cp <= 0x097F


def visible_length(text: str) -> int:
    """Visible characters: everything except combining signs and joiners."""
    return sum(1 for ch in text if not is_mark(ord(ch)) and ord(ch) not in (ZWJ, ZWNJ))


def normalize(value: object) -> str | None:
    """The validated name to display, or None for no name. Raises DisplayNameError."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise DisplayNameError(400, 'REQUEST_INVALID', 'display_name must be a string')
    if len(value) > MAX_RAW_CODEPOINTS:
        raise DisplayNameError(422, 'DISPLAY_NAME_TOO_LONG', 'the name for the report can be at most 80 characters')
    # Controls, line breaks, bidi and other format characters are refused anywhere,
    # including at the ends, so they can never be trimmed away silently.
    for ch in value:
        cat = unicodedata.category(ch)
        if cat in ('Cc', 'Cs', 'Co', 'Cn', 'Zl', 'Zp') or (cat == 'Cf' and ord(ch) not in (ZWJ, ZWNJ)):
            raise _invalid()
    text = unicodedata.normalize('NFC', value).strip(_TRIM)
    if not text:
        return None
    if visible_length(text) > MAX_VISIBLE:
        raise DisplayNameError(422, 'DISPLAY_NAME_TOO_LONG', 'the name for the report can be at most 80 characters')
    cps = [ord(ch) for ch in text]
    if any(cp not in ALLOWED for cp in cps) or cps[0] not in LETTERS:
        raise _invalid()
    for i, cp in enumerate(cps):
        prev = cps[i - 1] if i else None
        nxt = cps[i + 1] if i + 1 < len(cps) else None
        if is_mark(cp):
            # Devanagari signs only, and only on a Devanagari letter or sign.
            if not (is_devanagari(cp) and prev is not None and is_devanagari(prev)):
                raise _invalid()
        elif cp in (ZWJ, ZWNJ):
            if prev != VIRAMA or nxt is None or not (is_devanagari(nxt) and not is_mark(nxt)):
                raise _invalid()
        elif cp == SPACE:
            if prev == SPACE:
                raise _invalid()
        elif cp in APOSTROPHES or cp == HYPHEN:
            # Between letters: O'Brien, D’Souza, Mary-Jane.
            if prev is None or prev in SEPARATORS or nxt is None or nxt in SEPARATORS:
                raise _invalid()
        elif cp == FULL_STOP:
            # After a letter, then a space or the end: "R. K. Sharma", "Jr."
            if prev is None or prev in SEPARATORS or nxt not in (None, SPACE):
                raise _invalid()
    return text
