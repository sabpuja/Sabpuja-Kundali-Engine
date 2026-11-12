"""PAN-QA-08 identity gate, version 11 (KUN-PAN-VARA-G2-001: owner-adopted sunrise and Vara status and provenance).

v1 to v10 are preserved byte for byte; their SHA-256 values stay pinned in `identity_v2.py` to `identity_v10.py`.
v10 is now proved on the exact tree of its audited commit `30bdace` (the head of draft PR #93, the v11 base), v9 on
`7d9d10a` and v8 on `c759c41` as before.

v11 declares, in `identity-manifest-v11.json` (pinned below), the change of KUN-PAN-VARA-G2-001 inside the v1
scope. Every path is `modified`, none is added:

* the status and provenance metadata of `sun.py` and `vara.py` (owner adoption of PAN-D03, PAN-D05, PAN-D11-B and
  PAN-D17 for the English Essentials edition, PR #93 comment 6822876554) and the matching pins in
  `vara_report.py` (STATUS, CLAIM_BOUNDARY, METHOD_SHA256);
* the 25 synthetic `sabpuja-panchanga-vara/1` fixtures, whose only changed fields are `status`, `claim_boundary`
  and `method.convention_decision`;
* the Essentials English catalog (`wording_status` APPROVED_FOR_CUSTOMER_RELEASE and its note; the strings are
  the approved copy of 30bdace), its pin in `essentials.py`, the edition manifest and `test_essentials.py`;
* `package`: every other file of the Panchanga package at 30bdace (M1), pinned by SHA-256 and blob, so v11 proves
  them byte-identical to their accepted base.

Nothing else may change: no chart engine, data, preview, prototype, terminology register, report catalog, report
layout or Essentials PDF pin. `git diff 30bdace <commit>` restricted to the v1 scope, the declared paths, the
packet and the record must be exactly the v11 declaration. Regenerate and compare:
    python -m tests.panchanga.identity_v11 --check
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
from . import identity_v10 as v10m
from .identity_v2 import IdentityError, HEX40, HEX64, REPO, blob_id, sha256

V11_PATH = "tests/panchanga/identity-manifest-v11.json"
V11_SHA256 = "e9f1690eb5fd9f9752d499fe0e7fa4ebc98c23d90faf5805b20bea27e09f3f3e"
SCHEMA = "sabpuja-pan-qa-08-identity/11"
TASK = "KUN-PAN-VARA-G2-001"
BASE_COMMIT = "30bdacea14eac444f0dc3353b5922134a255c697"   # draft PR #93 head after independent QA: the v10 tree
PACKET_PREFIX = v5m.PACKET_PREFIX
RECORD = v5m.RECORD
EXPECTED_UNCHANGED_V1 = 209

_FIXTURES = "report/phase1/tests/fixtures/"
AUTHORIZED_MODIFIED = tuple(sorted((
    "src/sabpuja_kundali/panchanga/sun.py",
    "src/sabpuja_kundali/panchanga/vara.py",
    "report/phase1/vara_report.py",
    "report/phase1/essentials-edition-manifest.json",
    "report/phase1/essentials.py",
    "report/phase1/essentials_en.json",
    "report/phase1/tests/test_essentials.py",
    *(_FIXTURES + "vara/" + s + ".json" for s in (
        "s01-first-supported-date", "s02-last-supported-date", "s03-crowded-d1-house", "s04-crowded-d9-house",
        "s05-graha-near-boundary", "s06-lagna-near-boundary", "s07-noon", "s08-dawn", "s09-evening",
        "s10-late-night", "s11-afternoon", "s12-morning", "s13-remaining-lagna")),
    *(_FIXTURES + "vara-cases/" + s + ".json" for s in (
        "v01-typical-afternoon", "v02-pre-sunrise-previous-vara", "v03-first-second-after-sunrise",
        "v04-last-second-before-sunrise", "v05-inside-band-after", "v06-outside-band-after",
        "v07-london-clocks-forward", "v08-london-repeated-hour", "v09-dateline-kiritimati",
        "v10-polar-day-unavailable", "v11-vara-day-end-undefined", "v12-sunset-after-midnight")),
)))
NOTE = ("PAN-QA-08 identity manifest v11 (KUN-PAN-VARA-G2-001). Declares the change relative to 30bdace (draft PR "
        "#93, the v10 tree) inside the v1 scope: status and provenance metadata of the sun and Vara modules after the "
        "owner adopted PAN-D03, PAN-D05, PAN-D11-B and PAN-D17 for the English Essentials edition (PR #93 comment "
        "6822876554), the matching report pins, the 25 Vara fixtures (status, claim boundary and convention "
        "decision only) and the owner-approved Essentials wording status. The rest of the Panchanga package at "
        "30bdace is pinned unchanged. v1 to v10 are preserved and bound here by their SHA-256. Generated from git "
        "objects only: python -m tests.panchanga.identity_v11 --check.")


def v10_expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9, v10) -> dict:
    """{path: (sha256, git_blob or None, label)} as v1 to v10 declare them (the record excluded)."""
    return v10m.expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9, v10)


def _entry(e, keys, where):
    if not isinstance(e, dict) or set(e) != set(keys) or not all(isinstance(e[k], str) for k in keys):
        raise IdentityError(f"v11 {where} entry malformed")
    for k in keys:
        if not (HEX40 if k.endswith("git_blob") else HEX64).fullmatch(e[k]):
            raise IdentityError(f"v11 {where} entry malformed")


def _v10_binding(v10_bytes: bytes) -> dict:
    return {"path": v10m.V10_PATH, "sha256": sha256(v10_bytes), "base_commit": BASE_COMMIT,
            "v9_sha256": v9m.V9_SHA256, "v8_sha256": v8m.V8_SHA256, "v7_sha256": v7m.V7_SHA256,
            "v6_sha256": v6m.V6_SHA256, "v5_sha256": v5m.V5_SHA256, "v4_sha256": v4m.V4_SHA256,
            "v3_sha256": v3m.V3_SHA256, "v2_sha256": v2m.V2_SHA256, "v1_sha256": v2m.V1_SHA256}


def validate_v11(doc, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v10_bytes: bytes) -> dict:
    if not isinstance(doc, dict):
        raise IdentityError("v11 manifest must be an object")
    keys = {"manifest_schema", "note", "task", "v10_manifest", "package", "modified", "counts"}
    if set(doc) != keys:
        raise IdentityError(f"v11 manifest keys differ: {sorted(set(doc) ^ keys)}")
    if doc["manifest_schema"] != SCHEMA or doc["task"] != TASK:
        raise IdentityError("v11 manifest_schema or task wrong")
    if not isinstance(doc["note"], str) or not doc["note"]:
        raise IdentityError("v11 note missing")
    if doc["v10_manifest"] != _v10_binding(v10_bytes) or sha256(v10_bytes) != v10m.V10_SHA256:
        raise IdentityError("v11 v10_manifest record does not bind the preserved v1 to v10 manifests")
    mod, package = doc["modified"], doc["package"]
    if not all(isinstance(x, dict) for x in (mod, package)):
        raise IdentityError("v11 modified/package must be objects")
    if tuple(mod) != AUTHORIZED_MODIFIED:
        raise IdentityError("v11 modified paths differ from the authorized KUN-PAN-VARA-G2-001 paths")
    if doc["counts"] != {"modified": len(mod), "package": len(package)}:
        raise IdentityError("v11 counts wrong")
    prior = v10_expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9, v10)
    if not package or not all(p.startswith(v2m.PANCHANGA_PACKAGE_PREFIX) for p in package):
        raise IdentityError("v11 package must list the Panchanga package files")
    for p, e in package.items():
        _entry(e, ("sha256", "git_blob"), f"package {p}:")
        if p not in prior or prior[p][0] != e["sha256"] or prior[p][1] != e["git_blob"]:
            raise IdentityError(f"v11 package entry is not the v10 pin: {p}")
    if set(package) & set(mod):
        raise IdentityError("v11 modified path is also listed as a package file")
    for p, e in mod.items():
        _entry(e, ("before_sha256", "v11_sha256", "v11_git_blob"), f"modified {p}:")
        if p not in prior:
            raise IdentityError(f"v11 modified path is not pinned by v1 to v10: {p}")
        if e["before_sha256"] != prior[p][0]:
            raise IdentityError(f"v11 modified entry before_sha256 differs from {prior[p][2]}: {p}")
        if e["v11_sha256"] == e["before_sha256"]:
            raise IdentityError(f"v11 modified entry declares no change: {p}")
    return doc


def load_v11(data: bytes, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v10_bytes: bytes, expected_sha: str = None) -> dict:
    expected_sha = V11_SHA256 if expected_sha is None else expected_sha
    if sha256(data) != expected_sha:
        raise IdentityError("v11 manifest does not match its pinned SHA-256")
    try:
        doc = json.loads(data, object_pairs_hook=v2m._reject_duplicate_keys)
    except ValueError as exc:
        raise IdentityError(f"v11 manifest is not valid JSON: {exc}") from None
    return validate_v11(doc, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v10_bytes)


def load_committed(root: Path = REPO):
    root = Path(root)
    prior = v10m.load_committed(root)
    v10_bytes = (root / v10m.V10_PATH).read_bytes()
    return (*prior, load_v11((root / V11_PATH).read_bytes(), *prior, v10_bytes))


def expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11) -> dict:
    exp = v10_expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9, v10)
    for p, e in v11["package"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v11 package (30bdace)")
    for p, e in v11["modified"].items():
        exp[p] = (e["v11_sha256"], e["v11_git_blob"], "v11 modified")
    return exp


def verify_tree(root: Path, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11, *, read=None, listing=None,
                packet_listing=None) -> dict:
    """v1 to v10 expectations with the v11 overlay, on the working tree (or, via read/listing, on a commit)."""
    root = Path(root)

    def digest(rel):
        target = root / rel
        if target.is_symlink() or not target.is_file():
            return None
        return target.read_bytes()
    read = read or digest
    exp = expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11)
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
        problems.append(f"undeclared file in v1 scope (v11 counts the Panchanga package too): {p}")
    in_packet = packet_listing() if packet_listing else v4m._packet_listing(root)
    for p in sorted(in_packet - set(v5["packet"]) - {RECORD}):
        problems.append(f"undeclared file in the editorial packet: {p}")
    if problems:
        raise IdentityError("PAN-QA-08 v11 identity failed:\n  " + "\n  ".join(problems))
    if unchanged != EXPECTED_UNCHANGED_V1:
        raise IdentityError(f"expected {EXPECTED_UNCHANGED_V1} byte-identical v1 files, found {unchanged}")
    return {"v1_unchanged": unchanged, "v5_packet": len(v5["packet"]), "v5_record": 1,
            "v11_package": len(v11["package"]), "v11_modified": len(v11["modified"])}


def verify_commit(root: Path, commit: str, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11) -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    names = [n for n in git.run("ls-tree", "-r", "-z", "--name-only", commit).split("\0") if n]
    exp = set(expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11)) | {RECORD}
    blobs = git.blobs(commit, sorted(exp))
    return verify_tree(root, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11, read=blobs.get,
                       listing=lambda: {n for n in names if v2m.in_scope(n)},
                       packet_listing=lambda: {n for n in names if n.startswith(PACKET_PREFIX)})


def verify_git_v11(root: Path, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11, commit: str = "HEAD") -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    if git.run("cat-file", "-t", BASE_COMMIT).strip() != "commit":
        raise IdentityError(f"{BASE_COMMIT} is not a commit here")
    sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
    if git.run("merge-base", BASE_COMMIT, sha).strip() != BASE_COMMIT:
        raise IdentityError("30bdace is not an ancestor of the commit under test")
    # The base itself is exactly the v10 tree: v10 regenerates there and 7d9d10a..30bdace is the v10 declaration.
    if v10m.generate(root, commit=BASE_COMMIT) != git.blobs(BASE_COMMIT, [v10m.V10_PATH])[v10m.V10_PATH]:
        raise IdentityError("v10 does not regenerate at 30bdace")
    v10m.verify_git_v10(root, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, commit=BASE_COMMIT)
    paths = list(v11["modified"]) + list(v11["package"])
    at_base, at_head = git.blobs(BASE_COMMIT, paths), git.blobs(sha, paths)
    problems = []
    base_pkg = {n for n in git.run("ls-tree", "-r", "-z", "--name-only", BASE_COMMIT).split("\0")
                if n.startswith(v2m.PANCHANGA_PACKAGE_PREFIX)}
    if base_pkg != set(v11["package"]) | {p for p in v11["modified"] if p.startswith(v2m.PANCHANGA_PACKAGE_PREFIX)}:
        problems.append("v11 package and modified package files are not exactly the Panchanga package at 30bdace")
    for p, e in v11["package"].items():
        for where, data in (("30bdace", at_base[p]), (sha[:7], at_head[p])):
            if data is None or sha256(data) != e["sha256"] or blob_id(data) != e["git_blob"]:
                problems.append(f"Panchanga package file differs from v11 at {where}: {p}")
    for p, e in v11["modified"].items():
        if at_base[p] is None or sha256(at_base[p]) != e["before_sha256"]:
            problems.append(f"v11 before_sha256 differs from the 30bdace git object: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["v11_sha256"] or blob_id(at_head[p]) != e["v11_git_blob"]:
            problems.append(f"v11 modified hash differs from the committed object: {p}")
    prior = v10_expectations(v1, v2, v3, v4, v5, v6, v7, v8, v9, v10)
    side = {p: s for p, s in git.name_status(BASE_COMMIT, sha).items()
            if v7m._scope_or_declared(p, prior) or p == RECORD}
    expect = {p: "M" for p in v11["modified"]}
    if RECORD in side and side[RECORD] == "M":
        expect[RECORD] = "M"   # decision fields may be recorded (frozen part checked by the tree step)
    if side != expect:
        problems.append(f"30bdace..{sha[:7]} differs from the v11 declaration: "
                        f"{sorted(set(side.items()) ^ set(expect.items()))}")
    if problems:
        raise IdentityError("PAN-QA-08 v11 exact-commit check failed:\n  " + "\n  ".join(problems))
    return {"commit": sha, **verify_commit(root, sha, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11)}


def generate(root: Path, commit: str = "HEAD", worktree: bool = False) -> bytes:
    """Build v11 from 30bdace and `commit` (or, for --write before committing, the working tree)."""
    root = Path(root)
    git = v2m.Git(root)
    v10_bytes = git.blobs(BASE_COMMIT, [v10m.V10_PATH])[v10m.V10_PATH]
    paths = list(AUTHORIZED_MODIFIED)
    if worktree:
        cur = {p: (root / p).read_bytes() if (root / p).is_file() else None for p in paths}
    else:
        sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
        cur = git.blobs(sha, paths)
    missing = [p for p in paths if cur[p] is None]
    if missing:
        raise IdentityError(f"cannot generate v11: missing {missing}")
    before = git.blobs(BASE_COMMIT, paths)
    mod = {p: {"before_sha256": sha256(before[p]), "v11_sha256": sha256(cur[p]), "v11_git_blob": blob_id(cur[p])}
           for p in paths}
    names = sorted(n for n in git.run("ls-tree", "-r", "-z", "--name-only", BASE_COMMIT).split("\0")
                   if n.startswith(v2m.PANCHANGA_PACKAGE_PREFIX) and n not in mod)
    base = git.blobs(BASE_COMMIT, names)
    package = {p: {"sha256": sha256(base[p]), "git_blob": blob_id(base[p])} for p in names}
    doc = {"manifest_schema": SCHEMA, "note": NOTE, "task": TASK, "v10_manifest": _v10_binding(v10_bytes),
           "package": package, "modified": mod, "counts": {"modified": len(mod), "package": len(package)}}
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="regenerate from HEAD; verify tree, v10 base and v11 on git")
    g.add_argument("--write", action="store_true", help="write the manifest from the working tree (developer use)")
    args = ap.parse_args(argv)
    if args.write:
        data = generate(REPO, worktree=True)
        (REPO / V11_PATH).write_bytes(data)
        print(f"wrote {V11_PATH} sha256 {sha256(data)}")
        return 0
    if (REPO / V11_PATH).read_bytes() != generate(REPO):
        print("FAIL: committed v11 manifest differs from the git-derived regeneration at HEAD")
        return 1
    *prior, v11 = load_committed(REPO)
    t = verify_tree(REPO, *prior, v11)
    g_ = verify_git_v11(REPO, *prior, v11)
    print(f"PASS v1 to v9 preserved (pinned in code); v10 {v10m.V10_SHA256} regenerates at 30bdace and "
          f"7d9d10a..30bdace is exactly the v10 declaration")
    print(f"PASS v11 sha256 {V11_SHA256} regenerated byte-identical from git objects at {g_['commit'][:7]}")
    print(f"PASS tree: {t['v1_unchanged']} v1 unchanged; Panchanga package ({t['v11_package']} other files) "
          f"byte-identical to 30bdace; v11 {t['v11_modified']} modified (status, provenance, pins and fixtures); "
          f"no undeclared file")
    print(f"PASS git: 30bdace..{g_['commit'][:7]} is exactly the v11 declaration")
    return 0


if __name__ == "__main__":
    sys.exit(main())
