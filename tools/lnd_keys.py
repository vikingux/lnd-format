#!/usr/bin/env python3
"""lnd_keys · formateador de palabras reservadas LANDDY .lnd 1.2 (base de `cw fmt --lang`).

Reescribe solo palabras reservadas (bloques, campos, claves de cabecera, valores reservados, vistas sugeridas)
según keywords.json. Nunca toca contenido, ids de bloque ni enlaces @(id). Mismo número de líneas.

Uso:
  python3 lnd_keys.py --lang en archivo.lnd            # imprime el archivo con claves en inglés
  python3 lnd_keys.py --lang zh -w a.lnd b.lnd         # reescribe en el sitio (-w)
  python3 lnd_keys.py --lang en --salida DIR a.lnd     # escribe DIR/a.lnd
  python3 lnd_keys.py --migrar -w archivo.lnd          # actualiza términos renombrados (aliases_legacy) sin cambiar de idioma
  python3 lnd_keys.py --verificar archivo.lnd          # ida y vuelta es→en→zh→es byte a byte + mismo árbol normalizado
Salida: 0 si todo bien; 1 si --verificar encuentra diferencias.
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
try:
    import lnd_check_v12 as L
except ImportError:
    import lnd_check as L


def verificar(src):
    """Devuelve (ok, detalle). X0 = fmt(X, idioma propio); X0→otro→otro→X0 byte a byte; árbol(X) == árbol(cada versión)."""
    lg = L.idioma_claves(L.parse(src)[0])[0]
    x0 = L.convertir(src, lg)
    orden = {"es": ("en", "zh", "es"), "en": ("zh", "es", "en"), "zh": ("es", "en", "zh")}[lg]
    t0 = json.dumps(L.arbol(src), sort_keys=True, ensure_ascii=False); x, vs = x0, {}
    for d in orden:
        x = L.convertir(x, d); vs[d] = x
        if json.dumps(L.arbol(x), sort_keys=True, ensure_ascii=False) != t0:
            return False, f"árbol distinto en {d}"
    if x != x0:
        a, b = x0.split("\n"), x.split("\n")
        n = next((i for i, (p, q) in enumerate(zip(a, b)) if p != q), min(len(a), len(b)))
        return False, f"ida y vuelta distinta en la línea {n + 1}: {a[n:n+1]} ≠ {b[n:n+1]}"
    return True, "idéntico" + ("" if x0 == src else " (tras normalizar a su idioma)")


def main(argv):
    if not argv or "-h" in argv or "--help" in argv:
        print(__doc__); return 0
    lang = None; w = "-w" in argv; migrar = "--migrar" in argv; ver = "--verificar" in argv; salida = None
    if "--lang" in argv:
        lang = argv[argv.index("--lang") + 1]; lang = {"zh-CN": "zh", "zh-cn": "zh"}.get(lang, lang)[:2]
        assert lang in L.LANGS, "--lang es|en|zh"
    if "--salida" in argv:
        salida = pathlib.Path(argv[argv.index("--salida") + 1]); salida.mkdir(parents=True, exist_ok=True)
    skip = {argv.index(o) + 1 for o in ("--lang", "--salida") if o in argv}
    files = [a for i, a in enumerate(argv) if not a.startswith("-") and i not in skip]
    code = 0
    for f in files:
        src = pathlib.Path(f).read_text("utf-8")
        if ver:
            ok, det = verificar(src); code |= 0 if ok else 1
            print(f"{f}: {'ok' if ok else 'FALLA'} · {det}"); continue
        out = L.convertir(src, lang or "es", migrar=migrar or not lang)
        if w: pathlib.Path(f).write_text(out, "utf-8")
        elif salida: (salida / pathlib.Path(f).name).write_text(out, "utf-8")
        else: sys.stdout.write(out)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
