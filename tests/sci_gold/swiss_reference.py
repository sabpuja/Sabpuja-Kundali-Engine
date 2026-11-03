"""KUN-SCI-GOLD-001 official swetest reference receipts: capture, parse, verify.

For each chart fixture the reference instant is the fixture's expected UTC
(derived from the quoted IANA rule text, not from the engine). Its Julian Day is
computed exactly here (Unix epoch = JD 2440587.5) and rounded once to a double,
then passed to the separately built official swetest (Swiss C 2.10.03 from
aloistr/swisseph@c69c14a) as four separate processes:

  A  planets  -ut -sid1 -i65538 -p0123456m -fPl  -ep -g,        (frozen KUN-01-SWISS-01 switches)
  B  speeds   -ut -sid1 -i65794 -p0123456m -fPls -ep -g,        (adds SEFLG_SPEED: retrograde evidence only)
  C  houses   -ut -sid1 -i65536 -p -fPl -ep -g, -house<lon>,<lat>,W   (engine's ascendant vehicle, b"W")
  D  obliq.   -ut -po -fPlbr -ep -g,                            (true obliquity, tropical, for the Lagna formula)

The redacted stdout of each run is the "original reference evidence" and is
committed under receipts/<fixture>.txt with a SHA-256 in receipts/SHA256SUMS.
Paths are replaced by <SWETEST> and <EPHE>. Swiss-on-Swiss: same C library as
the engine; never independent astronomy.
"""
from __future__ import annotations

from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
import hashlib
import os
import re
import subprocess

HERE = Path(__file__).resolve().parent
RECEIPTS = HERE / "receipts"
UNIX_EPOCH_JD = Fraction(4881175, 2)     # JD 2440587.5 = 1970-01-01T00:00:00 UT, exactly

RUNS = {
    "A": ("-ut", "-sid1", "-i65538", "-p0123456m", "-fPl", "-ep", "-g,"),
    "B": ("-ut", "-sid1", "-i65794", "-p0123456m", "-fPls", "-ep", "-g,"),
    "C": ("-ut", "-sid1", "-i65536", "-p", "-fPl", "-ep", "-g,"),
    "D": ("-ut", "-po", "-fPlbr", "-ep", "-g,"),
}
NAMES = {"Sun": "sun", "Moon": "moon", "Mercury": "mercury", "Venus": "venus", "Mars": "mars",
         "Jupiter": "jupiter", "Saturn": "saturn", "mean Node": "rahu_mean"}
_NUM = r"-?\d+\.\d+"
_A = re.compile(rf"^(?P<name>[A-Za-z][A-Za-z0-9 .-]*?)\s*,\s*(?P<lon>{_NUM})$")
_B = re.compile(rf"^(?P<name>[A-Za-z][A-Za-z .]*?)\s*,\s*(?P<lon>{_NUM}),\s*(?P<speed>{_NUM})$")
_D = re.compile(rf"^Ecl\. Obl\.\s*,\s*(?P<true>{_NUM}),\s*(?P<mean>{_NUM}),\s*{_NUM}$")
_VERSION = re.compile(r"\bversion (\d+\.\d+\.\d+)\s*$")
_UT = re.compile(r"^UT:\s+(\d+\.\d{9})\s")
_AYAN = re.compile(r"ayanamsa =\s+(\d+)°\s*(\d+)'\s*(\d+\.\d+) \((?P<name>[^)]*)\)\s*$")


class ReceiptError(ValueError):
    pass


def exact_jd(utc_text: str) -> Fraction:
    """Exact JD(UT) of an ISO 'YYYY-MM-DDTHH:MM:SS[.ffffff]Z' instant, by integer arithmetic."""
    if not utc_text.endswith("Z"):
        raise ValueError("expected a Z instant")
    dt = datetime.fromisoformat(utc_text[:-1]).replace(tzinfo=timezone.utc)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = dt - epoch
    micro = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
    return UNIX_EPOCH_JD + Fraction(micro, 86_400_000_000)


def jd_double(utc_text: str) -> float:
    return float(exact_jd(utc_text))   # correctly rounded


def argv(run: str, swetest: str, ephe: str, jd: float, lat: float | None = None, lon: float | None = None) -> list[str]:
    text = repr(float(jd))
    if float(text) != jd:
        raise ValueError("JD does not round-trip")
    out = [swetest, f"-edir{ephe}", "-bj" + text, *RUNS[run]]
    if run == "C":
        out.append(f"-house{lon!r},{lat!r},W")
    return out


def redact(text: str, swetest: str, ephe: str) -> str:
    for real, label in sorted(((swetest, "<SWETEST>"), (ephe, "<EPHE>")), key=lambda p: -len(p[0])):
        text = text.replace(real, label)
    return text


def capture(fixture: dict, swetest: str, ephe: str) -> str:
    """Run A-D for one fixture and return the receipt text (deterministic)."""
    utc = fixture["time_reference"]["expected_utc"]
    jd = jd_double(utc)
    lat, lon = fixture["input"]["latitude"], fixture["input"]["longitude"]
    env = {k: v for k, v in os.environ.items() if k != "SE_EPHE_PATH"}
    parts = [f"# KUN-SCI-GOLD-001 swetest receipt {fixture['id']}", f"# expected_utc {utc}",
             f"# exact_jd {exact_jd(utc)}", f"# jd_double {jd!r}"]
    for run in "ABCD":
        cmd = argv(run, swetest, ephe, jd, lat, lon)
        proc = subprocess.run(cmd, capture_output=True, timeout=60, env=env, check=False)
        parts.append(f"## RUN {run} exit={proc.returncode}")
        parts.append(redact(proc.stdout.decode("utf-8", "replace"), swetest, ephe).rstrip("\n"))
        err = redact(proc.stderr.decode("utf-8", "replace"), swetest, ephe).strip()
        if err:
            parts.append(f"## STDERR {run}")
            parts.append(err)
    return "\n".join(parts) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse(text: str) -> dict:
    """Parse a committed receipt strictly. Raises ReceiptError on any unexpected shape."""
    sections, current = {}, None
    header = {}
    for line in text.splitlines():
        if line.startswith("## STDERR"):
            raise ReceiptError("swetest wrote to stderr")
        if line.startswith("## RUN "):
            run, code = line[7], line.split("exit=")[1]
            if code != "0":
                raise ReceiptError(f"run {run} exit {code}")
            current = sections.setdefault(run, [])
            continue
        if current is None:
            if line.startswith("# "):
                key, _, value = line[2:].partition(" ")
                header[key] = value
            continue
        current.append(line)
    if set(sections) != set("ABCD"):
        raise ReceiptError("missing run")
    out = {"header": header, "version": set(), "ut": set(), "planets": {}, "speeds": {}, "ascendant": None,
           "armc": None, "ayanamsa": None, "ayanamsa_text": None, "eps_true": None, "eps_mean": None}
    for run, lines in sections.items():
        lines = [x.strip() for x in lines if x.strip()]
        if not lines or not lines[0].startswith("<SWETEST> -edir<EPHE> -bj"):
            raise ReceiptError("first line is not the command echo")
        for line in lines[1:]:
            low = line.lower()
            if low.startswith(("warning", "error")) or "moshier" in low:
                raise ReceiptError("swetest warning or fallback")
            if line.startswith("date (dmy)"):
                m = _VERSION.search(line)
                if not m:
                    raise ReceiptError("no version")
                out["version"].add(m.group(1))
            elif line.startswith("UT:"):
                m = _UT.match(line)
                if not m:
                    raise ReceiptError("bad UT")
                out["ut"].add(m.group(1))
            elif line.startswith("TT:"):
                m = _AYAN.search(line)
                if m:
                    if m["name"] != "Lahiri":
                        raise ReceiptError("ayanamsa is not Lahiri")
                    text_val = f"{m.group(1)} {m.group(2)} {m.group(3)}"
                    val = Fraction(int(m.group(1))) + Fraction(int(m.group(2)), 60) + Fraction(m.group(3)) / 3600
                    if out["ayanamsa"] is not None and out["ayanamsa"] != val:
                        raise ReceiptError("ayanamsa differs between runs")
                    out["ayanamsa"], out["ayanamsa_text"] = val, text_val
            elif line.startswith(("geo. long", "Epsilon", "Nutation", "Houses system")):
                continue
            elif run == "A":
                m = _A.match(line)
                if not m or m["name"] not in NAMES:
                    raise ReceiptError("unexpected planet line")
                out["planets"][NAMES[m["name"]]] = m["lon"]
            elif run == "B":
                m = _B.match(line)
                if not m or m["name"] not in NAMES:
                    raise ReceiptError("unexpected speed line")
                out["speeds"][NAMES[m["name"]]] = (m["lon"], m["speed"])
            elif run == "C":
                m = _A.match(line)
                if not m:
                    raise ReceiptError("unexpected house line")
                name = " ".join(m["name"].split())
                if name == "Ascendant":
                    out["ascendant"] = m["lon"]
                elif name == "ARMC":
                    out["armc"] = m["lon"]
            elif run == "D":
                m = _D.match(line)
                if not m:
                    raise ReceiptError("unexpected obliquity line")
                out["eps_true"], out["eps_mean"] = m["true"], m["mean"]
    if out["version"] != {"2.10.03"}:
        raise ReceiptError("swetest version is not 2.10.03")
    if len(out["ut"]) != 1 or set(out["planets"]) != set(NAMES.values()) or out["ascendant"] is None \
            or out["armc"] is None or out["ayanamsa"] is None or out["eps_true"] is None:
        raise ReceiptError("incomplete receipt")
    if set(out["speeds"]) != set(NAMES.values()):
        raise ReceiptError("incomplete speed run")
    out["ut"] = out["ut"].pop()
    out["version"] = "2.10.03"
    return out
