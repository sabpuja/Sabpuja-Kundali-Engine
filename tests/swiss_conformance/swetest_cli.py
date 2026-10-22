"""Run the official standalone swetest as a separate process and parse its output strictly.

Only switches documented by swetest's own -h (and checked in its source) are
used; see spec.json. Output is accepted only if every non-empty line is a
known header line, the echo of our exact argv, or a "name, value" line with
11 decimals. Any warning or error line, including the silent Moshier
fallback swetest reports when a data file is missing, is surfaced to the
caller, which treats it as BLOCKED unless the case expects that refusal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import os
import re
import subprocess

PLANET_ARGS = ("-ut", "-sid1", "-i65538", "-p0123456m", "-fPl", "-ep", "-g,")
HOUSE_ARGS = ("-ut", "-sid1", "-i65536", "-p", "-fPl", "-ep", "-g,")
HEADER_PREFIXES = ("date (dmy)", "UT:", "TT:", "geo. long", "Epsilon", "Nutation", "Houses system")
_VALUE = re.compile(r"^(?P<name>[A-Za-z][A-Za-z0-9 .-]*?)\s*,\s*(?P<value>-?\d+\.\d{11})$")
_VERSION = re.compile(r"\bversion (\d+\.\d+\.\d+)\s*$")
_UT = re.compile(r"^UT:\s+(\d+\.\d{9})\s")
_AYANAMSA = re.compile(r"ayanamsa = .*\((?P<name>[^)]*)\)\s*$")
TIMEOUT_S = 60


class SwetestOutputError(ValueError):
    """swetest output did not have the expected shape. Message never contains raw output."""


@dataclass
class SwetestRun:
    argv: list[str]          # redacted: <SWETEST>, <EPHE>
    exit_code: int | None
    stdout: str              # redacted
    stderr: str              # redacted
    version: str | None = None
    ut_jd: float | None = None
    ayanamsa_name: str | None = None
    values: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jd_arg(jd: float) -> str:
    """repr() gives the shortest string that round-trips the double exactly through %lf."""
    text = repr(float(jd))
    if float(text) != jd:
        raise ValueError("JD does not round-trip")
    return "-bj" + text


def planet_argv(swetest: str, ephe: str, jd: float) -> list[str]:
    return [swetest, f"-edir{ephe}", jd_arg(jd), *PLANET_ARGS]


def house_argv(swetest: str, ephe: str, jd: float, lat: float, lon: float) -> list[str]:
    return [swetest, f"-edir{ephe}", jd_arg(jd), *HOUSE_ARGS, f"-house{lon!r},{lat!r},P"]


def redact(text: str, swetest: str, ephe: str) -> str:
    # Longest first so a path containing the other is replaced whole.
    for real, label in sorted(((swetest, "<SWETEST>"), (ephe, "<EPHE>")), key=lambda p: -len(p[0])):
        if real:
            text = text.replace(real, label)
    return text


def parse(stdout: str, echo: str) -> tuple[str, float, str | None, dict[str, float], list[str]]:
    """Return (version, ut_jd, ayanamsa_name, values, warnings) or raise SwetestOutputError."""
    lines = [line.rstrip() for line in stdout.splitlines()]
    nonempty = [line for line in lines if line.strip()]
    if not nonempty or nonempty[0] != echo.rstrip():
        raise SwetestOutputError("first line is not the echo of the exact command")
    version = ut_jd = ayanamsa = None
    values: dict[str, float] = {}
    warnings: list[str] = []
    for line in nonempty[1:]:
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered.startswith(("warning", "error")) or "moshier" in lowered:
            warnings.append(stripped)
            continue
        if stripped.startswith(HEADER_PREFIXES):
            if stripped.startswith("date (dmy)"):
                match = _VERSION.search(stripped)
                if not match:
                    raise SwetestOutputError("date line without version")
                version = match.group(1)
            elif stripped.startswith("UT:"):
                match = _UT.match(stripped)
                if not match:
                    raise SwetestOutputError("malformed UT line")
                ut_jd = float(match.group(1))
            elif stripped.startswith("TT:"):
                match = _AYANAMSA.search(stripped)
                ayanamsa = match.group("name") if match else None
            continue
        match = _VALUE.match(stripped)
        if not match:
            raise SwetestOutputError("unrecognised output line")
        name = " ".join(match.group("name").split())
        if name in values:
            raise SwetestOutputError("duplicate value line")
        values[name] = float(match.group("value"))
    if version is None or ut_jd is None:
        raise SwetestOutputError("header missing version or UT line")
    return version, ut_jd, ayanamsa, values, warnings


def run(argv: list[str], ephe: str) -> SwetestRun:
    """Run swetest without a shell, with SE_EPHE_PATH removed, and parse its output.

    Raises SwetestOutputError for malformed output; OSError if it cannot start.
    """
    env = {k: v for k, v in os.environ.items() if k != "SE_EPHE_PATH"}
    proc = subprocess.run(argv, capture_output=True, timeout=TIMEOUT_S, env=env, check=False)
    stdout = redact(proc.stdout.decode("utf-8", errors="replace"), argv[0], ephe)
    stderr = redact(proc.stderr.decode("utf-8", errors="replace"), argv[0], ephe)
    shown = [redact(a, argv[0], ephe) for a in argv]
    result = SwetestRun(argv=shown, exit_code=proc.returncode, stdout=stdout, stderr=stderr)
    if proc.returncode != 0:
        return result
    version, ut_jd, ayanamsa, values, warnings = parse(stdout, " ".join(shown) + " ")
    result.version, result.ut_jd, result.ayanamsa_name = version, ut_jd, ayanamsa
    result.values, result.warnings = values, warnings + ([stderr.strip()] if stderr.strip() else [])
    return result
