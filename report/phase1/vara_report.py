"""Sunrise and Vara page of the extended premium Kundali PDF (KUN-PAN-RPT-002, issue #83).

Display only. The page shows one validated `sabpuja-panchanga-vara/1` document, produced by
src/sabpuja_kundali/panchanga/vara.py from the QA-accepted sunrise module (convention SUN-D-IMD-47 at
the birthplace, PAN-D03 adopted for development only). This module never calls the engine.

It is drawn only in the separate opt-in edition `extended-panchanga-m2-vara/1`:

    premium_report.generate_extended(response, panchanga, ..., vara=doc)

which is the 13-page Panchanga edition plus this one page after "Transition times". Without `vara`
the ten-page report and the 13-page edition are unchanged byte for byte.

Before anything is drawn the document is checked against the chart response: same birth instant,
zone and birthplace coordinates, the same Swiss Ephemeris, ephemeris files and timezone data, the
pinned method block, the civil date and weekday of the birth instant, the Vara weekday of its governing
sunrise date, the order governing sunrise <= birth < next sunrise, every local time against its UTC
instant in the pinned zone, and the near-sunrise flag recomputed from the microsecond instants. Any
disagreement raises VaraReportError; nothing is recalculated or guessed.

Shown values: minute-rounded times marked "about" (UTC rounded half up once, the same instant converted
to the zone, as panchanga_report.display_instant), the time from the governing sunrise or to the next
one in hours and minutes, and drawing positions. An unavailable Vara is shown as not given, with the
typed reason, and the civil weekday alone.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
try:
    from . import premium_report as pr
    from . import premium_layout as layout
    from . import report_locale as loc
except ImportError:  # loaded by path or run as a script
    sys.path.insert(0, str(ROOT))
    import premium_report as pr
    import premium_layout as layout
    import report_locale as loc

CATALOG_PATH = ROOT / 'report_vara_i18n.json'
CATALOG = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
STRINGS = CATALOG['strings']

SCHEMA = 'sabpuja-panchanga-vara/1'
STATUS = 'DEVELOPMENT_PREVIEW_NOT_FOR_CUSTOMERS'
CLAIM_BOUNDARY = ("Development output for independent QA only. Not customer-facing. Sunrise and sunset are "
                  "calculated for the birthplace with a sea-level, level-horizon, geocentric model under the "
                  "IMD 47' definition; they do not establish when the Sun was actually visible. Times are "
                  "approximate to the minute. Published USNO and IMD times agree within a coarse 120 s "
                  "screen, which is not an accuracy claim, and IMD's four-city tables are not reproduced by "
                  "one depression angle.")
# SHA-256 of the canonical JSON of vara.METHOD (sorted keys, no spaces). Pinned by the tests; a document
# from another method revision or convention is refused, never shown.
METHOD_SHA256 = 'fc0d5a682df2d93c27eb20c720b60e3c7574084462d782ed201f9d50b17def5f'
EDITION = 'extended-panchanga-m2-vara/1'
PAGE_KEY = 'sunrise'
NEAR_SECONDS = 300
MICROS = 1_000_000
LOCAL_FIRST, LOCAL_LAST = date(1970, 1, 1), date(2100, 12, 31)   # D13-A, as the sun module
VARA_IDS = ('ravivara', 'somavara', 'mangalavara', 'budhavara', 'guruvara', 'shukravara', 'shanivara')
CIVIL_IDS = ('sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday')
UNDEFINED = 'PANCHANGA_SUNRISE_UNDEFINED'
OUTSIDE = 'PANCHANGA_SUNRISE_OUTSIDE_ENVELOPE'
# Typed reasons the page can explain; anything else is refused.
VARA_CONDITIONS = {
    UNDEFINED: ('SUN_ABOVE_DEPRESSION_ALL_DAY', 'SUN_BELOW_DEPRESSION_ALL_DAY', 'NO_SUNRISE_ON_LOCAL_DATE',
                'VARA_DAY_END_UNDEFINED'),
    OUTSIDE: ('GOVERNING_SUNRISE_BEFORE_1970_01_01', 'BIRTH_LOCAL_DATE_OUTSIDE_D13_A'),
}
NO_SUNSET = 'NO_SUNSET_WITHIN_24_HOURS_OF_SUNRISE'
NEXT_OUTSIDE = 'NEXT_SUNRISE_OUTSIDE_ENVELOPE'
DAY_END = 'VARA_DAY_END_UNDEFINED'
UTC_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
DISPLAY_ROUNDING = timedelta(seconds=30)
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class VaraReportError(ValueError):
    """The Vara document cannot be shown with this chart. Fixed text; never birth data."""


def _refuse(reason):
    raise VaraReportError('Vara document refused: ' + reason)


def check_catalog() -> list[str]:
    problems = []
    for key, entry in STRINGS.items():
        if set(entry) != set(loc.LOCALES):
            problems.append(f'{key}: locales')
        elif loc.placeholders(entry['en']) != loc.placeholders(entry['hi']):
            problems.append(f'{key}: placeholders differ')
    for vid in VARA_IDS:
        if f'vara.{vid}' not in STRINGS:
            problems.append(f'vara.{vid}: missing')
    for cid in CIVIL_IDS:
        if f'civil.{cid}' not in STRINGS:
            problems.append(f'civil.{cid}: missing')
    for conditions in VARA_CONDITIONS.values():
        for condition in conditions:
            if f'v.na.{condition}' not in STRINGS:
                problems.append(f'v.na.{condition}: missing')
    return problems


if check_catalog():
    raise RuntimeError('Vara report catalog inconsistent')


def canonical_sha256(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def _dt(t_us):
    return _EPOCH + timedelta(microseconds=t_us)


def _us(moment):
    delta = moment - _EPOCH
    return (delta.days * 86400 + delta.seconds) * MICROS + delta.microseconds


def _weekday_index(day: date) -> int:
    """0 = Sunday ... 6 = Saturday, as the engine ids."""
    return (day.weekday() + 1) % 7


def near_sunrise(birth_us: int, governing_us: int, next_us: int | None) -> dict:
    """The near-sunrise record the document must carry (the vara.py rule, restated independently)."""
    window = NEAR_SECONDS * MICROS
    after = birth_us - governing_us
    before = None if next_us is None else next_us - birth_us
    near = after <= window or (before is not None and before <= window)
    out = {'status': 'assessed' if before is not None or near else 'partial', 'window_seconds': NEAR_SECONDS,
           'after_governing_sunrise_us': after, 'before_next_sunrise_us': before, 'near_sunrise': near,
           'nearest': None if not near else ('governing' if before is None or after <= before else 'next')}
    if out['status'] == 'partial':
        out['reason'] = NEXT_OUTSIDE
    return out


# ---------------------------------------------------------------------------
# Validation of the document against the chart response.

def _event(value, zone):
    """utc_us of one available event, with its whole-second UTC and local fields checked."""
    if not isinstance(value, dict) or set(value) != {'status', 'utc_us', 'utc', 'local', 'local_date'}:
        _refuse('event fields')
    if value['status'] != 'available' or type(value['utc_us']) is not int:
        _refuse('event status or instant')
    t = value['utc_us']
    utc = _dt(t)
    second = utc.replace(microsecond=0) + (timedelta(seconds=1) if utc.microsecond >= 500_000 else timedelta(0))
    if value['utc'] != second.strftime('%Y-%m-%dT%H:%M:%SZ'):
        _refuse('event UTC is not its instant')
    local = second.astimezone(zone)
    if value['local'] != local.isoformat() or value['local_date'] != local.date().isoformat():
        _refuse('event local time is not the UTC instant in the birth zone')
    return t


def _unavailable(value, reasons):
    if not isinstance(value, dict) or set(value) != {'status', 'reason', 'condition'} \
            or value['status'] != 'unavailable':
        _refuse('unavailable fields')
    if (value['reason'], value['condition']) not in reasons:
        _refuse('unsupported unavailable reason')
    return value


def _get_zone(key):
    try:
        from sabpuja_kundali.timezones import get_zone
    except ImportError:
        sys.path.insert(0, str(pr.REPO / 'src'))
        from sabpuja_kundali.timezones import get_zone
    return get_zone(key)


def validate(response, doc):
    """The checked values the page displays. Raises VaraReportError on any disagreement."""
    if not isinstance(doc, dict):
        _refuse('not a document')
    keys = {'schema', 'status', 'claim_boundary', 'method', 'birth', 'civil', 'vara',
            'vara_differs_from_civil_weekday', 'governing_sunrise', 'sunset', 'next_sunrise', 'boundary',
            'provenance'}
    if set(doc) != keys:
        _refuse('unexpected or missing fields')
    if doc['schema'] != SCHEMA:
        _refuse('unsupported schema')
    if doc['status'] != STATUS:
        _refuse('unsupported status')
    if doc['claim_boundary'] != CLAIM_BOUNDARY:
        _refuse('claim boundary differs')
    if not isinstance(doc['method'], dict) or canonical_sha256(doc['method']) != METHOD_SHA256:
        _refuse('method differs from the adopted method')
    chart, info = response['chart'], response['input']
    birth, place = chart['birth'], info['place']
    b = doc['birth']
    if not isinstance(b, dict) or set(b) != {'utc', 'timezone', 'latitude', 'longitude'}:
        _refuse('birth fields')
    if b['utc'] != birth['utc'] or b['timezone'] != birth['timezone'] or place.get('timezone') != birth['timezone']:
        _refuse('birth instant or zone differs from the chart')
    for key in ('latitude', 'longitude'):
        if type(b[key]) not in (int, float) or type(place.get(key)) not in (int, float) or b[key] != place[key]:
            _refuse('birthplace differs from the chart')
    # Provenance: the same Swiss Ephemeris, ephemeris files and timezone data as the chart.
    meta = chart['calculation_metadata']
    prov = doc['provenance']
    expected_prov = {'swiss_ephemeris', 'ephemeris_manifest_sha256', 'timezone_data', 'swiss_calls',
                     'chart_schema_version_unchanged', 'calculation_metadata_schema_unchanged'}
    if not isinstance(prov, dict) or set(prov) != expected_prov:
        _refuse('provenance fields')
    if prov['swiss_ephemeris'] != meta['swiss_ephemeris']:
        _refuse('Swiss Ephemeris differs from the chart')
    if prov['ephemeris_manifest_sha256'] != meta['ephemeris_data'].get('manifest_sha256') \
            or meta['ephemeris_data'].get('verified_before_calculation') is not True:
        _refuse('ephemeris data differs from the chart')
    tz = meta['timezone_data']
    if prov['timezone_data'] != {k: tz.get(k) for k in ('package_version', 'iana_version', 'manifest_sha256')}:
        _refuse('timezone data differs from the chart')
    if (prov['chart_schema_version_unchanged'] != chart['schema_version']
            or prov['calculation_metadata_schema_unchanged'] != meta['metadata_schema']):
        _refuse('chart schema differs')
    if type(prov['swiss_calls']) is not int or not 1 <= prov['swiss_calls'] <= 100_000:
        _refuse('field out of range')

    zone = _get_zone(birth['timezone'])
    if not isinstance(birth['utc'], str) or not UTC_PATTERN.match(birth['utc']):
        _refuse('birth instant is not a whole-second UTC timestamp')
    t0 = datetime.strptime(birth['utc'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    birth_us = _us(t0)
    civil_day = t0.astimezone(zone).date()
    civil = doc['civil']
    if civil != {'date': civil_day.isoformat(), 'weekday': CIVIL_IDS[_weekday_index(civil_day)]}:
        _refuse('civil date or weekday is not the birth instant in the birth zone')

    vara = doc['vara']
    out = {'birth_us': birth_us, 'birth_local': t0.astimezone(zone), 'zone': zone, 'zone_name': birth['timezone'],
           'civil_date': civil_day, 'civil_weekday': civil['weekday'], 'provenance': prov}
    if isinstance(vara, dict) and vara.get('status') == 'available':
        if set(vara) != {'status', 'vara_id', 'sunrise_local_date'}:
            _refuse('vara fields')
        g = _event(doc['governing_sunrise'], zone)
        gdate = doc['governing_sunrise']['local_date']
        if vara['sunrise_local_date'] != gdate:
            _refuse('vara date is not the governing sunrise date')
        gday = date.fromisoformat(gdate)
        if vara['vara_id'] != VARA_IDS[_weekday_index(gday)]:
            _refuse('vara is not the weekday of its sunrise date')
        if gday not in (civil_day, civil_day - timedelta(days=1)) or not g <= birth_us:
            _refuse('governing sunrise does not precede the birth')
        if doc['vara_differs_from_civil_weekday'] is not (VARA_IDS.index(vara['vara_id'])
                                                          != CIVIL_IDS.index(civil['weekday'])):
            _refuse('civil weekday comparison wrong')
        sunset = doc['sunset']
        if isinstance(sunset, dict) and sunset.get('status') == 'available':
            s = _event(sunset, zone)
            if not g < s < g + 86400 * MICROS:
                _refuse('sunset is not within 24 hours after the governing sunrise')
        else:
            _unavailable(sunset, {(UNDEFINED, NO_SUNSET)})
            s = None
        nxt = doc['next_sunrise']
        if isinstance(nxt, dict) and nxt.get('status') == 'available':
            n = _event(nxt, zone)
            if nxt['local_date'] != (gday + timedelta(days=1)).isoformat() or not birth_us < n:
                _refuse('next sunrise is not the sunrise after the governing one')
            if gday != civil_day and nxt['local_date'] != civil_day.isoformat():
                _refuse('a birth before sunrise must precede the sunrise of its own date')
            if s is not None and not s < n:
                _refuse('sunset is after the next sunrise')
        else:
            _unavailable(nxt, {(OUTSIDE, NEXT_OUTSIDE)})
            if gday != LOCAL_LAST:
                _refuse('next sunrise withheld inside the supported dates')
            n = None
        if doc['boundary'] != near_sunrise(birth_us, g, n):
            _refuse('near-sunrise record is not the instants')
        out.update(available=True, vara_id=vara['vara_id'], governing_date=gday, governing_us=g, sunset_us=s,
                   next_us=n, boundary=doc['boundary'])
        return out
    reasons = {(r, c) for r, cs in VARA_CONDITIONS.items() for c in cs}
    vara = _unavailable(vara, reasons)
    if doc['vara_differs_from_civil_weekday'] is not None:
        _refuse('civil weekday comparison given without a Vara')
    if doc['boundary'] != {'status': 'not_assessed', 'reason': 'VARA_UNAVAILABLE'}:
        _refuse('near-sunrise record given without a Vara')
    if vara['condition'] == DAY_END:
        g = _event(doc['governing_sunrise'], zone)
        gday = date.fromisoformat(doc['governing_sunrise']['local_date'])
        if gday not in (civil_day, civil_day - timedelta(days=1)) or not g <= birth_us:
            _refuse('governing sunrise does not precede the birth')
        sunset = doc['sunset']
        if isinstance(sunset, dict) and sunset.get('status') == 'available':
            s = _event(sunset, zone)
            if not g < s < g + 86400 * MICROS:
                _refuse('sunset is not within 24 hours after the governing sunrise')
        else:
            _unavailable(sunset, {(UNDEFINED, NO_SUNSET)})
            s = None
        _unavailable(doc['next_sunrise'], {(UNDEFINED, c) for c in VARA_CONDITIONS[UNDEFINED][:3]})
        out.update(governing_us=g, governing_date=gday, sunset_us=s)
    else:
        for key in ('governing_sunrise', 'sunset', 'next_sunrise'):
            if doc[key] != vara:
                _refuse('events given without a governing sunrise')
        out.update(governing_us=None, sunset_us=None)
    out.update(available=False, reason=vara['reason'], condition=vara['condition'], next_us=None)
    return out


def display_instant(t_us, zone):
    """(UTC, local) of one event to the nearest minute: the UTC instant rounded half up once, the same
    rounded instant converted to the zone (panchanga_report.display_instant applied to whole seconds)."""
    utc = _dt(t_us)
    second = utc.replace(microsecond=0) + (timedelta(seconds=1) if utc.microsecond >= 500_000 else timedelta(0))
    rounded = (second + DISPLAY_ROUNDING).replace(second=0, microsecond=0)
    return rounded, rounded.astimezone(zone)


def hours_minutes(span_us):
    """Whole hours and minutes of a non-negative span, rounded half up to the minute."""
    minutes = (span_us + 30 * MICROS) // (60 * MICROS)
    return minutes // 60, minutes % 60


# ---------------------------------------------------------------------------
# The page.

class VaraPage:
    def __init__(self, response, doc, locale):
        self.locale = loc.validate_locale(locale)
        self.values = validate(response, doc)
        self.audit = {'schema': SCHEMA, 'status': STATUS, 'method_sha256': METHOD_SHA256,
                      'vara': self.values.get('vara_id'), 'available': self.values['available'],
                      'near_sunrise': (self.values.get('boundary') or {}).get('near_sunrise'),
                      'texts': []}

    def t(self, key, **values):
        entry = STRINGS.get(key)
        if entry is None:
            raise loc.ReportLocaleError(f'Missing Vara report string {key}')
        return entry[self.locale].format(**values)

    def has(self, key):
        return key in STRINGS

    # -- helpers -----------------------------------------------------------------------------
    def _time(self, d, t_us):
        utc, local = display_instant(t_us, self.values['zone'])
        return (self.t('v.time', time=local.strftime('%H:%M')),
                self.t('v.time_sub', date=d.date_text(local.date().isoformat()), utc=utc.strftime('%H:%M')),
                local)

    def _cards(self, d):
        v = self.values
        civil = (self.t('v.card.civil'), self.t(f"civil.{v['civil_weekday']}"),
                 self.t('v.civil_sub', date=d.date_text(v['civil_date'].isoformat())))
        if v['available']:
            vara = (self.t('v.card.vara'), self.t(f"vara.{v['vara_id']}"),
                    self.t('v.vara_sub', date=d.date_text(v['governing_date'].isoformat())))
            after = v['birth_us'] - v['governing_us']
            before = None if v['next_us'] is None else v['next_us'] - v['birth_us']
            if before is not None and before < after:
                span, key, sub = before, 'v.before', 'v.before_sub'
            else:
                span, key, sub = after, 'v.after', 'v.after_sub'
            h, m = hours_minutes(span)
            value = self.t('v.within') if span < 60 * MICROS else self.t(key, hours=h, minutes=f'{m:02d}')
            position = (self.t('v.card.position'), value, self.t(sub))
        else:
            vara = (self.t('v.card.vara'), self.t('v.unavailable'), self.t('v.sub.no_vara'))
            position = (self.t('v.card.position'), self.t('v.unavailable'), self.t('v.sub.no_vara'))
        events = []
        for label, t_us, missing in (('v.card.sunrise', v.get('governing_us'), None),
                                     ('v.card.sunset', v.get('sunset_us'), 'v.sub.no_sunset'),
                                     ('v.card.next', v.get('next_us'), None)):
            if t_us is not None:
                value, sub, _ = self._time(d, t_us)
            elif v['available'] and label == 'v.card.next':
                value, sub = self.t('v.not_calculated'), self.t('v.sub.outside')
            elif v.get('governing_us') is not None and label == 'v.card.sunset':
                value, sub = self.t('v.unavailable'), self.t(missing)
            else:
                value = self.t('v.unavailable')
                sub = self.t('v.sub.outside' if v.get('reason') == OUTSIDE else 'v.sub.undefined')
            events.append((self.t(label), value, sub))
        return [vara, civil, position] + events

    def draw(self, d, response, positions):
        v = self.values
        pr._header(d, PAGE_KEY)
        y = pr._title(d, PAGE_KEY, self.t('v.title'), self.t('v.intro', birth=d.page_of['birth']))
        cards = self._cards(d)
        cw, ch, gap = (pr.CW - 2 * 12) / 3, 64, 12
        top = y - 4
        for i, (label, value, sub) in enumerate(cards):
            x = pr.M + (i % 3) * (cw + gap)
            yy = top - (i // 3) * (ch + gap) - ch
            pr._card(d, x, yy, cw, ch)
            d.rect(x, yy + ch - 3, cw, 3, fill='primary' if i == 0 else 'accent')
            d.kicker(x + 14, yy + ch - 20, label, 'primary_text')
            d.fitted(x + 14, yy + ch - 40, value, cw - 28, 15, 'Head', 'ink', minimum=10, max_lines=1)
            d.fitted(x + 14, yy + 11, sub, cw - 28, 8.6, 'Body', 'muted', minimum=pr.MIN_TEXT, max_lines=1)
            self.audit['texts'].append((label, value, sub))
        y = top - 2 * (ch + gap) - 8
        if v['available']:
            y = self._strip(d, y)
            b = v['boundary']
            minutes = NEAR_SECONDS // 60
            if b['near_sunrise']:
                title, body = self.t('v.near_title'), self.t('v.near', minutes=minutes)
            elif b['status'] == 'partial':
                title, body = self.t('v.clear_title'), self.t('v.partial', minutes=minutes,
                                                              last=d.date_text(LOCAL_LAST.isoformat()))
            else:
                title, body = self.t('v.clear_title'), self.t('v.clear', minutes=minutes)
        else:
            title = self.t('v.na_title')
            body = self.t(f"v.na.{v['condition']}", **{k: d.date_text(x.isoformat()) for k, x in
                                                       (('first', LOCAL_FIRST), ('last', LOCAL_LAST))
                                                       if '{' + k + '}' in STRINGS[f"v.na.{v['condition']}"]['en']})
        self.audit['note'] = (title, body)
        y = self._caution(d, y, title, body, near=v['available'] and v['boundary']['near_sunrise']) - 12
        self._method(d, y)

    def _caution(self, d, y_top, title, body, near):
        if not near:
            return pr._note(d, pr.M, y_top, pr.CW, title, body, size=8.4)
        # The near-sunrise caution: same note shape, with a saffron edge and a warning mark.
        size = 8.4
        lines = d.split(body, 'Body', size, pr.CW - 40)
        h = 34 + len(lines) * size * 1.5
        d.rect(pr.M, y_top - h, pr.CW, h, fill='tint', radius=6)
        d.rect(pr.M, y_top - h, 4, h, fill='primary')
        d.diamond(pr.M + 18, y_top - 14, 5, 'primary')
        d.text(pr.M + 18, y_top - 16.8, '!', 8, 'HeadBold', 'surface', 'center')
        d.kicker(pr.M + 30, y_top - 17, title, 'primary_text')
        yy = y_top - 32
        for line in lines:
            d.text(pr.M + 30, yy, line, size, 'Body', 'ink')
            yy -= size * 1.5
        return y_top - h

    def _strip(self, d, y):
        v = self.values
        d.text(pr.M, y, self.t('v.strip_title'), 12, 'Head', 'ink')
        y -= 10
        d.line(pr.M, y, pr.W - pr.M, y, 'accent', 0.8)
        g, s, n, b = v['governing_us'], v['sunset_us'], v['next_us'], v['birth_us']
        end = n if n is not None else g + 24 * 3600 * MICROS
        pad = 45 * 60 * MICROS
        lo, hi = g - pad, end + pad
        x0, x1 = pr.M + 6, pr.W - pr.M - 6
        X = lambda t: x0 + (t - lo) * (x1 - x0) / (hi - lo)
        bar_top = y - 30
        bar_h = 14
        base = bar_top - bar_h
        d.rect(x0, base, x1 - x0, bar_h, fill='tint_soft', radius=3)
        d.rect(X(g), base, X(end) - X(g), bar_h, fill='tint')
        if s is not None:
            d.rect(X(g), base, X(s) - X(g), bar_h, fill='primary')
        window = NEAR_SECONDS * MICROS
        for t in [g] + ([n] if n is not None else []):
            d.rect(X(t - window), base - 3, max(X(t + window) - X(t - window), 1.6), bar_h + 6, fill='primary_text')
        if n is None:
            d.c.setDash(2, 2)
            d.line(X(end), base - 4, X(end), base + bar_h + 4, 'muted', 0.8)
            d.c.setDash()
        # Birth marker above the bar.
        bx = X(b)
        d.line(bx, base - 2, bx, bar_top + 8, 'ink', 1.1)
        d.diamond(bx, bar_top + 11, 3.4, 'primary_text')
        label = self.t('v.strip.birth')
        lw = d.width(label, 'Strong', 8.6)
        lx = min(max(bx - lw / 2, pr.M), pr.W - pr.M - lw)
        d.text(lx, bar_top + 18, label, 8.6, 'Strong', 'primary_text')
        # Event labels below the bar: sunrise left, next sunrise right, sunset centred, never overlapping.
        labels = [(X(g), self.t('v.strip.sunrise', time=display_instant(g, v['zone'])[1].strftime('%H:%M')), 'left')]
        if n is not None:
            labels.append((X(n), self.t('v.strip.next', time=display_instant(n, v['zone'])[1].strftime('%H:%M')),
                           'right'))
        else:
            labels.append((X(end), self.t('v.strip.next_none'), 'right'))
        boxes = []
        for x, text, align in labels:
            w = d.width(text, 'Medium', pr.MIN_TEXT)
            left = x if align == 'left' else x - w
            boxes.append((max(left, pr.M), text, w))
        rows = [base - 15] * len(boxes)
        if s is not None:
            # Centred under the sunset when it fits between the sunrise labels; otherwise (long polar-edge
            # days, a sunset just before the next sunrise) on a second line, still under the sunset.
            text = self.t('v.strip.sunset', time=display_instant(s, v['zone'])[1].strftime('%H:%M'))
            w = d.width(text, 'Medium', pr.MIN_TEXT)
            left = X(s) - w / 2
            if boxes[0][0] + boxes[0][2] + 8 <= left and left + w + 8 <= boxes[1][0]:
                rows.insert(1, base - 15)
            else:
                left = min(max(left, pr.M), pr.W - pr.M - w)
                rows.insert(1, base - 26)
                d.line(X(s), base - 1, X(s), base - 18, 'rule', 0.5)
            boxes.insert(1, (left, text, w))
        if boxes[0][0] + boxes[0][2] + 8 > boxes[-1][0]:
            raise layout.LayoutError('Sunrise labels overlap')
        for (left, text, w), row in zip(boxes, rows):
            if left < pr.M - 0.01 or left + w > pr.W - pr.M + 0.01:
                raise layout.LayoutError('Strip label outside the margins')
            d.text(left, row, text, pr.MIN_TEXT, 'Medium', 'muted')
            self.audit['texts'].append(text)
        return d.wrap(pr.M, min(rows) - 16, self.t('v.strip_note'), pr.CW, pr.MIN_TEXT, 11, 'Body', 'muted',
                      max_lines=2) - 2

    def _method(self, d, y):
        prov = self.values['provenance']
        tz = prov['timezone_data']
        d.text(pr.M, y, self.t('v.m_title'), 12, 'Head', 'ink')
        y -= 10
        d.line(pr.M, y, pr.W - pr.M, y, 'accent', 0.8)
        y -= 14
        rows = [
            (self.t('v.m.convention'), self.t('v.m.convention_value')),
            (self.t('v.m.place'), self.t('v.m.place_value')),
            (self.t('v.m.vara'), self.t('v.m.vara_value')),
            (self.t('v.m.times'), self.t('v.m.times_value')),
            (self.t('v.m.checks'), self.t('v.m.checks_value')),
            (self.t('v.m.data'), self.t('v.m.data_value', schema=SCHEMA,
                                        library=prov['swiss_ephemeris']['library_version'],
                                        manifest=prov['ephemeris_manifest_sha256'][:12],
                                        package=tz['package_version'], iana=tz['iana_version'],
                                        calls=prov['swiss_calls'])),
        ]
        tw = 92
        for label, text in rows:
            d.text(pr.M, y, label, 8.8, 'Strong', 'primary_text')
            y2 = d.wrap(pr.M + tw, y, text, pr.CW - tw, pr.MIN_TEXT, 10.8, 'Body', 'ink', max_lines=3)
            rule = y2 + 10.8 - 6
            d.line(pr.M, rule, pr.W - pr.M, rule, 'rule', 0.5)
            y = rule - 10.5
        y = d.wrap(pr.M, y + 2, self.t('v.status'), pr.CW, pr.MIN_TEXT, 11, 'Strong', 'muted', max_lines=2)
        if y < pr.FOOTER_Y + 22:
            raise layout.LayoutError('Sunrise and Vara page content reaches the footer')
