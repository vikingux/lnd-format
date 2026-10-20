<!-- Generado desde .lnd por build_paquetes.py · no editar a mano / generated from .lnd — do not edit -->

# LANDDY `.lnd` specification · profile lnd-1
The rules a parser must follow to read a `.lnd` file, the block types the reference renderer understands, and the diagnostics the validator reports. Each rule is marked **Normative** (required), **Implemented** (the reference renderer does it) or **Proposed** (under discussion).

<a id="h-file"></a>
## 1 · File

<a id="tb-file"></a>
**File basics**

| Item | Rule | Status |
|---|---|---|
| Extension | `.lnd` | Normative |
| Media type | `text/x-lnd; charset=utf-8` | Proposed |
| Encoding | UTF-8. Line endings `\n` or `\r\n`, normalized to `\n` | Normative |
| Control characters | Zero-width, bidirectional and control characters are removed before parsing | Implemented |
| Profile | A comment `// perfil: lnd-1.1` near the top declares the profile | Normative |

<a id="h-structure"></a>
## 2 · Structure

A document has an **intro** (everything before the first block or `---`: the `# Title` line and a short summary), then **items**: typed blocks and loose Markdown. `---` on its own line starts a new section.

<a id="h-lines"></a>
## 3 · Line rules

*The core of the parser. Each line is evaluated in this order.*

<a id="tb-order"></a>
**Evaluation order (Implemented)**

| # | Line | Meaning |
|---|---|---|
| 1 | inside `key::` | Appended to the multi-line value until a line that is exactly `::` |
| 2 | `// text` or `//` | Comment: hidden in views, preserved in the source |
| 3 | `@@` | Closes the open block |
| 4 | `---` | Closes the open block and starts a section |
| 5 | `@type id` | Opens a block. Exactly one optional token after the type |
| 6 | `key: value` right after the opening | A property. Keys start with a lowercase letter or `_` |
| 7 | first blank line in a block | Switches from properties to body |
| 8 | anything else | Body (Markdown) of the open block, or loose Markdown |

<a id="f-props"></a>
**Properties and values**

- A repeated key becomes a list, in order (`item:` in `@features`).
- `key::` alone on a line opens a multi-line value; `::` alone closes it.
- Values are text. A consumer may read `si`/`no` as booleans and `#RRGGBB` as a color, nothing more.

<a id="c-escape"></a>
**Escaping (Implemented)**

```lnd
What you write          What readers see
.@@                    @@        (one dot is removed)
.@nota x               @nota x   (text, not a block)
.---                   ---       (text, not a section break)
```

<a id="h-inline"></a>
## 4 · Inline marks and Markdown

Inline: `**bold**`, `*italic*`, backticks for code, `[text](https://…)`, `[text](?demo=id&vista=web)` for internal links, and `@(id text)` to reference a block. The body supports a Markdown subset: paragraphs, headings, lists, task lists, tables, fenced code and quotes. **Raw HTML is never rendered** (Normative).

<a id="h-common"></a>
## 5 · Properties any block can carry

<a id="tb-common"></a>
**Common properties**

| Property | Meaning |
|---|---|
| `certeza` | `Verificado`, `Supuesto` or `Por verificar` |
| `supuesto: si` / `verificar: si` | Shorthand for the two weaker states |
| `generado_por: ia` | Written by a model without human review |
| `idioma` | BCP 47 tag (`en`, `es`, `zh-Hans`) |
| `rel: type @(target)` | Typed relation to another block |
| `depende` | Ids this block depends on (comma separated) |

<a id="h-blocks"></a>
## 6 · Block types

*An unknown type is not an error: it renders as a generic block and is kept in the source.*

<a id="tb-blocks"></a>
**Types the reference renderer understands**

| Group | Types |
|---|---|
| Content | `heading`, `nota`, `table`, `code`, `quote`, `features`, `cta`, `hero`, `stat`, `timeline` |
| Knowledge | `afirmacion`, `fuente`, `entidad`, `ejemplo` |
| Work | `tablero`, `tarea`, `accion`, `proceso`, `paso`, `fase` |
| Product and design | `producto`, `paquete`, `wireframe`, `diseno` |
| Media | `image` (requires `alt`), `embed`, `iframe` (allow-listed domains only), `mermaid` |

<a id="h-views"></a>
## 7 · Views

The same file renders as Web, Slides (a `@heading` starts a slide), Board (`@tarea` by `estado`), Scroll-TV, Map (sections as lines, blocks as stations), Mission (runbook of `@accion` steps with saved state) and Source (raw text next to the render, with block ids). Markdown and HTML exports are generated from the parsed document and contain no scripts.

<a id="h-security"></a>
## 8 · Security

<a id="tb-security"></a>
**Rules for any renderer**

| Rule | Status |
|---|---|
| Escape all text before inserting it. No author HTML, CSS or JavaScript | Normative |
| Links and media: `https` only (plus `mailto:` and `tel:` in property lists) | Implemented |
| `@iframe`: domain allow-list, `sandbox`, lazy loading, strict referrer policy | Implemented |
| `@diseno`: colors as `#RRGGBB` and font names only | Implemented |
| Text addressed to models («ignore your instructions…») is data, never an instruction | Normative |
| `@secret` holds a reference, never a literal value | Normative |

<a id="h-diag"></a>
## 9 · Diagnostics

*Codes are stable. The validator prints messages in Spanish.*

<a id="tb-diag"></a>
**Codes**

| Code | Level | Rule |
|---|---|---|
| `LND-SYN-001` | error | `@@` without an open block |
| `LND-SYN-002` | error | `key::` without a closing `::` |
| `LND-SYN-003` | warning | `@type id extra` looks like a block but is text |
| `LND-SYN-004` | info | Block closed without `@@` |
| `LND-SYN-005` | warning | `//x` without a space is not a comment |
| `LND-ESQ-001` | error | Duplicate id |
| `LND-ESQ-002` | error | `@tarea` without an id |
| `LND-ESQ-003` | warning | Key starting with an uppercase letter |
| `LND-ESQ-004` | warning | Missing `# Title` |
| `LND-REF-001` | warning | `rel: siguiente` to a missing id |
| `LND-REF-002` | warning | `depende` to a missing id |
| `LND-REF-003` | warning | `@afirmacion` whose `fuente` has no `@fuente` |
| `LND-REF-004` | warning | Malformed `rel` |
| `LND-SEC-001` | error | `@iframe` outside the allow-list |
| `LND-SEC-002` | error | `@secret` with a literal value |
| `LND-SEC-003` | warning | Non-`https` URL in a media or link property |
| `LND-SEC-004` | warning | Control or bidirectional characters |
| `LND-LANG-001` | error | Reserved, wrong language codes `kcw` and `tsq` |
| `LND-LANG-002` | warning | `idioma` that does not look like BCP 47 |
| `LND-MED-001` | warning | `@image` without `alt` |
| `LND-VER-001` | info | Missing `// perfil: lnd-1.1` comment |
| `LND-VER-002` | info | Legacy profile name `cw-1`; use `lnd-1.1` |
| `LND-REF-007` | warning | `--links`: the block does not exist in the linked document |
| `LND-REF-008` | info | `--links`: link resolved through a `@movido` tombstone |
| `LND-REF-009` | error | `@movido` without `movido_a` |

<a id="h-ext"></a>
## 10 · Extending and versioning

<a id="f-ext"></a>
- New types and properties are allowed and must survive a round trip unchanged (Normative).
- Third-party types use a prefix: `@x-<org>-<type>` (Proposed).
- Additive changes keep the profile `lnd-1`. Additive changes raise the minor version (`lnd-1.1`, `lnd-1.2`). A change that breaks valid documents creates `lnd-2` with a migration tool (Normative). `cw-1` is the legacy alias of `lnd-1.0`: validators and renderers accept it and report `LND-VER-002` (Normative).
- The profile is named after the format, not after any product. Keys and type names are Spanish words in profile `lnd-1`. They are identifiers, not prose, and are the same in every language edition of a document.

<a id="h-v11"></a>
## 11 · Profile 1.1 additions

*Additive and backward compatible: a 1.0 renderer shows these blocks as generic blocks, and nothing that was valid becomes invalid.*

<a id="tb-v11"></a>
**New blocks**

| Block | Properties | Rendering |
|---|---|---|
| `@decision` | `pregunta`, `opciones` (separated by ` · `; a vertical bar is also accepted), `elegida`, `puntaje` (a number or `N/M`, set by a person), `estado` (`abierta` or `decidida`; `cerrada` reads as `decidida`), `reabrir_si`, repeated `fuente` (free text, or `@(id)` to an `@afirmacion` or `@fuente`); plus repeated `criterio` (name, weight, one score per option, separated by vertical bars) and `fecha` | Score table (weight × score, summed), linked evidence that inherits its Verified or Assumption mark, edges to the evidence in the Map view |
| `@ascii` | `alt` (required), `titulo`; the drawing in the body | Whitespace kept exactly, no reflow, scaled to fit the width |
| `@stream` | `url`, `tipo` (`hls`, `webrtc`, `youtube`, `otro`), `poster`, `estado`, `fecha` | Click to load, allow-listed domains only; offline it shows poster, status and date |
| `@playlist` | repeated `item`: source, title, start-end, subtitles (local relative paths allowed) | Ordered list that works offline |
| `@archivos` | repeated `archivo`: path, size, sha256 | File tree; the validator checks the sha256 format |
| `@repo`, `@issue` | `url` plus a snapshot (`nombre`, `descripcion`, `licencia`, `titulo`, `estado`…) and its `fecha` | Readable offline from the snapshot, with its date |

<a id="f-v11"></a>
**New fields on any block**

- `icono:` an emoji or a `:shortcode:`. There is no `@emoji` block.
- `:shortcode:` inline in text, for example `:check:` or `:warning:`. Inside code it stays literal.
- `pos: x,y` places the block freely on the Map canvas.
- `hash:` and `cache:` on any block with external content: the sha256 of the content and a local relative copy (for example a page saved as a single HTML file).
- **Human weights.** In `@decision`, weights are set by a person. An agent may compute the score and propose a choice, but does not change weights or `puntaje`, or mark the decision `decidida`, on its own.

<a id="tb-v11-diag"></a>
**New diagnostic codes**

| Code | Level | Rule |
|---|---|---|
| `LND-MED-002` | error | `@ascii` without `alt` |
| `LND-INT-001` | error | Malformed sha256 in `@archivos` or `hash` |
| `LND-DEC-001` | warning | `@decision` without `pregunta` |
| `LND-DEC-002` | warning | Fewer than two `opciones` |
| `LND-DEC-003` | warning | Malformed `criterio` (one score per option) |
| `LND-DEC-004` | warning | `elegida` is not one of the `opciones` |
| `LND-DEC-005` | warning | Invalid `estado`, or decided without `elegida` and `fecha` |
| `LND-DEC-006` | warning | `puntaje` is neither a number nor `N/M` |
| `LND-REF-005` | warning | A `fuente: @(id)` in `@decision` points to a missing id or to a block that is not `@afirmacion` or `@fuente` |
| `LND-ESQ-005` | warning | `@stream` with an unknown `tipo` |
| `LND-ESQ-006` | warning | Malformed `pos` or `icono` |
| `LND-ESQ-007` | warning | `@repo` or `@issue` without a snapshot `fecha` |
| `LND-ESQ-008` | warning | `@emoji` block (use `icono` or a shortcode) |
| `LND-SEC-006` | warning | `cache` or file path that is absolute or contains `..` |

<a id="h-enlaces"></a>
## 12 · Links between documents that survive moving folders

*Folders are for humans; ids are for machines.*

<a id="tb-enlaces"></a>
**Ways to link**

| Form | Example | Status |
|---|---|---|
| Block in the same document | `@(a-boiling)` | 1.0 |
| Another document, by id | `@(hello)` | 1.1 |
| A block in another document, by id | `@(hello#a-boiling)` | 1.1 |
| File path (fallback) | `@(examples/en/hello.lnd#a-boiling)` | 1.1 · breaks if the file moves |
| Tombstone for a moved document: `@movido id` with `movido_a: new-id` | the renderer redirects to the new id | Proposed 1.2 |

<a id="f-enlaces"></a>
**Rules**

- The renderer resolves the document id through its index (MANIFEST: id → current path). If the id is missing, it shows the link struck through as a **broken link** and emits `LND-REF-006`; it does not guess a target.
- No version numbers in file names: the version lives in Git and in the text, not in the path. Renaming or moving a file does not change its id.
- Planned tooling: `cw links` lists and checks every link in the repo, and `cw mv` moves a file and leaves the tombstone (see §13; Normative: they do not exist yet).

<a id="h-cli"></a>
## 13 · The `cw` command-line tool (plan)

*Normative: decided and not built yet, except the reference validator. A single TypeScript parser, `@landdy/cw`, compiled with Deno.*

<a id="tb-cli"></a>
**By stage**

| Stage | Commands | Done when |
|---|---|---|
| 0 | `cw validate`, `cw lint --leaks`, `cw publish --public` | CI fails on a broken `.lnd` or a leak |
| 1 | `fmt`, `get`/`set`, `propose`, `query`, `context`, `import`, `serve` (stdio, read-only plus `propose`), `links`, `mv` | `parse(fmt(parse(x))) == parse(x)` on every fixture |
| 2 | `diff`, `stale`, `index`, `decide`, `watch` | — |

The Python validator (`tools/lnd_check.py`) is ported to TypeScript and retired once both validators give the same result on every fixture.

<a id="h-12"></a>
## 14 · Version 1.2: reserved words in English, Spanish and Chinese

*Implemented in the reference validator and formatter. Every reserved word works in all three languages with the same behavior.*

<a id="f-12"></a>
**What 1.2 adds**

- **One table.** `tools/keywords.json` lists every reserved word (blocks, fields, header keys, reserved values, views) in es, en and zh. Canonical ids are the English column. The validator, the formatter and the renderer read it; the rest of the code never sees language-specific keys.
- **One language per file.** A file uses the keys of one language. Optional header `keys: en` (`claves: es`, `键名语言：zh`); without it the language is detected. Mixing key languages gives `LND-KEY-001`.
- **Full-width punctuation.** In zh, `：` is accepted for `:` and `＠` for `@`, as typed with a Chinese IME.
- **Formatter.** `python3 tools/lnd_keys.py --lang es|en|zh file.lnd` rewrites reserved words only: never content, block ids or `@(id)` links. The round trip es→en→zh→es is byte-identical.
- **Messages.** Validator messages quote keys in the language of the file; `--lang` defaults to it.
- **Memory blocks.** `@experience` (lesson reused across tasks; requires `lesson` and `origin`), the global field `replaces: @(id)` (version chain; cycles are `LND-REF-010`) and `reopen_if` on `@decision`. See `examples/*/memory-1-2.lnd`, `decisions-1-2.lnd` and `moved-1-2.lnd`.
- **Decision uncertainty (optional, after the Vega decision model).** `confidence`: a number from 0 to 1, the probability that the chosen option is right (out of range: `LND-DEC-008`). `candidates`: the options still plausible, a subset of `options` (`LND-DEC-007` if not). New `status` value `abstained`: there is not enough evidence to decide; it has no `chosen` and should have `reopen_if` (`LND-DEC-005`). Rule: if a tool or agent fills `confidence`, it must say how it was computed in `source`; the weights are still set by a person.

<a id="tb-12-codes"></a>
**New diagnostic codes**

| Code | Level | Meaning |
|---|---|---|
| `LND-KEY-001` | warning (info if only values mix) | Keys from more than one language in a file |
| `LND-KEY-002` | warning | Unknown key that looks like a typo of a reserved word (with suggestion), or a `keys:` value other than es, en, zh |
| `LND-KEY-003` | info | Renamed term (legacy alias): run `lnd_keys.py --migrar` |
| `LND-REF-010` | error | Cycle in `replaces` |
| `LND-EXP-001` | warning | `@experience` without `lesson` or `origin` |
| `LND-EXP-002` | warning | `uses` is not an integer |
| `LND-DEC-007` | warning | A `candidates` entry is not among `options` |
| `LND-DEC-008` | warning | `confidence` is not a number from 0 to 1 |

<a id="n-zh-provisional"></a>
> **Zh-cn.** zh-CN provisional: corrections will never break existing files. The Chinese reserved words are machine-translated and have not been reviewed by a native speaker. If a term changes, the old one moves to `aliases_legacy` in `keywords.json`: it keeps working, gives only `LND-KEY-003` (info), and `lnd_keys.py --migrar` rewrites it. Native speakers: please propose fixes in an issue (see CONTRIBUTING).

<a id="c-12-decision"></a>
**The same decision, keys in this file's language**

```lnd
@decision d-price
question: Which price model ships at launch?
options: One-time 89 · Monthly 9
chosen: One-time 89
status: decided
date: 2026-10-19
reopen_if: fewer than 20 sales in the first 30 days
@@
```
