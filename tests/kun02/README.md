# KUN-02 scientific probes (test-only)

Lagna `b"P"` versus `b"W"`, birth-time pipeline and supported-envelope probes. Nothing here is imported by the engine.
Reports, commands and the claim boundary: [docs/kun02/README.md](../../docs/kun02/README.md).

```bash
SABPUJA_TEST_EPHE_PATH=/srv/sabpuja/ephe python -m unittest discover -s tests -v
python -m tests.kun02.run --ephe /srv/sabpuja/ephe --report-dir reports/
```
