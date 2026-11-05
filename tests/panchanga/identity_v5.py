"""PAN-QA-08 identity gate, version 5 (KUN-GOV-SIMPLE-001, issue #75).

v1 (`baseline-hashes.json`), v2, v3 and v4 (`identity-manifest-v{2,3,4}.json`) are preserved byte for byte;
their SHA-256 values stay pinned in `identity_v2.py`, `identity_v3.py` and `identity_v4.py`. v4 is now proved
on the exact trees of its audited commit `b5e2fa7` and of main `4c57c73` (the v5 base).

v5 is the one-time bridge from the v4 packet inventory to the simplified owner policy ("the owner approves in
chat; the approval is recorded in GitHub; work continues"). It declares, in `identity-manifest-v5.json`
(pinned below):

* `modified`: the fixed set of paths KUN-GOV-SIMPLE-001 changes (the register gate and its tests, the
  packet documents that described signed paperwork), each with its v4-era SHA-256 and its new SHA-256 and
  git blob ID;
* `record`: the live decision record `editorial-acceptance-register.json`. Its **decision fields** (each
  item's `human_hindi_language`, `human_jyotish_terminology` and `owner_copy`, and `customer_release`) may
  change when a decision is recorded; everything else in it (rules, reviewed source, items, developer and
  engineering layers) is pinned through the SHA-256 of a canonical projection with those fields removed.
  The decision fields themselves are checked by `report/phase1/tests/test_editorial_register.py`;
* `packet`: the exact file inventory of the editorial packet, every file except the record pinned by
  SHA-256 and git blob ID. No file may be added (a `signed/` sheet included), removed or changed.

So recording an owner or reviewer decision changes only the record's decision fields and needs no v6, no
regenerated packages and no signature. Any change to catalogs, application code, tests, numerical
manifests, the rest of the packet or the frozen part of the record still fails here and needs explicit,
separately reviewed development work.

`verify_git_v5` binds v5 to exact commits: `4c57c73` satisfies v4, each modified path has its declared
"before" bytes there, and `git diff 4c57c73 <commit>` restricted to the v1 scope, the declared paths and the
packet is exactly the v5 declaration plus the record. Regenerate and compare (needs a clone with history):
    python -m tests.panchanga.identity_v5 --check
"""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from . import identity_v2 as v2m
from . import identity_v3 as v3m
from . import identity_v4 as v4m
from .identity_v2 import IdentityError, HEX40, HEX64, REPO, _safe_path, blob_id, sha256

V5_PATH = "tests/panchanga/identity-manifest-v5.json"
V5_SHA256 = "258312b69c9bf65ae6baf6cee0ef0b307fff22a1f6cd402a0f3f504a3d900d16"
SCHEMA = "sabpuja-pan-qa-08-identity/5"
TASK = "KUN-GOV-SIMPLE-001"
BASE_COMMIT = "4c57c7316615940c91a12cfbcf561c967888c5ab"   # main after PR #74 (v4), issue #75 base
PACKET_PREFIX = v4m.PACKET_PREFIX
RECORD = PACKET_PREFIX + "editorial-acceptance-register.json"
ITEM_DECISION_FIELDS = ("human_hindi_language", "human_jyotish_terminology", "owner_copy")
TOP_DECISION_FIELDS = ("customer_release",)
EXPECTED_UNCHANGED_V1 = 209   # as in v4: KUN-GOV-SIMPLE-001 changes no v1-pinned file

# The only paths KUN-GOV-SIMPLE-001 is authorized to change besides the record (issue #75). Order is fixed.
AUTHORIZED = (
    "docs/i18n/review/kun-i18n-003/CHANGE-A-ENGLISH-PAGE10.md",
    "docs/i18n/review/kun-i18n-003/CHANGE-B-SCHEMA-WORDING.md",
    "docs/i18n/review/kun-i18n-003/DECISION-SHEET.md",
    "docs/i18n/review/kun-i18n-003/EDITORIAL-ACCEPTANCE-REGISTER.md",
    "docs/i18n/review/kun-i18n-003/EVIDENCE-MANIFEST.md",
    "docs/i18n/review/kun-i18n-003/OWNER-COPY-ATTESTATION.md",
    "docs/i18n/review/kun-i18n-003/README.md",
    "docs/i18n/review/kun-i18n-003/REVIEW-PACKET.md",
    "docs/i18n/review/kun-i18n-003/refresh_manifest.py",
    "report/phase1/tests/test_editorial_register.py",
    "report/phase1/tests/test_owner_copy_change_a.py",
    "report/phase1/tests/test_owner_copy_change_b.py",
    "report/phase1/tests/test_review_packet_assets.py",
)
NOTE = ("PAN-QA-08 identity manifest v5 (KUN-GOV-SIMPLE-001). One-time bridge to the simplified owner policy: "
        "declares the paths that drop the signed-paperwork requirement relative to main 4c57c73, the exact "
        "editorial packet inventory, and the live decision record, whose decision fields may change when a "
        "decision recorded in GitHub is copied in, while the rest of it is pinned by a projection SHA-256. "
        "v1 to v4 are preserved and bound here by their SHA-256. No calculation, ephemeris, tolerance or chart "
        "value is declared. Generated from git objects only: python -m tests.panchanga.identity_v5 --check.")


# ---------------------------------------------------------------- the live decision record

def record_projection(data: bytes) -> bytes:
    """Canonical bytes of the record without its decision fields (refuses malformed or ambiguous JSON)."""
    try:
        doc = json.loads(data, object_pairs_hook=v2m._reject_duplicate_keys)
    except (ValueError, UnicodeDecodeError) as exc:
        raise IdentityError(f"decision record is not valid JSON: {exc}") from None
    if not isinstance(doc, dict) or not isinstance(doc.get("items"), list) \
            or not all(f in doc for f in TOP_DECISION_FIELDS):
        raise IdentityError("decision record has an unexpected shape")
    for f in TOP_DECISION_FIELDS:
        doc[f] = None
    for item in doc["items"]:
        if not isinstance(item, dict) or not all(f in item for f in ITEM_DECISION_FIELDS):
            raise IdentityError("decision record item has an unexpected shape")
        for f in ITEM_DECISION_FIELDS:
            item[f] = None
    return json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ---------------------------------------------------------------- expectations before v5

def v4_expectations(v1: dict, v2: dict, v3: dict, v4: dict) -> dict:
    """{path: (sha256, git_blob or None, label)} as v1 + v2 + v3 + v4 declare them."""
    exp = v4m.prior_expectations(v1, v2, v3)
    for p, e in v4["modified"].items():
        exp[p] = (e["v4_sha256"], e["v4_git_blob"], "v4 modified")
    for p, e in v4["added"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v4 added")
    for p, e in v4["packet"].items():
        if p not in exp:
            exp[p] = (e["sha256"], e["git_blob"], "v4 packet")
    return exp


def _scope_or_declared(path: str, prior: dict) -> bool:
    return v2m.in_scope(path) or path in prior or path.startswith(PACKET_PREFIX)


# ---------------------------------------------------------------- manifest structure

def _entry(e, keys, where):
    if not isinstance(e, dict) or set(e) != set(keys) or not all(isinstance(e[k], str) for k in keys):
        raise IdentityError(f"v5 {where} entry malformed")
    for k in keys:
        if not (HEX40 if k.endswith("git_blob") else HEX64).fullmatch(e[k]):
            raise IdentityError(f"v5 {where} entry malformed")


def validate_v5(doc, v1: dict, v2: dict, v3: dict, v4: dict, v4_bytes: bytes) -> dict:
    if not isinstance(doc, dict):
        raise IdentityError("v5 manifest must be an object")
    keys = {"manifest_schema", "note", "task", "v4_manifest", "modified", "record", "packet", "counts"}
    if set(doc) != keys:
        raise IdentityError(f"v5 manifest keys differ: {sorted(set(doc) ^ keys)}")
    if doc["manifest_schema"] != SCHEMA or doc["task"] != TASK:
        raise IdentityError("v5 manifest_schema or task wrong")
    if not isinstance(doc["note"], str) or not doc["note"]:
        raise IdentityError("v5 note missing")
    if doc["v4_manifest"] != {"path": v4m.V4_PATH, "sha256": sha256(v4_bytes), "base_commit": BASE_COMMIT,
                              "v3_sha256": v3m.V3_SHA256, "v2_sha256": v2m.V2_SHA256, "v1_sha256": v2m.V1_SHA256} \
            or sha256(v4_bytes) != v4m.V4_SHA256:
        raise IdentityError("v5 v4_manifest record does not bind the preserved v1/v2/v3/v4 manifests")
    mod, rec, packet = doc["modified"], doc["record"], doc["packet"]
    if not all(isinstance(x, dict) for x in (mod, rec, packet)):
        raise IdentityError("v5 modified/record/packet must be objects")
    if tuple(mod) != AUTHORIZED:
        raise IdentityError("v5 paths differ from the authorized KUN-GOV-SIMPLE-001 paths")
    if rec != {"path": RECORD, "item_decision_fields": list(ITEM_DECISION_FIELDS),
               "top_decision_fields": list(TOP_DECISION_FIELDS),
               "projection_sha256": rec.get("projection_sha256")} \
            or not HEX64.fullmatch(str(rec.get("projection_sha256"))):
        raise IdentityError("v5 record entry malformed")
    if doc["counts"] != {"modified": len(mod), "packet": len(packet)}:
        raise IdentityError("v5 counts wrong")
    prior = v4_expectations(v1, v2, v3, v4)
    for p, e in mod.items():
        _entry(e, ("before_sha256", "v5_sha256", "v5_git_blob"), f"modified {p}:")
        if p not in prior:
            raise IdentityError(f"v5 modified path is not pinned by v1 to v4: {p}")
        if e["before_sha256"] != prior[p][0]:
            raise IdentityError(f"v5 modified entry before_sha256 differs from {prior[p][2]}: {p}")
        if e["v5_sha256"] == e["before_sha256"]:
            raise IdentityError(f"v5 modified entry declares no change: {p}")
    if list(packet) != sorted(packet):
        raise IdentityError("v5 packet paths must be sorted")
    if RECORD in packet:
        raise IdentityError("v5 packet must not pin the live decision record (it is in `record`)")
    for p, e in packet.items():
        if not _safe_path(p) or not p.startswith(PACKET_PREFIX) or p == PACKET_PREFIX:
            raise IdentityError(f"v5 packet path unsafe or outside the packet: {p!r}")
        _entry(e, ("sha256", "git_blob"), f"packet {p}:")
        if p in mod and (e["sha256"], e["git_blob"]) != (mod[p]["v5_sha256"], mod[p]["v5_git_blob"]):
            raise IdentityError(f"v5 packet entry disagrees with its modified entry: {p}")
        if p not in mod and p in prior and e["sha256"] != prior[p][0]:
            raise IdentityError(f"v5 packet entry changes a {prior[p][2]} path without declaring it: {p}")
        if p not in prior:
            raise IdentityError(f"v5 packet entry is a new, unauthorized file: {p}")
    for p in AUTHORIZED:
        if p.startswith(PACKET_PREFIX) and p not in packet:
            raise IdentityError(f"v5 modified packet file missing from the inventory: {p}")
    for p in v4["packet"]:
        if p != RECORD and p not in packet:
            raise IdentityError(f"v5 packet inventory drops a v4 packet file: {p}")
    return doc


def load_v5(data: bytes, v1: dict, v2: dict, v3: dict, v4: dict, v4_bytes: bytes, expected_sha: str = None) -> dict:
    expected_sha = V5_SHA256 if expected_sha is None else expected_sha
    if sha256(data) != expected_sha:
        raise IdentityError("v5 manifest does not match its pinned SHA-256")
    try:
        doc = json.loads(data, object_pairs_hook=v2m._reject_duplicate_keys)
    except ValueError as exc:
        raise IdentityError(f"v5 manifest is not valid JSON: {exc}") from None
    return validate_v5(doc, v1, v2, v3, v4, v4_bytes)


def load_committed(root: Path = REPO):
    root = Path(root)
    v1, v2, v3, v4 = v4m.load_committed(root)
    v4_bytes = (root / v4m.V4_PATH).read_bytes()
    return v1, v2, v3, v4, load_v5((root / V5_PATH).read_bytes(), v1, v2, v3, v4, v4_bytes)


# ---------------------------------------------------------------- tree acceptance

def verify_tree(root: Path, v1: dict, v2: dict, v3: dict, v4: dict, v5: dict, *, read=None, listing=None,
                packet_listing=None) -> dict:
    """v1 to v4 expectations with the v5 overlay, on the working tree (or, via read/listing, on a commit)."""
    root = Path(root)

    def digest(rel):
        target = root / rel
        if target.is_symlink() or not target.is_file():
            return None
        return target.read_bytes()
    read = read or digest
    exp = v4_expectations(v1, v2, v3, v4)
    exp.pop(RECORD)
    for p, e in v5["modified"].items():
        exp[p] = (e["v5_sha256"], e["v5_git_blob"], "v5 modified")
    for p, e in v5["packet"].items():
        if p not in exp:
            exp[p] = (e["sha256"], e["git_blob"], "v5 packet")
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
            if sha256(record_projection(record)) != v5["record"]["projection_sha256"]:
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
        raise IdentityError("PAN-QA-08 v5 identity failed:\n  " + "\n  ".join(problems))
    if unchanged != EXPECTED_UNCHANGED_V1:
        raise IdentityError(f"expected {EXPECTED_UNCHANGED_V1} byte-identical v1 files, found {unchanged}")
    return {"v1_unchanged": unchanged, "v4_modified": len(v4["modified"]), "v4_added": len(v4["added"]),
            "v5_modified": len(v5["modified"]), "v5_packet": len(v5["packet"]), "v5_record": 1}


def verify_commit(root: Path, commit: str, v1: dict, v2: dict, v3: dict, v4: dict, v5: dict) -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    names = [n for n in git.run("ls-tree", "-r", "-z", "--name-only", commit).split("\0") if n]
    exp = set(v4_expectations(v1, v2, v3, v4)) | set(v5["packet"]) | {RECORD}
    blobs = git.blobs(commit, sorted(exp))
    return verify_tree(root, v1, v2, v3, v4, v5, read=blobs.get,
                       listing=lambda: {n for n in names if v2m.in_scope(n)},
                       packet_listing=lambda: {n for n in names if n.startswith(PACKET_PREFIX)})


def verify_git_v5(root: Path, v1: dict, v2: dict, v3: dict, v4: dict, v5: dict, commit: str = "HEAD") -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    if git.run("cat-file", "-t", BASE_COMMIT).strip() != "commit":
        raise IdentityError(f"{BASE_COMMIT} is not a commit here")
    sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
    if git.run("merge-base", BASE_COMMIT, sha).strip() != BASE_COMMIT:
        raise IdentityError("main 4c57c73 is not an ancestor of the commit under test")
    v4m.verify_commit(root, BASE_COMMIT, v1, v2, v3, v4)   # the base itself satisfies v4
    paths = list(v5["modified"]) + list(v5["packet"])
    at_base, at_head = git.blobs(BASE_COMMIT, paths), git.blobs(sha, paths)
    problems = []
    for p, e in v5["modified"].items():
        if at_base[p] is None or sha256(at_base[p]) != e["before_sha256"]:
            problems.append(f"v5 before_sha256 differs from the 4c57c73 git object: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["v5_sha256"] or blob_id(at_head[p]) != e["v5_git_blob"]:
            problems.append(f"v5 modified hash differs from the committed object: {p}")
    prior = v4_expectations(v1, v2, v3, v4)
    side = {p: s for p, s in git.name_status(BASE_COMMIT, sha).items() if _scope_or_declared(p, prior)}
    expect = {**{p: "M" for p in v5["modified"]}, RECORD: "M"}
    if side != expect:
        problems.append(f"4c57c73..{sha[:7]} differs from the v5 declaration: "
                        f"{sorted(set(side.items()) ^ set(expect.items()))}")
    if problems:
        raise IdentityError("PAN-QA-08 v5 exact-commit check failed:\n  " + "\n  ".join(problems))
    return {"commit": sha, **verify_commit(root, sha, v1, v2, v3, v4, v5)}


# ---------------------------------------------------------------- generator

def generate(root: Path, commit: str = "HEAD", worktree: bool = False) -> bytes:
    """Build v5 from 4c57c73 and `commit` (or, for --write before committing, the working tree)."""
    root = Path(root)
    git = v2m.Git(root)
    v4_bytes = git.blobs(BASE_COMMIT, [v4m.V4_PATH])[v4m.V4_PATH]
    if worktree:
        packet_paths = sorted(v4m._packet_listing(root))
        now = lambda ps: {p: (root / p).read_bytes() if (root / p).is_file() else None for p in ps}  # noqa: E731
    else:
        sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
        packet_paths = sorted(n for n in git.run("ls-tree", "-r", "-z", "--name-only", sha).split("\0")
                              if n.startswith(PACKET_PREFIX))
        now = lambda ps: git.blobs(sha, ps)  # noqa: E731
    packet_paths = [p for p in packet_paths if p != RECORD]
    before = git.blobs(BASE_COMMIT, list(AUTHORIZED))
    cur = now(list(AUTHORIZED) + packet_paths + [RECORD])
    mod = {p: {"before_sha256": sha256(before[p]), "v5_sha256": sha256(cur[p]), "v5_git_blob": blob_id(cur[p])}
           for p in AUTHORIZED}
    packet = {p: {"sha256": sha256(cur[p]), "git_blob": blob_id(cur[p])} for p in packet_paths}
    doc = {"manifest_schema": SCHEMA, "note": NOTE, "task": TASK,
           "v4_manifest": {"path": v4m.V4_PATH, "sha256": sha256(v4_bytes), "base_commit": BASE_COMMIT,
                           "v3_sha256": v3m.V3_SHA256, "v2_sha256": v2m.V2_SHA256, "v1_sha256": v2m.V1_SHA256},
           "modified": mod,
           "record": {"path": RECORD, "item_decision_fields": list(ITEM_DECISION_FIELDS),
                      "top_decision_fields": list(TOP_DECISION_FIELDS),
                      "projection_sha256": sha256(record_projection(cur[RECORD]))},
           "packet": packet, "counts": {"modified": len(mod), "packet": len(packet)}}
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="regenerate from HEAD; verify tree, v4 base and v5 on git")
    g.add_argument("--write", action="store_true", help="write the manifest from the working tree (developer use)")
    args = ap.parse_args(argv)
    if args.write:
        data = generate(REPO, worktree=True)
        (REPO / V5_PATH).write_bytes(data)
        print(f"wrote {V5_PATH} sha256 {sha256(data)}")
        return 0
    if (REPO / V5_PATH).read_bytes() != generate(REPO):
        print("FAIL: committed v5 manifest differs from the git-derived regeneration at HEAD")
        return 1
    v1, v2, v3, v4, v5 = load_committed(REPO)
    t = verify_tree(REPO, v1, v2, v3, v4, v5)
    g_ = verify_git_v5(REPO, v1, v2, v3, v4, v5)
    print(f"PASS v1 {v2m.V1_SHA256}, v2 {v2m.V2_SHA256}, v3 {v3m.V3_SHA256} and v4 {v4m.V4_SHA256} preserved "
          "(pinned in code)")
    print(f"PASS v5 sha256 {V5_SHA256} regenerated byte-identical from git objects at {g_['commit'][:7]}")
    print(f"PASS tree: {t['v1_unchanged']} v1 unchanged; v5 {t['v5_modified']} modified, packet inventory "
          f"{t['v5_packet']} files plus the decision record (frozen part pinned by projection)")
    print(f"PASS git: 4c57c73 satisfies v4; 4c57c73..{g_['commit'][:7]} is exactly the v5 declaration plus the record")
    return 0


if __name__ == "__main__":
    sys.exit(main())
