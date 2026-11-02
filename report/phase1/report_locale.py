"""Report language (KUN-I18N-001): the one lookup from catalog keys and engine values to display text.

Two catalogs, both JSON and both read-only:

* ``report_i18n.json`` (this directory): every sentence, label and heading of the ten-page
  premium report, English and Hindi side by side. The English values are the exact strings of
  the PR #58 renderer, so the English PDF stays byte-identical.
* ``prototype/kundali_prototype/static/i18n.json``: the terminology register shared with the
  web interface (Rashis, grahas, Nakshatras, months, places, translations of fixed engine
  sentences). The report and the page therefore use the same Hindi term for the same thing.

Locale is presentation only. Nothing here reads or changes a calculated value: engine values
(Rashi names, Nakshatra names, place ids, metadata sentences) are looked up and replaced by
their Hindi display form, and a value the register does not know raises ReportDataError
instead of being shown in English or guessed.
"""
from __future__ import annotations

import json
import re
import string
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
REPORT_CATALOG_PATH = ROOT / 'report_i18n.json'
TERMS_PATH = REPO / 'prototype/kundali_prototype/static/i18n.json'
LOCALES = ('en', 'hi')
DEFAULT_LOCALE = 'en'


class ReportLocaleError(ValueError):
    """Unsupported locale or a value the terminology register cannot display. Never rendered."""


def _load(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    return data


REPORT_CATALOG = _load(REPORT_CATALOG_PATH)
REGISTER = _load(TERMS_PATH)
STRINGS = REPORT_CATALOG['strings']
TERMS = REGISTER['terms']
ENGINE_TEXT = REGISTER['engine_text']


def placeholders(template: str) -> set[str]:
    return {field for _, field, _, _ in string.Formatter().parse(template) if field}


def check_catalogs() -> list[str]:
    """Consistency problems in both catalogs (empty when sound); used by tests and at import."""
    problems = []
    for key, entry in STRINGS.items():
        if set(entry) != set(LOCALES):
            problems.append(f'{key}: locales {sorted(entry)}')
            continue
        if placeholders(entry['en']) != placeholders(entry['hi']):
            problems.append(f'{key}: placeholders differ')
    for section in (STRINGS, REGISTER['ui'], ENGINE_TEXT):
        for key, entry in section.items():
            for loc, text in entry.items():
                if isinstance(text, str) and unicodedata.normalize('NFC', text) != text:
                    problems.append(f'{key}/{loc}: not NFC')
    return problems


_PROBLEMS = check_catalogs()
if _PROBLEMS:
    raise RuntimeError('report language catalog inconsistent: ' + '; '.join(_PROBLEMS[:5]))


def validate_locale(value) -> str:
    if value not in LOCALES:
        raise ReportLocaleError('Unsupported report locale')
    return value


class Translator:
    """Display text for one locale. For 'en' every engine value is returned unchanged."""

    def __init__(self, locale: str = DEFAULT_LOCALE):
        self.locale = validate_locale(locale)
        self.hindi = self.locale == 'hi'

    def t(self, key: str, **values) -> str:
        entry = STRINGS.get(key)
        if entry is None:
            raise ReportLocaleError(f'Missing report string {key}')
        return entry[self.locale].format(**values)

    # -- Terminology register ------------------------------------------------------------
    def rashi(self, name: str) -> str:
        entry = TERMS['rashi'].get(name)
        if entry is None:
            raise ReportLocaleError('Unknown Rashi')
        return entry[self.locale]

    def graha(self, key: str) -> tuple[str, str]:
        entry = TERMS['graha'].get(key)
        if entry is None:
            raise ReportLocaleError('Unknown graha')
        return entry[self.locale], entry[self.locale + '_abbr']

    def lagna(self) -> tuple[str, str]:
        entry = TERMS['lagna']
        return entry[self.locale], entry[self.locale + '_abbr']

    def nakshatra(self, name: str) -> str:
        if not self.hindi:
            return name
        value = TERMS['nakshatra'].get(name)
        if value is None:
            raise ReportLocaleError('Unknown Nakshatra')
        return value

    def month(self, index: int) -> str:
        return TERMS['month'][self.locale][index]

    def hemisphere(self, letter: str) -> str:
        return TERMS['hemisphere'][self.locale][letter]

    def ayanamsa(self, name: str) -> str:
        entry = TERMS['ayanamsa'].get(name)
        if entry is None:
            if not self.hindi:
                return name
            raise ReportLocaleError('Unknown ayanamsa')
        return entry[self.locale]

    def place(self, place: dict) -> tuple[str, str, str]:
        """(name, region, country). Hindi only for a catalogued place id whose English
        fields are exactly the catalogued ones; anything else raises in Hindi."""
        english = (place['name'], place['region'], place['country'])
        if not self.hindi:
            return english
        entry = TERMS['place'].get(place.get('id'))
        if entry is None or tuple(entry['en']) != english:
            raise ReportLocaleError('Birthplace has no Hindi name in the terminology register')
        return tuple(entry['hi'])

    def place_source(self, text: str) -> str:
        if not self.hindi:
            return text
        rule = TERMS['place_source']
        match = re.match(rule['pattern'], text)
        if match is None:
            raise ReportLocaleError('Place source text has no Hindi form')
        return rule['hi'].replace('{1}', match.group(1)).replace('{2}', match.group(2))

    def engine_text(self, key: str, value: str) -> str:
        """A fixed engine sentence (metadata). Hindi only when the engine sent exactly the
        catalogued English sentence, so a changed engine text can never be mistranslated."""
        if not self.hindi:
            return value
        entry = ENGINE_TEXT.get(key)
        if entry is None or entry['en'] != value:
            raise ReportLocaleError('Engine text has no reviewed Hindi form')
        return entry['hi']
