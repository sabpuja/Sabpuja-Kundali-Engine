"""KUN-01 convention-sensitivity probes (research evidence, NOT accuracy validation).

Every number here compares Swiss Ephemeris with itself under different
conventions. It sizes how much each owner decision moves outputs; it says
nothing about whether any output is astronomically correct.

Usage: python -I convention_probes.py /abs/path/to/ephe
"""
import sys
import swisseph as swe

EPHE = sys.argv[1]
swe.set_ephe_path(EPHE)
F = swe.FLG_SWIEPH
ARCSEC = 3600.0


def wrap(d):
    return (d + 180.0) % 360.0 - 180.0


def jd_grid(y0=1900, y1=2100, step_days=7.3):
    jd, end = swe.julday(y0, 1, 1, 0.0), swe.julday(y1, 12, 31, 23.99)
    while jd <= end:
        yield jd
        jd += step_days


def aya(jd, mode, flags=F):
    swe.set_sid_mode(mode, 0, 0)
    return swe.get_ayanamsa_ex_ut(jd, flags)[1]


from importlib.metadata import version
print("pyswisseph", version("pyswisseph"), "| swisseph.__version__", getattr(swe, "__version__", "?"), "| Swiss library", swe.version)

# 1. Lahiri variants relative to SE_SIDM_LAHIRI (true ayanamsha, default flags)
variants = {
    "LAHIRI|SIDBIT_PREC_ORIG (IAE IAU1976 reproduction)": swe.SIDM_LAHIRI | swe.SIDBIT_PREC_ORIG,
    "LAHIRI_ICRC (46, 23d15m00s 1956)": swe.SIDM_LAHIRI_ICRC,
    "LAHIRI_1940 (43)": swe.SIDM_LAHIRI_1940,
    "LAHIRI_VP285 (44)": swe.SIDM_LAHIRI_VP285,
    "KRISHNAMURTI (5)": swe.SIDM_KRISHNAMURTI,
    "RAMAN (3)": swe.SIDM_RAMAN,
}
grid = list(jd_grid())
print(f"\n[1] Ayanamsha difference vs SE_SIDM_LAHIRI, {len(grid)} UT samples 1900-01-01..2100-12-31")
base = [aya(j, swe.SIDM_LAHIRI) for j in grid]
for label, mode in variants.items():
    d = [(aya(j, mode) - b) * ARCSEC for j, b in zip(grid, base)]
    print(f"    {label:52s} min {min(d):+10.3f}\"  max {max(d):+10.3f}\"")
for y in (1900, 1956, 2000, 2026, 2100):
    j = swe.julday(y, 1, 1, 0.0)
    print(f"    SE_SIDM_LAHIRI true ayanamsha {y}-01-01 0h UT: {aya(j, swe.SIDM_LAHIRI):.6f} deg")

# 2. Does the sidereal flag subtract the TRUE ayanamsha (incl. nutation)?
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
worst_true = worst_mean = 0.0
for j in grid[::10]:
    trop = swe.calc_ut(j, swe.SUN, F)[0][0]
    sid = swe.calc_ut(j, swe.SUN, F | swe.FLG_SIDEREAL)[0][0]
    a_true = swe.get_ayanamsa_ex_ut(j, F)[1]
    a_mean = swe.get_ayanamsa_ex_ut(j, F | swe.FLG_NONUT)[1]
    worst_true = max(worst_true, abs(wrap(trop - a_true - sid)) * ARCSEC)
    worst_mean = max(worst_mean, abs(wrap(trop - a_mean - sid)) * ARCSEC)
print("\n[2] sidereal = tropical(true equinox) - ayanamsha_ex(...)")
print(f"    max |residual| with TRUE ayanamsha (incl. nutation): {worst_true:.6f}\"")
print(f"    max |residual| with MEAN ayanamsha (FLG_NONUT):      {worst_mean:.3f}\"  (= nutation in longitude)")

# 3. Mean vs true node
d = [wrap(swe.calc_ut(j, swe.TRUE_NODE, F | swe.FLG_SIDEREAL)[0][0]
          - swe.calc_ut(j, swe.MEAN_NODE, F | swe.FLG_SIDEREAL)[0][0]) for j in grid]
print(f"\n[3] true node - mean node, 1900-2100: min {min(d):+.4f} deg  max {max(d):+.4f} deg")
crossings = sum(
    1 for j in grid
    if int(swe.calc_ut(j, swe.TRUE_NODE, F | swe.FLG_SIDEREAL)[0][0] // 30)
    != int(swe.calc_ut(j, swe.MEAN_NODE, F | swe.FLG_SIDEREAL)[0][0] // 30))
print(f"    samples where Rahu sign differs mean vs true: {crossings}/{len(grid)} ({100*crossings/len(grid):.2f}%)")
crossings_nak = sum(
    1 for j in grid
    if int(swe.calc_ut(j, swe.TRUE_NODE, F | swe.FLG_SIDEREAL)[0][0] // (40/3))
    != int(swe.calc_ut(j, swe.MEAN_NODE, F | swe.FLG_SIDEREAL)[0][0] // (40/3)))
print(f"    samples where Rahu nakshatra differs mean vs true: {crossings_nak}/{len(grid)} ({100*crossings_nak/len(grid):.2f}%)")

# 4. Ascendant: does the house-system letter change ascmc[0]?
lats = [-66.0, -45.0, -33.87, -23.5, 0.0, 12.97, 19.07, 28.61, 34.08, 51.5, 60.0, 66.0]
lons = [-122.4, -43.2, 0.0, 72.88, 77.21, 88.36, 151.2]
maxdiff = {b"W": 0.0, b"E": 0.0, b"O": 0.0}
n = 0
for j in grid[::40]:
    for lat in lats:
        for lon in lons:
            p = swe.houses_ex(j, lat, lon, b"P", swe.FLG_SIDEREAL)[1][0]
            for hs in maxdiff:
                o = swe.houses_ex(j, lat, lon, hs, swe.FLG_SIDEREAL)[1][0]
                maxdiff[hs] = max(maxdiff[hs], abs(wrap(o - p)) * ARCSEC)
            n += 1
print(f"\n[4] |ascmc[0](hsys) - ascmc[0](P)| over {n} time/place samples, |lat|<=66:")
for hs, v in maxdiff.items():
    print(f"    {hs.decode()}: {v:.9f}\"")

# 5. Polar behaviour: P raises, W/E return an ascendant
print("\n[5] Polar latitudes (2000-01-01 12h UT, lon 0):")
j = swe.julday(2000, 1, 1, 12.0)
for lat in (66.0, 67.0, 70.0, 80.0, 88.9, -70.0, -88.9):
    row = []
    for hs in (b"P", b"W", b"E", b"O"):
        try:
            row.append(f"{hs.decode()}={swe.houses_ex(j, lat, 0.0, hs, swe.FLG_SIDEREAL)[1][0]:.6f}")
        except swe.Error as e:
            row.append(f"{hs.decode()}=ERROR")
    print(f"    lat {lat:+6.1f}: " + "  ".join(row))

# 6. Sidereal ascendant = tropical ascendant - true ayanamsha?
worst = 0.0
for j in grid[::40]:
    for lat in (28.61, -33.87, 51.5):
        t = swe.houses_ex(j, lat, 77.2, b"W", 0)[1][0]
        s = swe.houses_ex(j, lat, 77.2, b"W", swe.FLG_SIDEREAL)[1][0]
        worst = max(worst, abs(wrap(t - swe.get_ayanamsa_ex_ut(j, F)[1] - s)) * ARCSEC)
print(f"\n[6] max |tropical asc - true ayanamsha - sidereal asc|: {worst:.6f}\"")

# 7. Time sensitivity (deg per second of time) -> effect of UTC-vs-UT1 (<0.9 s)
print("\n[7] Rate of change per 1 s of time (finite difference, 2000-03-20 06h UT):")
j = swe.julday(2000, 3, 20, 6.0)
ds = 1.0 / 86400
for lat in (0.0, 28.61, 51.5, 60.0, 66.0):
    worst_rate = 0.0
    for h in range(24):
        jj = j + h / 24
        a0 = swe.houses_ex(jj, lat, 0.0, b"W", swe.FLG_SIDEREAL)[1][0]
        a1 = swe.houses_ex(jj + ds, lat, 0.0, b"W", swe.FLG_SIDEREAL)[1][0]
        worst_rate = max(worst_rate, abs(wrap(a1 - a0)) * ARCSEC)
    print(f"    ascendant lat {lat:5.1f}: max {worst_rate:7.2f}\"/s over 24 hourly samples")
m0 = swe.calc_ut(j, swe.MOON, F)[0][0]
m1 = swe.calc_ut(j + ds, swe.MOON, F)[0][0]
print(f"    Moon: {abs(wrap(m1 - m0)) * ARCSEC:.3f}\"/s")

# 8. Delta T used by this build
print("\n[8] Swiss Delta T (TT-UT) in seconds:")
for y in (1900, 1950, 2000, 2026, 2050, 2100):
    print(f"    {y}: {swe.deltat(swe.julday(y, 1, 1, 0.0)) * 86400:8.2f} s")

# 9. julday(UTC civil) vs utc_to_jd UT1 approximation
y, mo, d, h, mi, s = 2016, 12, 31, 23, 59, 59.0
jd_civil = swe.julday(y, mo, d, h + mi / 60 + s / 3600)
jd_tt, jd_ut1 = swe.utc_to_jd(y, mo, d, h, mi, s, swe.GREG_CAL)
print(f"\n[9] 2016-12-31 23:59:59 UTC: julday() - utc_to_jd() UT1 = {(jd_civil - jd_ut1) * 86400:+.3f} s")

# 10. Geocentric vs topocentric Moon (alternative not proposed; sizes the choice)
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
swe.set_topo(77.2090, 28.6139, 0.0)
d = []
nak = 0
for j in grid:
    g = swe.calc_ut(j, swe.MOON, F | swe.FLG_SIDEREAL)[0][0]
    t = swe.calc_ut(j, swe.MOON, F | swe.FLG_SIDEREAL | swe.FLG_TOPOCTR)[0][0]
    d.append(abs(wrap(t - g)))
    nak += int(g // (40 / 3)) != int(t // (40 / 3))
print(f"\n[10] |topocentric - geocentric| Moon at New Delhi, 1900-2100: max {max(d):.4f} deg;"
      f" nakshatra differs in {nak}/{len(grid)} samples ({100 * nak / len(grid):.2f}%)")

# 11. Apparent vs geometric (true) position: size of aberration/light-time choice
worst = {}
for name, body in (("sun", swe.SUN), ("moon", swe.MOON), ("mars", swe.MARS), ("saturn", swe.SATURN)):
    worst[name] = max(abs(wrap(swe.calc_ut(j, body, F | swe.FLG_SIDEREAL | swe.FLG_TRUEPOS | swe.FLG_NOABERR | swe.FLG_NOGDEFL)[0][0]
                               - swe.calc_ut(j, body, F | swe.FLG_SIDEREAL)[0][0])) * ARCSEC for j in grid[::20])
print("[11] max |geometric - apparent| (arcsec): " + ", ".join(f"{k} {v:.1f}" for k, v in worst.items()))
