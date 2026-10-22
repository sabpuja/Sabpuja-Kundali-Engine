# KUN-02 scientific probes (test-only)

Lagna `b"P"` versus `b"W"`, birth-time pipeline and supported-envelope probes. Nothing here is imported by the engine.
Reports, commands and the claim boundary: [docs/kun02/README.md](../../docs/kun02/README.md).

```bash
SABPUJA_TEST_EPHE_PATH=/srv/sabpuja/ephe python -m unittest discover -s tests -v
python -m tests.kun02.run --ephe /srv/sabpuja/ephe --report-dir reports/
```

Each runner invariant first checks that its evidence is complete against the fixtures (expected IDs and sample counts); an empty, partial or malformed probe section makes that invariant FAIL rather than pass vacuously. Count-based checks (A1–A8 points, A10 D1/D9 checks, B2 per-zone probe instants) require the exact predeclared totals, derived from the fixtures and the probe schedules (`lagna_probe.chart_consistency_plan`, `time_probe.iana_probe_instants`) and pinned by `test_predeclared_counts_are_frozen`. `InvariantGuards` in `test_kun02.py` injects such failures into a synthetic report and runs without ephemeris data.
