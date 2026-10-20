# Changelog

## 0.9.2 · 2026-10-20

First public release of the repository.

- Specification 1.2 in en, es and zh-CN (`spec/`, with `.lnd` sources in `docs/lnd/`).
- Reserved words in es, en and zh in `tools/keywords.json` (zh-CN is provisional).
- Minimal parser `tools/lnd_parse.py`: normalized JSON tree, the same for all three key languages.
- Validator `tools/lnd_check_v12.py` (short name `tools/lnd_check.py`) and key converter `tools/lnd_keys.py` with `--verificar` round trip.
- Unit tests `tools/pruebas_v12.py` and a GitHub Actions workflow that runs them.
- Examples in es, en and zh-CN.
