"""PAN-QA-08 identity gate, version 2 (KUN-I18N-INT-001).

Version 1 (`baseline-hashes.json`, 222 SHA-256 values taken from the git objects of
PR #62 `6722b5c`) is preserved byte for byte and is never regenerated. It stays the
historical acceptance record for the PR #62 / PR #68 engineering base.

The bilingual integration (PR #61 `fee3967`, carrying PR #59 and PR #60) changes 12
of those 222 files on purpose and adds 55 new paths. Version 2
(`identity-manifest-v2.json`) declares exactly those changes and nothing else:

* every one of the 12 modified paths with its v1 SHA-256 (which must equal the v1
  baseline) and its v2 SHA-256 and git blob ID (which must equal PR #61);
* every one of the 55 added paths with its SHA-256 and git blob ID;
* the SHA-256 of the v1 baseline file itself, so the baseline cannot be swapped.

`verify_tree` is the current-working-tree acceptance: the other 210 v1 files must be
byte-identical to v1, the 12 must carry their declared v2 bytes, the 55 must be
present with their declared bytes, and no file in the v1 scope may exist that neither
version declares (except the PR #68 Panchanga package, which the existing PAN-QA-08
test already confines to `src/sabpuja_kundali/panchanga/`).

`verify_git` proves the same manifest against exact commits: v1 hashes against the
blobs of `6722b5c`, v2 hashes against the blobs of `fee3967`, and the declared path
set against `git diff merge-base..fee3967`.

Both manifests' SHA-256 values are pinned below, in code, so that changing either
one is a reviewable code change rather than a data edit. Nothing here reads or alters
a scientific tolerance, an ephemeris or a chart value.

Regenerate (deterministic, from git objects only) and compare:
    python -m tests.panchanga.identity_v2 --check
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

V1_PATH = "tests/panchanga/baseline-hashes.json"
V2_PATH = "tests/panchanga/identity-manifest-v2.json"

# Pinned in code. The v1 value is the SHA-256 of the file as committed in PR #68 and
# carried unchanged to main 3ba9f5b; it must never change.
V1_SHA256 = "2e913eda7bb60f6159463ee219b4ad840a7fa971bf66e39ac30b871158cb007e"
V2_SHA256 = "d2dea049b652df4ff3f02ce5064e211d3b7f0c97d222e085ce36826bc2f087da"

V1_BASE_COMMIT = "6722b5c46c3fb510495d8587b7b613f32691d97a"   # PR #62
V1_FILE_COUNT = 222
MAIN_COMMIT = "3ba9f5b14739f08d5d07ef476bebb0584b463da0"      # approved main
INTEGRATED_HEAD = "fee3967d62d0229e31de98682da9ada5d9190e93"  # PR #61 head (with #59, #60)
MERGE_BASE = "fde3ec670618a02f2b913e9bbbedd1521d3840c7"       # PR #58, merge base with main
# The commit that introduced and was independently audited with v2 (PR #71 review 5765253656).
V2_CANDIDATE_COMMIT = "be608d873fe9af22d91c3d87ccb6659337b215e3"
SCHEMA = "sabpuja-pan-qa-08-identity/2"
EXPECTED_COUNTS = {"v1": 222, "modified": 12, "unchanged": 210, "added": 55}

# The v1 scope, exactly as the v1 note states it. Fixed in code, not in the manifest.
SCOPE_ROOTS = ("src", "report", "prototype", "preview", "tests", "data", "examples")
SCOPE_FILES = ("pyproject.toml",)
SCOPE_EXCLUDED_PREFIX = "tests/panchanga/"
# Inherited from PR #68 and already enforced by the existing PAN-QA-08 test.
PANCHANGA_PACKAGE_PREFIX = "src/sabpuja_kundali/panchanga/"

HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")


class IdentityError(AssertionError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _safe_path(p) -> bool:
    if not isinstance(p, str) or not p or "\\" in p or "\0" in p:
        return False
    pp = PurePosixPath(p)
    return not pp.is_absolute() and all(part not in ("", ".", "..") for part in p.split("/"))


def in_scope(path: str) -> bool:
    if path in SCOPE_FILES:
        return True
    return path.split("/", 1)[0] in SCOPE_ROOTS and not path.startswith(SCOPE_EXCLUDED_PREFIX)


# ---------------------------------------------------------------- manifest structure

def load_v1(data: bytes, expected_sha: str = None) -> dict:
    expected_sha = V1_SHA256 if expected_sha is None else expected_sha
    if sha256(data) != expected_sha:
        raise IdentityError("v1 baseline does not match its pinned SHA-256 (baseline substitution)")
    doc = json.loads(data)
    if set(doc) != {"note", "base_commit", "files"} or doc["base_commit"] != V1_BASE_COMMIT:
        raise IdentityError("v1 baseline structure changed")
    files = doc["files"]
    if not isinstance(files, dict) or len(files) != V1_FILE_COUNT:
        raise IdentityError("v1 baseline must list exactly 222 files")
    for p, h in files.items():
        if not _safe_path(p) or not isinstance(h, str) or not HEX64.fullmatch(h):
            raise IdentityError(f"v1 baseline entry malformed: {p!r}")
    return doc


def _reject_duplicate_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise IdentityError(f"duplicate key in manifest: {k!r}")
        out[k] = v
    return out


def load_v2(data: bytes, v1: dict, v1_bytes: bytes, expected_sha: str = None) -> dict:
    """Parse and validate the v2 manifest against the (already verified) v1 baseline."""
    expected_sha = V2_SHA256 if expected_sha is None else expected_sha
    if sha256(data) != expected_sha:
        raise IdentityError("v2 manifest does not match its pinned SHA-256")
    try:
        doc = json.loads(data, object_pairs_hook=_reject_duplicate_keys)
    except ValueError as exc:
        raise IdentityError(f"v2 manifest is not valid JSON: {exc}") from None
    return validate_v2(doc, v1, v1_bytes)


def validate_v2(doc, v1: dict, v1_bytes: bytes) -> dict:
    if not isinstance(doc, dict):
        raise IdentityError("v2 manifest must be an object")
    keys = {"manifest_schema", "note", "v1_baseline", "sources", "modified", "added", "counts"}
    if set(doc) != keys:
        raise IdentityError(f"v2 manifest keys differ: {sorted(set(doc) ^ keys)}")
    if doc["manifest_schema"] != SCHEMA:
        raise IdentityError("v2 manifest_schema wrong")
    if not isinstance(doc["note"], str) or not doc["note"]:
        raise IdentityError("v2 note missing")
    base = doc["v1_baseline"]
    if base != {"path": V1_PATH, "sha256": sha256(v1_bytes), "base_commit": V1_BASE_COMMIT,
                "file_count": V1_FILE_COUNT}:
        raise IdentityError("v2 v1_baseline record does not bind the preserved v1 baseline")
    if doc["sources"] != {"main": MAIN_COMMIT, "integrated_head": INTEGRATED_HEAD, "merge_base": MERGE_BASE}:
        raise IdentityError("v2 sources do not name the approved commits")
    if doc["counts"] != EXPECTED_COUNTS:
        raise IdentityError("v2 counts differ from 222 / 12 / 210 / 55")
    mod, add = doc["modified"], doc["added"]
    if not isinstance(mod, dict) or not isinstance(add, dict):
        raise IdentityError("v2 modified/added must be objects")
    if list(mod) != sorted(mod) or list(add) != sorted(add):
        raise IdentityError("v2 paths must be sorted")
    if len(mod) != EXPECTED_COUNTS["modified"] or len(add) != EXPECTED_COUNTS["added"]:
        raise IdentityError("v2 path counts differ from the declared counts")
    files = v1["files"]
    for p, e in mod.items():
        if not _safe_path(p):
            raise IdentityError(f"modified path unsafe: {p!r}")
        if p not in files:
            raise IdentityError(f"modified path is not a v1 file: {p}")
        if not isinstance(e, dict) or set(e) != {"v1_sha256", "v2_sha256", "v2_git_blob"}:
            raise IdentityError(f"modified entry malformed: {p}")
        if not all(isinstance(e[k], str) for k in e) or not HEX64.fullmatch(e["v1_sha256"]) \
                or not HEX64.fullmatch(e["v2_sha256"]) or not HEX40.fullmatch(e["v2_git_blob"]):
            raise IdentityError(f"modified entry hash malformed: {p}")
        if e["v1_sha256"] != files[p]:
            raise IdentityError(f"modified entry v1_sha256 differs from the v1 baseline: {p}")
        if e["v2_sha256"] == e["v1_sha256"]:
            raise IdentityError(f"modified entry declares no change: {p}")
    for p, e in add.items():
        if not _safe_path(p):
            raise IdentityError(f"added path unsafe: {p!r}")
        if p in files or p in mod:
            raise IdentityError(f"added path already exists in v1: {p}")
        if p in (V1_PATH, V2_PATH):
            raise IdentityError(f"a manifest cannot declare itself: {p}")
        if not isinstance(e, dict) or set(e) != {"sha256", "git_blob"} or not all(isinstance(e[k], str) for k in e) \
                or not HEX64.fullmatch(e["sha256"]) or not HEX40.fullmatch(e["git_blob"]):
            raise IdentityError(f"added entry malformed: {p}")
    if len(files) - len(mod) != EXPECTED_COUNTS["unchanged"]:
        raise IdentityError("unchanged count is not 210")
    return doc


# ---------------------------------------------------------------- working tree

def _scope_files(root: Path) -> set[str]:
    out = set()
    for name in SCOPE_FILES:
        if (root / name).is_file():
            out.add(name)
    for top in SCOPE_ROOTS:
        base = root / top
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_dir() or "__pycache__" in p.parts or p.name.endswith(".pyc") or ".egg-info" in str(p):
                continue
            rel = p.relative_to(root).as_posix()
            if in_scope(rel):
                out.add(rel)
    return out


def verify_tree(root: Path, v1: dict, v2: dict, *, read=None, listing=None, v3: dict = None) -> dict:
    """Tree acceptance against v2 (optionally with the v3 overlay). Raises IdentityError listing every problem.

    By default the working tree under `root` is read. `read(path) -> bytes | None` and
    `listing() -> set[str]` let the same check run on an exact git commit (`verify_commit`).
    `v3` (identity_v3) replaces the expected bytes of the v2 paths it declares as modified and
    adds the paths it declares as added; every other expectation is v2's, unchanged.
    """
    root = Path(root)
    files, mod, add = v1["files"], v2["modified"], dict(v2["added"])
    v3_mod = v3["modified"] if v3 else {}
    v3_add = v3["added"] if v3 else {}
    problems, unchanged = [], 0

    def digest(rel):
        target = root / rel
        if target.is_symlink() or not target.is_file():
            return None
        return target.read_bytes()
    read = read or digest

    def expect(p, data, sha, blob, label):
        if sha256(data) != sha or blob_id(data) != blob:
            problems.append(f"unexpected hash (declared {label}): {p}")

    for p, h in files.items():
        data = read(p)
        if data is None:
            problems.append(f"missing: {p}")
        elif p in v3_mod:
            expect(p, data, v3_mod[p]["v3_sha256"], v3_mod[p]["v3_git_blob"], "v3 modified")
        elif p in mod:
            expect(p, data, mod[p]["v2_sha256"], mod[p]["v2_git_blob"], "v2 modified")
        elif sha256(data) != h:
            problems.append(f"undeclared change to a v1 file: {p}")
        else:
            unchanged += 1
    for p, e in add.items():
        data = read(p)
        if data is None:
            problems.append(f"missing: {p}")
        elif p in v3_mod:
            expect(p, data, v3_mod[p]["v3_sha256"], v3_mod[p]["v3_git_blob"], "v3 modified")
        else:
            expect(p, data, e["sha256"], e["git_blob"], "v2 added")
    for p, e in v3_add.items():
        data = read(p)
        if data is None:
            problems.append(f"missing: {p}")
        else:
            expect(p, data, e["sha256"], e["git_blob"], "v3 added")
    declared = set(files) | set(add) | set(v3_add)
    present = listing() if listing else _scope_files(root)
    for p in sorted(present - declared):
        if not p.startswith(PANCHANGA_PACKAGE_PREFIX):
            problems.append(f"undeclared file in v1 scope: {p}")
    if problems:
        raise IdentityError(f"PAN-QA-08 {'v3' if v3 else 'v2'} identity failed:\n  " + "\n  ".join(problems))
    if unchanged != EXPECTED_COUNTS["unchanged"]:
        raise IdentityError(f"expected 210 byte-identical v1 files, found {unchanged}")
    out = {"unchanged": unchanged, "modified": len(mod), "added": len(add)}
    if v3:
        out.update(v3_modified=len(v3_mod), v3_added=len(v3_add))
    return out


def verify_commit(root: Path, commit: str, v1: dict, v2: dict, v3: dict = None) -> dict:
    """The same tree acceptance on the committed tree of `commit` (git objects, not the disk)."""
    git = Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    names = [n for n in git.run("ls-tree", "-r", "-z", "--name-only", commit).split("\0") if n]
    scope = {n for n in names if in_scope(n)}
    v3_paths = list(v3["modified"]) + list(v3["added"]) if v3 else []
    wanted = sorted(set(v1["files"]) | set(v2["added"]) | set(v3_paths))
    blobs = git.blobs(commit, wanted)
    return verify_tree(root, v1, v2, read=blobs.get, listing=lambda: scope, v3=v3)


# ---------------------------------------------------------------- exact git commits

class Git:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

    def run(self, *args, text=True):
        res = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=text, env=self.env)
        if res.returncode != 0:
            raise IdentityError(f"git {' '.join(args[:2])} failed: needs a clone with history back to "
                                f"PR #62 6722b5c (e.g. git fetch --depth=200)")
        return res.stdout

    def available(self) -> bool:
        if shutil.which("git") is None:
            return False
        try:
            return Path(self.run("rev-parse", "--show-toplevel").strip()).resolve() == self.root
        except IdentityError:
            return False

    def blobs(self, commit: str, paths) -> dict:
        """{path: bytes or None} for `paths` at `commit`, via one cat-file batch."""
        paths = list(paths)
        req = "".join(f"{commit}:{p}\n" for p in paths).encode()
        res = subprocess.run(["git", "-C", str(self.root), "cat-file", "--batch"], input=req,
                             capture_output=True, env=self.env)
        if res.returncode != 0:
            raise IdentityError("git cat-file --batch failed")
        out, i, result = res.stdout, 0, {}
        for p in paths:
            nl = out.index(b"\n", i)
            header = out[i:nl].decode()
            i = nl + 1
            if header.endswith(" missing"):
                result[p] = None
                continue
            size = int(header.split()[2])
            result[p] = out[i:i + size]
            i += size + 1
        return result

    def name_status(self, a: str, b: str) -> dict:
        out = self.run("diff", "--no-renames", "--name-status", "-z", a, b)
        parts = out.split("\0")
        return {parts[k + 1]: parts[k] for k in range(0, len(parts) - 1, 2)}


def verify_git(root: Path, v1: dict, v2: dict) -> dict:
    """Prove v1 and v2 against exact commits: 6722b5c (v1), fee3967 (v2) and merge-base..fee3967."""
    git = Git(root)
    if not git.available():
        raise IdentityError("not a git clone of this repository: exact-commit checks cannot run")
    for c in (V1_BASE_COMMIT, MAIN_COMMIT, INTEGRATED_HEAD, MERGE_BASE):
        if git.run("cat-file", "-t", c).strip() != "commit":
            raise IdentityError(f"{c} is not a commit here")
    if git.run("merge-base", MAIN_COMMIT, INTEGRATED_HEAD).strip() != MERGE_BASE:
        raise IdentityError("merge base of main and PR #61 is not fde3ec6")
    problems = []
    files, mod, add = v1["files"], v2["modified"], v2["added"]
    at_v1 = git.blobs(V1_BASE_COMMIT, files)
    for p, h in files.items():
        if at_v1[p] is None or sha256(at_v1[p]) != h:
            problems.append(f"v1 hash differs from PR #62 git object: {p}")
    at_head = git.blobs(INTEGRATED_HEAD, list(mod) + list(add))
    at_main = git.blobs(MAIN_COMMIT, list(files) + list(add) + [V1_PATH])
    for p, e in mod.items():
        data = at_head[p]
        if data is None or sha256(data) != e["v2_sha256"] or blob_id(data) != e["v2_git_blob"]:
            problems.append(f"v2 modified hash differs from PR #61 git object: {p}")
    for p, e in add.items():
        data = at_head[p]
        if data is None or sha256(data) != e["sha256"] or blob_id(data) != e["git_blob"]:
            problems.append(f"v2 added hash differs from PR #61 git object: {p}")
        if at_main[p] is not None:
            problems.append(f"v2 added path already on main: {p}")
    for p, h in files.items():
        if at_main[p] is None or sha256(at_main[p]) != h:
            problems.append(f"approved main does not carry the v1 bytes: {p}")
    if at_main[V1_PATH] is None or sha256(at_main[V1_PATH]) != v2["v1_baseline"]["sha256"]:
        problems.append("approved main's v1 baseline differs from the preserved one")
    side = git.name_status(MERGE_BASE, INTEGRATED_HEAD)
    expect = {**{p: "M" for p in mod}, **{p: "A" for p in add}}
    if side != expect:
        problems.append(f"PR #61 side diff differs from v2 declaration: {sorted(set(side.items()) ^ set(expect.items()))}")
    if problems:
        raise IdentityError("PAN-QA-08 v2 exact-commit check failed:\n  " + "\n  ".join(problems))
    return {"v1_checked": len(files), "modified": len(mod), "added": len(add)}


# ---------------------------------------------------------------- generator

NOTE = ("PAN-QA-08 identity manifest v2 (KUN-I18N-INT-001). Declares the 12 v1-baseline paths that the "
        "bilingual integration of PR #61 fee3967 (with PR #59 and PR #60) changes on purpose, with their v1 "
        "and v2 SHA-256, and inventories the 55 paths it adds. The v1 baseline is preserved unchanged and "
        "bound here by its own SHA-256. Generated from git objects only: "
        "python -m tests.panchanga.identity_v2 --check.")


def generate(root: Path) -> bytes:
    git = Git(root)
    v1_bytes = git.blobs(MAIN_COMMIT, [V1_PATH])[V1_PATH]
    v1 = json.loads(v1_bytes)
    side = git.name_status(MERGE_BASE, INTEGRATED_HEAD)
    head = git.blobs(INTEGRATED_HEAD, sorted(side))
    mod, add = {}, {}
    for p in sorted(side):
        data = head[p]
        if side[p] == "M" and p in v1["files"]:
            mod[p] = {"v1_sha256": v1["files"][p], "v2_sha256": sha256(data), "v2_git_blob": blob_id(data)}
        elif side[p] == "A":
            add[p] = {"sha256": sha256(data), "git_blob": blob_id(data)}
        else:
            raise IdentityError(f"PR #61 side change outside the v1 baseline or not M/A: {side[p]} {p}")
    doc = {
        "manifest_schema": SCHEMA,
        "note": NOTE,
        "v1_baseline": {"path": V1_PATH, "sha256": sha256(v1_bytes), "base_commit": V1_BASE_COMMIT,
                        "file_count": len(v1["files"])},
        "sources": {"main": MAIN_COMMIT, "integrated_head": INTEGRATED_HEAD, "merge_base": MERGE_BASE},
        "modified": mod,
        "added": add,
        "counts": {"v1": len(v1["files"]), "modified": len(mod), "unchanged": len(v1["files"]) - len(mod),
                   "added": len(add)},
    }
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def load_committed(root: Path = REPO):
    v1_bytes = (Path(root) / V1_PATH).read_bytes()
    v1 = load_v1(v1_bytes)
    v2 = load_v2((Path(root) / V2_PATH).read_bytes(), v1, v1_bytes)
    return v1, v2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="regenerate from git and compare; verify tree and git")
    g.add_argument("--write", action="store_true", help="write the manifest (developer use; review the diff)")
    args = ap.parse_args(argv)
    data = generate(REPO)
    if args.write:
        (REPO / V2_PATH).write_bytes(data)
        print(f"wrote {V2_PATH} sha256 {sha256(data)}")
        return 0
    committed = (REPO / V2_PATH).read_bytes()
    if committed != data:
        print("FAIL: committed v2 manifest differs from the git-derived regeneration")
        return 1
    v1, v2 = load_committed(REPO)
    t = verify_commit(REPO, V2_CANDIDATE_COMMIT, v1, v2)
    g_ = verify_git(REPO, v1, v2)
    print(f"PASS v1 sha256 {V1_SHA256} ({V1_FILE_COUNT} files, PR #62 {V1_BASE_COMMIT[:7]})")
    print(f"PASS v2 sha256 {V2_SHA256} regenerated byte-identical from git objects")
    print(f"PASS v2 tree at {V2_CANDIDATE_COMMIT[:7]}: {t['unchanged']} unchanged, {t['modified']} modified, "
          f"{t['added']} added (the current tree is checked by identity_v3)")
    print(f"PASS git: {g_['v1_checked']} v1 hashes = 6722b5c blobs; {g_['modified']}+{g_['added']} = fee3967 blobs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
