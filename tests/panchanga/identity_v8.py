"""PAN-QA-08 identity gate, version 8 (KUN-PAN-M2-SUN-001).

v1 to v7 are preserved byte for byte; their SHA-256 values stay pinned in `identity_v2.py` to `identity_v7.py`.
v7 is now proved on the exact tree of its audited commit `a8c3108` (the head of draft PR #81, the v8 base).

v8 declares, in `identity-manifest-v8.json` (pinned below), the change of KUN-PAN-M2-SUN-001 inside the v1 scope:

* `modified`: nothing. No engine, chart, Panchanga M1, report, preview, prototype, data or catalog file changes;
* `added`: exactly one file, the sunrise/sunset/Vara validation module `src/sabpuja_kundali/panchanga/sun.py`;
* `m1_package`: every file of the Panchanga package at a8c3108 (the frozen M1 code), pinned by SHA-256 and blob,
  so v8 proves the M1 package byte-identical to its accepted base.

The v1 rule exempts new files inside the Panchanga package from the "undeclared file" check, so v7 alone would
not notice this module. v8 pins it explicitly and requires `git diff a8c3108 <commit>` restricted to the v1
scope, the declared paths, the editorial packet and the decision record to be exactly that one added file.
Tests, fixtures, research evidence and documents of this task live outside the v1 scope (`tests/panchanga/`,
`research/`, `docs/`) and are not declared. Regenerate and compare:
    python -m tests.panchanga.identity_v8 --check
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
from .identity_v2 import IdentityError, HEX40, HEX64, REPO, blob_id, sha256

V8_PATH = "tests/panchanga/identity-manifest-v8.json"
V8_SHA256 = "403a33310684feeb2a1f8251d6b132c812047f84b3171652b35dacce511b9cd3"
SCHEMA = "sabpuja-pan-qa-08-identity/8"
TASK = "KUN-PAN-M2-SUN-001"
BASE_COMMIT = "a8c31081dfc631f5a0a960c699aaabc24b05d7fe"   # draft PR #81 head after independent QA: the v7 tree
PACKET_PREFIX = v5m.PACKET_PREFIX
RECORD = v5m.RECORD
EXPECTED_UNCHANGED_V1 = 209

AUTHORIZED_MODIFIED = ()
AUTHORIZED_ADDED = ("src/sabpuja_kundali/panchanga/sun.py",)
NOTE = ("PAN-QA-08 identity manifest v8 (KUN-PAN-M2-SUN-001). Declares the change relative to a8c3108 (draft PR "
        "#81, the v7 tree) inside the v1 scope: no modified file and one added file, the sunrise/sunset/Vara "
        "validation module, which nothing in the engine, Panchanga M1, chart or reports imports. v1 to v7 are "
        "preserved and bound here by their SHA-256. Generated from git objects only: "
        "python -m tests.panchanga.identity_v8 --check.")


def v7_expectations(v1, v2, v3, v4, v5, v6, v7) -> dict:
    exp = v7m.v6_expectations(v1, v2, v3, v4, v5, v6)
    for p, e in v7["modified"].items():
        exp[p] = (e["v7_sha256"], e["v7_git_blob"], "v7 modified")
    for p, e in v7["added"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v7 added")
    return exp


def _v7_binding(v7_bytes: bytes) -> dict:
    return {"path": v7m.V7_PATH, "sha256": sha256(v7_bytes), "base_commit": BASE_COMMIT,
            "v6_sha256": v6m.V6_SHA256, "v5_sha256": v5m.V5_SHA256, "v4_sha256": v4m.V4_SHA256,
            "v3_sha256": v3m.V3_SHA256, "v2_sha256": v2m.V2_SHA256, "v1_sha256": v2m.V1_SHA256}


def validate_v8(doc, v1, v2, v3, v4, v5, v6, v7, v7_bytes: bytes) -> dict:
    if not isinstance(doc, dict):
        raise IdentityError("v8 manifest must be an object")
    keys = {"manifest_schema", "note", "task", "v7_manifest", "m1_package", "modified", "added", "counts"}
    if set(doc) != keys:
        raise IdentityError(f"v8 manifest keys differ: {sorted(set(doc) ^ keys)}")
    if doc["manifest_schema"] != SCHEMA or doc["task"] != TASK:
        raise IdentityError("v8 manifest_schema or task wrong")
    if not isinstance(doc["note"], str) or not doc["note"]:
        raise IdentityError("v8 note missing")
    if doc["v7_manifest"] != _v7_binding(v7_bytes) or sha256(v7_bytes) != v7m.V7_SHA256:
        raise IdentityError("v8 v7_manifest record does not bind the preserved v1 to v7 manifests")
    mod, added = doc["modified"], doc["added"]
    if not all(isinstance(x, dict) for x in (mod, added)):
        raise IdentityError("v8 modified/added must be objects")
    if tuple(mod) != AUTHORIZED_MODIFIED:
        raise IdentityError("v8 modified paths differ from the authorized KUN-PAN-M2-SUN-001 paths (none)")
    if tuple(added) != AUTHORIZED_ADDED:
        raise IdentityError("v8 added paths differ from the authorized KUN-PAN-M2-SUN-001 paths")
    if doc["counts"] != {"modified": len(mod), "added": len(added)}:
        raise IdentityError("v8 counts wrong")
    m1 = doc["m1_package"]
    if not isinstance(m1, dict) or not m1 or not all(p.startswith(v2m.PANCHANGA_PACKAGE_PREFIX) for p in m1):
        raise IdentityError("v8 m1_package must list the Panchanga package files")
    for p, e in m1.items():
        if not isinstance(e, dict) or set(e) != {"sha256", "git_blob"} or not HEX64.fullmatch(str(e["sha256"])) \
                or not HEX40.fullmatch(str(e["git_blob"])):
            raise IdentityError(f"v8 m1_package entry malformed: {p}")
    if set(m1) & set(added):
        raise IdentityError("v8 added path is also listed as an M1 package file")
    prior = v7_expectations(v1, v2, v3, v4, v5, v6, v7)
    for p, e in added.items():
        if not isinstance(e, dict) or set(e) != {"sha256", "git_blob"} or not HEX64.fullmatch(str(e["sha256"])) \
                or not HEX40.fullmatch(str(e["git_blob"])):
            raise IdentityError(f"v8 added entry malformed: {p}")
        if p in prior or p == RECORD:
            raise IdentityError(f"v8 added path is already pinned by v1 to v7: {p}")
        if not v2m.in_scope(p) or p.startswith(PACKET_PREFIX):
            raise IdentityError(f"v8 added path is outside the v1 scope or inside the packet: {p}")
    return doc


def load_v8(data: bytes, v1, v2, v3, v4, v5, v6, v7, v7_bytes: bytes, expected_sha: str = None) -> dict:
    expected_sha = V8_SHA256 if expected_sha is None else expected_sha
    if sha256(data) != expected_sha:
        raise IdentityError("v8 manifest does not match its pinned SHA-256")
    try:
        doc = json.loads(data, object_pairs_hook=v2m._reject_duplicate_keys)
    except ValueError as exc:
        raise IdentityError(f"v8 manifest is not valid JSON: {exc}") from None
    return validate_v8(doc, v1, v2, v3, v4, v5, v6, v7, v7_bytes)


def load_committed(root: Path = REPO):
    root = Path(root)
    v1, v2, v3, v4, v5, v6, v7 = v7m.load_committed(root)
    v7_bytes = (root / v7m.V7_PATH).read_bytes()
    return v1, v2, v3, v4, v5, v6, v7, load_v8((root / V8_PATH).read_bytes(), v1, v2, v3, v4, v5, v6, v7, v7_bytes)


def verify_tree(root: Path, v1, v2, v3, v4, v5, v6, v7, v8, *, read=None, listing=None, packet_listing=None) -> dict:
    """v1 to v7 with the v8 overlay. Unlike v1, a file in the Panchanga package that is not declared fails."""
    root = Path(root)

    def digest(rel):
        target = root / rel
        if target.is_symlink() or not target.is_file():
            return None
        return target.read_bytes()
    read = read or digest
    exp = v7_expectations(v1, v2, v3, v4, v5, v6, v7)
    for p, e in v8["m1_package"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v8 M1 package (a8c3108)")
    for p, e in v8["added"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v8 added")
    base = v7m.verify_tree(root, v1, v2, v3, v4, v5, v6, v7, read=read, listing=listing,
                           packet_listing=packet_listing)
    problems = []
    for p, (want_sha, want_blob, label) in sorted(v8_only(exp).items()):
        data = read(p)
        if data is None:
            problems.append(f"missing: {p}")
        elif sha256(data) != want_sha or blob_id(data) != want_blob:
            problems.append(f"unexpected hash (declared {label}): {p}")
    present = listing() if listing else v2m._scope_files(root)
    for p in sorted(present - set(exp)):
        problems.append(f"undeclared file in v1 scope (v8 counts the Panchanga package too): {p}")
    if problems:
        raise IdentityError("PAN-QA-08 v8 identity failed:\n  " + "\n  ".join(problems))
    return {**base, "v8_modified": len(v8["modified"]), "v8_added": len(v8["added"])}


def v8_only(exp: dict) -> dict:
    return {p: v for p, v in exp.items() if v[2].startswith("v8 ")}


def verify_commit(root: Path, commit: str, v1, v2, v3, v4, v5, v6, v7, v8) -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    names = [n for n in git.run("ls-tree", "-r", "-z", "--name-only", commit).split("\0") if n]
    exp = set(v7_expectations(v1, v2, v3, v4, v5, v6, v7)) | set(v8["added"]) | set(v8["m1_package"]) | {RECORD}
    blobs = git.blobs(commit, sorted(exp))
    return verify_tree(root, v1, v2, v3, v4, v5, v6, v7, v8, read=blobs.get,
                       listing=lambda: {n for n in names if v2m.in_scope(n)},
                       packet_listing=lambda: {n for n in names if n.startswith(PACKET_PREFIX)})


def verify_git_v8(root: Path, v1, v2, v3, v4, v5, v6, v7, v8, commit: str = "HEAD") -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    if git.run("cat-file", "-t", BASE_COMMIT).strip() != "commit":
        raise IdentityError(f"{BASE_COMMIT} is not a commit here")
    sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
    if git.run("merge-base", BASE_COMMIT, sha).strip() != BASE_COMMIT:
        raise IdentityError("a8c3108 is not an ancestor of the commit under test")
    # The base itself is exactly the v7 tree: v7 regenerates there and f26dd10..a8c3108 is the v7 declaration.
    if v7m.generate(root, commit=BASE_COMMIT) != git.blobs(BASE_COMMIT, [v7m.V7_PATH])[v7m.V7_PATH]:
        raise IdentityError("v7 does not regenerate at a8c3108")
    v7m.verify_git_v7(root, v1, v2, v3, v4, v5, v6, v7, commit=BASE_COMMIT)
    paths = list(v8["added"]) + list(v8["m1_package"])
    at_base, at_head = git.blobs(BASE_COMMIT, paths), git.blobs(sha, paths)
    problems = []
    base_names = {n for n in git.run("ls-tree", "-r", "-z", "--name-only", BASE_COMMIT).split("\0")
                  if n.startswith(v2m.PANCHANGA_PACKAGE_PREFIX)}
    if base_names != set(v8["m1_package"]):
        problems.append("v8 m1_package is not exactly the Panchanga package at a8c3108")
    for p, e in v8["m1_package"].items():
        for where, data in (("a8c3108", at_base[p]), (sha[:7], at_head[p])):
            if data is None or sha256(data) != e["sha256"] or blob_id(data) != e["git_blob"]:
                problems.append(f"M1 package file differs from v8 at {where}: {p}")
    for p, e in v8["added"].items():
        if at_base[p] is not None:
            problems.append(f"v8 added path already exists at a8c3108: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["sha256"] or blob_id(at_head[p]) != e["git_blob"]:
            problems.append(f"v8 added hash differs from the committed object: {p}")
    prior = v7_expectations(v1, v2, v3, v4, v5, v6, v7)
    side = {p: s for p, s in git.name_status(BASE_COMMIT, sha).items()
            if v7m._scope_or_declared(p, prior) or p == RECORD}
    expect = {p: "A" for p in v8["added"]}
    if RECORD in side and side[RECORD] == "M":
        expect[RECORD] = "M"   # decision fields may be recorded (frozen part checked by the tree step)
    if side != expect:
        problems.append(f"a8c3108..{sha[:7]} differs from the v8 declaration: "
                        f"{sorted(set(side.items()) ^ set(expect.items()))}")
    if problems:
        raise IdentityError("PAN-QA-08 v8 exact-commit check failed:\n  " + "\n  ".join(problems))
    return {"commit": sha, **verify_commit(root, sha, v1, v2, v3, v4, v5, v6, v7, v8)}


def generate(root: Path, commit: str = "HEAD", worktree: bool = False) -> bytes:
    root = Path(root)
    git = v2m.Git(root)
    v7_bytes = git.blobs(BASE_COMMIT, [v7m.V7_PATH])[v7m.V7_PATH]
    paths = list(AUTHORIZED_ADDED)
    if worktree:
        cur = {p: (root / p).read_bytes() if (root / p).is_file() else None for p in paths}
    else:
        sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
        cur = git.blobs(sha, paths)
    missing = [p for p in paths if cur[p] is None]
    if missing:
        raise IdentityError(f"cannot generate v8: missing {missing}")
    added = {p: {"sha256": sha256(cur[p]), "git_blob": blob_id(cur[p])} for p in AUTHORIZED_ADDED}
    names = sorted(n for n in git.run("ls-tree", "-r", "-z", "--name-only", BASE_COMMIT).split("\0")
                   if n.startswith(v2m.PANCHANGA_PACKAGE_PREFIX))
    base = git.blobs(BASE_COMMIT, names)
    m1 = {p: {"sha256": sha256(base[p]), "git_blob": blob_id(base[p])} for p in names}
    doc = {"manifest_schema": SCHEMA, "note": NOTE, "task": TASK, "v7_manifest": _v7_binding(v7_bytes),
           "m1_package": m1, "modified": {}, "added": added, "counts": {"modified": 0, "added": len(added)}}
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="regenerate from HEAD; verify tree, v7 base and v8 on git")
    g.add_argument("--write", action="store_true", help="write the manifest from the working tree (developer use)")
    args = ap.parse_args(argv)
    if args.write:
        data = generate(REPO, worktree=True)
        (REPO / V8_PATH).write_bytes(data)
        print(f"wrote {V8_PATH} sha256 {sha256(data)}")
        return 0
    if (REPO / V8_PATH).read_bytes() != generate(REPO):
        print("FAIL: committed v8 manifest differs from the git-derived regeneration at HEAD")
        return 1
    v1, v2, v3, v4, v5, v6, v7, v8 = load_committed(REPO)
    t = verify_tree(REPO, v1, v2, v3, v4, v5, v6, v7, v8)
    g_ = verify_git_v8(REPO, v1, v2, v3, v4, v5, v6, v7, v8)
    print(f"PASS v1 to v6 preserved (pinned in code); v7 {v7m.V7_SHA256} regenerates at a8c3108 and "
          f"f26dd10..a8c3108 is exactly the v7 declaration")
    print(f"PASS v8 sha256 {V8_SHA256} regenerated byte-identical from git objects at {g_['commit'][:7]}")
    print(f"PASS tree: {t['v1_unchanged']} v1 unchanged; v7 {t['v7_modified']} modified, {t['v7_added']} added; "
          f"v8 {t['v8_modified']} modified, {t['v8_added']} added; no undeclared file, Panchanga package included")
    print(f"PASS git: a8c3108..{g_['commit'][:7]} is exactly the v8 declaration")
    return 0


if __name__ == "__main__":
    sys.exit(main())
