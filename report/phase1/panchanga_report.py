"""Extended edition of the premium Kundali PDF: birth-instant Panchanga pages (KUN-PAN-RPT-001).

The standard ten-page report (premium_report.generate) is not changed. This module is used only
through premium_report.generate_extended(response, panchanga, ...), which adds three pages before
the methodology page:

    Panchanga at birth  ·  Transition times  ·  Method and limits

Display only. Every Panchanga value comes from the `sabpuja-panchanga/1` document produced by
the existing Panchanga M1 module (src/sabpuja_kundali/panchanga), which this module never calls.
Before a page is drawn the document is checked against the chart response it is shown with:
same birth instant and zone, same Moon Nakshatra and Pada, elongation and Yoga sum consistent
with the chart's own Sun and Moon longitudes, the same Swiss Ephemeris, ephemeris manifest and
timezone data, the pinned method block (frozen limits), and every transition and local time.
Any disagreement raises PanchangaReportError; nothing is recalculated or guessed.

The only derived display values are a calendar-formatted local date, hours relative to birth for
the timeline, and drawing positions. Local times are re-derived from the UTC instant with the
pinned IANA data only to check that the document's local time is the correct one.

No Tithi, Karana or Yoga name is displayed (D07-A, D16-M1-INDEX): they are shown by number. The
document's validation status ENGINEERING_UNVERIFIED_PENDING_INDEPENDENT_QA is printed with a
plain-language limitation on the Method and limits page.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
try:
    from . import premium_report as pr
    from . import premium_layout as layout
    from . import report_locale as loc
except ImportError:  # loaded by path or run as a script
    sys.path.insert(0, str(ROOT))
    import premium_report as pr
    import premium_layout as layout
    import report_locale as loc

CATALOG_PATH = ROOT / 'report_panchanga_i18n.json'
CATALOG = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
STRINGS = CATALOG['strings']

# The one Panchanga document this edition displays. A later schema, status or method revision
# must be adopted here deliberately; until then it is refused, never shown.
SCHEMA = 'sabpuja-panchanga/1'
VALIDATION_STATUS = 'ENGINEERING_UNVERIFIED_PENDING_INDEPENDENT_QA'
METHOD_ID = 'KUN-PAN-M1'
# SHA-256 of the canonical JSON (sorted keys, no spaces) of contract._method(DEFAULT_LIMITS), and
# of the claim_boundary sentence, at main 07da75e. A document computed with other (for example
# failure-injection) limits, or by another method revision, is refused. Pinned by the tests.
METHOD_SHA256 = '2d8499e36653ba2afd4db7c0144f760960904ca1a8278c448851e5e9fc231683'
CLAIM_BOUNDARY = ('Engineering output for independent QA only. Not customer-facing. Tithi and '
                  'Karana transitions at E = 0, 90, 180, 270 deg are compared with USNO/NASA '
                  'published minutes; everything else is rule-oracle and Swiss-on-Swiss '
                  'conformance, not independent astronomical accuracy.')
CLAIM_BOUNDARY_SHA256 = hashlib.sha256(CLAIM_BOUNDARY.encode()).hexdigest()
NAME_OMITTED = 'PANCHANGA_METHOD_NOT_ADOPTED'
LOCAL_FIRST, LOCAL_LAST = date(1970, 1, 1), date(2100, 12, 31)   # D13-A envelope
LOCAL_RENDERING = {
    'offset_rule': 'pinned IANA tzdata (SCI-03), converted from the UTC instant; no rounding',
    'envelope_local_dates': {'first': LOCAL_FIRST.isoformat(), 'last': LOCAL_LAST.isoformat()},
    'outside_envelope': 'withheld_outside_envelope (D13-A); the UTC instant is still reported',
}
MAX_EXTENT = timedelta(days=2.5)        # D09-A-M1 frozen bracket extent, each direction
MAX_BRACKET_US = 500_000                # frozen final bracket
MAX_BRACKET_STEPS = 10                  # 2.5 days in 6-hour steps
MAX_ITERATIONS = 64
# Display tolerance: E and S are printed to 8 decimals from unrounded values, and the chart's
# longitudes are each printed to 8 decimals: at most 3 half-units apart, plus float noise.
ANGLE_TOLERANCE = 1.6e-8
UTC_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
ELEMENTS = ('tithi', 'karana', 'yoga', 'nakshatra', 'pada')
PAGE_KEYS = ('panchanga', 'transitions', 'pmethod')


class PanchangaReportError(ValueError):
    """The Panchanga document cannot be shown with this chart. Fixed text; never birth data."""


def _refuse(reason):
    raise PanchangaReportError('Panchanga document refused: ' + reason)


def check_catalog() -> list[str]:
    problems = []
    for key, entry in STRINGS.items():
        if set(entry) != set(loc.LOCALES):
            problems.append(f'{key}: locales')
        elif loc.placeholders(entry['en']) != loc.placeholders(entry['hi']):
            problems.append(f'{key}: placeholders differ')
    return problems


if check_catalog():
    raise RuntimeError('Panchanga report catalog inconsistent')


def canonical_sha256(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def _get_zone(key):
    """The engine's pinned-tzdata zone loader (never the host TZPATH)."""
    try:
        from sabpuja_kundali.timezones import get_zone
    except ImportError:
        sys.path.insert(0, str(REPO / 'src'))
        from sabpuja_kundali.timezones import get_zone
    return get_zone(key)


# ---------------------------------------------------------------------------
# Validation of the Panchanga document against the chart response.

def _utc(text):
    if not isinstance(text, str) or not UTC_PATTERN.match(text):
        _refuse('instant is not a whole-second UTC timestamp')
    try:
        return datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        _refuse('instant is not a valid UTC timestamp')


def _int(value, low, high):
    if type(value) is not int or not low <= value <= high:
        _refuse('field out of range')
    return value


DISPLAY_ROUNDING = timedelta(seconds=30)


def display_instant(moment_utc, moment_local, zone):
    """Customer display of one M1 transition: (UTC, local or None), both to the nearest minute.

    The UTC instant (a whole second in the M1 document) is rounded once, half up (:29 down, :30 up),
    and that same rounded instant is converted to the pinned zone, so the two printed clock times
    never disagree, including across midnight, summer-time gaps and repeated hours. A local time M1
    withheld stays withheld; a rounded local time that would fall outside the D13-A envelope is
    withheld too, never shown. The M1 document itself keeps its whole seconds.
    """
    rounded = (moment_utc + DISPLAY_ROUNDING).replace(second=0, microsecond=0)
    if moment_local is None:
        return rounded, None
    local = rounded.astimezone(zone)
    return rounded, (local if LOCAL_FIRST <= local.date() <= LOCAL_LAST else None)


def _instant(value, zone):
    """(utc datetime, local datetime or None) of one transition, checked."""
    if not isinstance(value, dict):
        _refuse('transition missing')
    keys = set(value)
    rendering = value.get('local_rendering')
    if rendering == 'rendered':
        if keys != {'utc', 'local', 'local_rendering', 'search'}:
            _refuse('transition fields')
    elif rendering == 'withheld_outside_envelope':
        if keys != {'utc', 'local_rendering', 'search'}:
            _refuse('transition fields')
    else:
        _refuse('unknown local rendering')
    moment = _utc(value['utc'])
    search = value['search']
    if not isinstance(search, dict) or set(search) != {'bracket_steps', 'iterations', 'final_bracket_us'}:
        _refuse('transition search record')
    _int(search['bracket_steps'], 1, MAX_BRACKET_STEPS)
    _int(search['iterations'], 0, MAX_ITERATIONS)
    _int(search['final_bracket_us'], 1, MAX_BRACKET_US)
    expected = moment.astimezone(zone)
    inside = LOCAL_FIRST <= expected.date() <= LOCAL_LAST
    if rendering == 'rendered':
        if not inside or value['local'] != expected.isoformat():
            _refuse('local time is not the UTC instant in the birth zone')
        return moment, expected
    if inside:
        _refuse('local time withheld inside the supported envelope')
    return moment, None


def _near_step(angle, step):
    """True when a printed angle is within the display tolerance of a sector edge."""
    r = angle % step
    return min(r, step - r) <= Fraction(ANGLE_TOLERANCE)


def _sector_consistent(printed, step, number):
    """The engine classifies the unrounded angle; the printed one must agree unless on an edge."""
    angle = Fraction(printed)
    expected = int(angle // step) + 1
    if expected == number:
        return True
    if _near_step(angle, step):
        count = int(round(360 / step))
        return number in ((expected - 2) % count + 1, expected % count + 1)
    return False


def _circular_gap(a, b):
    gap = abs(a - b) % 360
    return min(gap, 360 - gap)


def validate(response, doc):
    """The checked values the pages display. Raises PanchangaReportError on any disagreement."""
    if not isinstance(doc, dict):
        _refuse('not a document')
    expected_keys = {'schema', 'validation_status', 'claim_boundary', 'method', 'birth', 'angles', 'tithi',
                     'karana', 'yoga', 'nakshatra', 'local_rendering', 'provenance'}
    if set(doc) != expected_keys:
        _refuse('unexpected or missing fields')
    if doc['schema'] != SCHEMA:
        _refuse('unsupported schema')
    if doc['validation_status'] != VALIDATION_STATUS:
        _refuse('unsupported validation status')
    if doc['claim_boundary'] != CLAIM_BOUNDARY:
        _refuse('claim boundary differs')
    if not isinstance(doc['method'], dict) or canonical_sha256(doc['method']) != METHOD_SHA256:
        _refuse('method or search limits differ from the adopted method')
    chart, info = response['chart'], response['input']
    birth = chart['birth']
    if doc['birth'] != {'utc': birth['utc'], 'timezone': birth['timezone']}:
        _refuse('birth instant or zone differs from the chart')
    if info['place'].get('timezone') != birth['timezone']:
        _refuse('zone differs from the input')
    if doc['local_rendering'] != {'zone': birth['timezone'], **LOCAL_RENDERING}:
        _refuse('local rendering rule differs')
    # Provenance: the same Swiss Ephemeris, ephemeris files and timezone data as the chart.
    meta = chart['calculation_metadata']
    prov = doc['provenance']
    expected_prov = {'swiss_ephemeris', 'ephemeris_manifest_sha256', 'timezone_data', 'swiss_calls',
                     'chart_schema_version_unchanged', 'calculation_metadata_schema_unchanged'}
    if not isinstance(prov, dict) or set(prov) != expected_prov:
        _refuse('provenance fields')
    if prov['swiss_ephemeris'] != meta['swiss_ephemeris']:
        _refuse('Swiss Ephemeris differs from the chart')
    if prov['ephemeris_manifest_sha256'] != meta['ephemeris_data'].get('manifest_sha256'):
        _refuse('ephemeris data differs from the chart')
    if meta['ephemeris_data'].get('verified_before_calculation') is not True:
        _refuse('chart ephemeris data not verified')
    tz = meta['timezone_data']
    if prov['timezone_data'] != {k: tz.get(k) for k in ('package_version', 'iana_version', 'manifest_sha256')}:
        _refuse('timezone data differs from the chart')
    if (prov['chart_schema_version_unchanged'] != chart['schema_version']
            or prov['calculation_metadata_schema_unchanged'] != meta['metadata_schema']):
        _refuse('chart schema differs')
    _int(prov['swiss_calls'], 1, 10_000)

    # Angles against the chart's own printed longitudes.
    angles = doc['angles']
    if not isinstance(angles, dict) or set(angles) != {'elongation_deg', 'yoga_sum_deg', 'note'}:
        _refuse('angle fields')
    e, s = angles['elongation_deg'], angles['yoga_sum_deg']
    for value in (e, s):
        if type(value) is not float or not math.isfinite(value) or not 0 <= value < 360:
            _refuse('angle out of range')
    sun = chart['planets']['sun']['longitude_deg']
    moon = chart['planets']['moon']['longitude_deg']
    if _circular_gap(e, (moon - sun) % 360) > ANGLE_TOLERANCE or _circular_gap(s, (sun + moon) % 360) > ANGLE_TOLERANCE:
        _refuse('angles do not match the chart Sun and Moon')

    tithi, karana, yoga, nak = doc['tithi'], doc['karana'], doc['yoga'], doc['nakshatra']
    if not all(isinstance(x, dict) for x in (tithi, karana, yoga, nak)):
        _refuse('element missing')
    if set(tithi) != {'number', 'paksha', 'paksha_day', 'start', 'end'}:
        _refuse('tithi fields')
    if set(karana) != {'index', 'name_omitted', 'start', 'end'} or set(yoga) != {'index', 'name_omitted', 'start', 'end'}:
        _refuse('karana or yoga fields')
    if karana['name_omitted'] != NAME_OMITTED or yoga['name_omitted'] != NAME_OMITTED:
        _refuse('names must stay omitted')
    if set(nak) != {'index', 'name', 'pada', 'start', 'end', 'pada_start', 'pada_end'}:
        _refuse('nakshatra fields')
    number = _int(tithi['number'], 1, 30)
    paksha = 'shukla' if number <= 15 else 'krishna'
    if tithi['paksha'] != paksha or _int(tithi['paksha_day'], 1, 15) != (number - 1) % 15 + 1:
        _refuse('paksha disagrees with the tithi number')
    k = _int(karana['index'], 1, 60)
    y = _int(yoga['index'], 1, 27)
    if k not in (2 * number - 1, 2 * number):
        _refuse('karana is not a half of the tithi')
    if not (_sector_consistent(e, 12, number) and _sector_consistent(e, 6, k)
            and _sector_consistent(s, Fraction(40, 3), y)):
        _refuse('element number does not match its printed angle')
    moon_nak = chart['moon_nakshatra']
    if {key: nak[key] for key in ('index', 'name', 'pada')} != moon_nak:
        _refuse('Moon Nakshatra differs from the chart')

    zone = _get_zone(birth['timezone'])
    t0 = _utc(birth['utc'])
    spans = {}
    pairs = {'tithi': (tithi['start'], tithi['end']), 'karana': (karana['start'], karana['end']),
             'yoga': (yoga['start'], yoga['end']), 'nakshatra': (nak['start'], nak['end']),
             'pada': (nak['pada_start'], nak['pada_end'])}
    for element, (start, end) in pairs.items():
        (s_utc, s_loc), (e_utc, e_loc) = _instant(start, zone), _instant(end, zone)
        if not (t0 - MAX_EXTENT <= s_utc <= t0 < e_utc <= t0 + MAX_EXTENT):
            _refuse('transition does not bracket the birth instant')
        spans[element] = {'start': (s_utc, s_loc), 'end': (e_utc, e_loc)}
    # Nesting: a Karana is the first or second half of its Tithi; a Pada lies in its Nakshatra.
    t_s, t_e = spans['tithi']['start'][0], spans['tithi']['end'][0]
    k_s, k_e = spans['karana']['start'][0], spans['karana']['end'][0]
    if not t_s <= k_s < k_e <= t_e or (k_s == t_s) != (k % 2 == 1) or (k_e == t_e) != (k % 2 == 0):
        _refuse('karana span is not half of the tithi span')
    n_s, n_e = spans['nakshatra']['start'][0], spans['nakshatra']['end'][0]
    p_s, p_e = spans['pada']['start'][0], spans['pada']['end'][0]
    pada = moon_nak['pada']
    if not n_s <= p_s < p_e <= n_e or (p_s == n_s) != (pada == 1) or (p_e == n_e) != (pada == 4):
        _refuse('pada span is not inside the nakshatra span')
    return {'number': number, 'paksha': paksha, 'paksha_day': tithi['paksha_day'], 'karana': k, 'yoga': y,
            'nakshatra': dict(moon_nak), 'elongation': e, 'yoga_sum': s, 'birth_utc': t0,
            'birth_local': t0.astimezone(zone), 'zone': birth['timezone'], 'zone_info': zone, 'spans': spans,
            'provenance': prov,
            'search': doc['method']['transition_search'], 'method_id': doc['method']['method_id']}


# ---------------------------------------------------------------------------
# The extension object used by premium_report.render.

class Extension:
    def __init__(self, response, doc, locale):
        self.locale = loc.validate_locale(locale)
        self.values = validate(response, doc)
        self.audit = {'schema': SCHEMA, 'validation_status': VALIDATION_STATUS,
                      'method_sha256': METHOD_SHA256, 'withheld': [], 'texts': []}

    def t(self, key, **values):
        entry = STRINGS.get(key)
        if entry is None:
            raise loc.ReportLocaleError(f'Missing Panchanga report string {key}')
        return entry[self.locale].format(**values)

    def apply(self, d):
        base = pr.pages(d.locale)
        at = [k for k, _, _ in base].index('method')
        extra = [(key, self.t(f'page.{key}.title'), self.t(f'page.{key}.desc')) for key in PAGE_KEYS]
        d.contents = base[:at] + extra + base[at:]
        d.page_of = {key: i + 1 for i, (key, _, _) in enumerate(d.contents)}
        d.total = len(d.contents)
        d.edition = pr.EDITION_PANCHANGA
        d.extension = self

    def page_drawers(self):
        return [self._page_panchanga, self._page_transitions, self._page_method]

    def method_lists(self, d):
        """Inclusions and exclusions of the methodology page in the extended edition."""
        first, last = d.page_of[PAGE_KEYS[0]], d.page_of[PAGE_KEYS[-1]]
        inc = [d.t(f'method.inc{i}') for i in range(1, 6)] + [self.t('method.inc6', first=first, last=last)]
        exc = [self.t('method.exc1'), self.t('method.exc2'), d.t('method.exc3'), d.t('method.exc4'),
               d.t('method.exc5'), self.t('method.exc6')]
        half = pr.CW / 2 - 10
        for text in inc + exc:
            if d.width(text, 'Body', 8.6) > half - 14:
                raise layout.LayoutError('Methodology list item too long')
        return inc, exc

    # -- helpers ---------------------------------------------------------------------------
    def _paksha(self, v):
        return self.t('pan.paksha.' + v['paksha'])

    def _date_time(self, d, moment):
        return self.t('tr.local', date=d.date_text(moment.date().isoformat()), time=moment.strftime('%H:%M'))

    @staticmethod
    def _offset(moment):
        text = moment.strftime('%z')
        return text[:3] + ':' + text[3:]

    # -- Page: Panchanga at birth ----------------------------------------------------------
    def _page_panchanga(self, d, response, positions):
        v = self.values
        pr._header(d, 'panchanga')
        y = pr._title(d, 'panchanga', self.t('pan.title'), self.t('pan.intro', positions=d.page_of['positions']))
        nak = v['nakshatra']
        transitions = d.page_of['transitions']
        cards = [
            (self.t('pan.tithi'), self.t('pan.tithi_value', number=v['number']),
             self.t('pan.tithi_sub', day=v['paksha_day'])),
            (self.t('pan.paksha'), self._paksha(v), self.t('pan.paksha_sub.' + v['paksha'])),
            (self.t('pan.karana'), self.t('pan.karana_value', index=v['karana']), self.t('pan.karana_sub')),
            (self.t('pan.yoga'), self.t('pan.yoga_value', index=v['yoga']), self.t('pan.yoga_sub')),
            (self.t('pan.nakshatra'), d.tr.nakshatra(nak['name']),
             self.t('pan.nakshatra_sub', pada=nak['pada'])),
            (self.t('pan.angle'), f"{v['elongation']:.8f}°", self.t('pan.angle_sub', sum=f"{v['yoga_sum']:.8f}")),
        ]
        cw, ch, gap = (pr.CW - 2 * 12) / 3, 80, 12
        top = y - 6
        for i, (label, value, sub) in enumerate(cards):
            x = pr.M + (i % 3) * (cw + gap)
            yy = top - (i // 3) * (ch + gap) - ch
            pr._card(d, x, yy, cw, ch)
            d.rect(x, yy + ch - 3, cw, 3, fill='primary' if i == 0 else 'accent')
            d.kicker(x + 14, yy + ch - 22, label, 'primary_text')
            d.text(x + cw - 14, yy + ch - 22, self.t('pan.page_ref', page=transitions if i < 5 else d.page_of['pmethod']),
                   pr.MIN_TEXT, 'Medium', 'muted', 'right')
            d.fitted(x + 14, yy + ch - 46, value, cw - 28, 16, 'Head', 'ink', minimum=11, max_lines=1)
            d.fitted(x + 14, yy + 14, sub, cw - 28, 8.6, 'Body', 'muted', minimum=pr.MIN_TEXT, max_lines=1)
        y = top - 2 * (ch + gap) - 16
        d.text(pr.M, y, self.t('pan.read_title'), 12, 'Head', 'ink')
        y -= 10
        d.line(pr.M, y, pr.W - pr.M, y, 'accent', 0.8)
        # Tithi ring on the left, definitions on the right.
        ring = 136
        cx, cy = pr.M + ring / 2 + 4, y - 22 - ring / 2
        self._tithi_ring(d, cx, cy, ring / 2, v)
        caption_end = d.wrap(pr.M, cy - ring / 2 - 36, self.t('pan.ring_caption'), ring + 14, pr.MIN_TEXT, 10.5, 'Body', 'muted',
               max_lines=5)
        x = pr.M + ring + 30
        width = pr.W - pr.M - x
        yy = y - 22
        for key in ('tithi', 'paksha', 'karana', 'yoga', 'nakshatra'):
            yy = d.wrap(x, yy, self.t(f'pan.def.{key}', positions=d.page_of['positions']), width, 8.6, 12.2,
                        'Body', 'ink', max_lines=4) - 5
        bottom = min(yy, caption_end) - 8
        end = pr._note(d, pr.M, bottom, pr.CW, self.t('pan.instant_title'), self.t('pan.instant'), size=8.4)
        if end < pr.FOOTER_Y + 22:
            raise layout.LayoutError('Panchanga page content reaches the footer')

    def _tithi_ring(self, d, cx, cy, r, v):
        """30 Tithi sectors of E drawn clockwise from the top; the birth Tithi in saffron."""
        c = d.c
        inner = r - 17

        def point(angle, radius):
            a = math.radians(90 - angle)
            return cx + radius * math.cos(a), cy + radius * math.sin(a)

        for i in range(30):
            a0, a1 = 12 * i, 12 * (i + 1)
            p = c.beginPath()
            steps = 6
            for j in range(steps + 1):
                px, py = point(a0 + (a1 - a0) * j / steps, r)
                (p.moveTo if j == 0 else p.lineTo)(px, py)
            for j in range(steps, -1, -1):
                p.lineTo(*point(a0 + (a1 - a0) * j / steps, inner))
            p.close()
            role = 'primary' if i + 1 == v['number'] else ('tint' if i < 15 else 'rule')
            c.setFillColor(d.pal[role])
            c.setStrokeColor(d.pal['surface'])
            c.setLineWidth(0.8)
            c.drawPath(p, fill=1, stroke=1)
        c.setStrokeColor(d.pal['accent'])
        c.setLineWidth(0.6)
        c.circle(cx, cy, r + 3, stroke=1, fill=0)
        # Shukla / Krishna divide at E = 0 and 180.
        d.line(*point(0, inner - 4), *point(0, r + 6), 'primary_text', 0.9)
        d.line(*point(180, inner - 4), *point(180, r + 6), 'primary_text', 0.9)
        # Marker at E.
        mx, my = point(v['elongation'], r + 8)
        d.diamond(mx, my, 3.4, 'primary_text')
        d.text(cx, cy + 2, str(v['number']), 22, 'HeadBold', 'primary', 'center')
        d.text(cx, cy - 14, self._paksha(v), pr.MIN_TEXT, 'Medium', 'muted', 'center')
        d.text(cx, cy + r + 10, '0°', pr.MIN_TEXT, 'Medium', 'muted', 'center')
        d.text(cx, cy - r - 17, '180°', pr.MIN_TEXT, 'Medium', 'muted', 'center')

    # -- Page: transition times ------------------------------------------------------------
    def _time_cell(self, moment_local, moment_utc):
        ext = self
        shown_utc, shown_local = display_instant(moment_utc, moment_local, self.values['zone_info'])

        def draw(d, x, base, width, align):
            if moment_local is None:
                ext.audit['withheld'].append(moment_utc.strftime('%Y-%m-%dT%H:%M:%SZ'))
            if shown_local is None:
                first = ext.t('tr.withheld')
                second = ext.t('tr.utc_only', utc=shown_utc.strftime('%Y-%m-%d %H:%M'))
            else:
                first = ext._date_time(d, shown_local)
                second = ext.t('tr.utc', utc=shown_utc.strftime('%Y-%m-%d %H:%M'),
                               offset=ext._offset(shown_local))
            ext._two_lines(d, x, base, width, first, second)
        return draw

    def _two_lines(self, d, x, base, width, first, second, first_face='Medium'):
        fs1 = d.fit(first, first_face, 9.25, width - 20, pr.MIN_TEXT)
        fs2 = d.fit(second, 'Body', 8.5, width - 20, pr.MIN_TEXT)
        if fs1 is None or fs2 is None:
            raise layout.LayoutError('Transition cell text too long')
        d.text(x + 10, base + 5.6, first, fs1, first_face, 'ink')
        d.text(x + 10, base - 6.8, second, fs2, 'Body', 'muted')
        self.audit['texts'].append((first, second))

    def _value_cell(self, first, second):
        ext = self

        def draw(d, x, base, width, align):
            ext._two_lines(d, x, base, width, first, second, 'Strong')
        return draw

    def _page_transitions(self, d, response, positions):
        v = self.values
        spans = v['spans']
        pr._header(d, 'transitions')
        y = pr._title(d, 'transitions', self.t('tr.title'), self.t('tr.intro', zone=v['zone']))
        nak = v['nakshatra']
        values = {
            'tithi': (self.t('pan.tithi_value', number=v['number']), self._paksha(v)),
            'karana': (self.t('pan.karana_value', index=v['karana']),
                       self.t('tr.val.karana_' + ('first' if v['karana'] % 2 else 'second'), number=v['number'])),
            'yoga': (self.t('pan.yoga_value', index=v['yoga']), self.t('tr.val.yoga')),
            'nakshatra': (d.tr.nakshatra(nak['name']), self.t('tr.val.nakshatra', index=nak['index'])),
            'pada': (self.t('tr.val.pada', pada=nak['pada']), d.tr.nakshatra(nak['name'])),
        }
        columns = [(self.t('tr.col.element'), 66, 'left'), (self.t('tr.col.value'), 101, 'left'),
                   (self.t('tr.col.start'), 166, 'left'), (self.t('tr.col.end'), 166, 'left')]
        rows = []
        for element in ELEMENTS:
            (s_utc, s_loc), (e_utc, e_loc) = spans[element]['start'], spans[element]['end']
            rows.append([pr._cell(self.t(f'tr.el.{element}'), 'Strong', 'primary_text'),
                         self._value_cell(*values[element]),
                         self._time_cell(s_loc, s_utc), self._time_cell(e_loc, e_utc)])
        y = pr._table(d, pr.M, y - 4, columns, rows, row_h=40, header_h=28) - 26
        y = self._timeline(d, y, v)
        how = self.t('tr.how', step=_num(v['search']['bracket_step_hours']),
                     days=_num(v['search']['bracket_extent_max_days_each_direction']),
                     bracket=_num(v['search']['transition_bracket_max_seconds']))
        birth_offset = self._offset(v['birth_local'])
        shown = [display_instant(u, m, v['zone_info']) for span in spans.values() for u, m in span.values()]
        offsets = {self._offset(m) for _, m in shown if m is not None}
        if offsets - {birth_offset}:
            how += self.t('tr.offset_note', offset=birth_offset)
        if any(m is None for _, m in shown):
            how += self.t('tr.withheld_note', first=d.date_text(LOCAL_FIRST.isoformat()),
                          last=d.date_text(LOCAL_LAST.isoformat()))
        end = pr._note(d, pr.M, y - 6, pr.CW, self.t('tr.how_title'), how, size=8.4)
        if end < pr.FOOTER_Y + 22:
            raise layout.LayoutError('Transition page content reaches the footer')

    def _timeline(self, d, y, v):
        d.text(pr.M, y, self.t('tr.timeline_title'), 12, 'Head', 'ink')
        y -= 10
        d.line(pr.M, y, pr.W - pr.M, y, 'accent', 0.8)
        t0 = v['birth_utc']
        hours = {el: ((sp['start'][0] - t0).total_seconds() / 3600, (sp['end'][0] - t0).total_seconds() / 3600)
                 for el, sp in v['spans'].items()}
        lo = math.floor(min(a for a, _ in hours.values()) / 12) * 12
        hi = math.ceil(max(b for _, b in hours.values()) / 12) * 12
        x0, x1 = pr.M + 128, pr.W - pr.M - 16
        scale = (x1 - x0) / (hi - lo)
        X = lambda h: x0 + (h - lo) * scale
        top = y - 16
        row = 17
        for i, element in enumerate(ELEMENTS):
            a, b = hours[element]
            yy = top - i * row
            d.text(pr.M, yy - 8, self.t(f'tr.el.{element}'), 8.6, 'Strong', 'primary_text')
            seconds = int((v['spans'][element]['end'][0] - v['spans'][element]['start'][0]).total_seconds())
            lasted = self.t('tr.duration', hours=seconds // 3600, minutes=f'{seconds % 3600 // 60:02d}')
            if d.width(self.t(f'tr.el.{element}'), 'Strong', 8.6) + d.width(lasted, 'Medium', pr.MIN_TEXT) > x0 - pr.M - 14:
                raise layout.LayoutError('Timeline label and duration do not fit')
            d.text(x0 - 8, yy - 8, lasted, pr.MIN_TEXT, 'Medium', 'muted', 'right')
            d.rect(x0, yy - 10, x1 - x0, 11, fill='tint_soft')
            d.rect(X(a), yy - 10, max(X(b) - X(a), 1.2), 11, fill='primary' if element == 'tithi' else 'accent',
                   radius=2)
        bottom = top - len(ELEMENTS) * row
        for h in range(lo, hi + 1, 12):
            d.line(X(h), bottom + 2, X(h), bottom - 2, 'muted', 0.5)
            label = self.t('tr.birth') if h == 0 else self.t('tr.hours', hours=f'{h:+d}'.replace('-', '−'))
            d.text(X(h), bottom - 12, label, pr.MIN_TEXT, 'Medium', 'primary_text' if h == 0 else 'muted', 'center')
        d.line(X(0), top + 4, X(0), bottom, 'primary_text', 1.1)
        y = d.wrap(pr.M, bottom - 28, self.t('tr.axis_note'), pr.CW, pr.MIN_TEXT, 11, 'Body', 'muted', max_lines=2)
        return y - 6

    # -- Page: method and limits -----------------------------------------------------------
    def _page_method(self, d, response, positions):
        v = self.values
        prov = v['provenance']
        pr._header(d, 'pmethod')
        y = pr._title(d, 'pmethod', self.t('pm.title'), self.t('pm.intro'))
        tz = prov['timezone_data']
        rows = [
            (self.t('pm.positions'), self.t('pm.positions_value')),
            (self.t('pm.tithi'), self.t('pm.tithi_value')),
            (self.t('pm.karana'), self.t('pm.karana_value')),
            (self.t('pm.yoga'), self.t('pm.yoga_value')),
            (self.t('pm.nakshatra'), self.t('pm.nakshatra_value')),
            (self.t('pm.boundary'), self.t('pm.boundary_value')),
            (self.t('pm.time'), self.t('pm.time_value')),
            (self.t('pm.data'), self.t('pm.data_value', schema=SCHEMA, method=v['method_id'],
                                       library=prov['swiss_ephemeris']['library_version'],
                                       manifest=prov['ephemeris_manifest_sha256'][:12],
                                       package=tz['package_version'], iana=tz['iana_version'],
                                       calls=prov['swiss_calls'])),
        ]
        tw = 112
        for label, text in rows:
            d.text(pr.M, y, label, 9.2, 'Strong', 'primary_text')
            y2 = d.wrap(pr.M + tw, y, text, pr.CW - tw, 8.6, 12.2, 'Body', 'ink', max_lines=4)
            rule = y2 + 12.2 - 7
            d.line(pr.M, rule, pr.W - pr.M, rule, 'rule', 0.5)
            y = rule - 14
        y -= 6
        y = pr._note(d, pr.M, y, pr.CW, self.t('pm.status_title', status=VALIDATION_STATUS), self.t('pm.status'),
                     size=8.4) - 18
        half = pr.CW / 2 - 10
        d.text(pr.M, y, self.t('pm.included'), 11, 'Head', 'ink')
        d.text(pr.M + half + 20, y, self.t('pm.excluded'), 11, 'Head', 'ink')
        yy = y - 18
        for i in range(1, 6):
            a, b = self.t(f'pm.inc{i}'), self.t(f'pm.exc{i}')
            for text in (a, b):
                if d.width(text, 'Body', 8.6) > half - 14:
                    raise layout.LayoutError('Panchanga list item too long')
            d.diamond(pr.M + 3, yy + 3, 2.4)
            d.text(pr.M + 12, yy, a, 8.6, 'Body', 'ink')
            d.diamond(pr.M + half + 23, yy + 3, 2.4, 'muted', fill=False)
            d.text(pr.M + half + 32, yy, b, 8.6, 'Body', 'ink')
            yy -= 14.5
        if yy < pr.FOOTER_Y + 22:
            raise layout.LayoutError('Panchanga method page content reaches the footer')


def _num(value):
    """6.0 -> '6', 2.5 -> '2.5' (method block values, display only)."""
    return f'{value:g}'
