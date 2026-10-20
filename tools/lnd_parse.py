#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 vikingux and the LANDDY .lnd contributors
"""lnd_parse · parser mínimo de LANDDY .lnd: imprime el árbol normalizado de un archivo en JSON.

Las claves pueden estar en es, en o zh; el árbol usa los ids canónicos de keywords.json (columna en),
así que el mismo documento en tres idiomas da el mismo árbol. Usa el parser de lnd_check_v12.py, sin dependencias.

Uso:
  python3 tools/lnd_parse.py archivo.lnd          # árbol JSON por la salida estándar
  python3 tools/lnd_parse.py --bloques archivo.lnd  # solo tipo e id de cada bloque, una línea por bloque
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import lnd_check_v12 as L


def main(argv):
    solo = "--bloques" in argv
    rutas = [a for a in argv if not a.startswith("--")]
    if not rutas:
        print(__doc__.strip()); return 2
    for r in rutas:
        arbol = L.arbol(pathlib.Path(r).read_text("utf-8"))
        if solo:
            for b in arbol["items"]:
                print(f'{r}\t{b.get("tipo")}\t{b.get("id")}')
        else:
            print(json.dumps(arbol, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
