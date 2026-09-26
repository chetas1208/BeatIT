# BeatIT M10.5 Release Demo Golden Fixture

This directory is a compact, secret-free manifest of the canonical synthetic
demo inputs used by final verification. It references checked-in fixtures
rather than duplicating their contents. Every source is synthetic and
non-PHI; no value is an observed patient measurement.

Generate or refresh the manifest with:

```bash
python scripts/build_release_golden.py
```

Validate it with:

```bash
./scripts/verify-demo.sh
```
