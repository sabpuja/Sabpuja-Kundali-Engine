"""Independence guard for the reference generator (qa-architecture.md section 6).

The generator must never see the engine: no import of the engine package or
of Swiss Ephemeris bindings, no reading of engine report files, and no
dynamic import or exec that a static scan cannot check. Expected values may
only come from independent reference classes (I-code, I-data, I-pub).
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import ast
import importlib.abc
import sys

FORBIDDEN_ROOTS = ("sabpuja_kundali", "swisseph")
FORBIDDEN_PATH_MARKERS = ("reports", "golden-report")
INDEPENDENT_CLASSES = ("I-code", "I-data", "I-pub")
_IMPORT_CALLS = {"__import__", "import_module", "find_spec", "run_module", "run_path", "load_module"}
_DYNAMIC_CALLS = {"exec", "eval", "compile"}
_FILE_CALLS = {"open", "Path", "PurePath", "read_text", "read_bytes", "load", "loads", "loadtxt", "glob"}


def _forbidden_module(name: str) -> bool:
    return any(name == root or name.startswith(root + ".") for root in FORBIDDEN_ROOTS)


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def scan_source(text: str, filename: str = "<source>") -> list[str]:
    """Static violations in one Python source. A syntax error is a violation."""
    try:
        tree = ast.parse(text, filename=filename)
    except SyntaxError as exc:
        return [f"{filename}: cannot parse ({exc.msg})"]
    found = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", 0)
        if isinstance(node, ast.Import):
            found += [f"{filename}:{line}: imports {a.name}" for a in node.names if _forbidden_module(a.name)]
        elif isinstance(node, ast.ImportFrom):
            # Relative imports stay inside the generator package.
            if node.level == 0 and node.module and _forbidden_module(node.module):
                found.append(f"{filename}:{line}: imports from {node.module}")
        elif isinstance(node, ast.Call):
            name = _call_name(node)
            literals = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
            if name in _IMPORT_CALLS:
                if len(literals) != len(node.args) or not node.args:
                    found.append(f"{filename}:{line}: dynamic {name} with a non-literal name")
                found += [f"{filename}:{line}: {name}({v!r})" for v in literals if _forbidden_module(v)]
            elif name in _DYNAMIC_CALLS:
                found.append(f"{filename}:{line}: {name} is not allowed in the generator")
            elif name in _FILE_CALLS:
                found += [f"{filename}:{line}: reads engine output path {v!r}" for v in literals
                          if any(m in v for m in FORBIDDEN_PATH_MARKERS)]
    return found


def scan_directory(directory: Path) -> list[str]:
    """Scan every .py file under the generator directory, recursively."""
    if not directory.is_dir():
        return [f"generator directory missing: {directory.name}"]
    found = []
    for path in sorted(directory.rglob("*.py")):
        rel = path.relative_to(directory).as_posix()
        found += scan_source(path.read_text(encoding="utf-8"), rel)
    return found


def loaded_forbidden_modules() -> list[str]:
    """Forbidden modules already imported into this process (the guard cannot undo those)."""
    return sorted(name for name in sys.modules if _forbidden_module(name))


class _Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if _forbidden_module(fullname):
            raise ImportError(f"{fullname} is forbidden in the reference generator")
        return None


@contextmanager
def import_guard():
    """Refuse forbidden imports for the duration of the block.

    Fails immediately if a forbidden module is already loaded, because a
    cached module would bypass the finder.
    """
    already = loaded_forbidden_modules()
    if already:
        raise ImportError(f"forbidden modules already loaded: {already}")
    blocker = _Blocker()
    sys.meta_path.insert(0, blocker)
    try:
        yield
    finally:
        sys.meta_path.remove(blocker)


def check_reference_classes(references: list[dict], registry: dict) -> list[str]:
    """Reasons a fixture's expected-value sources are not acceptable references."""
    reasons = []
    for ref in references:
        source_id = ref.get("source_id")
        entry = registry.get(source_id)
        if entry is None:
            reasons.append(f"REFERENCE_UNKNOWN: {source_id}")
        elif entry.get("class") not in INDEPENDENT_CLASSES:
            reasons.append(f"REFERENCE_CLASS_NOT_INDEPENDENT: {source_id} is class {entry.get('class')}")
        elif entry.get("obtained") is not True:
            reasons.append(f"REFERENCE_NOT_OBTAINED: {source_id}")
    return reasons
