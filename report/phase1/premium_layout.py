"""Presentation helpers for the Phase 2A premium report: no astronomy, only display of engine values.

Everything here is a deterministic conversion of fields the engine already returned:
sign-relative degrees from `longitude_deg` and the engine's own Rashi, and the
placement of labels inside fixed North Indian house shapes. A disagreement with
the engine raises ReportDataError instead of being corrected.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

SIGNS = ['Mesha', 'Vrishabha', 'Mithuna', 'Karka', 'Simha', 'Kanya',
         'Tula', 'Vrischika', 'Dhanu', 'Makara', 'Kumbha', 'Meena']
# Conventional English names, used only as a reading aid in the glossary.
SIGN_ENGLISH = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
                'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

# The engine prints longitudes with 8 decimals and classifies with the unrounded
# value (calculation_metadata.longitude_display). A printed value can therefore
# sit exactly on a boundary that the unrounded value had not reached yet; half a
# display unit is the only tolerance accepted for that case.
DISPLAY_HALF_UNIT = Decimal('0.000000005')


class ReportDataError(ValueError):
    """Engine data the report cannot display faithfully. Never rendered."""


@dataclass(frozen=True)
class SignPosition:
    rashi: str
    rashi_number: int
    degrees: int
    minutes: int
    seconds: int
    at_display_boundary: bool

    def dms(self) -> str:
        return f'{self.degrees}°{self.minutes:02d}′{self.seconds:02d}″'

    def short(self) -> str:
        return f'{self.degrees}°'


def sign_position(longitude: float, engine_rashi: str) -> SignPosition:
    """Degrees within the engine's Rashi, truncated to whole arc-seconds.

    The Rashi is the engine's, never re-derived: the longitude is only checked to
    lie in it. Truncation (not rounding) means 29°59'59.7" shows as 29°59'59" and
    can never display as 30°00'00" of a sign the body has not entered.
    The decimal is taken from the float's shortest repr, which is the engine's
    printed value, so 0.0175 stays exactly 63 arc-seconds.
    """
    if engine_rashi not in SIGNS:
        raise ReportDataError('Unknown Rashi')
    if isinstance(longitude, bool) or not isinstance(longitude, (int, float)) or not math.isfinite(longitude):
        raise ReportDataError('Invalid longitude')
    value = Decimal(repr(float(longitude)))
    if not Decimal(0) <= value < Decimal(360):
        raise ReportDataError('Longitude outside [0, 360)')
    index = SIGNS.index(engine_rashi)
    printed_index = int(value // 30)
    relative = value - 30 * index
    boundary = False
    if printed_index != index:
        # Accepted only when the printed value equals the next boundary within half a
        # display unit (including 360 printed as 0) and the engine put it in the lower sign.
        upper = Decimal(30 * (index + 1))
        wrapped = value + 360 if index == 11 and printed_index == 0 else value
        if not (Decimal(0) <= wrapped - upper <= DISPLAY_HALF_UNIT):
            raise ReportDataError(f'Longitude does not lie in the engine Rashi {engine_rashi}')
        boundary = True
        relative = Decimal(30) - DISPLAY_HALF_UNIT
    total = int((relative * 3600) // 1)
    degrees, rest = divmod(total, 3600)
    minutes, seconds = divmod(rest, 60)
    if not 0 <= degrees < 30:
        raise ReportDataError('Sign-relative degree outside 0 to 30')
    return SignPosition(engine_rashi, index + 1, degrees, minutes, seconds, boundary)


def coordinate(value: float, positive: str, negative: str) -> str:
    """Decimal degrees with hemisphere, keeping the source's printed precision."""
    text = repr(float(abs(value)))
    return f'{text}° {positive if value >= 0 else negative}'


# ---------------------------------------------------------------------------
# North Indian chart geometry, 600-unit square, y downwards (as prototype chart.js).
HOUSES = [None,
 ((300, 0), (450, 150), (300, 300), (150, 150)), ((0, 0), (300, 0), (150, 150)),
 ((0, 0), (150, 150), (0, 300)), ((0, 300), (150, 150), (300, 300), (150, 450)),
 ((0, 300), (150, 450), (0, 600)), ((0, 600), (150, 450), (300, 600)),
 ((300, 600), (150, 450), (300, 300), (450, 450)), ((300, 600), (450, 450), (600, 600)),
 ((600, 600), (450, 450), (600, 300)), ((600, 300), (450, 450), (300, 300), (450, 150)),
 ((600, 300), (450, 150), (600, 0)), ((600, 0), (450, 150), (300, 0))]
# The vertex of each house that points into the chart; its Rashi number sits there.
INNER_VERTEX = [None, (300, 300), (150, 150), (150, 150), (300, 300), (150, 450), (150, 450),
                (300, 300), (450, 450), (450, 450), (300, 300), (450, 150), (450, 150)]
NUMBER_OFFSET = 36      # units from the inner vertex to the Rashi number centre
NUMBER_KEEPOUT = 62     # labels stay this far (along the house axis) from the inner vertex
EDGE_PAD = 9            # labels stay this far from every house edge


def _centroid(points):
    return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))


def _axis(house):
    vx, vy = INNER_VERTEX[house]
    cx, cy = _centroid(HOUSES[house])
    dx, dy = cx - vx, cy - vy
    length = math.hypot(dx, dy)
    return vx, vy, dx / length, dy / length


def number_position(house: int) -> tuple[float, float]:
    vx, vy, ux, uy = _axis(house)
    return vx + ux * NUMBER_OFFSET, vy + uy * NUMBER_OFFSET


def label_constraints(house: int, pad: float = EDGE_PAD, keepout: float = NUMBER_KEEPOUT):
    """Half-planes a*x + b*y >= c bounding where labels may go in this house."""
    points = HOUSES[house]
    cx, cy = _centroid(points)
    planes = []
    for i, (px, py) in enumerate(points):
        qx, qy = points[(i + 1) % len(points)]
        a, b = -(qy - py), qx - px
        norm = math.hypot(a, b)
        a, b = a / norm, b / norm
        if a * (cx - px) + b * (cy - py) < 0:
            a, b = -a, -b
        planes.append((a, b, a * px + b * py + pad))
    vx, vy, ux, uy = _axis(house)
    planes.append((ux, uy, ux * vx + uy * vy + keepout))
    return planes


def _interval(planes, y):
    lo, hi = -math.inf, math.inf
    for a, b, c in planes:
        if abs(a) < 1e-12:
            if b * y < c - 1e-9:
                return None
            continue
        bound = (c - b * y) / a
        if a > 0:
            lo = max(lo, bound)
        else:
            hi = min(hi, bound)
    return (lo, hi) if lo < hi else None


def _band(planes, y0, y1):
    top, bottom = _interval(planes, y0), _interval(planes, y1)
    if top is None or bottom is None:
        return None
    lo, hi = max(top[0], bottom[0]), min(top[1], bottom[1])
    return (lo, hi) if lo < hi else None


def inside_house(house: int, x: float, y: float, pad: float = 0.0) -> bool:
    return all(a * x + b * y >= c - 1e-6 for a, b, c in label_constraints(house, pad, -10_000))


@dataclass(frozen=True)
class PlacedLabel:
    index: int          # position in the token list given to layout_house
    x: float            # left edge, chart units
    y: float            # top edge, chart units (y downwards)
    width: float
    height: float
    size: float         # font size in points
    with_detail: bool


class LayoutError(RuntimeError):
    """Labels cannot be placed legibly in a house; the PDF is not produced."""


def layout_house(house: int, widths, scale: float, sizes=(11.5, 11, 10.5, 10, 9.5, 9, 8.5, 8),
                 gap_em: float = 0.55, leading: float = 1.32):
    """Place tokens in rows inside the house without overlap; largest legible size wins.

    `widths(size, with_detail)` returns each token's width in points. Chart units are
    points / scale. Returns PlacedLabel boxes (chart units) or raises LayoutError.
    """
    planes = label_constraints(house)
    ys = [y for y in range(0, 601)]
    feasible = [y for y in ys if _interval(planes, y) is not None]
    if not feasible:
        raise LayoutError('House has no label area')
    y_min, y_max = feasible[0], feasible[-1]
    cy = _centroid(HOUSES[house])[1]
    for size in sizes:
        for detail in (True, False):
            token_widths = [w / scale for w in widths(size, detail)]
            if not token_widths:
                return []
            gap = size * gap_em / scale
            row_h = size * leading / scale
            for rows in range(1, len(token_widths) + 1):
                height = rows * row_h
                if height > y_max - y_min:
                    break
                # Candidate tops nearest the visual centre first.
                tops = sorted(
                    (y_min + step * 2.0 for step in range(int((y_max - y_min - height) / 2.0) + 1)),
                    key=lambda t: abs(t + height / 2 - cy))
                for top in tops:
                    placed = _fill_rows(planes, token_widths, rows, top, row_h, gap)
                    if placed is not None:
                        return [PlacedLabel(i, x, y, w, row_h, size, detail) for i, x, y, w in placed]
    raise LayoutError(f'Labels do not fit in house {house}')


def _fill_rows(planes, widths, rows, top, row_h, gap):
    bands = []
    for r in range(rows):
        band = _band(planes, top + r * row_h, top + (r + 1) * row_h)
        if band is None:
            return None
        bands.append(band)
    placed, i = [], 0
    for r, (lo, hi) in enumerate(bands):
        remaining_rows = rows - r
        remaining = len(widths) - i
        if remaining <= 0:
            return None  # an empty row means fewer rows would have done
        want = math.ceil(remaining / remaining_rows)
        take = 0
        total = 0.0
        while take < want and i + take < len(widths):
            extra = widths[i + take] + (gap if take else 0)
            if total + extra > hi - lo:
                break
            total += extra
            take += 1
        if take == 0:
            return None
        x = (lo + hi - total) / 2
        for k in range(take):
            placed.append((i + k, x, top + r * row_h, widths[i + k]))
            x += widths[i + k] + gap
        i += take
    return placed if i == len(widths) else None
