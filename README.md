# LANDDY `.lnd` · lnd-format

> Agentic and human, we are free like an OS.

A plain-text format for knowledge that people and AI agents can both read, write, cite and review. A block opens with `@type id`, takes `key: value` lines and a Markdown body, and closes with `@@`. Reserved words work in English, Spanish and Chinese. This repository holds the specification, the reserved-word table, a minimal parser and the validator. Version **0.9.2**, Apache-2.0.

| Path | What it is |
|---|---|
| [spec/SPEC.md](spec/SPEC.md) | The specification (also [es](spec/SPEC.es.md), [zh-CN](spec/SPEC.zh-CN.md)); `.lnd` sources in `docs/lnd/` |
| [tools/keywords.json](tools/keywords.json) | Every reserved word in es, en and zh |
| `tools/lnd_parse.py` | Minimal parser: prints the normalized tree as JSON |
| `tools/lnd_check_v12.py` | Validator (`tools/lnd_check.py` is the short name) |
| `tools/lnd_keys.py` | Rewrites reserved words into another language; `--verificar` checks the round trip |
| `tools/pruebas_v12.py` | Unit tests |
| [examples/](examples/) | Example files in es, en and zh-CN |

```sh
python3 tools/lnd_check_v12.py --estricto examples/en/hello.lnd
python3 tools/lnd_parse.py --bloques examples/en/hello.lnd
python3 tools/lnd_keys.py --lang zh examples/en/hello.lnd
python3 tools/pruebas_v12.py
```

Python 3, no dependencies. To view a `.lnd` file in a browser, see [conocimiento.wiki](https://github.com/vikingux/conocimiento-wiki).

Other languages: [Español](README.es.md) · [简体中文](README.zh-CN.md). License: [Apache-2.0](LICENSE) · [NOTICE](NOTICE). Contact: [info@conocimiento.wiki](mailto:info@conocimiento.wiki).
