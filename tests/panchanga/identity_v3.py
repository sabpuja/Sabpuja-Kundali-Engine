"""PAN-QA-08 identity gate, version 3 (KUN-I18N-INT-001A).

v1 (`baseline-hashes.json`) and v2 (`identity-manifest-v2.json`) are preserved byte for
byte; both SHA-256 values stay pinned in `identity_v2.py`. v2 is now proved on the exact
tree of the commit it was audited with, `be608d8` (PR #71 review 5765253656).

The KUN-I18N-INT-001A remediation changes one v2-declared file and adds one test file. v3
(`identity-manifest-v3.json`, pinned below) declares exactly those two paths and nothing
else, each with its v2 expectation (for the modified path) and its new SHA-256 and git blob.
The current-tree check is v2's check with the v3 overlay: the 210 untouched v1 files, the
other 11 v2-modified files and all 55 v2-added files must still hold their v2 bytes.

`verify_git_v3` binds v3 to exact commits: at `be608d8` the modified path has its v2 bytes,
and `git diff be608d8 <commit>` inside the v1 scope (plus the v2-added paths) is exactly the
v3 declaration. Regenerate and compare:
    python -m tests.panchanga.identity_v3 --check
"""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from . import identity_v2 as v2m
from .identity_v2 import IdentityError, HEX40, HEX64, REPO, blob_id, sha256

V3_PATH = "tests/panchanga/identity-manifest-v3.json"
V3_SHA256 = "9a2051d9fd74ef016b5d48e9cd182714028dbbb017fda2a3df89f494276f0e77"
SCHEMA = "sabpuja-pan-qa-08-identity/3"
BASE_COMMIT = v2m.V2_CANDIDATE_COMMIT
TASK = "KUN-I18N-INT-001A"
# The only paths this remediation is authorized to touch (owner task KUN-I18N-INT-001A).
AUTHORIZED = {"modified": ("prototype/kundali_prototype/server.py",),
              "added": ("prototype/tests/test_report_slot_release.py",)}
NOTE = ("PAN-QA-08 identity manifest v3 (KUN-I18N-INT-001A). Declares the one v2 path the HTTP report "
        "repeatability fix changes (the render slot is released before the response is written) and the one "
        "regression test it adds, relative to the independently audited v2 candidate be608d8. v1 and v2 are "
        "preserved and bound here by their SHA-256. Generated from git objects only: "
        "python -m tests.panchanga.identity_v3 --check.")


def _scope_or_v2_added(path: str, v2: dict) -> bool:
    return v2m.in_scope(path) or path in v2["added"]


def validate_v3(doc, v1: dict, v2: dict, v2_bytes: bytes) -> dict:
    if not isinstance(doc, dict):
        raise IdentityError("v3 manifest must be an object")
    keys = {"manifest_schema", "note", "task", "v2_manifest", "modified", "added", "counts"}
    if set(doc) != keys:
        raise IdentityError(f"v3 manifest keys differ: {sorted(set(doc) ^ keys)}")
    if doc["manifest_schema"] != SCHEMA or doc["task"] != TASK:
        raise IdentityError("v3 manifest_schema or task wrong")
    if not isinstance(doc["note"], str) or not doc["note"]:
        raise IdentityError("v3 note missing")
    if doc["v2_manifest"] != {"path": v2m.V2_PATH, "sha256": sha256(v2_bytes), "base_commit": BASE_COMMIT,
                              "v1_sha256": v2m.V1_SHA256}:
        raise IdentityError("v3 v2_manifest record does not bind the preserved v1/v2 manifests")
    mod, add = doc["modified"], doc["added"]
    if not isinstance(mod, dict) or not isinstance(add, dict):
        raise IdentityError("v3 modified/added must be objects")
    if tuple(mod) != AUTHORIZED["modified"] or tuple(add) != AUTHORIZED["added"]:
        raise IdentityError("v3 paths differ from the authorized remediation paths")
    if doc["counts"] != {"modified": len(mod), "added": len(add)}:
        raise IdentityError("v3 counts wrong")
    for p, e in mod.items():
        if not isinstance(e, dict) or set(e) != {"v2_sha256", "v3_sha256", "v3_git_blob"} \
                or not all(isinstance(e[k], str) for k in e) or not HEX64.fullmatch(e["v2_sha256"]) \
                or not HEX64.fullmatch(e["v3_sha256"]) or not HEX40.fullmatch(e["v3_git_blob"]):
            raise IdentityError(f"v3 modified entry malformed: {p}")
        before = v2["modified"].get(p, {}).get("v2_sha256") or v2["added"].get(p, {}).get("sha256")
        if before is None:
            raise IdentityError(f"v3 modified path is not declared by v2: {p}")
        if e["v2_sha256"] != before:
            raise IdentityError(f"v3 modified entry v2_sha256 differs from v2: {p}")
        if e["v3_sha256"] == e["v2_sha256"]:
            raise IdentityError(f"v3 modified entry declares no change: {p}")
    for p, e in add.items():
        if p in v1["files"] or p in v2["added"] or p in mod or not v2m.in_scope(p):
            raise IdentityError(f"v3 added path not new or not in the v1 scope: {p}")
        if not isinstance(e, dict) or set(e) != {"sha256", "git_blob"} or not all(isinstance(e[k], str) for k in e) \
                or not HEX64.fullmatch(e["sha256"]) or not HEX40.fullmatch(e["git_blob"]):
            raise IdentityError(f"v3 added entry malformed: {p}")
    return doc


def load_v3(data: bytes, v1: dict, v2: dict, v2_bytes: bytes, expected_sha: str = None) -> dict:
    expected_sha = V3_SHA256 if expected_sha is None else expected_sha
    if sha256(data) != expected_sha:
        raise IdentityError("v3 manifest does not match its pinned SHA-256")
    try:
        doc = json.loads(data, object_pairs_hook=v2m._reject_duplicate_keys)
    except ValueError as exc:
        raise IdentityError(f"v3 manifest is not valid JSON: {exc}") from None
    return validate_v3(doc, v1, v2, v2_bytes)


def load_committed(root: Path = REPO):
    root = Path(root)
    v1, v2 = v2m.load_committed(root)
    v2_bytes = (root / v2m.V2_PATH).read_bytes()
    return v1, v2, load_v3((root / V3_PATH).read_bytes(), v1, v2, v2_bytes)


def verify_tree(root: Path, v1: dict, v2: dict, v3: dict) -> dict:
    return v2m.verify_tree(root, v1, v2, v3=v3)


def _side_diff(git, v2: dict, commit: str) -> dict:
    side = git.name_status(BASE_COMMIT, commit)
    return {p: s for p, s in side.items() if _scope_or_v2_added(p, v2)}


def verify_git_v3(root: Path, v1: dict, v2: dict, v3: dict, commit: str = "HEAD") -> dict:
    """v3 against exact commits: be608d8 carries the v2 bytes; be608d8..commit is exactly v3."""
    git = v2m.Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    if git.run("cat-file", "-t", BASE_COMMIT).strip() != "commit":
        raise IdentityError(f"{BASE_COMMIT} is not a commit here")
    sha = git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
    if git.run("merge-base", BASE_COMMIT, sha).strip() != BASE_COMMIT:
        raise IdentityError("the v2 candidate be608d8 is not an ancestor of the commit under test")
    problems = []
    at_base = git.blobs(BASE_COMMIT, list(v3["modified"]) + list(v3["added"]))
    at_head = git.blobs(sha, list(v3["modified"]) + list(v3["added"]))
    for p, e in v3["modified"].items():
        if at_base[p] is None or sha256(at_base[p]) != e["v2_sha256"]:
            problems.append(f"v3 v2_sha256 differs from the be608d8 git object: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["v3_sha256"] or blob_id(at_head[p]) != e["v3_git_blob"]:
            problems.append(f"v3 modified hash differs from the committed object: {p}")
    for p, e in v3["added"].items():
        if at_base[p] is not None:
            problems.append(f"v3 added path already exists at be608d8: {p}")
        if at_head[p] is None or sha256(at_head[p]) != e["sha256"] or blob_id(at_head[p]) != e["git_blob"]:
            problems.append(f"v3 added hash differs from the committed object: {p}")
    side = _side_diff(git, v2, sha)
    expect = {**{p: "M" for p in v3["modified"]}, **{p: "A" for p in v3["added"]}}
    if side != expect:
        problems.append(f"be608d8..{sha[:7]} differs from the v3 declaration: "
                        f"{sorted(set(side.items()) ^ set(expect.items()))}")
    if problems:
        raise IdentityError("PAN-QA-08 v3 exact-commit check failed:\n  " + "\n  ".join(problems))
    tree = v2m.verify_commit(root, sha, v1, v2, v3)
    return {"commit": sha, **tree}


def generate(root: Path, commit: str = "HEAD", worktree: bool = False) -> bytes:
    """Build v3 from be608d8 and `commit` (or, for --write before committing, the working tree)."""
    root = Path(root)
    git = v2m.Git(root)
    v2_bytes = git.blobs(BASE_COMMIT, [v2m.V2_PATH])[v2m.V2_PATH]
    v2 = json.loads(v2_bytes)
    paths = list(AUTHORIZED["modified"]) + list(AUTHORIZED["added"])
    if worktree:
        now = {p: (root / p).read_bytes() if (root / p).is_file() else None for p in paths}
    else:
        now = git.blobs(git.run("rev-parse", "--verify", f"{commit}^{{commit}}").strip(), paths)
    mod = {}
    for p in AUTHORIZED["modified"]:
        before = v2["modified"].get(p, {}).get("v2_sha256") or v2["added"][p]["sha256"]
        mod[p] = {"v2_sha256": before, "v3_sha256": sha256(now[p]), "v3_git_blob": blob_id(now[p])}
    add = {p: {"sha256": sha256(now[p]), "git_blob": blob_id(now[p])} for p in AUTHORIZED["added"]}
    doc = {"manifest_schema": SCHEMA, "note": NOTE, "task": TASK,
           "v2_manifest": {"path": v2m.V2_PATH, "sha256": sha256(v2_bytes), "base_commit": BASE_COMMIT,
                           "v1_sha256": v2m.V1_SHA256},
           "modified": mod, "added": add, "counts": {"modified": len(mod), "added": len(add)}}
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="regenerate from HEAD; verify tree, v2 and v3 on git")
    g.add_argument("--write", action="store_true", help="write the manifest from the working tree (developer use)")
    args = ap.parse_args(argv)
    if args.write:
        data = generate(REPO, worktree=True)
        (REPO / V3_PATH).write_bytes(data)
        print(f"wrote {V3_PATH} sha256 {sha256(data)}")
        return 0
    if (REPO / V3_PATH).read_bytes() != generate(REPO):
        print("FAIL: committed v3 manifest differs from the git-derived regeneration at HEAD")
        return 1
    v1, v2, v3 = load_committed(REPO)
    t = verify_tree(REPO, v1, v2, v3)
    g_ = verify_git_v3(REPO, v1, v2, v3)
    print(f"PASS v1 {v2m.V1_SHA256} and v2 {v2m.V2_SHA256} preserved (pinned in identity_v2)")
    print(f"PASS v3 sha256 {V3_SHA256} regenerated byte-identical from git objects at {g_['commit'][:7]}")
    print(f"PASS tree: {t['unchanged']} v1 unchanged, {t['modified']} v2 modified ({t['v3_modified']} of them "
          f"re-declared by v3), {t['added']} v2 added, {t['v3_added']} v3 added")
    print(f"PASS git: be608d8..{g_['commit'][:7]} is exactly the v3 declaration; committed tree verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
