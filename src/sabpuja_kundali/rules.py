"""Pure Vedic chart helpers. Longitude must be sidereal degrees."""
from __future__ import annotations

SIGNS = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
         "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena")
NAKSHATRAS = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati"
)

def normalize(longitude: float) -> float:
    import math
    if not math.isfinite(longitude):
        raise ValueError("Longitude must be finite")
    return longitude % 360.0

def sign_index(longitude: float) -> int:
    return min(11, int(normalize(longitude) / 30.0))

def sign(longitude: float) -> str:
    return SIGNS[sign_index(longitude)]

def nakshatra(longitude: float) -> dict[str, object]:
    sector = 360.0 / 27.0
    pos = normalize(longitude)
    index = min(26, int(pos / sector))
    pada = min(4, int((pos - index * sector) / (sector / 4.0)) + 1)
    return {"index": index, "name": NAKSHATRAS[index], "pada": pada}

def navamsa_sign(longitude: float) -> str:
    """D9 sign by 3 degree 20 minute sidereal segments across zodiac."""
    step = 30.0 / 9.0
    index = int(normalize(longitude) / step) % 12
    return SIGNS[index]

def whole_sign_house(longitude: float, ascendant: float) -> int:
    return (sign_index(longitude) - sign_index(ascendant)) % 12 + 1
