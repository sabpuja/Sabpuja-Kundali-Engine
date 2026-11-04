"""PAN-QA-08: D1/D9 chart byte identity, Moon Nakshatra identity, unchanged schema 0.3.0 and /3.

1. Version-aware file identity (KUN-I18N-INT-001):
   v1 - `baseline-hashes.json`, the 222 SHA-256 values of the fixed engineering base
        PR #62, is preserved unchanged (pinned SHA-256) and proved against the git
        objects of 6722b5c. It is the historical acceptance record.
   v2 - `identity-manifest-v2.json` declares the 12 v1 files the bilingual integration
        (PR #61 fee3967) changes on purpose and the 55 files it adds. The current tree
        must hold the 210 other v1 files byte for byte, exactly the declared bytes for
        the 12 and the 55, and nothing undeclared in the v1 scope. See identity_v2.py.
   Until KUN-I18N-INT-001 this test asserted v1 directly against the working tree;
   that assertion is replaced by the v2 check, never skipped or relaxed.
2. Charts are byte-identical with and without a preceding Panchanga call in the
   same process, for all 50 KUN-SCI-GOLD-001 chart fixtures.
3. The Panchanga Nakshatra equals the chart `moon_nakshatra` byte for byte for the
   gold fixtures, a seeded sweep of 1970-2100 instants and births on Pada edges.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import copy
import hashlib
import json
import random
import unittest

from .common import EPHE, HERE, REPO, gold_chart_requests, parse_utc, real_data, request_at_utc
from . import checkers, identity_v2
from .phase_events import SideSwiss

BASELINE = json.loads((HERE / "baseline-hashes.json").read_text(encoding="utf-8"))


def dumps(doc) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=2)


class BaselineFilesTest(unittest.TestCase):
    def test_every_baseline_file_is_byte_identical_to_pr62(self):
        """v1 (historical): the preserved baseline equals the PR #62 git objects, all 222 files.

        Before KUN-I18N-INT-001 this compared v1 with the working tree. The working-tree
        comparison now runs through v2 (next test), which keeps v1 for the 210 files the
        integration does not touch and requires the declared bytes for the other 12.
        """
        self.assertEqual(BASELINE["base_commit"], "6722b5c46c3fb510495d8587b7b613f32691d97a")
        raw = (HERE / "baseline-hashes.json").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), identity_v2.V1_SHA256)
        self.assertEqual(len(BASELINE["files"]), 222)
        git = identity_v2.Git(REPO)
        self.assertTrue(git.available(), "PAN-QA-08 v1 needs a git clone with history back to PR #62 6722b5c")
        at_pr62 = git.blobs(identity_v2.V1_BASE_COMMIT, BASELINE["files"])
        changed = [p for p, digest in BASELINE["files"].items()
                   if at_pr62[p] is None or hashlib.sha256(at_pr62[p]).hexdigest() != digest]
        self.assertEqual(changed, [])

    def test_current_tree_matches_v2_identity_manifest(self):
        """v2 (current tree): 210 v1 files unchanged, 12 declared changes, 55 declared additions, nothing else."""
        v1, v2 = identity_v2.load_committed(REPO)
        self.assertEqual(identity_v2.verify_tree(REPO, v1, v2), {"unchanged": 210, "modified": 12, "added": 55})

    def test_v2_manifest_reproduces_from_exact_commits(self):
        """v2 regenerates byte for byte from git objects and binds to 6722b5c, 3ba9f5b and fee3967."""
        v1, v2 = identity_v2.load_committed(REPO)
        self.assertEqual(identity_v2.generate(REPO), (REPO / identity_v2.V2_PATH).read_bytes())
        self.assertEqual(identity_v2.verify_git(REPO, v1, v2), {"v1_checked": 222, "modified": 12, "added": 55})

    def test_new_engine_files_are_only_the_panchanga_package(self):
        tracked = {p for p in BASELINE["files"] if p.startswith("src/")}
        present = {str(p.relative_to(REPO)) for p in (REPO / "src").rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".pyc")
                   and ".egg-info" not in str(p)}
        extra = sorted(present - tracked)
        self.assertTrue(all(p.startswith("src/sabpuja_kundali/panchanga/") for p in extra), extra)

    def test_chart_schema_and_metadata_constants_unchanged(self):
        from sabpuja_kundali import provenance
        self.assertEqual(provenance.SCHEMA_VERSION, "0.3.0")
        self.assertEqual(provenance.METADATA_SCHEMA, "sabpuja-calculation-metadata/3")


@real_data
class ChartIdentityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sabpuja_kundali import engine
        cls.gold = gold_chart_requests()
        # Reference charts first, before any Panchanga call in this process.
        cls.reference = {fid: dumps(engine.calculate(req, EPHE)) for fid, req, _ in cls.gold}

    def test_charts_byte_identical_after_panchanga_calls(self):
        from sabpuja_kundali import engine
        from sabpuja_kundali.panchanga import calculate
        for fid, req, _ in self.gold:
            before = copy.deepcopy(req)
            doc = calculate(req, EPHE)
            self.assertEqual(req, before, "request mutated")
            self.assertEqual(dumps(engine.calculate(req, EPHE)), self.reference[fid], fid)
            chart = json.loads(self.reference[fid])
            self.assertEqual(chart["schema_version"], "0.3.0")
            self.assertEqual(chart["calculation_metadata"]["metadata_schema"], "sabpuja-calculation-metadata/3")
            self.assertEqual({k: doc["nakshatra"][k] for k in ("index", "name", "pada")}, chart["moon_nakshatra"])
            self.assertEqual(list(doc["nakshatra"])[:3], ["index", "name", "pada"])
            self.assertEqual(doc["birth"]["utc"], chart["birth"]["utc"])
            self.assertEqual(doc["provenance"]["chart_schema_version_unchanged"], "0.3.0")
            self.assertEqual(doc["provenance"]["ephemeris_manifest_sha256"],
                             chart["calculation_metadata"]["ephemeris_data"]["manifest_sha256"])

    def test_gold_documents_pass_the_independent_checker(self):
        from sabpuja_kundali import engine
        from sabpuja_kundali.panchanga import calculate
        side = SideSwiss(EPHE)
        for fid, req, _ in self.gold:
            doc = calculate(req, EPHE)
            self.assertEqual(checkers.check_document(doc, side, engine.calculate(req, EPHE)), [], fid)

    def test_nakshatra_identity_sweep_and_pada_edge_births(self):
        from sabpuja_kundali import engine
        from sabpuja_kundali.panchanga import calculate
        rng = random.Random(8080)
        start = datetime(1970, 1, 2, tzinfo=timezone.utc).timestamp()
        end = datetime(2100, 12, 30, tzinfo=timezone.utc).timestamp()
        zones = (("Asia/Kolkata", timedelta(hours=5, minutes=30)), ("Asia/Kathmandu", timedelta(hours=5, minutes=45)))
        edges = []
        for i in range(120):
            utc = datetime.fromtimestamp(rng.uniform(start, end), timezone.utc).replace(microsecond=rng.choice((0, 250000)))
            zone, offset = zones[i % 2]
            if zone == "Asia/Kathmandu" and utc.year < 1986:
                zone, offset = zones[0]
            req = request_at_utc(utc, zone, offset)
            doc, chart = calculate(req, EPHE), engine.calculate(req, EPHE)
            self.assertEqual({k: doc["nakshatra"][k] for k in ("index", "name", "pada")}, chart["moon_nakshatra"])
            if i < 10:
                edges.append(parse_utc(doc["nakshatra"]["pada_end"]["utc"]))
        for t in edges:
            for delta in (-1, 0):
                req = request_at_utc(t + timedelta(seconds=delta))
                doc, chart = calculate(req, EPHE), engine.calculate(req, EPHE)
                self.assertEqual({k: doc["nakshatra"][k] for k in ("index", "name", "pada")}, chart["moon_nakshatra"])
                if delta == 0:
                    self.assertEqual(doc["nakshatra"]["pada_start"]["utc"], t.strftime("%Y-%m-%dT%H:%M:%SZ"))


if __name__ == "__main__":
    unittest.main()
