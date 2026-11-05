"""PAN-QA-08 identity gate, version 6 (KUN-PAN-RPT-001, issue #78).

v1 to v5 (`baseline-hashes.json`, `identity-manifest-v{2,3,4,5}.json`) are preserved byte for byte; their
SHA-256 values stay pinned in `identity_v2.py` to `identity_v5.py`. v5 is now proved on the exact trees of its
audited commit `5e82f64` and of main `07da75e` (the v6 base), which have the same tree.

v6 declares, in `identity-manifest-v6.json` (pinned below), the report-only change of KUN-PAN-RPT-001 (an
opt-in extended EN/HI report edition with birth-instant Panchanga M1 pages):

* `modified`: the two existing report files the task changes (`report/phase1/premium_report.py` and
  `report/phase1/README.md`), each with its v5-era SHA-256 and its new SHA-256 and git blob ID;
* `added`: the fixed set of new report files (the extension module and its catalog, the synthetic Panchanga
  fixtures for the 13 existing scenarios, the tests and two developer tools), each pinned by SHA-256 and blob.

Nothing else may change. The v5 editorial packet inventory and the frozen part of the live decision record
are carried over unchanged (the record's decision fields stay free, as in v5). No engine, Panchanga M1,
data, preview or catalog file (`report_i18n.json`, the UI register) is declared, so any change there still
fails. No calculation, ephemeris, tolerance or chart value is declared.

`verify_git_v6` binds v6 to exact commits: `07da75e` satisfies v5, each modified path has its declared
"before" bytes there, no added path exists there, and `git diff 07da75e <commit>` restricted to the v1 scope,
the declared paths and the packet is exactly the v6 declaration. Regenerate and compare:
    python -m tests.panchanga.identity_v6 --check
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
from .identity_v2 import IdentityError, HEX40, HEX64, REPO, blob_id, sha256

V6_PATH = "tests/panchanga/identity-manifest-v6.json"
V6_SHA256 = "bc0d983f45ff5fc161274ca9807bdacd738f6d8c822d827c193f1217f67093a4"
SCHEMA = "sabpuja-pan-qa-08-identity/6"
TASK = "KUN-PAN-RPT-001"
BASE_COMMIT = "07da75eebae6bb2f86d4c581229630962bda65fc"          # main after PR #76 (v5), issue #78 base
V5_CANDIDATE_COMMIT = "5e82f644c96352d1a973fc441c27e22085d7b7e8"  # the audited v5 commit (same tree as main)
PACKET_PREFIX = v5m.PACKET_PREFIX
RECORD = v5m.RECORD
EXPECTED_UNCHANGED_V1 = 209   # as in v4 and v5: KUN-PAN-RPT-001 changes no v1-pinned file

# The only existing paths KUN-PAN-RPT-001 changes, and the only paths it adds (issue #78). Order is fixed.
AUTHORIZED_MODIFIED = (
    "report/phase1/README.md",
    "report/phase1/premium_report.py",
)
_SCENARIOS = ("s01-first-supported-date", "s02-last-supported-date", "s03-crowded-d1-house",
              "s04-crowded-d9-house", "s05-graha-near-boundary", "s06-lagna-near-boundary", "s07-noon",
              "s08-dawn", "s09-evening", "s10-late-night", "s11-afternoon", "s12-morning", "s13-remaining-lagna")
AUTHORIZED_ADDED = (
    "report/phase1/panchanga_report.py",
    "report/phase1/report_panchanga_i18n.json",
    *(f"report/phase1/tests/fixtures/panchanga/{s}.json" for s in _SCENARIOS),
    "report/phase1/tests/test_panchanga_report.py",
    "report/phase1/tools/make_panchanga_fixtures.py",
    "report/phase1/tools/panchanga_review.py",
)
NOTE = ("PAN-QA-08 identity manifest v6 (KUN-PAN-RPT-001). Declares the report-only change relative to main "
        "07da75e: two modified report files and the new extended-edition files (Panchanga M1 report pages, "
        "their catalog, synthetic fixtures, tests and tools). The v5 packet inventory and the frozen part of "
        "the decision record are carried over unchanged. v1 to v5 are preserved and bound here by their "
        "SHA-256. No engine, Panchanga M1, data, preview, catalog, calculation, ephemeris, tolerance or chart "
        "value is declared. Generated from git objects only: python -m tests.panchanga.identity_v6 --check.")


# ---------------------------------------------------------------- expectations before v6

def v5_expectations(v1: dict, v2: dict, v3: dict, v4: dict, v5: dict) -> dict:
    """{path: (sha256, git_blob or None, label)} as v1 to v5 declare them (the record excluded)."""
    exp = v5m.v4_expectations(v1, v2, v3, v4)
    exp.pop(RECORD)
    for p, e in v5["modified"].items():
        exp[p] = (e["v5_sha256"], e["v5_git_blob"], "v5 modified")
    for p, e in v5["packet"].items():
        if p not in exp:
            exp[p] = (e["sha256"], e["git_blob"], "v5 packet")
    return exp


def _scope_or_declared(path: str, prior: dict) -> bool:
    return v2m.in_scope(path) or path in prior or path.startswith(PACKET_PREFIX)


# ---------------------------------------------------------------- manifest structure

def _entry(e, keys, where):
    if not isinstance(e, dict) or set(e) != set(keys) or not all(isinstance(e[k], str) for k in keys):
        raise IdentityError(f"v6 {where} entry malformed")
    for k in keys:
        if not (HEX40 if k.endswith("git_blob") else HEX64).fullmatch(e[k]):
            raise IdentityError(f"v6 {where} entry malformed")


def _v5_binding(v5_bytes: bytes) -> dict:
    return {"path": v5m.V5_PATH, "sha256": sha256(v5_bytes), "base_commit": BASE_COMMIT,
            "v5_candidate_commit": V5_CANDIDATE_COMMIT, "v4_sha256": v4m.V4_SHA256, "v3_sha256": v3m.V3_SHA256,
            "v2_sha256": v2m.V2_SHA256, "v1_sha256": v2m.V1_SHA256}


def validate_v6(doc, v1: dict, v2: dict, v3: dict, v4: dict, v5: dict, v5_bytes: bytes) -> dict:
    if not isinstance(doc, dict):
        raise IdentityError("v6 manifest must be an object")
    keys = {"manifest_schema", "note", "task", "v5_manifest", "modified", "added", "counts"}
    if set(doc) != keys:
        raise IdentityError(f"v6 manifest keys differ: {sorted(set(doc) ^ keys)}")
    if doc["manifest_schema"] != SCHEMA or doc["task"] != TASK:
        raise IdentityError("v6 manifest_schema or task wrong")
    if not isinstance(doc["note"], str) or not doc["note"]:
        raise IdentityError("v6 note missing")
    if doc["v5_manifest"] != _v5_binding(v5_bytes) or sha256(v5_bytes) != v5m.V5_SHA256:
        raise IdentityError("v6 v5_manifest record does not bind the preserved v1 to v5 manifests")
    mod, added = doc["modified"], doc["added"]
    if not all(isinstance(x, dict) for x in (mod, added)):
        raise IdentityError("v6 modified/added must be objects")
    if tuple(mod) != AUTHORIZED_MODIFIED:
        raise IdentityError("v6 modified paths differ from the authorized KUN-PAN-RPT-001 paths")
    if tuple(added) != AUTHORIZED_ADDED:
        raise IdentityError("v6 added paths differ from the authorized KUN-PAN-RPT-001 paths")
    if doc["counts"] != {"modified": len(mod), "added": len(added)}:
        raise IdentityError("v6 counts wrong")
    prior = v5_expectations(v1, v2, v3, v4, v5)
    for p, e in mod.items():
        _entry(e, ("before_sha256", "v6_sha256", "v6_git_blob"), f"modified {p}:")
        if p not in prior:
            raise IdentityError(f"v6 modified path is not pinned by v1 to v5: {p}")
        if e["before_sha256"] != prior[p][0]:
            raise IdentityError(f"v6 modified entry before_sha256 differs from {prior[p][2]}: {p}")
        if e["v6_sha256"] == e["before_sha256"]:
            raise IdentityError(f"v6 modified entry declares no change: {p}")
    for p, e in added.items():
        _entry(e, ("sha256", "git_blob"), f"added {p}:")
        if p in prior or p == RECORD:
            raise IdentityError(f"v6 added path is already pinned by v1 to v5: {p}")
        if not v2m.in_scope(p) or p.startswith(PACKET_PREFIX):
            raise IdentityError(f"v6 added path is outside the v1 scope or inside the packet: {p}")
    return doc


def load_v6(data: bytes, v1: dict, v2: dict, v3: dict, v4: dict, v5: dict, v5_bytes: bytes,
            expected_sha: str = None) -> dict:
    expected_sha = V6_SHA256 if expected_sha is None else expected_sha
    if sha256(data) != expected_sha:
        raise IdentityError("v6 manifest does not match its pinned SHA-256")
    try:
        doc = json.loads(data, object_pairs_hook=v2m._reject_duplicate_keys)
    except ValueError as exc:
        raise IdentityError(f"v6 manifest is not valid JSON: {exc}") from None
    return validate_v6(doc, v1, v2, v3, v4, v5, v5_bytes)


def load_committed(root: Path = REPO):
    root = Path(root)
    v1, v2, v3, v4, v5 = v5m.load_committed(root)
    v5_bytes = (root / v5m.V5_PATH).read_bytes()
    return v1, v2, v3, v4, v5, load_v6((root / V6_PATH).read_bytes(), v1, v2, v3, v4, v5, v5_bytes)


# ---------------------------------------------------------------- tree acceptance

def verify_tree(root: Path, v1: dict, v2: dict, v3: dict, v4: dict, v5: dict, v6: dict, *, read=None,
                listing=None, packet_listing=None) -> dict:
    """v1 to v5 expectations with the v6 overlay, on the working tree (or, via read/listing, on a commit)."""
    root = Path(root)

    def digest(rel):
        target = root / rel
        if target.is_symlink() or not target.is_file():
            return None
        return target.read_bytes()
    read = read or digest
    exp = v5_expectations(v1, v2, v3, v4, v5)
    for p, e in v6["modified"].items():
        exp[p] = (e["v6_sha256"], e["v6_git_blob"], "v6 modified")
    for p, e in v6["added"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v6 added")
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
        raise IdentityError("PAN-QA-08 v6 identity failed:\n  " + "\n  ".join(problems))
    if unchanged != EXPECTED_UNCHANGED_V1:
        raise IdentityError(f"expected {EXPECTED_UNCHANGED_V1} byte-identical v1 files, found {unchanged}")
    return {"v1_unchanged": unchanged, "v5_modified": len(v5["modified"]), "v5_packet": len(v5["packet"]),
            "v5_record": 1, "v6_modified": len(v6["modified"]), "v6_added": len(v6["added"])}


def verify_commit(root: Path, commit: str, v1: dict, v2: dict, v3: dict, v4: dict, v5: dict, v6: dict) -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    names = [n for n in git.run("ls-tree", "-r", "-z", "--name-only", commit).split("\0") if n]
    exp = set(v5_expectations(v1, v2, v3, v4, v5)) | set(v6["added"]) | {RECORD}
    blobs = git.blobs(commit, sorted(exp))
    return verify_tree(root, v1, v2, v3, v4, v5, v6, read=blobs.get,
                       listing=lambda: {n for n in names if v2m.in_scope(n)},
                       packet_listing=lambda: {n for n in names if n.startswith(PACKET_PREFIX)})


def verify_git_v6(root: Path, v1: dict, v2: dict, v3: dict, v4: dict, v5: dict, v6: dict,
                  commit: str = "HEAD") -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    if git.run("cat-file", "-t", BASE_COMMIT).strip() != "commit":
        raise IdentityError(f"{BASE_COMMIT} is not a commit here")
    sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
    if git.run("merge-base", BASE_COMMIT, sha).strip() != BASE_COMMIT:
        raise IdentityError("main 07da75e is not an ancestor of the commit under test")
    v5m.verify_commit(root, BASE_COMMIT, v1, v2, v3, v4, v5)   # the base itself satisfies v5
    paths = list(v6["modified"]) + list(v6["added"])
    at_base, at_head = git.blobs(BASE_COMMIT, paths), git.blobs(sha, paths)
    problems = []
    for p, e in v6["modified"].items():
        if at_base[p] is None or sha256(at_base[p]) != e["before_sha256"]:
            problems.append(f"v6 before_sha256 differs from the 07da75e git object: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["v6_sha256"] or blob_id(at_head[p]) != e["v6_git_blob"]:
            problems.append(f"v6 modified hash differs from the committed object: {p}")
    for p, e in v6["added"].items():
        if at_base[p] is not None:
            problems.append(f"v6 added path already exists at 07da75e: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["sha256"] or blob_id(at_head[p]) != e["git_blob"]:
            problems.append(f"v6 added hash differs from the committed object: {p}")
    prior = v5_expectations(v1, v2, v3, v4, v5)
    side = {p: s for p, s in git.name_status(BASE_COMMIT, sha).items()
            if _scope_or_declared(p, prior) or p == RECORD}
    expect = {**{p: "M" for p in v6["modified"]}, **{p: "A" for p in v6["added"]}}
    if RECORD in side and side[RECORD] == "M":
        expect[RECORD] = "M"   # decision fields may be recorded (frozen part checked by the tree step)
    if side != expect:
        problems.append(f"07da75e..{sha[:7]} differs from the v6 declaration: "
                        f"{sorted(set(side.items()) ^ set(expect.items()))}")
    if problems:
        raise IdentityError("PAN-QA-08 v6 exact-commit check failed:\n  " + "\n  ".join(problems))
    return {"commit": sha, **verify_commit(root, sha, v1, v2, v3, v4, v5, v6)}


# ---------------------------------------------------------------- generator

def generate(root: Path, commit: str = "HEAD", worktree: bool = False) -> bytes:
    """Build v6 from 07da75e and `commit` (or, for --write before committing, the working tree)."""
    root = Path(root)
    git = v2m.Git(root)
    v5_bytes = git.blobs(BASE_COMMIT, [v5m.V5_PATH])[v5m.V5_PATH]
    paths = list(AUTHORIZED_MODIFIED) + list(AUTHORIZED_ADDED)
    if worktree:
        cur = {p: (root / p).read_bytes() if (root / p).is_file() else None for p in paths}
    else:
        sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
        cur = git.blobs(sha, paths)
    missing = [p for p in paths if cur[p] is None]
    if missing:
        raise IdentityError(f"cannot generate v6: missing {missing}")
    before = git.blobs(BASE_COMMIT, list(AUTHORIZED_MODIFIED))
    mod = {p: {"before_sha256": sha256(before[p]), "v6_sha256": sha256(cur[p]), "v6_git_blob": blob_id(cur[p])}
           for p in AUTHORIZED_MODIFIED}
    added = {p: {"sha256": sha256(cur[p]), "git_blob": blob_id(cur[p])} for p in AUTHORIZED_ADDED}
    doc = {"manifest_schema": SCHEMA, "note": NOTE, "task": TASK, "v5_manifest": _v5_binding(v5_bytes),
           "modified": mod, "added": added, "counts": {"modified": len(mod), "added": len(added)}}
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="regenerate from HEAD; verify tree, v5 base and v6 on git")
    g.add_argument("--write", action="store_true", help="write the manifest from the working tree (developer use)")
    args = ap.parse_args(argv)
    if args.write:
        data = generate(REPO, worktree=True)
        (REPO / V6_PATH).write_bytes(data)
        print(f"wrote {V6_PATH} sha256 {sha256(data)}")
        return 0
    if (REPO / V6_PATH).read_bytes() != generate(REPO):
        print("FAIL: committed v6 manifest differs from the git-derived regeneration at HEAD")
        return 1
    v1, v2, v3, v4, v5, v6 = load_committed(REPO)
    t = verify_tree(REPO, v1, v2, v3, v4, v5, v6)
    g_ = verify_git_v6(REPO, v1, v2, v3, v4, v5, v6)
    print(f"PASS v1 {v2m.V1_SHA256}, v2 {v2m.V2_SHA256}, v3 {v3m.V3_SHA256}, v4 {v4m.V4_SHA256} and "
          f"v5 {v5m.V5_SHA256} preserved (pinned in code)")
    print(f"PASS v6 sha256 {V6_SHA256} regenerated byte-identical from git objects at {g_['commit'][:7]}")
    print(f"PASS tree: {t['v1_unchanged']} v1 unchanged; v6 {t['v6_modified']} modified, {t['v6_added']} added; "
          f"v5 packet ({t['v5_packet']} files) and frozen decision record carried over")
    print(f"PASS git: 07da75e satisfies v5; 07da75e..{g_['commit'][:7]} is exactly the v6 declaration")
    return 0


if __name__ == "__main__":
    sys.exit(main())
