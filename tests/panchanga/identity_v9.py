"""PAN-QA-08 identity gate, version 9 (KUN-PAN-RPT-002, issue #83).

v1 to v8 are preserved byte for byte; their SHA-256 values stay pinned in `identity_v2.py` to `identity_v8.py`.
v8 is now proved on the exact tree of its audited commit `c759c41` (the head of draft PR #82, the v9 base),
and v7 on `a8c3108` as before.

v9 declares, in `identity-manifest-v9.json` (pinned below), the change of KUN-PAN-RPT-002 inside the v1 scope:

* `modified`: the three report files the opt-in sunrise and Vara edition changes (`report/phase1/README.md`,
  `report/phase1/panchanga_report.py`, `report/phase1/premium_report.py`), each with its SHA-256 at c759c41
  and its new SHA-256 and git blob ID;
* `added`: the engine document module `src/sabpuja_kundali/panchanga/vara.py`, the page module and its
  catalog, the 25 synthetic fixtures, the 100 pinned 14-page hashes, the tests and two developer tools;
* `package`: every file of the Panchanga package at c759c41 (the M1 code and the accepted `sun.py`), pinned by
  SHA-256 and blob, so v9 proves both byte-identical to their accepted base.

Nothing else may change: no chart engine, M1, sun module, data, preview, prototype, terminology register or
existing report catalog. The v5 packet and the frozen part of the decision record are carried over. Unlike v1,
an undeclared file in the Panchanga package fails. `git diff c759c41 <commit>` restricted to the v1 scope, the
declared paths, the packet and the record must be exactly the v9 declaration. Regenerate and compare:
    python -m tests.panchanga.identity_v9 --check
"""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from . import identity_v2 as v2m
from . import identity_v3 as v3m
from . import identity_v4 as v4m
from . import identity_v5 as v5m
from . import identity_v6 as v6m
from . import identity_v7 as v7m
from . import identity_v8 as v8m
from .identity_v2 import IdentityError, HEX40, HEX64, REPO, blob_id, sha256

V9_PATH = "tests/panchanga/identity-manifest-v9.json"
V9_SHA256 = "0000000000000000000000000000000000000000000000000000000000000000"
SCHEMA = "sabpuja-pan-qa-08-identity/9"
TASK = "KUN-PAN-RPT-002"
BASE_COMMIT = "c759c412b22753f7f5b6134e2aaaad0f04412007"   # draft PR #82 head after independent QA: the v8 tree
PACKET_PREFIX = v5m.PACKET_PREFIX
RECORD = v5m.RECORD
EXPECTED_UNCHANGED_V1 = 209

AUTHORIZED_MODIFIED = (
    "report/phase1/README.md",
    "report/phase1/panchanga_report.py",
    "report/phase1/premium_report.py",
)
_SCENARIOS = ("s01-first-supported-date", "s02-last-supported-date", "s03-crowded-d1-house", "s04-crowded-d9-house",
              "s05-graha-near-boundary", "s06-lagna-near-boundary", "s07-noon", "s08-dawn", "s09-evening",
              "s10-late-night", "s11-afternoon", "s12-morning", "s13-remaining-lagna")
_CASES = ("v01-typical-afternoon", "v02-pre-sunrise-previous-vara", "v03-first-second-after-sunrise",
          "v04-last-second-before-sunrise", "v05-inside-band-after", "v06-outside-band-after",
          "v07-london-clocks-forward", "v08-london-repeated-hour", "v09-dateline-kiritimati",
          "v10-polar-day-unavailable", "v11-vara-day-end-undefined", "v12-sunset-after-midnight")
AUTHORIZED_ADDED = tuple(sorted(
    ["report/phase1/report_vara_i18n.json",
     "report/phase1/tests/fixtures/extended-14-page-vara-sha256.json",
     "report/phase1/tests/test_vara_report.py",
     "report/phase1/tools/make_vara_fixtures.py",
     "report/phase1/tools/make_vara_pins.py",
     "report/phase1/vara_report.py",
     "src/sabpuja_kundali/panchanga/vara.py"]
    + [f"report/phase1/tests/fixtures/vara/{s}.json" for s in _SCENARIOS]
    + [f"report/phase1/tests/fixtures/vara-cases/{c}.json" for c in _CASES]))
NOTE = ("PAN-QA-08 identity manifest v9 (KUN-PAN-RPT-002). Declares the change relative to c759c41 (draft PR #82, "
        "the v8 tree) inside the v1 scope: three modified report files and the added files of the opt-in sunrise "
        "and Vara edition (engine document module, page module, catalog, synthetic fixtures, pinned 14-page hashes, "
        "tests and tools). The Panchanga package at c759c41 (M1 and the accepted sun module) is pinned unchanged. "
        "v1 to v8 are preserved and bound here by their SHA-256. Generated from git objects only: "
        "python -m tests.panchanga.identity_v9 --check.")


def v8_expectations(v1, v2, v3, v4, v5, v6, v7, v8) -> dict:
    """{path: (sha256, git_blob or None, label)} as v1 to v8 declare them (the record excluded)."""
    exp = v8m.v7_expectations(v1, v2, v3, v4, v5, v6, v7)
    for p, e in v8["m1_package"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v8 M1 package")
    for p, e in v8["added"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v8 added")
    return exp


def _entry(e, keys, where):
    if not isinstance(e, dict) or set(e) != set(keys) or not all(isinstance(e[k], str) for k in keys):
        raise IdentityError(f"v9 {where} entry malformed")
    for k in keys:
        if not (HEX40 if k.endswith("git_blob") else HEX64).fullmatch(e[k]):
            raise IdentityError(f"v9 {where} entry malformed")


def _v8_binding(v8_bytes: bytes) -> dict:
    return {"path": v8m.V8_PATH, "sha256": sha256(v8_bytes), "base_commit": BASE_COMMIT,
            "v7_sha256": v7m.V7_SHA256, "v6_sha256": v6m.V6_SHA256, "v5_sha256": v5m.V5_SHA256,
            "v4_sha256": v4m.V4_SHA256, "v3_sha256": v3m.V3_SHA256, "v2_sha256": v2m.V2_SHA256,
            "v1_sha256": v2m.V1_SHA256}


def validate_v9(doc, v1, v2, v3, v4, v5, v6, v7, v8, v8_bytes: bytes) -> dict:
    if not isinstance(doc, dict):
        raise IdentityError("v9 manifest must be an object")
    keys = {"manifest_schema", "note", "task", "v8_manifest", "package", "modified", "added", "counts"}
    if set(doc) != keys:
        raise IdentityError(f"v9 manifest keys differ: {sorted(set(doc) ^ keys)}")
    if doc["manifest_schema"] != SCHEMA or doc["task"] != TASK:
        raise IdentityError("v9 manifest_schema or task wrong")
    if not isinstance(doc["note"], str) or not doc["note"]:
        raise IdentityError("v9 note missing")
    if doc["v8_manifest"] != _v8_binding(v8_bytes) or sha256(v8_bytes) != v8m.V8_SHA256:
        raise IdentityError("v9 v8_manifest record does not bind the preserved v1 to v8 manifests")
    mod, added, package = doc["modified"], doc["added"], doc["package"]
    if not all(isinstance(x, dict) for x in (mod, added, package)):
        raise IdentityError("v9 modified/added/package must be objects")
    if tuple(mod) != AUTHORIZED_MODIFIED:
        raise IdentityError("v9 modified paths differ from the authorized KUN-PAN-RPT-002 paths")
    if tuple(added) != AUTHORIZED_ADDED:
        raise IdentityError("v9 added paths differ from the authorized KUN-PAN-RPT-002 paths")
    if doc["counts"] != {"modified": len(mod), "added": len(added), "package": len(package)}:
        raise IdentityError("v9 counts wrong")
    prior = v8_expectations(v1, v2, v3, v4, v5, v6, v7, v8)
    if not package or not all(p.startswith(v2m.PANCHANGA_PACKAGE_PREFIX) for p in package):
        raise IdentityError("v9 package must list the Panchanga package files")
    for p, e in package.items():
        _entry(e, ("sha256", "git_blob"), f"package {p}:")
        if p not in prior or prior[p][0] != e["sha256"] or prior[p][1] != e["git_blob"]:
            raise IdentityError(f"v9 package entry is not the v8 pin: {p}")
    if set(package) & set(added):
        raise IdentityError("v9 added path is also listed as a package file")
    for p, e in mod.items():
        _entry(e, ("before_sha256", "v9_sha256", "v9_git_blob"), f"modified {p}:")
        if p not in prior:
            raise IdentityError(f"v9 modified path is not pinned by v1 to v8: {p}")
        if e["before_sha256"] != prior[p][0]:
            raise IdentityError(f"v9 modified entry before_sha256 differs from {prior[p][2]}: {p}")
        if e["v9_sha256"] == e["before_sha256"]:
            raise IdentityError(f"v9 modified entry declares no change: {p}")
    for p, e in added.items():
        _entry(e, ("sha256", "git_blob"), f"added {p}:")
        if p in prior or p == RECORD:
            raise IdentityError(f"v9 added path is already pinned by v1 to v8: {p}")
        if not v2m.in_scope(p) or p.startswith(PACKET_PREFIX):
            raise IdentityError(f"v9 added path is outside the v1 scope or inside the packet: {p}")
    return doc


def load_v9(data: bytes, v1, v2, v3, v4, v5, v6, v7, v8, v8_bytes: bytes, expected_sha: str = None) -> dict:
    expected_sha = V9_SHA256 if expected_sha is None else expected_sha
    if sha256(data) != expected_sha:
        raise IdentityError("v9 manifest does not match its pinned SHA-256")
    try:
        doc = json.loads(data, object_pairs_hook=v2m._reject_duplicate_keys)
    except ValueError as exc:
        raise IdentityError(f"v9 manifest is not valid JSON: {exc}") from None
    return validate_v9(doc, v1, v2, v3, v4, v5, v6, v7, v8, v8_bytes)


def load_committed(root: Path = REPO):
    root = Path(root)
    v1, v2, v3, v4, v5, v6, v7, v8 = v8m.load_committed(root)
    v8_bytes = (root / v8m.V8_PATH).read_bytes()
    return v1, v2, v3, v4, v5, v6, v7, v8, load_v9((root / V9_PATH).read_bytes(), v1, v2, v3, v4, v5, v6, v7, v8,
                                                   v8_bytes)


def expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9) -> dict:
    exp = v8_expectations(v1, v2, v3, v4, v5, v6, v7, v8)
    for p, e in v9["package"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v9 package (c759c41)")
    for p, e in v9["modified"].items():
        exp[p] = (e["v9_sha256"], e["v9_git_blob"], "v9 modified")
    for p, e in v9["added"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v9 added")
    return exp


def verify_tree(root: Path, v1, v2, v3, v4, v5, v6, v7, v8, v9, *, read=None, listing=None,
                packet_listing=None) -> dict:
    """v1 to v8 expectations with the v9 overlay, on the working tree (or, via read/listing, on a commit)."""
    root = Path(root)

    def digest(rel):
        target = root / rel
        if target.is_symlink() or not target.is_file():
            return None
        return target.read_bytes()
    read = read or digest
    exp = expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9)
    problems, unchanged = [], 0
    for p in sorted(exp):
        want_sha, want_blob, label = exp[p]
        data = read(p)
        if data is None:
            problems.append(f"missing: {p}")
        elif sha256(data) != want_sha or (want_blob is not None and blob_id(data) != want_blob):
            problems.append(f"undeclared change to a v1 file: {p}" if label == "v1"
                            else f"unexpected hash (declared {label}): {p}")
        elif label == "v1":
            unchanged += 1
    record = read(RECORD)
    if record is None:
        problems.append(f"missing: {RECORD}")
    else:
        try:
            if sha256(v5m.record_projection(record)) != v5["record"]["projection_sha256"]:
                problems.append(f"decision record changed outside its decision fields: {RECORD}")
        except IdentityError as exc:
            problems.append(f"{exc}: {RECORD}")
    present = listing() if listing else v2m._scope_files(root)
    for p in sorted(present - set(exp)):
        problems.append(f"undeclared file in v1 scope (v9 counts the Panchanga package too): {p}")
    in_packet = packet_listing() if packet_listing else v4m._packet_listing(root)
    for p in sorted(in_packet - set(v5["packet"]) - {RECORD}):
        problems.append(f"undeclared file in the editorial packet: {p}")
    if problems:
        raise IdentityError("PAN-QA-08 v9 identity failed:\n  " + "\n  ".join(problems))
    if unchanged != EXPECTED_UNCHANGED_V1:
        raise IdentityError(f"expected {EXPECTED_UNCHANGED_V1} byte-identical v1 files, found {unchanged}")
    return {"v1_unchanged": unchanged, "v5_packet": len(v5["packet"]), "v5_record": 1,
            "v9_package": len(v9["package"]), "v9_modified": len(v9["modified"]), "v9_added": len(v9["added"])}


def verify_commit(root: Path, commit: str, v1, v2, v3, v4, v5, v6, v7, v8, v9) -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    names = [n for n in git.run("ls-tree", "-r", "-z", "--name-only", commit).split("\0") if n]
    exp = set(expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9)) | {RECORD}
    blobs = git.blobs(commit, sorted(exp))
    return verify_tree(root, v1, v2, v3, v4, v5, v6, v7, v8, v9, read=blobs.get,
                       listing=lambda: {n for n in names if v2m.in_scope(n)},
                       packet_listing=lambda: {n for n in names if n.startswith(PACKET_PREFIX)})


def verify_git_v9(root: Path, v1, v2, v3, v4, v5, v6, v7, v8, v9, commit: str = "HEAD") -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    if git.run("cat-file", "-t", BASE_COMMIT).strip() != "commit":
        raise IdentityError(f"{BASE_COMMIT} is not a commit here")
    sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
    if git.run("merge-base", BASE_COMMIT, sha).strip() != BASE_COMMIT:
        raise IdentityError("c759c41 is not an ancestor of the commit under test")
    # The base itself is exactly the v8 tree: v8 regenerates there and a8c3108..c759c41 is the v8 declaration.
    if v8m.generate(root, commit=BASE_COMMIT) != git.blobs(BASE_COMMIT, [v8m.V8_PATH])[v8m.V8_PATH]:
        raise IdentityError("v8 does not regenerate at c759c41")
    v8m.verify_git_v8(root, v1, v2, v3, v4, v5, v6, v7, v8, commit=BASE_COMMIT)
    paths = list(v9["modified"]) + list(v9["added"]) + list(v9["package"])
    at_base, at_head = git.blobs(BASE_COMMIT, paths), git.blobs(sha, paths)
    problems = []
    base_pkg = {n for n in git.run("ls-tree", "-r", "-z", "--name-only", BASE_COMMIT).split("\0")
                if n.startswith(v2m.PANCHANGA_PACKAGE_PREFIX)}
    if base_pkg != set(v9["package"]):
        problems.append("v9 package is not exactly the Panchanga package at c759c41")
    for p, e in v9["package"].items():
        for where, data in (("c759c41", at_base[p]), (sha[:7], at_head[p])):
            if data is None or sha256(data) != e["sha256"] or blob_id(data) != e["git_blob"]:
                problems.append(f"Panchanga package file differs from v9 at {where}: {p}")
    for p, e in v9["modified"].items():
        if at_base[p] is None or sha256(at_base[p]) != e["before_sha256"]:
            problems.append(f"v9 before_sha256 differs from the c759c41 git object: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["v9_sha256"] or blob_id(at_head[p]) != e["v9_git_blob"]:
            problems.append(f"v9 modified hash differs from the committed object: {p}")
    for p, e in v9["added"].items():
        if at_base[p] is not None:
            problems.append(f"v9 added path already exists at c759c41: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["sha256"] or blob_id(at_head[p]) != e["git_blob"]:
            problems.append(f"v9 added hash differs from the committed object: {p}")
    prior = v8_expectations(v1, v2, v3, v4, v5, v6, v7, v8)
    side = {p: s for p, s in git.name_status(BASE_COMMIT, sha).items()
            if v7m._scope_or_declared(p, prior) or p == RECORD}
    expect = {**{p: "M" for p in v9["modified"]}, **{p: "A" for p in v9["added"]}}
    if RECORD in side and side[RECORD] == "M":
        expect[RECORD] = "M"   # decision fields may be recorded (frozen part checked by the tree step)
    if side != expect:
        problems.append(f"c759c41..{sha[:7]} differs from the v9 declaration: "
                        f"{sorted(set(side.items()) ^ set(expect.items()))}")
    if problems:
        raise IdentityError("PAN-QA-08 v9 exact-commit check failed:\n  " + "\n  ".join(problems))
    return {"commit": sha, **verify_commit(root, sha, v1, v2, v3, v4, v5, v6, v7, v8, v9)}


def generate(root: Path, commit: str = "HEAD", worktree: bool = False) -> bytes:
    """Build v9 from c759c41 and `commit` (or, for --write before committing, the working tree)."""
    root = Path(root)
    git = v2m.Git(root)
    v8_bytes = git.blobs(BASE_COMMIT, [v8m.V8_PATH])[v8m.V8_PATH]
    paths = list(AUTHORIZED_MODIFIED) + list(AUTHORIZED_ADDED)
    if worktree:
        cur = {p: (root / p).read_bytes() if (root / p).is_file() else None for p in paths}
    else:
        sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
        cur = git.blobs(sha, paths)
    missing = [p for p in paths if cur[p] is None]
    if missing:
        raise IdentityError(f"cannot generate v9: missing {missing}")
    before = git.blobs(BASE_COMMIT, list(AUTHORIZED_MODIFIED))
    mod = {p: {"before_sha256": sha256(before[p]), "v9_sha256": sha256(cur[p]), "v9_git_blob": blob_id(cur[p])}
           for p in AUTHORIZED_MODIFIED}
    added = {p: {"sha256": sha256(cur[p]), "git_blob": blob_id(cur[p])} for p in AUTHORIZED_ADDED}
    names = sorted(n for n in git.run("ls-tree", "-r", "-z", "--name-only", BASE_COMMIT).split("\0")
                   if n.startswith(v2m.PANCHANGA_PACKAGE_PREFIX))
    base = git.blobs(BASE_COMMIT, names)
    package = {p: {"sha256": sha256(base[p]), "git_blob": blob_id(base[p])} for p in names}
    doc = {"manifest_schema": SCHEMA, "note": NOTE, "task": TASK, "v8_manifest": _v8_binding(v8_bytes),
           "package": package, "modified": mod, "added": added,
           "counts": {"modified": len(mod), "added": len(added), "package": len(package)}}
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="regenerate from HEAD; verify tree, v8 base and v9 on git")
    g.add_argument("--write", action="store_true", help="write the manifest from the working tree (developer use)")
    args = ap.parse_args(argv)
    if args.write:
        data = generate(REPO, worktree=True)
        (REPO / V9_PATH).write_bytes(data)
        print(f"wrote {V9_PATH} sha256 {sha256(data)}")
        return 0
    if (REPO / V9_PATH).read_bytes() != generate(REPO):
        print("FAIL: committed v9 manifest differs from the git-derived regeneration at HEAD")
        return 1
    v1, v2, v3, v4, v5, v6, v7, v8, v9 = load_committed(REPO)
    t = verify_tree(REPO, v1, v2, v3, v4, v5, v6, v7, v8, v9)
    g_ = verify_git_v9(REPO, v1, v2, v3, v4, v5, v6, v7, v8, v9)
    print(f"PASS v1 to v7 preserved (pinned in code); v8 {v8m.V8_SHA256} regenerates at c759c41 and "
          f"a8c3108..c759c41 is exactly the v8 declaration")
    print(f"PASS v9 sha256 {V9_SHA256} regenerated byte-identical from git objects at {g_['commit'][:7]}")
    print(f"PASS tree: {t['v1_unchanged']} v1 unchanged; Panchanga package ({t['v9_package']} files, M1 and sun.py) "
          f"byte-identical to c759c41; v9 {t['v9_modified']} modified, {t['v9_added']} added; no undeclared file")
    print(f"PASS git: c759c41..{g_['commit'][:7]} is exactly the v9 declaration")
    return 0


if __name__ == "__main__":
    sys.exit(main())
