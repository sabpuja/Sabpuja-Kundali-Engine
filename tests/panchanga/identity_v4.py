"""PAN-QA-08 identity gate, version 4 (KUN-I18N-COPY-005).

v1 (`baseline-hashes.json`), v2 (`identity-manifest-v2.json`) and v3 (`identity-manifest-v3.json`) are
preserved byte for byte; their SHA-256 values stay pinned in `identity_v2.py` and `identity_v3.py`. v3 is
now proved on the exact trees of its audited commit `85f6a89` and of main `7fc1702` (the v4 base).

The owner-approved copy Changes A and B (issue #73) change a fixed, reviewed set of paths. v4
(`identity-manifest-v4.json`, pinned below) declares exactly that set and nothing else:

* `modified`: every changed path that v1, v2 or v3 already pins, with the SHA-256 it had before (which
  must equal the v1/v2/v3 expectation) and its new SHA-256 and git blob ID;
* `added`: the two new copy tests, which are new paths in the v1 scope;
* `packet`: the exact file inventory of the editorial review packet `docs/i18n/review/kun-i18n-003/`
  (path, SHA-256 and git blob ID of every file). No file may be added to, removed from or changed in the
  packet without a new, separately reviewed overlay. In particular a signed sheet under `signed/` or an
  edited `OWNER-COPY-ATTESTATION.md` is refused: a later signed-decision intake needs its own version.

The authorized paths are fixed in code (`AUTHORIZED`), not in the manifest. The current-tree check is the
v1/v2/v3 expectation with the v4 overlay: the 209 v1 files no version touches stay byte-identical to v1, every
other v2/v3 path keeps its declared bytes, and no undeclared file may appear in the v1 scope.

`verify_git_v4` binds v4 to exact commits: at `7fc1702` the tree satisfies v3, each modified path has its
declared "before" bytes and each added path is absent; at the commit under test every declared path has its
v4 bytes; and `git diff 7fc1702 <commit>` restricted to the v1 scope, the v2/v3-declared paths and the packet
is exactly the v4 declaration. Regenerate and compare (needs a clone with history):
    python -m tests.panchanga.identity_v4 --check
"""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from . import identity_v2 as v2m
from . import identity_v3 as v3m
from .identity_v2 import IdentityError, HEX40, HEX64, REPO, _safe_path, blob_id, sha256

V4_PATH = "tests/panchanga/identity-manifest-v4.json"
V4_SHA256 = "6f39046e8fc57e0129f67f96410fa4c5a3b3fefa4db7d65c8f27a8aa9602686b"
SCHEMA = "sabpuja-pan-qa-08-identity/4"
TASK = "KUN-I18N-COPY-005"
BASE_COMMIT = "7fc1702d4763001a9b14675db22c0d538935c68f"   # main after PR #71 (v3), owner issue #73 base
PACKET_PREFIX = "docs/i18n/review/kun-i18n-003/"
EXPECTED_UNCHANGED_V1 = 209   # v2's 210 minus report/phase1/tests/test_premium_name.py (Change A pins)

# The only paths KUN-I18N-COPY-005 is authorized to change (issue #73). Order is fixed.
AUTHORIZED = {
    "modified": (
        "docs/i18n/review/kun-i18n-003/CHANGE-A-ENGLISH-PAGE10.md",
        "docs/i18n/review/kun-i18n-003/CHANGE-B-SCHEMA-WORDING.md",
        "docs/i18n/review/kun-i18n-003/DECISION-SHEET.csv",
        "docs/i18n/review/kun-i18n-003/DECISION-SHEET.md",
        "docs/i18n/review/kun-i18n-003/EDITORIAL-ACCEPTANCE-REGISTER.md",
        "docs/i18n/review/kun-i18n-003/EVIDENCE-MANIFEST.md",
        "docs/i18n/review/kun-i18n-003/LOCATIONS.md",
        "docs/i18n/review/kun-i18n-003/README.md",
        "docs/i18n/review/kun-i18n-003/REVIEW-PACKET.md",
        "docs/i18n/review/kun-i18n-003/assets/en-hi-page-10.png",
        "docs/i18n/review/kun-i18n-003/assets/sample-en-anonymous.pdf",
        "docs/i18n/review/kun-i18n-003/assets/screens/i18n-en-1440.png",
        "docs/i18n/review/kun-i18n-003/assets/screens/i18n-en-280.png",
        "docs/i18n/review/kun-i18n-003/assets/screens/i18n-en-375.png",
        "docs/i18n/review/kun-i18n-003/assets/screens/i18n-en-768.png",
        "docs/i18n/review/kun-i18n-003/assets/screens/i18n-hi-1440.png",
        "docs/i18n/review/kun-i18n-003/assets/screens/i18n-hi-280.png",
        "docs/i18n/review/kun-i18n-003/assets/screens/i18n-hi-375.png",
        "docs/i18n/review/kun-i18n-003/assets/screens/i18n-hi-768.png",
        "docs/i18n/review/kun-i18n-003/editorial-acceptance-register.json",
        "docs/i18n/review/kun-i18n-003/locations.py",
        "prototype/kundali_prototype/static/i18n.json",
        "prototype/kundali_prototype/static/index.html",
        "report/phase1/report_i18n.json",
        "report/phase1/tests/test_premium_name.py",
    ),
    "added": (
        "report/phase1/tests/test_owner_copy_change_a.py",
        "report/phase1/tests/test_owner_copy_change_b.py",
    ),
    # New in the packet only (outside the v1 scope and not declared by v2/v3): inventoried in `packet`.
    "packet_added": (
        "docs/i18n/review/kun-i18n-003/OWNER-COPY-ATTESTATION.md",
    ),
}
NOTE = ("PAN-QA-08 identity manifest v4 (KUN-I18N-COPY-005). Declares the paths that the owner-approved copy "
        "Changes A (English PDF page 10) and B (web D9 footnote) change relative to main 7fc1702, each with its "
        "previous and new SHA-256, the two new copy tests, and the exact file inventory of the editorial review "
        "packet. v1, v2 and v3 are preserved and bound here by their SHA-256. No calculation, ephemeris, "
        "tolerance or chart value is declared. Generated from git objects only: "
        "python -m tests.panchanga.identity_v4 --check.")


# ---------------------------------------------------------------- expectations before v4

def prior_expectations(v1: dict, v2: dict, v3: dict) -> dict:
    """{path: (sha256, git_blob or None, label)} as v1 + v2 + v3 declare them."""
    exp = {p: (h, None, "v1") for p, h in v1["files"].items()}
    for p, e in v2["modified"].items():
        exp[p] = (e["v2_sha256"], e["v2_git_blob"], "v2 modified")
    for p, e in v2["added"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v2 added")
    for p, e in v3["modified"].items():
        exp[p] = (e["v3_sha256"], e["v3_git_blob"], "v3 modified")
    for p, e in v3["added"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v3 added")
    return exp


def _scope_or_declared(path: str, prior: dict) -> bool:
    return v2m.in_scope(path) or path in prior or path.startswith(PACKET_PREFIX)


# ---------------------------------------------------------------- manifest structure

def _entry(e, keys, where):
    if not isinstance(e, dict) or set(e) != set(keys) or not all(isinstance(e[k], str) for k in keys):
        raise IdentityError(f"v4 {where} entry malformed")
    for k in keys:
        if not (HEX40 if k.endswith("git_blob") else HEX64).fullmatch(e[k]):
            raise IdentityError(f"v4 {where} entry malformed")


def validate_v4(doc, v1: dict, v2: dict, v3: dict, v3_bytes: bytes) -> dict:
    if not isinstance(doc, dict):
        raise IdentityError("v4 manifest must be an object")
    keys = {"manifest_schema", "note", "task", "v3_manifest", "modified", "added", "packet", "counts"}
    if set(doc) != keys:
        raise IdentityError(f"v4 manifest keys differ: {sorted(set(doc) ^ keys)}")
    if doc["manifest_schema"] != SCHEMA or doc["task"] != TASK:
        raise IdentityError("v4 manifest_schema or task wrong")
    if not isinstance(doc["note"], str) or not doc["note"]:
        raise IdentityError("v4 note missing")
    if doc["v3_manifest"] != {"path": v3m.V3_PATH, "sha256": sha256(v3_bytes), "base_commit": BASE_COMMIT,
                              "v2_sha256": v2m.V2_SHA256, "v1_sha256": v2m.V1_SHA256} \
            or sha256(v3_bytes) != v3m.V3_SHA256:
        raise IdentityError("v4 v3_manifest record does not bind the preserved v1/v2/v3 manifests")
    mod, add, packet = doc["modified"], doc["added"], doc["packet"]
    if not all(isinstance(x, dict) for x in (mod, add, packet)):
        raise IdentityError("v4 modified/added/packet must be objects")
    if tuple(mod) != AUTHORIZED["modified"] or tuple(add) != AUTHORIZED["added"]:
        raise IdentityError("v4 paths differ from the authorized KUN-I18N-COPY-005 paths")
    if doc["counts"] != {"modified": len(mod), "added": len(add), "packet": len(packet)}:
        raise IdentityError("v4 counts wrong")
    prior = prior_expectations(v1, v2, v3)
    for p, e in mod.items():
        _entry(e, ("before_sha256", "v4_sha256", "v4_git_blob"), f"modified {p}:")
        if p not in prior:
            raise IdentityError(f"v4 modified path is not pinned by v1/v2/v3: {p}")
        if e["before_sha256"] != prior[p][0]:
            raise IdentityError(f"v4 modified entry before_sha256 differs from {prior[p][2]}: {p}")
        if e["v4_sha256"] == e["before_sha256"]:
            raise IdentityError(f"v4 modified entry declares no change: {p}")
    for p, e in add.items():
        if p in prior or not v2m.in_scope(p):
            raise IdentityError(f"v4 added path not new or not in the v1 scope: {p}")
        _entry(e, ("sha256", "git_blob"), f"added {p}:")
    if list(packet) != sorted(packet):
        raise IdentityError("v4 packet paths must be sorted")
    for p, e in packet.items():
        if not _safe_path(p) or not p.startswith(PACKET_PREFIX) or p == PACKET_PREFIX:
            raise IdentityError(f"v4 packet path unsafe or outside the packet: {p!r}")
        _entry(e, ("sha256", "git_blob"), f"packet {p}:")
        if p in mod and (e["sha256"], e["git_blob"]) != (mod[p]["v4_sha256"], mod[p]["v4_git_blob"]):
            raise IdentityError(f"v4 packet entry disagrees with its modified entry: {p}")
        if p not in mod and p in prior and e["sha256"] != prior[p][0]:
            raise IdentityError(f"v4 packet entry changes a {prior[p][2]} path without declaring it: {p}")
        if p not in mod and p not in prior and p not in AUTHORIZED["packet_added"]:
            raise IdentityError(f"v4 packet entry is a new, unauthorized file: {p}")
    for p in AUTHORIZED["packet_added"]:
        if p not in packet or p in prior:
            raise IdentityError(f"v4 authorized packet file missing or not new: {p}")
    for p in AUTHORIZED["modified"]:
        if p.startswith(PACKET_PREFIX) and p not in packet:
            raise IdentityError(f"v4 modified packet file missing from the inventory: {p}")
    for p in prior:
        if p.startswith(PACKET_PREFIX) and p not in packet:
            raise IdentityError(f"v4 packet inventory drops a v2-declared file: {p}")
    return doc


def load_v4(data: bytes, v1: dict, v2: dict, v3: dict, v3_bytes: bytes, expected_sha: str = None) -> dict:
    expected_sha = V4_SHA256 if expected_sha is None else expected_sha
    if sha256(data) != expected_sha:
        raise IdentityError("v4 manifest does not match its pinned SHA-256")
    try:
        doc = json.loads(data, object_pairs_hook=v2m._reject_duplicate_keys)
    except ValueError as exc:
        raise IdentityError(f"v4 manifest is not valid JSON: {exc}") from None
    return validate_v4(doc, v1, v2, v3, v3_bytes)


def load_committed(root: Path = REPO):
    root = Path(root)
    v1, v2, v3 = v3m.load_committed(root)
    v3_bytes = (root / v3m.V3_PATH).read_bytes()
    return v1, v2, v3, load_v4((root / V4_PATH).read_bytes(), v1, v2, v3, v3_bytes)


# ---------------------------------------------------------------- tree acceptance

def _packet_listing(root: Path) -> set:
    base = Path(root) / PACKET_PREFIX
    if not base.exists():
        return set()
    out = set()
    for p in base.rglob("*"):
        if "__pycache__" in p.parts or p.name.endswith(".pyc"):
            continue
        if p.is_symlink() or not p.is_dir():
            out.add(p.relative_to(root).as_posix())
    return out


def verify_tree(root: Path, v1: dict, v2: dict, v3: dict, v4: dict, *, read=None, listing=None,
                packet_listing=None) -> dict:
    """v1 + v2 + v3 expectations with the v4 overlay, on the working tree (or, via read/listing, on a commit)."""
    root = Path(root)

    def digest(rel):
        target = root / rel
        if target.is_symlink() or not target.is_file():
            return None
        return target.read_bytes()
    read = read or digest
    exp = prior_expectations(v1, v2, v3)
    for p, e in v4["modified"].items():
        exp[p] = (e["v4_sha256"], e["v4_git_blob"], "v4 modified")
    for p, e in v4["added"].items():
        exp[p] = (e["sha256"], e["git_blob"], "v4 added")
    for p, e in v4["packet"].items():
        if p not in exp:
            exp[p] = (e["sha256"], e["git_blob"], "v4 packet")
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
    present = listing() if listing else v2m._scope_files(root)
    for p in sorted(present - set(exp)):
        if not p.startswith(v2m.PANCHANGA_PACKAGE_PREFIX):
            problems.append(f"undeclared file in v1 scope: {p}")
    in_packet = packet_listing() if packet_listing else _packet_listing(root)
    for p in sorted(in_packet - set(v4["packet"])):
        problems.append(f"undeclared file in the editorial packet: {p}")
    if problems:
        raise IdentityError("PAN-QA-08 v4 identity failed:\n  " + "\n  ".join(problems))
    if unchanged != EXPECTED_UNCHANGED_V1:
        raise IdentityError(f"expected {EXPECTED_UNCHANGED_V1} byte-identical v1 files, found {unchanged}")
    return {"v1_unchanged": unchanged, "v2_modified": len(v2["modified"]), "v2_added": len(v2["added"]),
            "v3_modified": len(v3["modified"]), "v3_added": len(v3["added"]),
            "v4_modified": len(v4["modified"]), "v4_added": len(v4["added"]), "v4_packet": len(v4["packet"])}


def verify_commit(root: Path, commit: str, v1: dict, v2: dict, v3: dict, v4: dict) -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    names = [n for n in git.run("ls-tree", "-r", "-z", "--name-only", commit).split("\0") if n]
    exp = set(prior_expectations(v1, v2, v3)) | set(v4["added"]) | set(v4["packet"])
    blobs = git.blobs(commit, sorted(exp))
    return verify_tree(root, v1, v2, v3, v4, read=blobs.get, listing=lambda: {n for n in names if v2m.in_scope(n)},
                       packet_listing=lambda: {n for n in names if n.startswith(PACKET_PREFIX)})


def verify_git_v4(root: Path, v1: dict, v2: dict, v3: dict, v4: dict, commit: str = "HEAD") -> dict:
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    if git.run("cat-file", "-t", BASE_COMMIT).strip() != "commit":
        raise IdentityError(f"{BASE_COMMIT} is not a commit here")
    sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
    if git.run("merge-base", BASE_COMMIT, sha).strip() != BASE_COMMIT:
        raise IdentityError("main 7fc1702 is not an ancestor of the commit under test")
    v2m.verify_commit(root, BASE_COMMIT, v1, v2, v3)   # the base itself satisfies v3
    paths = list(v4["modified"]) + list(v4["added"]) + list(v4["packet"])
    at_base, at_head = git.blobs(BASE_COMMIT, paths), git.blobs(sha, paths)
    problems = []
    for p, e in v4["modified"].items():
        if at_base[p] is None or sha256(at_base[p]) != e["before_sha256"]:
            problems.append(f"v4 before_sha256 differs from the 7fc1702 git object: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["v4_sha256"] or blob_id(at_head[p]) != e["v4_git_blob"]:
            problems.append(f"v4 modified hash differs from the committed object: {p}")
    for p, e in list(v4["added"].items()) + [(p, v4["packet"][p]) for p in AUTHORIZED["packet_added"]]:
        if at_base[p] is not None:
            problems.append(f"v4 added path already exists at 7fc1702: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["sha256"] or blob_id(at_head[p]) != e["git_blob"]:
            problems.append(f"v4 added hash differs from the committed object: {p}")
    prior = prior_expectations(v1, v2, v3)
    side = {p: s for p, s in git.name_status(BASE_COMMIT, sha).items() if _scope_or_declared(p, prior)}
    expect = {**{p: "M" for p in v4["modified"]}, **{p: "A" for p in v4["added"]},
              **{p: "A" for p in AUTHORIZED["packet_added"]}}
    if side != expect:
        problems.append(f"7fc1702..{sha[:7]} differs from the v4 declaration: "
                        f"{sorted(set(side.items()) ^ set(expect.items()))}")
    if problems:
        raise IdentityError("PAN-QA-08 v4 exact-commit check failed:\n  " + "\n  ".join(problems))
    return {"commit": sha, **verify_commit(root, sha, v1, v2, v3, v4)}


# ---------------------------------------------------------------- generator

def generate(root: Path, commit: str = "HEAD", worktree: bool = False) -> bytes:
    """Build v4 from 7fc1702 and `commit` (or, for --write before committing, the working tree)."""
    root = Path(root)
    git = v2m.Git(root)
    v3_bytes = git.blobs(BASE_COMMIT, [v3m.V3_PATH])[v3m.V3_PATH]
    if worktree:
        packet_paths = sorted(_packet_listing(root))
        now = lambda ps: {p: (root / p).read_bytes() if (root / p).is_file() else None for p in ps}  # noqa: E731
    else:
        sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
        packet_paths = sorted(n for n in git.run("ls-tree", "-r", "-z", "--name-only", sha).split("\0")
                              if n.startswith(PACKET_PREFIX))
        now = lambda ps: git.blobs(sha, ps)  # noqa: E731
    before = git.blobs(BASE_COMMIT, list(AUTHORIZED["modified"]))
    cur = now(list(AUTHORIZED["modified"]) + list(AUTHORIZED["added"]) + packet_paths)
    mod = {p: {"before_sha256": sha256(before[p]), "v4_sha256": sha256(cur[p]), "v4_git_blob": blob_id(cur[p])}
           for p in AUTHORIZED["modified"]}
    add = {p: {"sha256": sha256(cur[p]), "git_blob": blob_id(cur[p])} for p in AUTHORIZED["added"]}
    packet = {p: {"sha256": sha256(cur[p]), "git_blob": blob_id(cur[p])} for p in packet_paths}
    doc = {"manifest_schema": SCHEMA, "note": NOTE, "task": TASK,
           "v3_manifest": {"path": v3m.V3_PATH, "sha256": sha256(v3_bytes), "base_commit": BASE_COMMIT,
                           "v2_sha256": v2m.V2_SHA256, "v1_sha256": v2m.V1_SHA256},
           "modified": mod, "added": add, "packet": packet,
           "counts": {"modified": len(mod), "added": len(add), "packet": len(packet)}}
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="regenerate from HEAD; verify tree, v3 base and v4 on git")
    g.add_argument("--write", action="store_true", help="write the manifest from the working tree (developer use)")
    args = ap.parse_args(argv)
    if args.write:
        data = generate(REPO, worktree=True)
        (REPO / V4_PATH).write_bytes(data)
        print(f"wrote {V4_PATH} sha256 {sha256(data)}")
        return 0
    if (REPO / V4_PATH).read_bytes() != generate(REPO):
        print("FAIL: committed v4 manifest differs from the git-derived regeneration at HEAD")
        return 1
    v1, v2, v3, v4 = load_committed(REPO)
    t = verify_tree(REPO, v1, v2, v3, v4)
    g_ = verify_git_v4(REPO, v1, v2, v3, v4)
    print(f"PASS v1 {v2m.V1_SHA256}, v2 {v2m.V2_SHA256} and v3 {v3m.V3_SHA256} preserved (pinned in code)")
    print(f"PASS v4 sha256 {V4_SHA256} regenerated byte-identical from git objects at {g_['commit'][:7]}")
    print(f"PASS tree: {t['v1_unchanged']} v1 unchanged; v4 {t['v4_modified']} modified, {t['v4_added']} added, "
          f"packet inventory {t['v4_packet']} files")
    print(f"PASS git: 7fc1702 satisfies v3; 7fc1702..{g_['commit'][:7]} is exactly the v4 declaration")
    return 0


if __name__ == "__main__":
    sys.exit(main())
