#!/usr/bin/env python3
"""lnd_check 1.2 · validador de LANDDY .lnd (perfil lnd-1; acepta el alias heredado cw-1).

Novedades 1.2: palabras reservadas en es, en y zh (tabla keywords.json, al lado de este archivo).
El parser normaliza bloques, campos y valores a ids canónicos (columna en); las reglas solo ven ids canónicos.
Bloques y campos 1.2: @experience/@experiencia/@经验, replaces/reemplaza/取代, @moved + moved_to, reopen_if.
Sin dependencias. Licencia prevista: Apache-2.0.

Uso:
  python3 lnd_check.py archivo.lnd [más.lnd …]        # texto
  python3 lnd_check.py --json archivo.lnd              # JSON (incluye «claves»: idioma de las claves)
  python3 lnd_check.py --estricto archivo.lnd          # avisos cuentan como error
  python3 lnd_check.py --lang en archivo.lnd           # mensajes en es, en o zh (por defecto: el idioma de las claves del archivo)
  python3 lnd_check.py --links CARPETA                 # resuelve @(doc-id#bloque) entre todos los .lnd de la carpeta
  python3 lnd_check.py --arbol archivo.lnd             # árbol normalizado (JSON canónico, para pruebas de paridad)
Salida: código 0 sin errores, 1 con errores, 2 si no pudo leer un archivo.
"""
import difflib, json, pathlib, re, sys
from urllib.parse import urlparse

LANGS = ("es", "en", "zh")


class Palabras:
    """Tabla de palabras reservadas (keywords.json). Id canónico = columna en."""
    def __init__(self, ruta=None):
        ruta = pathlib.Path(ruta) if ruta else pathlib.Path(__file__).with_name("keywords.json")
        self.kw = kw = json.loads(ruta.read_text("utf-8"))
        self.ent, self.sal, self.leg = {}, {}, {}  # ent[cat][palabra] = (canon, {idiomas}); sal[cat][canon][lg]; leg[cat][palabra] = (canon, lg)
        cats = {"b": kw["bloques"], "f": kw["campos"], "h": kw["cabecera"], "v": kw["vistas"]}
        cats.update({"v:" + k: v for k, v in kw["valores"].items()})
        for c, tab in cats.items():
            E, S, L = self.ent.setdefault(c, {}), self.sal.setdefault(c, {}), self.leg.setdefault(c, {})
            for canon, e in tab.items():
                S[canon] = {lg: e[lg] for lg in LANGS}
                for lg in LANGS:
                    for w in [e[lg]] + e.get("aliases", {}).get(lg, []):
                        E.setdefault(w, (canon, set()))[1].add(lg)
                    for w in e.get("aliases_legacy", {}).get(lg, []):
                        E.setdefault(w, (canon, set()))[1].add(lg); L[w] = (canon, lg)
        zh = lambda c: sorted((w for w, (_, l) in self.ent[c].items() if "zh" in l and not re.match(r"^[A-Za-z_]", w)), key=len, reverse=True)
        alt = lambda ws: "|".join(map(re.escape, ws)) or "(?!)"
        self.OPEN = re.compile(r"^[@＠]([A-Za-z_][\w-]*|" + alt(zh("b")) + r")(?:\s+(\S+))?\s*$")
        self.KV = re.compile(r"^([a-z_][\w-]*|" + alt(zh("f")) + r")[:：][ \t]?(.*)$")
        self.ML = re.compile(r"^([a-z_][\w-]*|" + alt(zh("f")) + r")(?:::|：：)\s*$")
        self.HSEG = re.compile(r"^(\s*)(" + alt(sorted(self.ent["h"], key=len, reverse=True)) + r")([:：])(.*)$", re.S)

    def canon(self, c, w):
        x = self.ent[c].get(w)
        return x[0] if x else None

    def idiomas(self, c, w):
        x = self.ent[c].get(w)
        return x[1] if x else None

    def palabra(self, c, canon, lg):
        s = self.sal[c].get(canon)
        return s[lg] if s else canon

    def ambito_valor(self, tipo, campo):
        """Categoría de valores reservados para un campo canónico (None si su valor es libre)."""
        if campo == "type" and tipo == "stream": return "v:type@stream"
        if campo == "status" and tipo == "experience": return "v:certainty"  # §1: estado Supuesto | Verificado
        if campo == "confidence": return "v:priority"  # alta/media/baja (o un número, que no se toca)
        return "v:" + campo if campo in ("status", "certainty", "priority", "rel") else None


KW = Palabras()
CTRL = re.compile("[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F\u200B-\u200F\u202A-\u202E\u2060-\u2064\u2066-\u2069\uFEFF]")
OPEN_CASI = re.compile(r"^[@＠]([A-Za-z_][\w-]*)\s+\S+\s+\S")
ESC = re.compile(r"^\.+(@|＠|---|::|//)")
IFRAME_OK = {"www.youtube-nocookie.com", "www.youtube.com", "player.vimeo.com", "www.openstreetmap.org", "docs.conocimiento.wiki", "conocimiento.wiki"}
BCP47 = re.compile(r"^[a-z]{2,3}(-[A-Z][a-z]{3})?(-([A-Z]{2}|\d{3}))?(-[A-Za-z0-9]{5,8})*$")
URL_PROPS = {"src", "imagen", "foto", "repo", "uri", "enlace", "web", "url_img"}


def unesc(l):
    return l[1:] if ESC.match(l) else l


def es_cierre(t):
    return t in ("@@", "＠＠")


def segmentos_cabecera(c):
    """«perfil: lnd-1.1 · ámbito: x» → [(clave_cruda, valor), …] solo para claves de cabecera reservadas."""
    out = []
    for seg in re.split(r"\s+·\s+", c):
        m = KW.HSEG.match(seg)
        if m: out.append((m.group(2), m.group(4).strip()))
    return out


def parse(src, kw=None):
    """Parser 1.2. Mismas reglas de línea que 1.1; además acepta palabras reservadas es/en/zh y «：»/«＠».
    Cada bloque guarda «tipo» canónico y «tipo_crudo»; props con claves canónicas; doc['tokens'] lista (línea, categoría, palabra)."""
    K = kw or KW
    lines = CTRL.sub("", src.replace("\r\n", "\n").replace("\r", "\n")).split("\n")
    doc = {"intro": [], "comments": [], "items": [], "diags": [], "tokens": []}
    st = {"cur": None, "mode": None, "ml": None, "mlbuf": [], "mlstart": 0, "sec": 0, "sep": False, "loose": None}
    tok = lambda n, c, w: doc["tokens"].append((n, c, w))

    def d(n, nivel, cod, msg, t=None, **p):
        doc["diags"].append({"linea": n, "nivel": nivel, "codigo": cod, "mensaje": msg, "_t": t or cod, "_p": p})

    def add(b, k, v):
        if k in b["props"]:
            if not isinstance(b["props"][k], list):
                b["props"][k] = [b["props"][k]]
            b["props"][k].append(v)
        else:
            b["props"][k] = v

    def clave(raw, n):
        c = K.canon("f", raw)
        if c: tok(n, "f", raw); return c, raw
        return raw, raw

    def close(implicit_line=None):
        c = st["cur"]
        if c:
            if implicit_line is not None:
                c["cierre_implicito"] = True
            doc["items"].append(c)
        st["cur"], st["mode"] = None, None

    def close_loose():
        if st["loose"]:
            if any(x.strip() for x in st["loose"]["body"]):
                doc["items"].append(st["loose"])
            st["loose"] = None

    for i, line in enumerate(lines, 1):
        if st["ml"]:
            if line.strip() in ("::", "：："):
                add(st["cur"], st["ml"], "\n".join(st["mlbuf"])); st["ml"], st["mlbuf"] = None, []
            else:
                st["mlbuf"].append(unesc(line))
            continue
        if line == "//" or line.startswith("// "):
            if st["cur"]:
                st["cur"]["comments"].append(line[3:])
            else:
                doc["comments"].append(line[3:])
                for w, _v in segmentos_cabecera(line[3:]): tok(i, "h", w)
            continue
        if line.startswith("//"):
            d(i, "aviso", "LND-SYN-005", "«//» sin espacio: no es comentario, se muestra como texto (usa «// »)")
        t = line.strip()
        if es_cierre(t):
            if not st["cur"]:
                d(i, "error", "LND-SYN-001", "«@@» sin bloque abierto")
            close(); continue
        if t == "---":
            close(i if st["cur"] else None); close_loose(); st["sec"] += 1; st["sep"] = True; continue
        m = K.OPEN.match(line)
        if m:
            close(i if st["cur"] else None); close_loose()
            raw = m.group(1).lower(); c = K.canon("b", raw)
            if c: tok(i, "b", raw)
            st["cur"] = {"tipo": c or raw, "tipo_crudo": m.group(1), "id": m.group(2), "props": {}, "crudas": {}, "body": [], "comments": [], "linea": i, "sec": st["sec"], "lineas": {}}
            st["mode"] = "props"; continue
        if OPEN_CASI.match(line):
            d(i, "aviso", "LND-SYN-003", "Parece apertura de bloque pero tiene más de un token después del tipo: se toma como texto. Usa «@tipo id» o escapa con «.»")
        cur = st["cur"]
        if cur:
            if st["mode"] == "props":
                if t == "":
                    st["mode"] = "body"; continue
                mm = K.ML.match(line)
                if mm:
                    c, raw = clave(mm.group(1), i); cur["crudas"][c] = raw; cur["lineas"].setdefault(c, i)
                    st["ml"], st["mlstart"] = c, i; st["mlraw"] = raw; continue
                kv = K.KV.match(line)
                if kv:
                    c, raw = clave(kv.group(1), i); cur["crudas"][c] = raw; cur["lineas"].setdefault(c, i)
                    v = kv.group(2).strip(); amb = K.ambito_valor(cur["tipo"], c)
                    if amb:
                        w = v.split()[0] if (amb == "v:rel" and v) else v
                        cv = K.canon(amb, w)
                        if cv:
                            tok(i, amb, w); v = cv + v[len(w):] if amb == "v:rel" else cv
                    add(cur, c, v); continue
                if re.match(r"^[A-Z][\w-]*:\s", line):
                    d(i, "aviso", "LND-ESQ-003", "Clave con mayúscula inicial: no se lee como propiedad (las claves empiezan en minúscula o «_»)")
                st["mode"] = "body"
            cur["body"].append(unesc(line))
        elif not st["sep"] and not doc["items"]:
            doc["intro"].append(unesc(line))
        else:
            if not st["loose"]:
                st["loose"] = {"tipo": "md", "tipo_crudo": "md", "id": None, "props": {}, "crudas": {}, "body": [], "comments": [], "linea": i, "sec": st["sec"], "lineas": {}}
            st["loose"]["body"].append(unesc(line))
    if st["ml"]:
        d(st["mlstart"], "error", "LND-SYN-002", f"Valor multilínea «{st['mlraw']}::» sin cierre «::»", q=st["mlraw"] + "::")
    close(len(lines) if st["cur"] else None); close_loose()
    return doc, lines


def idioma_claves(doc, kw=None):
    """(idioma, declarado, tokens fuera de idioma). «claves:/keys:/键语言:» en la cabecera manda; si falta, se detecta."""
    K = kw or KW; dec = None
    for c in doc["comments"]:
        for w, v in segmentos_cabecera(c):
            if K.canon("h", w) == "keys": dec = v.split()[0].lower()[:2] if v else ""
    toks = [(n, c, w) for n, c, w in doc["tokens"] if K.idiomas(c, w) and len(K.idiomas(c, w)) < 3]
    fuera = {lg: [x for x in toks if lg not in K.idiomas(x[1], x[2])] for lg in LANGS}
    if dec in LANGS:
        return dec, True, fuera[dec]
    lg = min(LANGS, key=lambda l: (len(fuera[l]), LANGS.index(l)))
    return lg, dec is not None and dec != "", fuera[lg] if dec is None else fuera[lg]


def arr(v):
    return [] if v is None else (v if isinstance(v, list) else [v])


def opciones_decision(v):
    """Opciones de @decision: separadas por « · » (forma preferida) o por «|»."""
    v = str(v or "")
    return [o.strip() for o in (v.split("|") if "|" in v else re.split(r"\s+·\s+", v)) if o.strip()]


NOMBRE_IDIOMA = {"es": {"es": "español", "en": "inglés", "zh": "chino"}, "en": {"es": "Spanish", "en": "English", "zh": "Chinese"}, "zh": {"es": "西班牙语", "en": "英语", "zh": "中文"}}


def check(src, kw=None):
    K = kw or KW
    doc, lines = parse(src, K)
    D = doc["diags"]
    lg, declarado, fuera = idioma_claves(doc, K)
    doc["claves"] = lg
    F = lambda c: K.palabra("f", c, lg)           # campo en el idioma del archivo
    B = lambda c: K.palabra("b", c, lg)           # bloque
    H = lambda c: K.palabra("h", c, lg)           # cabecera
    VV = lambda a, c: K.palabra(a, c, lg)         # valor
    VI = lambda c: K.kw["vistas"][c]["rotulo"][lg]

    def d(n, nivel, cod, msg, t=None, **p):
        D.append({"linea": n, "nivel": nivel, "codigo": cod, "mensaje": msg, "_t": t or cod, "_p": p})

    # ---- 1.2 · idioma de las claves ----
    for n, c, w in doc["tokens"]:
        if w in K.leg[c]:
            canon, _ = K.leg[c][w]; nuevo = K.palabra(c, canon, K.leg[c][w][1])
            d(n, "info", "LND-KEY-003", f"Término renombrado «{w}» → «{nuevo}»: corre `cw fmt` (lnd_keys.py --migrar) para actualizar", q=w, n2=nuevo)
    for c in doc["comments"]:
        for w, v in segmentos_cabecera(c):
            if K.canon("h", w) == "keys" and (v.split()[0].lower()[:2] if v else "") not in LANGS:
                d(1, "aviso", "LND-KEY-002", f"«{w}: {v}»: usa es, en o zh", t="LND-KEY-002b", q=f"{w}: {v}")
    vistos = set()
    for n, c, w in fuera:
        if (c, w) in vistos: continue
        vistos.add((c, w)); sug = K.palabra(c, K.canon(c, w), lg)
        ids = "/".join(NOMBRE_IDIOMA["es"][x] for x in LANGS if x in K.idiomas(c, w))
        d(n, "info" if c.startswith("v:") else "aviso", "LND-KEY-001", f"Claves de varios idiomas: «{w}» es {ids} y el archivo usa claves en {NOMBRE_IDIOMA['es'][lg]}: escribe «{sug}» (o corre lnd_keys.py --lang {lg})",
          q=w, s=sug, l=lg, ls=[x for x in LANGS if x in K.idiomas(c, w)])
    # candidatos de los tres idiomas: el aviso no depende del idioma de las claves (paridad); la sugerencia sí sale en el idioma del archivo
    conocidas = {"b": list(K.ent["b"]), "f": list(K.ent["f"])}
    for b in doc["items"]:
        cand = [("b", b["tipo_crudo"].lower(), b["linea"])] if b["tipo"] != "md" and not K.canon("b", b["tipo_crudo"].lower()) else []
        cand += [("f", raw, b["lineas"].get(c, b["linea"])) for c, raw in b["crudas"].items() if not K.canon("f", raw)]
        for cat, raw, n in cand:
            if len(raw) < 6: continue
            m = difflib.get_close_matches(raw, conocidas[cat], n=1, cutoff=0.85)
            if m and m[0] != raw:
                sug = K.palabra(cat, K.canon(cat, m[0]), lg)
                d(n, "aviso", "LND-KEY-002", f"Clave desconocida «{raw}»: ¿quisiste decir «{sug}»?", q=raw, s=sug)

    if CTRL.search(src):
        n = next((k for k, l in enumerate(src.split("\n"), 1) if CTRL.search(l)), 1)
        d(n, "aviso", "LND-SEC-004", "Caracteres de control, de ancho cero o bidireccionales: el parser los elimina")
    if not any(re.match(r"^#\s+", l) for l in doc["intro"]):
        d(1, "aviso", "LND-ESQ-004", "Falta el título «# …» en la introducción (antes del primer bloque)")
    perf = [m.group(1) for c in doc["comments"] for m in [re.search(r"(?:" + "|".join(sorted((w for w, (cn, _) in K.ent["h"].items() if cn == "profile"), key=len, reverse=True)) + r")[:：]\s*(lnd-1(?:\.\d+)?|cw-1)\b", c)] if m]
    if not perf:
        d(1, "info", "LND-VER-001", f"Sin comentario de perfil «// {H('profile')}: lnd-1.1 · {H('scope')}: … · {H('suggested_views')}: …»", p=H("profile"), a=H("scope"), v=H("suggested_views"))
    elif perf[0] == "cw-1":
        d(1, "info", "LND-VER-002", f"Perfil «cw-1»: es el alias heredado de «lnd-1.0»; se acepta. Usa «{H('profile')}: lnd-1.1»", p=H("profile"))
    idx, seen = {}, {}
    for b in doc["items"]:
        if b["tipo"] == "md":
            continue
        if b.get("cierre_implicito"):
            d(b["linea"], "info", "LND-SYN-004", f"@{b['tipo_crudo']} {b['id'] or ''} se cierra sin «@@» (recomendado para arrastrar bloques)", q=f"@{b['tipo_crudo']} {b['id'] or ''}".strip())
        if b["id"]:
            if b["id"] in seen:
                d(b["linea"], "error", "LND-ESQ-001", f"id duplicado «{b['id']}» (también en la línea {seen[b['id']]})", q=b["id"], n=seen[b["id"]])
            seen[b["id"]] = b["linea"]; idx[b["id"]] = b
    reemp = {}
    for b in doc["items"]:
        P, n, tipo, T = b["props"], b["linea"], b["tipo"], "@" + b["tipo_crudo"]
        for r in arr(P.get("rel")):
            m = re.match(r"^(\S+)\s+@\(([^\s)]+)", r)
            if not m:
                d(n, "aviso", "LND-REF-004", f"rel mal formado «{r}» (forma: «{F('rel')}: tipo @(destino)»)", q=r, k=F("rel"))
            elif m.group(1) == "next" and m.group(2) not in idx:
                d(n, "aviso", "LND-REF-001", f"«{VV('v:rel', 'next')}» apunta a «{m.group(2)}», que no existe en el documento", q=m.group(2), k=VV("v:rel", "next"))
        for v in arr(P.get("depends_on")):
            for x in re.split(r"[,\s]+", v):
                x = re.sub(r"^@\(|\)$", "", x)
                if x and x not in idx:
                    d(n, "aviso", "LND-REF-002", f"«{F('depends_on')}» apunta a «{x}», que no existe en el documento", q=x, k=F("depends_on"))
        if tipo == "claim" and P.get("source") and P["source"] not in idx:
            d(n, "aviso", "LND-REF-003", f"{F('source')} «{P['source']}» sin bloque @{B('source')} en el documento", q=P["source"], k=F("source"), b=B("source"))
        if tipo in ("iframe",) and P.get("src"):
            try:
                u = urlparse(P["src"]); ok = u.scheme == "https" and u.hostname in IFRAME_OK
            except Exception:
                ok = False
            if not ok:
                d(n, "error", "LND-SEC-001", f"{T} {b['id'] or ''}: dominio fuera de la lista blanca", b=T)
        if tipo == "secret" and any(k in P for k in ("value", "valor")):
            d(n, "error", "LND-SEC-002", "@secret con valor literal: guarda solo la referencia secret://…")
        for k in URL_PROPS & set(P):
            for v in arr(P[k]):
                v0 = v.split()[0] if v.strip() else v
                if re.match(r"^(http|javascript|data|vbscript|file):", v0, re.I):
                    kr = b["crudas"].get(k, k)
                    d(n, "aviso", "LND-SEC-003", f"{kr}: «{v0[:40]}» no es https; el renderer no lo usa", q=v0[:40], k=kr)
        for v in arr(P.get("locale")):
            base = v.split("-")[0].lower()
            if base in ("kcw", "tsq"):
                d(n, "error", "LND-LANG-001", f"{F('locale')} «{v}» prohibido: Kichwa es qu-EC (qug/qvi), Tsafiki es cof", q=v, k=F("locale"))
            elif not BCP47.match(v):
                d(n, "aviso", "LND-LANG-002", f"{F('locale')} «{v}» no parece una etiqueta BCP 47 (ej.: es, es-EC, qu-EC, cof, zh-Hans)", q=v, k=F("locale"))
        if tipo == "image" and not P.get("alt"):
            d(n, "aviso", "LND-MED-001", f"{T} sin «{F('alt')}» (obligatorio para accesibilidad)", b=T, k=F("alt"))
        # ---- perfil lnd-1 · adiciones 1.1 ----
        if tipo == "ascii" and not P.get("alt"):
            d(n, "error", "LND-MED-002", f"{T} sin «{F('alt')}» (obligatorio: describe el dibujo para lectores de pantalla y agentes)", b=T, k=F("alt"))
        if tipo == "decision":
            ops = opciones_decision(P.get("options", ""))
            if not P.get("question"):
                d(n, "aviso", "LND-DEC-001", f"{T} sin «{F('question')}»", b=T, k=F("question"))
            if len(ops) < 2:
                d(n, "aviso", "LND-DEC-002", f"{T} con menos de dos «{F('options')}» (sepáralas con « · » o «|»)", b=T, k=F("options"))
            for c in arr(P.get("criterion")):
                x = [y.strip() for y in c.split("|")]
                try:
                    float(x[1].replace(",", ".")); [float(v.replace(",", ".")) for v in x[2:]]
                    okc = len(x) - 2 == len(ops)
                except (IndexError, ValueError):
                    okc = False
                if not okc:
                    d(n, "aviso", "LND-DEC-003", f"{F('criterion')} mal formado «{c[:50]}» (forma: «nombre | peso | nota opción 1 | nota opción 2 …», una nota por opción)", q=c[:50], k=F("criterion"))
            el = P.get("chosen")
            if el and el not in ops:
                d(n, "aviso", "LND-DEC-004", f"«{F('chosen')}: {el}» no está en «{F('options')}»", q=f"{F('chosen')}: {el}", k=F("options"))
            est = str(P.get("status", "open")); estc = K.canon("v:status", est.lower()) or est.lower()
            if estc not in ("open", "decided", "closed", "abstained"):
                d(n, "aviso", "LND-DEC-005", f"{F('status')} «{est.lower()}» de {T}: usa «{VV('v:status', 'open')}» o «{VV('v:status', 'decided')}»", t="LND-DEC-005a",
                  q=est.lower(), k=F("status"), b=T, a=VV("v:status", "open"), c=VV("v:status", "decided"))
            if estc in ("decided", "closed") and not (el and P.get("date")):
                d(n, "aviso", "LND-DEC-005", f"{T} {VV('v:status', 'decided')} sin «{F('chosen')}» o sin «{F('date')}»", t="LND-DEC-005b", b=T, c=VV("v:status", "decided"), k=F("chosen"), f=F("date"))
            if estc == "abstained":
                if el:
                    d(n, "aviso", "LND-DEC-005", f"{T} {VV('v:status', 'abstained')} con «{F('chosen')}»: quítala o usa «{VV('v:status', 'decided')}»", t="LND-DEC-005c",
                      b=T, c=VV("v:status", "abstained"), k=F("chosen"), a=VV("v:status", "decided"))
                if not P.get("reopen_if"):
                    d(n, "aviso", "LND-DEC-005", f"{T} {VV('v:status', 'abstained')} sin «{F('reopen_if')}» (di qué evidencia falta para decidir)", t="LND-DEC-005d",
                      b=T, c=VV("v:status", "abstained"), k=F("reopen_if"))
            for v in arr(P.get("confidence")):
                try:
                    okc = 0 <= float(str(v).strip().replace(",", ".")) <= 1
                except ValueError:
                    okc = False
                if not okc:
                    d(n, "aviso", "LND-DEC-008", f"{F('confidence')} «{str(v)[:20]}»: usa un número entre 0 y 1 (probabilidad de que la opción elegida sea la correcta)", q=str(v)[:20], k=F("confidence"))
            if P.get("candidates"):
                for x in opciones_decision(P.get("candidates")):
                    if x not in ops:
                        d(n, "aviso", "LND-DEC-007", f"«{F('candidates')}»: «{x}» no está en «{F('options')}»", q=x, k=F("candidates"), o=F("options"))
            pj = str(P.get("score", "")).strip()
            if pj and not re.fullmatch(r"\d+([.,]\d+)?(\s*/\s*\d+)?", pj):
                d(n, "aviso", "LND-DEC-006", f"{F('score')} «{pj[:20]}»: usa un número o «N/M» (lo pone una persona)", q=pj[:20], k=F("score"))
            for v in arr(P.get("source")):
                for ref in re.findall(r"@\(([^\s)]+)\)", v):
                    if ref not in idx:
                        d(n, "aviso", "LND-REF-005", f"{F('source')} «@({ref})» de {T} no existe en el documento", t="LND-REF-005a", q=f"@({ref})", k=F("source"), b=T)
                    elif idx[ref]["tipo"] not in ("claim", "source"):
                        d(n, "aviso", "LND-REF-005", f"{F('source')} «@({ref})» de {T} debe ser @{B('claim')} o @{B('source')}", t="LND-REF-005b", q=f"@({ref})", k=F("source"), b=T, b1=B("claim"), b2=B("source"))
        if tipo == "stream":
            if str(P.get("type", "other")) not in ("hls", "webrtc", "youtube", "other"):
                d(n, "aviso", "LND-ESQ-005", f"{T}: «{F('type')}» debe ser hls, webrtc, youtube u {VV('v:type@stream', 'other')}", b=T, k=F("type"), o=VV("v:type@stream", "other"))
            if not str(P.get("url", "")).startswith("https://"):
                d(n, "aviso", "LND-SEC-003", f"{T}: «{F('url')}» debe ser https", t="LND-SEC-003b", b=T, k=F("url"))
        if tipo == "files":
            for a_ in arr(P.get("file")):
                x = [y.strip() for y in a_.split("|")]
                if len(x) > 2 and x[2] and not re.fullmatch(r"[0-9a-fA-F]{64}", x[2]):
                    d(n, "error", "LND-INT-001", f"sha256 mal formado en «{x[0]}» (64 caracteres hexadecimales)", t="LND-INT-001a", q=x[0])
                if not x[0] or x[0].startswith("/") or ".." in x[0]:
                    d(n, "aviso", "LND-SEC-006", f"ruta «{x[0]}»: usa rutas relativas sin «..»", t="LND-SEC-006a", q=x[0])
        for v in arr(P.get("hash")):
            if not re.match(r"\s*(sha256|[0-9a-fA-F]{8,}\s*$)", v, re.I):
                d(n, "info", "LND-INT-002", f"{F('hash')} «{v[:30]}» todavía sin calcular", q=v[:30], k=F("hash"))
            elif not re.fullmatch(r"(sha256[:-])?[0-9a-fA-F]{64}|sha256-[A-Za-z0-9+/]{43}=", v.strip()):
                d(n, "error", "LND-INT-001", f"{F('hash')} «{v[:30]}» no es sha256 (hex de 64, «sha256:…» o «sha256-…» base64)", t="LND-INT-001b", q=v[:30], k=F("hash"))
        for v in arr(P.get("cache")):
            if v.startswith("/") or ".." in v or re.match(r"^[a-z]+:", v, re.I):
                d(n, "aviso", "LND-SEC-006", f"{F('cache')} «{v[:40]}»: debe ser una ruta relativa local, sin «..»", t="LND-SEC-006b", q=v[:40], k=F("cache"))
        for v in arr(P.get("pos")):
            if not re.fullmatch(r"\s*-?\d{1,5}\s*,\s*-?\d{1,5}\s*", v):
                d(n, "aviso", "LND-ESQ-006", f"{F('pos')} «{v}»: forma «x,y» con enteros", t="LND-ESQ-006a", q=v, k=F("pos"))
        for v in arr(P.get("icon")):
            if not (re.fullmatch(r":[a-z_]{2,20}:", v) or (0 < len(v) <= 8 and not re.search(r"[\w<>&\"']", v))):
                d(n, "aviso", "LND-ESQ-006", f"{F('icon')} «{v[:20]}»: un emoji o un :shortcode:", t="LND-ESQ-006b", q=v[:20], k=F("icon"))
        if tipo in ("repo", "issue") and not P.get("date"):
            d(n, "aviso", "LND-ESQ-007", f"{T} sin «{F('date')}» de la instantánea (sin red se muestra la copia y su fecha)", b=T, k=F("date"))
        if tipo == "emoji":
            d(n, "aviso", "LND-ESQ-008", f"@emoji no existe: usa «{F('icon')}:» en el bloque o :shortcode: en el texto", k=F("icon"))
        if tipo == "moved" and not P.get("moved_to"):
            d(n, "error", "LND-REF-009", f"{T} sin «{F('moved_to')}» (id nuevo del documento)", b=T, k=F("moved_to"))
        if tipo == "task" and not b["id"]:
            d(n, "error", "LND-ESQ-002", f"{T} sin id: la vista {VI('board')} no puede moverla", b=T, v=VI("board"))
        # ---- 1.2 · memoria reutilizable ----
        if tipo == "experience":
            for req in ("lesson", "origin"):
                if not P.get(req):
                    d(n, "aviso", "LND-EXP-001", f"{T} sin «{F(req)}» (obligatorio)", b=T, k=F(req))
            for v in arr(P.get("uses")):
                if not re.fullmatch(r"\d+", v.strip()):
                    d(n, "aviso", "LND-EXP-002", f"«{F('uses')}: {v[:20]}» no es un entero (lo sube la herramienta)", q=f"{F('uses')}: {v[:20]}")
        for campo in (("origin", "replaces") if tipo == "experience" else ("replaces",)):
            for v in arr(P.get(campo)):
                refs = re.findall(r"@\(([^\s)#]+)\)", v)
                if not refs:
                    d(n, "aviso", "LND-REF-006", f"«{F(campo)}: {v[:40]}»: usa «@(id)»", t="LND-REF-006b", q=f"{F(campo)}: {v[:40]}")
                for ref in refs:
                    if ref not in idx:
                        d(n, "aviso", "LND-REF-006", f"«{F(campo)}» apunta a «@({ref})», que no existe en el documento", t="LND-REF-006c", q=f"@({ref})", k=F(campo))
                    if campo == "replaces" and b["id"]: reemp.setdefault(b["id"], []).append(ref)
    # ciclos en replaces (LND-REF-010)
    hechos = set()
    for ini in reemp:
        camino, x = [], ini
        while x in reemp and x not in camino:
            camino.append(x); x = reemp[x][0]
        if x in camino and x not in hechos:
            ciclo = camino[camino.index(x):] + [x]; hechos |= set(ciclo)
            d(idx[x]["linea"], "error", "LND-REF-010", f"Ciclo en «{F('replaces')}»: {' → '.join(ciclo)}", q=" → ".join(ciclo), k=F("replaces"))
    D.sort(key=lambda x: x["linea"])
    return doc, D


# ---- mensajes en/zh: mismas variables que el mensaje es; las claves citadas ya vienen en el idioma del archivo ----
MSG = {
 "LND-SYN-001": ("«@@» with no open block", "没有打开的块却出现「@@」"),
 "LND-SYN-002": ("Multi-line value «{q}» has no closing «::»", "多行值「{q}」缺少结束符「::」"),
 "LND-SYN-003": ("Looks like a block opener but has more than one token after the type; read as text. Use «@type id» or escape with «.»", "看起来像块开头，但类型后有多个记号，按文本处理。请用「@类型 id」或用「.」转义"),
 "LND-SYN-004": ("«{q}» closes without «@@» (recommended so blocks can be moved)", "「{q}」没有用「@@」结束（建议加上，便于移动块）"),
 "LND-SYN-005": ("«//» with no space is not a comment; shown as text (use «// »)", "「//」后没有空格，不是注释，按文本显示（请用「// 」）"),
 "LND-ESQ-001": ("Duplicate id «{q}» (also on line {n})", "重复的 id「{q}」（另见第 {n} 行）"),
 "LND-ESQ-002": ("{b} without id: the {v} view cannot move it", "{b} 没有 id：{v}视图无法移动它"),
 "LND-ESQ-003": ("Key starts with a capital letter: not read as a property (keys start lowercase or «_»)", "键以大写字母开头，不会被读作属性（键以小写或「_」开头）"),
 "LND-ESQ-004": ("Missing «# …» title in the introduction (before the first block)", "引言中缺少「# …」标题（在第一个块之前）"),
 "LND-ESQ-005": ("{b}: «{k}» must be hls, webrtc, youtube or {o}", "{b}：「{k}」须为 hls、webrtc、youtube 或 {o}"),
 "LND-ESQ-006a": ("{k} «{q}»: use «x,y» with integers", "{k}「{q}」：请用整数「x,y」"),
 "LND-ESQ-006b": ("{k} «{q}»: one emoji or a :shortcode:", "{k}「{q}」：一个表情符号或 :shortcode:"),
 "LND-ESQ-007": ("{b} without «{k}» of the snapshot (offline the copy and its date are shown)", "{b} 缺少快照的「{k}」（离线时显示副本及其日期）"),
 "LND-ESQ-008": ("@emoji does not exist: use «{k}:» on the block or a :shortcode: in text", "@emoji 不存在：请在块上用「{k}:」或在文本中用 :shortcode:"),
 "LND-REF-001": ("«{k}» points to «{q}», which does not exist in the document", "「{k}」指向「{q}」，文档中不存在"),
 "LND-REF-002": ("«{k}» points to «{q}», which does not exist in the document", "「{k}」指向「{q}」，文档中不存在"),
 "LND-REF-003": ("{k} «{q}» has no @{b} block in the document", "{k}「{q}」在文档中没有 @{b} 块"),
 "LND-REF-004": ("Malformed rel «{q}» (form: «{k}: type @(target)»)", "rel 格式错误「{q}」（形式：「{k}: 类型 @(目标)」）"),
 "LND-REF-005a": ("{k} «{q}» of {b} does not exist in the document", "{b} 的{k}「{q}」在文档中不存在"),
 "LND-REF-005b": ("{k} «{q}» of {b} must be @{b1} or @{b2}", "{b} 的{k}「{q}」必须是 @{b1} 或 @{b2}"),
 "LND-REF-006": ("Linked document «{q}» is not in the folder or index (broken link)", "链接的文档「{q}」不在文件夹或索引中（失效链接）"),
 "LND-REF-006b": ("«{q}»: use «@(id)»", "「{q}」：请使用「@(id)」"),
 "LND-REF-006c": ("«{k}» points to «{q}», which does not exist in the document", "「{k}」指向「{q}」，文档中不存在"),
 "LND-REF-007": ("Block «{q}» does not exist in the linked document", "链接的文档中不存在块「{q}」"),
 "LND-REF-008": ("Link «{q}» resolved through a tombstone; point it to «{n2}»", "链接「{q}」经由墓碑解析；请改为指向「{n2}」"),
 "LND-REF-009": ("{b} without «{k}» (new document id)", "{b} 缺少「{k}」（新的文档 id）"),
 "LND-REF-010": ("Cycle in «{k}»: {q}", "「{k}」中存在循环：{q}"),
 "LND-SEC-001": ("{b}: domain is not on the allowlist", "{b}：域名不在允许列表中"),
 "LND-SEC-002": ("@secret with a literal value: store only the secret://… reference", "@secret 含字面值：只保存 secret://… 引用"),
 "LND-SEC-003": ("{k}: «{q}» is not https; the renderer does not use it", "{k}：「{q}」不是 https，渲染器不会使用"),
 "LND-SEC-003b": ("{b}: «{k}» must be https", "{b}：「{k}」必须是 https"),
 "LND-SEC-004": ("Control, zero-width or bidirectional characters: the parser removes them", "控制字符、零宽或双向字符：解析器会删除它们"),
 "LND-SEC-006a": ("Path «{q}»: use relative paths without «..»", "路径「{q}」：请使用不含「..」的相对路径"),
 "LND-SEC-006b": ("{k} «{q}»: must be a local relative path, without «..»", "{k}「{q}」：必须是本地相对路径，不含「..」"),
 "LND-LANG-001": ("Forbidden {k} «{q}»: Kichwa is qu-EC (qug/qvi), Tsafiki is cof", "禁止的{k}「{q}」：基奇瓦语为 qu-EC（qug/qvi），察奇拉语为 cof"),
 "LND-LANG-002": ("{k} «{q}» does not look like a BCP 47 tag (e.g. es, es-EC, qu-EC, cof, zh-Hans)", "{k}「{q}」不像 BCP 47 标签（如 es、es-EC、qu-EC、cof、zh-Hans）"),
 "LND-MED-001": ("{b} without «{k}» (required for accessibility)", "{b} 缺少「{k}」（无障碍必需）"),
 "LND-MED-002": ("{b} without «{k}» (required: describe the drawing for screen readers and agents)", "{b} 缺少「{k}」（必需：为读屏软件和智能体描述该图）"),
 "LND-DEC-001": ("{b} without «{k}»", "{b} 缺少「{k}」"),
 "LND-DEC-002": ("{b} with fewer than two «{k}» (separate with « · » or «|»)", "{b} 的「{k}」少于两个（用「 · 」或「|」分隔）"),
 "LND-DEC-003": ("Malformed {k} «{q}» (form: «name | weight | score 1 | score 2 …», one score per option)", "{k} 格式错误「{q}」（形式：「名称 | 权重 | 选项1分 | 选项2分 …」）"),
 "LND-DEC-004": ("«{q}» is not among «{k}»", "「{q}」不在「{k}」中"),
 "LND-DEC-005a": ("{k} «{q}» of {b}: use «{a}» or «{c}»", "{b} 的{k}「{q}」：请用「{a}」或「{c}」"),
 "LND-DEC-005b": ("{b} {c} without «{k}» or without «{f}»", "{b} 已是「{c}」但缺少「{k}」或「{f}」"),
 "LND-DEC-005c": ("{b} {c} with «{k}»: remove it or use «{a}»", "{b} 为「{c}」却有「{k}」：请删除或改用「{a}」"),
 "LND-DEC-005d": ("{b} {c} without «{k}» (say what evidence is missing to decide)", "{b} 为「{c}」但缺少「{k}」（说明还缺哪些证据）"),
 "LND-DEC-007": ("«{k}»: «{q}» is not among «{o}»", "「{k}」：「{q}」不在「{o}」中"),
 "LND-DEC-008": ("{k} «{q}»: use a number from 0 to 1 (probability that the chosen option is right)", "{k}「{q}」：请用 0 到 1 之间的数（所选选项正确的概率）"),
 "LND-DEC-006": ("{k} «{q}»: use a number or «N/M» (set by a person)", "{k}「{q}」：请用数字或「N/M」（由人填写）"),
 "LND-INT-001a": ("Malformed sha256 in «{q}» (64 hex characters)", "「{q}」中的 sha256 格式错误（64 个十六进制字符）"),
 "LND-INT-001b": ("{k} «{q}» is not sha256 (64 hex, «sha256:…» or «sha256-…» base64)", "{k}「{q}」不是 sha256（64 位十六进制、「sha256:…」或「sha256-…」base64）"),
 "LND-INT-002": ("{k} «{q}» not computed yet", "{k}「{q}」尚未计算"),
 "LND-VER-001": ("No profile comment «// {p}: lnd-1.1 · {a}: … · {v}: …»", "缺少规范注释「// {p}: lnd-1.1 · {a}: … · {v}: …」"),
 "LND-VER-002": ("Profile «cw-1» is the legacy alias of «lnd-1.0»; accepted. Use «{p}: lnd-1.1»", "规范「cw-1」是「lnd-1.0」的旧别名，仍可接受。请改用「{p}: lnd-1.1」"),
 "LND-KEY-001": ("Mixed key languages: «{q}» is {ls} and this file uses {l} keys: write «{s}» (or run lnd_keys.py --lang {l0})", "键语言混用：「{q}」属于{ls}，本文件使用{l}键：请写「{s}」（或运行 lnd_keys.py --lang {l0}）"),
 "LND-KEY-002": ("Unknown key «{q}»: did you mean «{s}»?", "未知的键「{q}」：是否想写「{s}」？"),
 "LND-KEY-002b": ("«{q}»: use es, en or zh", "「{q}」：请用 es、en 或 zh"),
 "LND-KEY-003": ("Term renamed «{q}» → «{n2}»: run `cw fmt` (lnd_keys.py --migrar) to update", "术语已更名「{q}」→「{n2}」：运行 `cw fmt`（lnd_keys.py --migrar）更新"),
 "LND-EXP-001": ("{b} without «{k}» (required)", "{b} 缺少「{k}」（必需）"),
 "LND-EXP-002": ("«{q}» is not an integer (the tool increments it)", "「{q}」不是整数（由工具递增）"),
}
NIVEL = {"en": {"error": "error", "aviso": "warning", "info": "info"}, "zh": {"error": "错误", "aviso": "警告", "info": "提示"}}


def traducir(x, lang):
    if lang not in ("en", "zh"): return x["mensaje"]
    t = MSG.get(x.get("_t")) or MSG.get(x["codigo"])
    if not t: return x["mensaje"]
    p = dict(x.get("_p", {}))
    if "l" in p:
        nm = NOMBRE_IDIOMA[lang]; p["l0"] = p["l"]; p["l"] = nm[p["l"]]; p["ls"] = "/".join(nm[y] for y in p["ls"])
    try:
        return t[0 if lang == "en" else 1].format(**p)
    except (KeyError, IndexError):
        return x["mensaje"]


def arbol(src, kw=None):
    """Árbol normalizado (ids canónicos), independiente del idioma de las claves: base de la prueba de paridad."""
    doc, _ = parse(src, kw)
    com = []
    for c in doc["comments"]:
        segs = []
        for seg in re.split(r"\s+·\s+", c):
            m = (kw or KW).HSEG.match(seg)
            if m:
                k = (kw or KW).canon("h", m.group(2)); v = m.group(4).strip()
                if k == "suggested_views": v = ", ".join((kw or KW).canon("v", w.strip().lower()) or w.strip() for w in v.split(","))
                if k == "keys": v = "*"
                segs.append(f"{k}: {v}")
            else:
                segs.append(seg)
        com.append(" · ".join(segs))
    return {"intro": doc["intro"], "comments": com,
            "items": [{"tipo": b["tipo"], "id": b["id"], "props": b["props"], "body": b["body"], "comments": b["comments"]} for b in doc["items"]]}


# ---- formateador de claves (lnd_keys.py): reescribe solo palabras reservadas, línea por línea ----
def convertir(src, destino, kw=None, migrar=False):
    """Traduce bloques, campos, claves de cabecera, valores reservados y vistas sugeridas a «destino» (es|en|zh).
    No toca contenido, ids ni @(id). Mantiene «：»/«＠» solo si el destino es zh. Mismo número de líneas."""
    K = kw or KW; out = []
    if migrar:
        destino = idioma_claves(parse(src, K)[0], K)[0]
    zh = destino == "zh"
    lines = src.split("\n"); st = {"cur": None, "mode": None, "ml": False}
    ascii_ = lambda s: s if zh else s.replace("：", ":").replace("＠", "@")
    for line in lines:
        l0 = CTRL.sub("", line.rstrip("\r"))
        if st["ml"]:
            if l0.strip() in ("::", "：："): st["ml"] = False; line = ascii_(line) if l0.strip() == "：：" else line
            out.append(line); continue
        if l0 == "//" or l0.startswith("// "):
            if not st["cur"]:
                pre, cuerpo = line[:3], line[3:]; segs = re.split(r"(\s+·\s+)", cuerpo); nue = []
                for s in segs:
                    m = K.HSEG.match(s)
                    if m and K.canon("h", m.group(2)):
                        c = K.canon("h", m.group(2)); val = m.group(4)
                        if c == "suggested_views":
                            val = re.sub(r"[^,\s][^,]*?(?=\s*(,|$))", lambda mm: (K.palabra("v", K.canon("v", mm.group(0).lower()), destino) if K.canon("v", mm.group(0).lower()) else mm.group(0)), val)
                        if c == "keys":
                            val = re.sub(r"^(\s*)(es|en|zh)\b", lambda mm: mm.group(1) + destino, val)
                        s = m.group(1) + K.palabra("h", c, destino) + (m.group(3) if zh else ":") + val
                    nue.append(s)
                line = pre + "".join(nue)
            out.append(line); continue
        t = l0.strip()
        if es_cierre(t):
            st["cur"], st["mode"] = None, None; out.append(ascii_(line)); continue
        if t == "---":
            st["cur"], st["mode"] = None, None; out.append(line); continue
        m = K.OPEN.match(l0)
        if m:
            c = K.canon("b", m.group(1).lower())
            st["cur"], st["mode"] = (c or m.group(1).lower()), "props"
            if c:
                line = (line[0] if zh else "@") + K.palabra("b", c, destino) + line[1 + len(m.group(1)):]
            else:
                line = ascii_(line[0]) + line[1:]
            out.append(line); continue
        if st["cur"] and st["mode"] == "props":
            if t == "":
                st["mode"] = "body"; out.append(line); continue
            mm = K.ML.match(l0)
            if mm:
                c = K.canon("f", mm.group(1)); st["ml"] = True
                if c: line = K.palabra("f", c, destino) + (line[len(mm.group(1)):] if zh else line[len(mm.group(1)):].replace("：：", "::"))
                out.append(line); continue
            kv = K.KV.match(l0)
            if kv:
                raw = kv.group(1); c = K.canon("f", raw); sep = line[len(raw)]; resto = line[len(raw) + 1:]
                k2 = K.palabra("f", c, destino) if c else raw
                amb = K.ambito_valor(st["cur"], c or raw)
                if amb:
                    mv = re.match(r"^(\s*)(\S+)(.*)$", resto, re.S) if amb == "v:rel" else re.match(r"^(\s*)(.*?)(\s*)$", resto, re.S)
                    if mv and K.canon(amb, mv.group(2)):
                        resto = mv.group(1) + K.palabra(amb, K.canon(amb, mv.group(2)), destino) + mv.group(3)
                line = k2 + (sep if zh else ":") + resto
                out.append(line); continue
            st["mode"] = "body"
        out.append(line)
    return "\n".join(out)


def doc_ids(path, src, base):
    """ids por los que se puede enlazar un documento: «// id:», el nombre del archivo y <carpeta>-<nombre>."""
    doc, _ = parse(src); ids = set()
    for c in doc["comments"]:
        m = re.match(r"\s*id[:：]\s*([\w.-]+)", c)
        if m: ids.add(m.group(1))
    st = path.stem; ids |= {st, st.lower(), st.lower().replace("_", "-")}
    if path.parent != base: ids.add(f"{path.parent.name.lower()}-{st.lower()}")
    return doc, ids


def links(carpeta):
    """Versión mínima de «cw links»: resuelve @(doc-id) y @(doc-id#bloque) entre los .lnd de una carpeta."""
    base = pathlib.Path(carpeta); fs = sorted(base.rglob("*.lnd")); idx, docs = {}, {}
    for f in fs:
        doc, ids = doc_ids(f, f.read_text("utf-8"), base); docs[f] = doc
        for i in ids: idx.setdefault(i, f)
    out = []
    for f, doc in docs.items():
        D = []; local = {b["id"] for b in doc["items"] if b["id"]}
        for b in doc["items"]:
            texto = "\n".join(b["body"]) + "\n" + "\n".join(str(v) for v in b["props"].values())
            for m in re.finditer(r"@\(([\w.-]+)(?:#([\w.-]+))?", texto):
                d_, bl = m.group(1), m.group(2)
                if not bl and d_ in local: continue  # bloque del mismo documento
                if d_ not in idx:
                    D.append({"linea": b["linea"], "nivel": "aviso", "codigo": "LND-REF-006", "mensaje": f"documento «{d_}» no está en la carpeta (enlace roto)", "_p": {"q": d_}}); continue
                g = idx[d_]; dg = docs[g]
                mv = next((x for x in dg["items"] if x["tipo"] == "moved" and x["props"].get("moved_to")), None)
                if mv:
                    nuevo = mv["props"]["moved_to"]
                    D.append({"linea": b["linea"], "nivel": "info", "codigo": "LND-REF-008", "mensaje": f"«{d_}» es una lápida: apunta a «{nuevo}»", "_p": {"q": d_, "n2": nuevo}})
                    if nuevo in idx: g = idx[nuevo]; dg = docs[g]
                if bl and bl not in {x["id"] for x in dg["items"] if x["id"]}:
                    D.append({"linea": b["linea"], "nivel": "aviso", "codigo": "LND-REF-007", "mensaje": f"bloque «{bl}» no existe en «{g.relative_to(base)}»", "_p": {"q": bl}})
        out.append({"archivo": str(f), "bloques": sum(1 for b in doc["items"] if b["tipo"] != "md"), "errores": 0, "diagnosticos": D})
    return out


def main(argv):
    as_json = "--json" in argv; estricto = "--estricto" in argv
    lang = None
    if "--lang" in argv:
        i = argv.index("--lang"); lang = (argv[i + 1] if i + 1 < len(argv) else "es")[:2]; argv = argv[:i] + argv[i + 2:]
    if "--arbol" in argv:
        for f in [a for a in argv if not a.startswith("--")]:
            print(json.dumps(arbol(open(f, encoding="utf-8").read()), ensure_ascii=False, sort_keys=True))
        return 0
    if "--links" in argv:
        i = argv.index("--links"); carpeta = argv[i + 1] if i + 1 < len(argv) else "."
        out = links(carpeta)
        for r in out:
            r["errores"] = sum(1 for x in r["diagnosticos"] if x["nivel"] == "error" or (estricto and x["nivel"] == "aviso"))
            r["lang"] = lang or "es"
    else:
        files = [a for a in argv if not a.startswith("--")]
        if not files:
            print(__doc__); return 2
        out = []
        for f in files:
            try:
                src = open(f, encoding="utf-8").read()
            except OSError as e:
                print(f"{f}: no se pudo leer ({e})", file=sys.stderr); return 2
            doc, D = check(src)
            e = sum(1 for x in D if x["nivel"] == "error" or (estricto and x["nivel"] == "aviso"))
            out.append({"archivo": f, "claves": doc["claves"], "bloques": sum(1 for b in doc["items"] if b["tipo"] != "md"), "errores": e, "diagnosticos": D, "lang": lang or doc["claves"]})
    errs = sum(r["errores"] for r in out)
    for r in out:
        for x in r["diagnosticos"]:
            x["mensaje"] = traducir(x, r["lang"]); x.pop("_t", None); x.pop("_p", None)
    if as_json:
        for r in out: r.pop("lang", None)
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        for r in out:
            lg = r["lang"]; NV = NIVEL.get(lg, {}); res = {"es": "{b} bloques · {e} errores", "en": "{b} blocks · {e} errors", "zh": "{b} 个块 · {e} 个错误"}.get(lg, "{b} bloques · {e} errores")
            for x in r["diagnosticos"]:
                print(f"{r['archivo']}:{x['linea']}: {NV.get(x['nivel'], x['nivel'])} {x['codigo']} {x['mensaje']}")
            print(f"{r['archivo']}: " + res.format(b=r["bloques"], e=r["errores"]))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
