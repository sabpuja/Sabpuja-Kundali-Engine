"""PAN-QA-08 identity gate, version 10 (KUN-RC-ESS-001: the frozen English Janam Kundali Essentials edition).

v1 to v9 are preserved byte for byte; their SHA-256 values stay pinned in `identity_v2.py` to `identity_v9.py`.
v9 is now proved on the exact tree of its audited commit `7d9d10a` (the head of draft PR #84, the v10 base),
and v8 on `c759c41` as before.

v10 declares, in `identity-manifest-v10.json` (pinned below), the change of KUN-RC-ESS-001 inside the v1 scope:

* `modified`: the four report files that gain the opt-in catalog overlay (`report/phase1/README.md`,
  `report/phase1/panchanga_report.py`, `report/phase1/premium_report.py`, `report/phase1/vara_report.py`), each
  with its SHA-256 at 7d9d10a and its new SHA-256 and git blob ID;
* `added`: the Essentials module, its English catalog, its edition manifest, its pinned hashes, its tests and the
  pin tool;
* `package`: every file of the Panchanga package at 7d9d10a (M1, `sun.py` and `vara.py`), pinned by SHA-256 and
  blob, so v10 proves them byte-identical to their accepted base.

Nothing else may change: no chart engine, Panchanga calculation, data, preview, prototype, terminology register
or existing report catalog. The v5 packet and the frozen part of the decision record are carried over.
`git diff 7d9d10a <commit>` restricted to the v1 scope, the declared paths, the packet and the record must be
exactly the v10 declaration. Regenerate and compare:
    python -m tests.panchanga.identity_v10 --check
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
from . import identity_v9 as v9m
from .identity_v2 import IdentityError, HEX40, HEX64, REPO, blob_id, sha256

V10_PATH = "tests/panchanga/identity-manifest-v10.json"
V10_SHA256 = "364813920ac3c99464364d6dfd433f80de2db90abef2ed2748c7fc819d284d9d"
SCHEMA = "sabpuja-pan-qa-08-identity/10"
TASK = "KUN-RC-ESS-001"
BASE_COMMIT = "7d9d10aeca82380946fe5435ee6d0b0c5fe79273"   # draft PR #84 head after independent QA: the v9 tree
PACKET_PREFIX = v5m.PACKET_PREFIX
RECORD = v5m.RECORD
EXPECTED_UNCHANGED_V1 = 209

AUTHORIZED_MODIFIED = (
    "report/phase1/README.md",
    "report/phase1/panchanga_report.py",
    "report/phase1/premium_report.py",
    "report/phase1/vara_report.py",
)
AUTHORIZED_ADDED = tuple(sorted((
    "report/phase1/essentials-edition-manifest.json",
    "report/phase1/essentials.py",
    "report/phase1/essentials_en.json",
    "report/phase1/tests/fixtures/essentials-en-sha256.json",
    "report/phase1/tests/test_essentials.py",
    "report/phase1/tools/make_essentials_pins.py",
)))
NOTE = ("PAN-QA-08 identity manifest v10 (KUN-RC-ESS-001). Declares the change relative to 7d9d10a (draft PR #84, "
        "the v9 tree) inside the v1 scope: four modified report files that gain an opt-in catalog overlay, and the "
        "added files of the frozen English Janam Kundali Essentials edition (module, English catalog, edition "
        "manifest, pinned hashes, tests and pin tool). The Panchanga package at 7d9d10a (M1, sun and vara modules) "
        "is pinned unchanged. v1 to v9 are preserved and bound here by their SHA-256. Generated from git objects "
        "only: python -m tests.panchanga.identity_v10 --check.")


def v9_expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9) -> dict:
    """{path: (sha256, git_blob or None, label)} as v1 to v9 declare them (the record excluded)."""
    return v9m.expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9)


def _entry(e, keys, where):
    if not isinstance(e, dict) or set(e) != set(keys) or not all(isinstance(e[k], str) for k in keys):
        raise IdentityError(f"v10 {where} entry malformed")
    for k in keys:
        if not (HEX40 if k.endswith("git_blob") else HEX64).fullmatch(e[k]):
            raise IdentityError(f"v10 {where} entry malformed")


def _v9_binding(v9_bytes: bytes) -> dict:
    return {"path": v9m.V9_PATH, "sha256": sha256(v9_bytes), "base_commit": BASE_COMMIT,
            "v8_sha256": v8m.V8_SHA256, "v7_sha256": v7m.V7_SHA256, "v6_sha256": v6m.V6_SHA256,
            "v5_sha256": v5m.V5_SHA256, "v4_sha256": v4m.V4_SHA256, "v3_sha256": v3m.V3_SHA256,
            "v2_sha256": v2m.V2_SHA256, "v1_sha256": v2m.V1_SHA256}


def validate_v10(doc, v1, v2, v3, v4, v5, v6, v7, v8, v9, v9_bytes: bytes) -> dict:
    if not isinstance(doc, dict):
        raise IdentityError("v10 manifest must be an object")
    keys = {"manifest_schema", "note", "task", "v9_manifest", "package", "modified", "added", "counts"}
    if set(doc) != keys:
        raise IdentityError(f"v10 manifest keys differ: {sorted(set(doc) ^ keys)}")
    if doc["manifest_schema"] != SCHEMA or doc["task"] != TASK:
        raise IdentityError("v10 manifest_schema or task wrong")
    if not isinstance(doc["note"], str) or not doc["note"]:
        raise IdentityError("v10 note missing")
    if doc["v9_manifest"] != _v9_binding(v9_bytes) or sha256(v9_bytes) != v9m.V9_SHA256:
        raise IdentityError("v10 v9_manifest record does not bind the preserved v1 to v9 manifests")
    mod, added, package = doc["modified"], doc["added"], doc["package"]
    if not all(isinstance(x, dict) for x in (mod, added, package)):
        raise IdentityError("v10 modified/added/package must be objects")
    if tuple(mod) != AUTHORIZED_MODIFIED:
        raise IdentityError("v10 modified paths differ from the authorized KUN-RC-ESS-001 paths")
    if tuple(added) != AUTHORIZED_ADDED:
        raise IdentityError("v10 added paths differ from the authorized KUN-RC-ESS-001 paths")
    if doc["counts"] != {"modified": len(mod), "added": len(added), "package": len(package)}:
        raise IdentityError("v10 counts wrong")
    prior = v9_expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9)
    if not package or not all(p.startswith(v2m.PANCHANGA_PACKAGE_PREFIX) for p in package):
        raise IdentityError("v10 package must list the Panchanga package files")
    for p, e in package.items():
        _entry(e, ("sha256", "git_blob"), f"package {p}:")
        if p not in prior or prior[p][0] != e["sha256"] or prior[p][1] != e["git_blob"]:
            raise IdentityError(f"v10 package entry is not the v9 pin: {p}")
    if set(package) & set(added):
        raise IdentityError("v10 added path is also listed as a package file")
    for p, e in mod.items():
        _entry(e, ("before_sha256", "v10_sha256", "v10_git_blob"), f"modified {p}:")
        if p not in prior:
            raise IdentityError(f"v10 modified path is not pinned by v1 to v9: {p}")
        if e["before_sha256"] != prior[p][0]:
            raise IdentityError(f"v10 modified entry before_sha256 differs from {prior[p][2]}: {p}")
        if e["v10_sha256"] == e["before_sha256"]:
            raise IdentityError(f"v10 modified entry declares no change: {p}")
    for p, e in added.items():
        _entry(e, ("sha256", "git_blob"), f"added {p}:")
        if p in prior or p == RECORD:
            raise IdentityError(f"v10 added path is already pinned by v1 to v9: {p}")
        if not v2m.in_scope(p) or p.startswith(PACKET_PREFIX):
            raise IdentityError(f"v10 added path is outside the v1 scope or inside the packet: {p}")
    return doc


def load_v10(data: bytes, v1, v2, v3, v4, v5, v6, v7, v8, v9, v9_bytes: bytes, expected_sha: str = None) -> dict:
    expected_sha = V10_SHA256 if expected_sha is None else expected_sha
    if sha256(data) != expected_sha:
        raise IdentityError("v10 manifest does not match its pinned SHA-256")
    try:
        doc = json.loads(data, object_pairs_hook=v2m._reject_duplicate_keys)
    except ValueError as exc:
        raise IdentityError(f"v10 manifest is not valid JSON: {exc}") from None
    return validate_v10(doc, v1, v2, v3, v4, v5, v6, v7, v8, v9, v9_bytes)


def load_committed(root: Path = REPO):
    root = Path(root)
    v1, v2, v3, v4, v5, v6, v7, v8, v9 = v9m.load_committed(root)
    v9_bytes = (root / v9m.V9_PATH).read_bytes()
    return v1, v2, v3, v4, v5, v6, v7, v8, v9, load_v10((root / V10_PATH).read_bytes(), v1, v2, v3, v4, v5, v6, v7,
                                                         v8, v9, v9_bytes)


def expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9, v10) -> dict:
    exp = v9_expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9)
    for p, e in v10["package"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v10 package (7d9d10a)")
    for p, e in v10["modified"].items():
        exp[p] = (e["v10_sha256"], e["v10_git_blob"], "v10 modified")
    for p, e in v10["added"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v10 added")
    return exp


def verify_tree(root: Path, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, *, read=None, listing=None,
                packet_listing=None) -> dict:
    """v1 to v9 expectations with the v10 overlay, on the working tree (or, via read/listing, on a commit)."""
    root = Path(root)

    def digest(rel):
        target = root / rel
        if target.is_symlink() or not target.is_file():
            return None
        return target.read_bytes()
    read = read or digest
    exp = expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9, v10)
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
        problems.append(f"undeclared file in v1 scope (v10 counts the Panchanga package too): {p}")
    in_packet = packet_listing() if packet_listing else v4m._packet_listing(root)
    for p in sorted(in_packet - set(v5["packet"]) - {RECORD}):
        problems.append(f"undeclared file in the editorial packet: {p}")
    if problems:
        raise IdentityError("PAN-QA-08 v10 identity failed:\n  " + "\n  ".join(problems))
    if unchanged != EXPECTED_UNCHANGED_V1:
        raise IdentityError(f"expected {EXPECTED_UNCHANGED_V1} byte-identical v1 files, found {unchanged}")
    return {"v1_unchanged": unchanged, "v5_packet": len(v5["packet"]), "v5_record": 1,
            "v10_package": len(v10["package"]), "v10_modified": len(v10["modified"]),
            "v10_added": len(v10["added"])}


def verify_commit(root: Path, commit: str, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10) -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    names = [n for n in git.run("ls-tree", "-r", "-z", "--name-only", commit).split("\0") if n]
    exp = set(expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9, v10)) | {RECORD}
    blobs = git.blobs(commit, sorted(exp))
    return verify_tree(root, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, read=blobs.get,
                       listing=lambda: {n for n in names if v2m.in_scope(n)},
                       packet_listing=lambda: {n for n in names if n.startswith(PACKET_PREFIX)})


def verify_git_v10(root: Path, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, commit: str = "HEAD") -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    if git.run("cat-file", "-t", BASE_COMMIT).strip() != "commit":
        raise IdentityError(f"{BASE_COMMIT} is not a commit here")
    sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
    if git.run("merge-base", BASE_COMMIT, sha).strip() != BASE_COMMIT:
        raise IdentityError("7d9d10a is not an ancestor of the commit under test")
    # The base itself is exactly the v9 tree: v9 regenerates there and c759c41..7d9d10a is the v9 declaration.
    if v9m.generate(root, commit=BASE_COMMIT) != git.blobs(BASE_COMMIT, [v9m.V9_PATH])[v9m.V9_PATH]:
        raise IdentityError("v9 does not regenerate at 7d9d10a")
    v9m.verify_git_v9(root, v1, v2, v3, v4, v5, v6, v7, v8, v9, commit=BASE_COMMIT)
    paths = list(v10["modified"]) + list(v10["added"]) + list(v10["package"])
    at_base, at_head = git.blobs(BASE_COMMIT, paths), git.blobs(sha, paths)
    problems = []
    base_pkg = {n for n in git.run("ls-tree", "-r", "-z", "--name-only", BASE_COMMIT).split("\0")
                if n.startswith(v2m.PANCHANGA_PACKAGE_PREFIX)}
    if base_pkg != set(v10["package"]):
        problems.append("v10 package is not exactly the Panchanga package at 7d9d10a")
    for p, e in v10["package"].items():
        for where, data in (("7d9d10a", at_base[p]), (sha[:7], at_head[p])):
            if data is None or sha256(data) != e["sha256"] or blob_id(data) != e["git_blob"]:
                problems.append(f"Panchanga package file differs from v10 at {where}: {p}")
    for p, e in v10["modified"].items():
        if at_base[p] is None or sha256(at_base[p]) != e["before_sha256"]:
            problems.append(f"v10 before_sha256 differs from the 7d9d10a git object: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["v10_sha256"] or blob_id(at_head[p]) != e["v10_git_blob"]:
            problems.append(f"v10 modified hash differs from the committed object: {p}")
    for p, e in v10["added"].items():
        if at_base[p] is not None:
            problems.append(f"v10 added path already exists at 7d9d10a: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["sha256"] or blob_id(at_head[p]) != e["git_blob"]:
            problems.append(f"v10 added hash differs from the committed object: {p}")
    prior = v9_expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9)
    side = {p: s for p, s in git.name_status(BASE_COMMIT, sha).items()
            if v7m._scope_or_declared(p, prior) or p == RECORD}
    expect = {**{p: "M" for p in v10["modified"]}, **{p: "A" for p in v10["added"]}}
    if RECORD in side and side[RECORD] == "M":
        expect[RECORD] = "M"   # decision fields may be recorded (frozen part checked by the tree step)
    if side != expect:
        problems.append(f"7d9d10a..{sha[:7]} differs from the v10 declaration: "
                        f"{sorted(set(side.items()) ^ set(expect.items()))}")
    if problems:
        raise IdentityError("PAN-QA-08 v10 exact-commit check failed:\n  " + "\n  ".join(problems))
    return {"commit": sha, **verify_commit(root, sha, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10)}


def generate(root: Path, commit: str = "HEAD", worktree: bool = False) -> bytes:
    """Build v10 from 7d9d10a and `commit` (or, for --write before committing, the working tree)."""
    root = Path(root)
    git = v2m.Git(root)
    v9_bytes = git.blobs(BASE_COMMIT, [v9m.V9_PATH])[v9m.V9_PATH]
    paths = list(AUTHORIZED_MODIFIED) + list(AUTHORIZED_ADDED)
    if worktree:
        cur = {p: (root / p).read_bytes() if (root / p).is_file() else None for p in paths}
    else:
        sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
        cur = git.blobs(sha, paths)
    missing = [p for p in paths if cur[p] is None]
    if missing:
        raise IdentityError(f"cannot generate v10: missing {missing}")
    before = git.blobs(BASE_COMMIT, list(AUTHORIZED_MODIFIED))
    mod = {p: {"before_sha256": sha256(before[p]), "v10_sha256": sha256(cur[p]), "v10_git_blob": blob_id(cur[p])}
           for p in AUTHORIZED_MODIFIED}
    added = {p: {"sha256": sha256(cur[p]), "git_blob": blob_id(cur[p])} for p in AUTHORIZED_ADDED}
    names = sorted(n for n in git.run("ls-tree", "-r", "-z", "--name-only", BASE_COMMIT).split("\0")
                   if n.startswith(v2m.PANCHANGA_PACKAGE_PREFIX))
    base = git.blobs(BASE_COMMIT, names)
    package = {p: {"sha256": sha256(base[p]), "git_blob": blob_id(base[p])} for p in names}
    doc = {"manifest_schema": SCHEMA, "note": NOTE, "task": TASK, "v9_manifest": _v9_binding(v9_bytes),
           "package": package, "modified": mod, "added": added,
           "counts": {"modified": len(mod), "added": len(added), "package": len(package)}}
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="regenerate from HEAD; verify tree, v9 base and v10 on git")
    g.add_argument("--write", action="store_true", help="write the manifest from the working tree (developer use)")
    args = ap.parse_args(argv)
    if args.write:
        data = generate(REPO, worktree=True)
        (REPO / V10_PATH).write_bytes(data)
        print(f"wrote {V10_PATH} sha256 {sha256(data)}")
        return 0
    if (REPO / V10_PATH).read_bytes() != generate(REPO):
        print("FAIL: committed v10 manifest differs from the git-derived regeneration at HEAD")
        return 1
    v1, v2, v3, v4, v5, v6, v7, v8, v9, v10 = load_committed(REPO)
    t = verify_tree(REPO, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10)
    g_ = verify_git_v10(REPO, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10)
    print(f"PASS v1 to v8 preserved (pinned in code); v9 {v9m.V9_SHA256} regenerates at 7d9d10a and "
          f"c759c41..7d9d10a is exactly the v9 declaration")
    print(f"PASS v10 sha256 {V10_SHA256} regenerated byte-identical from git objects at {g_['commit'][:7]}")
    print(f"PASS tree: {t['v1_unchanged']} v1 unchanged; Panchanga package ({t['v10_package']} files, M1, sun.py and "
          f"vara.py) byte-identical to 7d9d10a; v10 {t['v10_modified']} modified, {t['v10_added']} added; "
          f"no undeclared file")
    print(f"PASS git: 7d9d10a..{g_['commit'][:7]} is exactly the v10 declaration")
    return 0


if __name__ == "__main__":
    sys.exit(main())
