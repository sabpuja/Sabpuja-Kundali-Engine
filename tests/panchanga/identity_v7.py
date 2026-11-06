"""PAN-QA-08 identity gate, version 7 (KUN-PAN-M2-NAMES-001, issue #80).

v1 to v6 (`baseline-hashes.json`, `identity-manifest-v{2,3,4,5,6}.json`) are preserved byte for byte; their
SHA-256 values stay pinned in `identity_v2.py` to `identity_v6.py`. v6 is now proved on the exact tree of its
audited commit `f26dd10` (the head of draft PR #79, the v7 base).

v7 declares, in `identity-manifest-v7.json` (pinned below), the report-only change of KUN-PAN-M2-NAMES-001
(source-checked Tithi, Karana and Yoga names, drawn only in an internal QA preview):

* `modified`: the two v6 report files the task changes (`report/phase1/panchanga_report.py` and
  `report/phase1/premium_report.py`), each with its v6 SHA-256 and its new SHA-256 and git blob ID;
* `added`: the fixed set of new report files (the names module and catalog, the pinned f26dd10 13-page
  hashes, the tests and the crosswalk tool), each pinned by SHA-256 and blob.

Nothing else may change. The v5 editorial packet and the frozen part of the decision record are carried over
unchanged. No engine, Panchanga M1, data, preview or catalog file (`report_i18n.json`,
`report_panchanga_i18n.json`, the UI register) is declared, so any change there still fails. No calculation,
ephemeris, tolerance or chart value is declared.

`verify_git_v7` binds v7 to exact commits: `f26dd10` satisfies v6, each modified path has its declared
"before" bytes there, no added path exists there, and `git diff f26dd10 <commit>` restricted to the v1 scope,
the declared paths and the packet is exactly the v7 declaration. Regenerate and compare:
    python -m tests.panchanga.identity_v7 --check
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
from .identity_v2 import IdentityError, HEX40, HEX64, REPO, blob_id, sha256

V7_PATH = "tests/panchanga/identity-manifest-v7.json"
V7_SHA256 = "e4bfc37ae5ec23be843d50418f3586161bc2be527dfec0dfcc1984136e96dd73"
SCHEMA = "sabpuja-pan-qa-08-identity/7"
TASK = "KUN-PAN-M2-NAMES-001"
BASE_COMMIT = "f26dd10829200e34fa6290bf19a5cebd44ced6a1"   # draft PR #79 head after independent QA: the v6 tree
PACKET_PREFIX = v5m.PACKET_PREFIX
RECORD = v5m.RECORD
EXPECTED_UNCHANGED_V1 = 209   # as in v4 to v6: no v1-pinned file changes

AUTHORIZED_MODIFIED = (
    "report/phase1/panchanga_report.py",
    "report/phase1/premium_report.py",
)
AUTHORIZED_ADDED = (
    "report/phase1/panchanga_names.json",
    "report/phase1/panchanga_names.py",
    "report/phase1/tests/fixtures/extended-13-page-sha256-f26dd10.json",
    "report/phase1/tests/test_panchanga_names.py",
    "report/phase1/tools/panchanga_names_crosswalk.py",
)
NOTE = ("PAN-QA-08 identity manifest v7 (KUN-PAN-M2-NAMES-001). Declares the report-only change relative to "
        "f26dd10 (draft PR #79, the v6 tree): two modified report files and the new Panchanga names files "
        "(catalog, module, pinned 13-page hashes, tests and crosswalk tool). The v5 packet inventory and the "
        "frozen part of the decision record are carried over unchanged. v1 to v6 are preserved and bound here by "
        "their SHA-256. No engine, Panchanga M1, data, preview, catalog, calculation, ephemeris, tolerance or "
        "chart value is declared. Generated from git objects only: python -m tests.panchanga.identity_v7 --check.")


def v6_expectations(v1: dict, v2: dict, v3: dict, v4: dict, v5: dict, v6: dict) -> dict:
    """{path: (sha256, git_blob or None, label)} as v1 to v6 declare them (the record excluded)."""
    exp = v6m.v5_expectations(v1, v2, v3, v4, v5)
    for p, e in v6["modified"].items():
        exp[p] = (e["v6_sha256"], e["v6_git_blob"], "v6 modified")
    for p, e in v6["added"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v6 added")
    return exp


def _scope_or_declared(path: str, prior: dict) -> bool:
    return v2m.in_scope(path) or path in prior or path.startswith(PACKET_PREFIX)


def _entry(e, keys, where):
    if not isinstance(e, dict) or set(e) != set(keys) or not all(isinstance(e[k], str) for k in keys):
        raise IdentityError(f"v7 {where} entry malformed")
    for k in keys:
        if not (HEX40 if k.endswith("git_blob") else HEX64).fullmatch(e[k]):
            raise IdentityError(f"v7 {where} entry malformed")


def _v6_binding(v6_bytes: bytes) -> dict:
    return {"path": v6m.V6_PATH, "sha256": sha256(v6_bytes), "base_commit": BASE_COMMIT,
            "v5_sha256": v5m.V5_SHA256, "v4_sha256": v4m.V4_SHA256, "v3_sha256": v3m.V3_SHA256,
            "v2_sha256": v2m.V2_SHA256, "v1_sha256": v2m.V1_SHA256}


def validate_v7(doc, v1, v2, v3, v4, v5, v6, v6_bytes: bytes) -> dict:
    if not isinstance(doc, dict):
        raise IdentityError("v7 manifest must be an object")
    keys = {"manifest_schema", "note", "task", "v6_manifest", "modified", "added", "counts"}
    if set(doc) != keys:
        raise IdentityError(f"v7 manifest keys differ: {sorted(set(doc) ^ keys)}")
    if doc["manifest_schema"] != SCHEMA or doc["task"] != TASK:
        raise IdentityError("v7 manifest_schema or task wrong")
    if not isinstance(doc["note"], str) or not doc["note"]:
        raise IdentityError("v7 note missing")
    if doc["v6_manifest"] != _v6_binding(v6_bytes) or sha256(v6_bytes) != v6m.V6_SHA256:
        raise IdentityError("v7 v6_manifest record does not bind the preserved v1 to v6 manifests")
    mod, added = doc["modified"], doc["added"]
    if not all(isinstance(x, dict) for x in (mod, added)):
        raise IdentityError("v7 modified/added must be objects")
    if tuple(mod) != AUTHORIZED_MODIFIED:
        raise IdentityError("v7 modified paths differ from the authorized KUN-PAN-M2-NAMES-001 paths")
    if tuple(added) != AUTHORIZED_ADDED:
        raise IdentityError("v7 added paths differ from the authorized KUN-PAN-M2-NAMES-001 paths")
    if doc["counts"] != {"modified": len(mod), "added": len(added)}:
        raise IdentityError("v7 counts wrong")
    prior = v6_expectations(v1, v2, v3, v4, v5, v6)
    for p, e in mod.items():
        _entry(e, ("before_sha256", "v7_sha256", "v7_git_blob"), f"modified {p}:")
        if p not in prior:
            raise IdentityError(f"v7 modified path is not pinned by v1 to v6: {p}")
        if e["before_sha256"] != prior[p][0]:
            raise IdentityError(f"v7 modified entry before_sha256 differs from {prior[p][2]}: {p}")
        if e["v7_sha256"] == e["before_sha256"]:
            raise IdentityError(f"v7 modified entry declares no change: {p}")
    for p, e in added.items():
        _entry(e, ("sha256", "git_blob"), f"added {p}:")
        if p in prior or p == RECORD:
            raise IdentityError(f"v7 added path is already pinned by v1 to v6: {p}")
        if not v2m.in_scope(p) or p.startswith(PACKET_PREFIX):
            raise IdentityError(f"v7 added path is outside the v1 scope or inside the packet: {p}")
    return doc


def load_v7(data: bytes, v1, v2, v3, v4, v5, v6, v6_bytes: bytes, expected_sha: str = None) -> dict:
    expected_sha = V7_SHA256 if expected_sha is None else expected_sha
    if sha256(data) != expected_sha:
        raise IdentityError("v7 manifest does not match its pinned SHA-256")
    try:
        doc = json.loads(data, object_pairs_hook=v2m._reject_duplicate_keys)
    except ValueError as exc:
        raise IdentityError(f"v7 manifest is not valid JSON: {exc}") from None
    return validate_v7(doc, v1, v2, v3, v4, v5, v6, v6_bytes)


def load_committed(root: Path = REPO):
    root = Path(root)
    v1, v2, v3, v4, v5, v6 = v6m.load_committed(root)
    v6_bytes = (root / v6m.V6_PATH).read_bytes()
    return v1, v2, v3, v4, v5, v6, load_v7((root / V7_PATH).read_bytes(), v1, v2, v3, v4, v5, v6, v6_bytes)


def verify_tree(root: Path, v1, v2, v3, v4, v5, v6, v7, *, read=None, listing=None, packet_listing=None) -> dict:
    """v1 to v6 expectations with the v7 overlay, on the working tree (or, via read/listing, on a commit)."""
    root = Path(root)

    def digest(rel):
        target = root / rel
        if target.is_symlink() or not target.is_file():
            return None
        return target.read_bytes()
    read = read or digest
    exp = v6_expectations(v1, v2, v3, v4, v5, v6)
    for p, e in v7["modified"].items():
        exp[p] = (e["v7_sha256"], e["v7_git_blob"], "v7 modified")
    for p, e in v7["added"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v7 added")
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
        if not p.startswith(v2m.PANCHANGA_PACKAGE_PREFIX):
            problems.append(f"undeclared file in v1 scope: {p}")
    in_packet = packet_listing() if packet_listing else v4m._packet_listing(root)
    for p in sorted(in_packet - set(v5["packet"]) - {RECORD}):
        problems.append(f"undeclared file in the editorial packet: {p}")
    if problems:
        raise IdentityError("PAN-QA-08 v7 identity failed:\n  " + "\n  ".join(problems))
    if unchanged != EXPECTED_UNCHANGED_V1:
        raise IdentityError(f"expected {EXPECTED_UNCHANGED_V1} byte-identical v1 files, found {unchanged}")
    return {"v1_unchanged": unchanged, "v5_packet": len(v5["packet"]), "v5_record": 1,
            "v6_modified": len(v6["modified"]), "v6_added": len(v6["added"]),
            "v7_modified": len(v7["modified"]), "v7_added": len(v7["added"])}


def verify_commit(root: Path, commit: str, v1, v2, v3, v4, v5, v6, v7) -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    names = [n for n in git.run("ls-tree", "-r", "-z", "--name-only", commit).split("\0") if n]
    exp = set(v6_expectations(v1, v2, v3, v4, v5, v6)) | set(v7["added"]) | {RECORD}
    blobs = git.blobs(commit, sorted(exp))
    return verify_tree(root, v1, v2, v3, v4, v5, v6, v7, read=blobs.get,
                       listing=lambda: {n for n in names if v2m.in_scope(n)},
                       packet_listing=lambda: {n for n in names if n.startswith(PACKET_PREFIX)})


def verify_git_v7(root: Path, v1, v2, v3, v4, v5, v6, v7, commit: str = "HEAD") -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    if git.run("cat-file", "-t", BASE_COMMIT).strip() != "commit":
        raise IdentityError(f"{BASE_COMMIT} is not a commit here")
    sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
    if git.run("merge-base", BASE_COMMIT, sha).strip() != BASE_COMMIT:
        raise IdentityError("f26dd10 is not an ancestor of the commit under test")
    v6m.verify_commit(root, BASE_COMMIT, v1, v2, v3, v4, v5, v6)   # the base itself satisfies v6
    paths = list(v7["modified"]) + list(v7["added"])
    at_base, at_head = git.blobs(BASE_COMMIT, paths), git.blobs(sha, paths)
    problems = []
    for p, e in v7["modified"].items():
        if at_base[p] is None or sha256(at_base[p]) != e["before_sha256"]:
            problems.append(f"v7 before_sha256 differs from the f26dd10 git object: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["v7_sha256"] or blob_id(at_head[p]) != e["v7_git_blob"]:
            problems.append(f"v7 modified hash differs from the committed object: {p}")
    for p, e in v7["added"].items():
        if at_base[p] is not None:
            problems.append(f"v7 added path already exists at f26dd10: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["sha256"] or blob_id(at_head[p]) != e["git_blob"]:
            problems.append(f"v7 added hash differs from the committed object: {p}")
    prior = v6_expectations(v1, v2, v3, v4, v5, v6)
    side = {p: s for p, s in git.name_status(BASE_COMMIT, sha).items()
            if _scope_or_declared(p, prior) or p == RECORD}
    expect = {**{p: "M" for p in v7["modified"]}, **{p: "A" for p in v7["added"]}}
    if RECORD in side and side[RECORD] == "M":
        expect[RECORD] = "M"   # decision fields may be recorded (frozen part checked by the tree step)
    if side != expect:
        problems.append(f"f26dd10..{sha[:7]} differs from the v7 declaration: "
                        f"{sorted(set(side.items()) ^ set(expect.items()))}")
    if problems:
        raise IdentityError("PAN-QA-08 v7 exact-commit check failed:\n  " + "\n  ".join(problems))
    return {"commit": sha, **verify_commit(root, sha, v1, v2, v3, v4, v5, v6, v7)}


def generate(root: Path, commit: str = "HEAD", worktree: bool = False) -> bytes:
    """Build v7 from f26dd10 and `commit` (or, for --write before committing, the working tree)."""
    root = Path(root)
    git = v2m.Git(root)
    v6_bytes = git.blobs(BASE_COMMIT, [v6m.V6_PATH])[v6m.V6_PATH]
    paths = list(AUTHORIZED_MODIFIED) + list(AUTHORIZED_ADDED)
    if worktree:
        cur = {p: (root / p).read_bytes() if (root / p).is_file() else None for p in paths}
    else:
        sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
        cur = git.blobs(sha, paths)
    missing = [p for p in paths if cur[p] is None]
    if missing:
        raise IdentityError(f"cannot generate v7: missing {missing}")
    before = git.blobs(BASE_COMMIT, list(AUTHORIZED_MODIFIED))
    mod = {p: {"before_sha256": sha256(before[p]), "v7_sha256": sha256(cur[p]), "v7_git_blob": blob_id(cur[p])}
           for p in AUTHORIZED_MODIFIED}
    added = {p: {"sha256": sha256(cur[p]), "git_blob": blob_id(cur[p])} for p in AUTHORIZED_ADDED}
    doc = {"manifest_schema": SCHEMA, "note": NOTE, "task": TASK, "v6_manifest": _v6_binding(v6_bytes),
           "modified": mod, "added": added, "counts": {"modified": len(mod), "added": len(added)}}
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="regenerate from HEAD; verify tree, v6 base and v7 on git")
    g.add_argument("--write", action="store_true", help="write the manifest from the working tree (developer use)")
    args = ap.parse_args(argv)
    if args.write:
        data = generate(REPO, worktree=True)
        (REPO / V7_PATH).write_bytes(data)
        print(f"wrote {V7_PATH} sha256 {sha256(data)}")
        return 0
    if (REPO / V7_PATH).read_bytes() != generate(REPO):
        print("FAIL: committed v7 manifest differs from the git-derived regeneration at HEAD")
        return 1
    v1, v2, v3, v4, v5, v6, v7 = load_committed(REPO)
    t = verify_tree(REPO, v1, v2, v3, v4, v5, v6, v7)
    g_ = verify_git_v7(REPO, v1, v2, v3, v4, v5, v6, v7)
    print(f"PASS v1 {v2m.V1_SHA256}, v2 {v2m.V2_SHA256}, v3 {v3m.V3_SHA256}, v4 {v4m.V4_SHA256}, "
          f"v5 {v5m.V5_SHA256} and v6 {v6m.V6_SHA256} preserved (pinned in code)")
    print(f"PASS v7 sha256 {V7_SHA256} regenerated byte-identical from git objects at {g_['commit'][:7]}")
    print(f"PASS tree: {t['v1_unchanged']} v1 unchanged; v7 {t['v7_modified']} modified, {t['v7_added']} added; "
          f"v6 report files, v5 packet ({t['v5_packet']} files) and frozen decision record carried over")
    print(f"PASS git: f26dd10 satisfies v6; f26dd10..{g_['commit'][:7]} is exactly the v7 declaration")
    return 0


if __name__ == "__main__":
    sys.exit(main())
