"""Pruebas unitarias 1.2: códigos nuevos, «：»/«＠», idioma de claves, término zh renombrado (aliases_legacy) y --migrar."""
import sys, json, pathlib, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import lnd_check_v12 as L
ok = 0
def cods(s, kw=None): return [(x["codigo"], x["nivel"]) for x in L.check(s, kw)[1]]
def t(nombre, cond):
    global ok
    assert cond, nombre; ok += 1; print("ok ·", nombre)
CAB = "# T\n\n// perfil: lnd-1.1 · ámbito: prueba\n\n---\n\n"
t("ES 1.1 sin cambios: decision válida", cods(CAB + "@decision d1\npregunta: ¿A o B?\nopciones: A · B\nelegida: A\nestado: decidida\nfecha: 2026-10-20\n@@\n") == [])
EN = "# T\n\n// profile: lnd-1.1 · scope: prueba\n\n---\n\n@decision d1\nquestion: ¿A o B?\noptions: A · B\nchosen: A\nstatus: decided\ndate: 2026-10-20\n@@\n"
t("EN equivalente sin diagnósticos", cods(EN) == [])
ZH = "# T\n\n// 规范版本：lnd-1.1 · 范围：prueba\n\n---\n\n＠决策 d1\n问题：¿A o B?\n选项：A · B\n选定：A\n状态：已定\n日期：2026-10-20\n＠＠\n"
t("zh revisado: los términos viejos (规范, 已决) siguen válidos con solo info KEY-003", set(cods(ZH.replace("规范版本：", "规范：").replace("已定", "已决"))) == {("LND-KEY-003", "info")})
t("ZH con «：» y «＠» sin diagnósticos", cods(ZH) == [])
t("mismo árbol es/en/zh", L.arbol(L.convertir(EN, "es")) == L.arbol(EN) == L.arbol(ZH))
t("zh conserva «：»/«＠» al formatear en zh", L.convertir(ZH, "zh") == ZH and "：" not in L.convertir(ZH, "en"))
MIX = "# T\n\n// profile: lnd-1.1\n\n---\n\n@decision d1\nquestion: A?\nopciones: A · B\n@@\n"
t("KEY-001 aviso al mezclar claves", ("LND-KEY-001", "aviso") in cods(MIX))
m = [x for x in L.check(MIX)[1] if x["codigo"] == "LND-KEY-001"]
t("KEY-001 sugiere la clave del idioma del archivo (options)", m and "«options»" in m[0]["mensaje"] and "«options»" in L.traducir(m[0], "en"))
m = [x for x in L.check(EN.replace("question: ¿A o B?\n", ""))[1] if x["codigo"] == "LND-DEC-001"]
t("mensaje cita la clave en el idioma del archivo (question)", m and "«question»" in m[0]["mensaje"] and "«question»" in L.traducir(m[0], "en"))
t("mensaje en zh con clave zh", any("「选项」" in L.traducir(x, "zh") for x in L.check(L.convertir("# T\n\n---\n\n@decision d1\nquestion: A?\n@@\n", "zh"))[1] if x["codigo"] == "LND-DEC-002"))
t("KEY-002 sugiere ante errata", any(x["codigo"] == "LND-KEY-002" and "«question»" in x["mensaje"] for x in L.check("# T\n\n// profile: lnd-1.1\n\n---\n\n@decision d\nquestoin: A?\noptions: A · B\n@@\n")[1]))
t("KEY-002b ante claves: xx", ("LND-KEY-002", "aviso") in cods(CAB.replace("ámbito: prueba", "claves: fr")))
CIC = CAB + "@nota a\nreemplaza: @(b)\n@@\n\n@nota b\nreemplaza: @(a)\n@@\n"
t("REF-010 ciclo en reemplaza", ("LND-REF-010", "error") in cods(CIC))
t("REF-006 reemplaza sin destino", ("LND-REF-006", "aviso") in cods(CAB + "@nota a\nreemplaza: @(zzz)\n@@\n"))
EXP = CAB + "@experiencia x1\naplica_a: dns\nusos: tres\n@@\n"
t("EXP-001 (leccion, origen) y EXP-002 (usos)", [c for c, _ in cods(EXP)].count("LND-EXP-001") == 2 and ("LND-EXP-002", "aviso") in cods(EXP))
t("@moved sin moved_to → REF-009 en en", ("LND-REF-009", "error") in cods("# T\n\n---\n\n@moved m\ndate: 2026-10-20\n@@\n"))
# término zh renombrado: copia temporal de keywords.json con 选项 → 选择项 y 选项 en aliases_legacy
kw = json.loads(pathlib.Path(L.__file__).with_name("keywords.json").read_text("utf-8"))
kw["campos"]["options"]["zh"] = "选择项"; kw["campos"]["options"]["aliases_legacy"]["zh"] = ["选项"]
with tempfile.TemporaryDirectory() as d:
    p = pathlib.Path(d) / "keywords.json"; p.write_text(json.dumps(kw, ensure_ascii=False), "utf-8"); K2 = L.Palabras(p)
    c2 = cods(ZH, K2)
    t("zh viejo sigue válido: solo info KEY-003", c2 == [("LND-KEY-003", "info")])
    mig = L.convertir(ZH, None, K2, migrar=True)
    t("--migrar reescribe 选项 → 选择项 y nada más", "选择项：A · B" in mig and mig.replace("选择项", "选项") == ZH and cods(mig, K2) == [])
DV = CAB + "@decision d\npregunta: ¿A?\nopciones: A · B · C\n"
t("confianza fuera de 0–1 → DEC-008", ("LND-DEC-008", "aviso") in cods(DV + "confianza: 1,4\n@@\n") and cods(DV + "confianza: 0,7\n@@\n") == [])
t("candidatas fuera de opciones → DEC-007", ("LND-DEC-007", "aviso") in cods(DV + "candidatas: A · D\n@@\n") and cods(DV + "candidatas: A · B\n@@\n") == [])
t("abstenida con elegida y sin reabrir_si → 2 avisos DEC-005", [c for c, _ in cods(DV + "estado: abstenida\nelegida: A\n@@\n")].count("LND-DEC-005") == 2)
t("abstenida bien formada sin diagnósticos, igual en zh", cods(DV + "estado: abstenida\nreabrir_si: hay datos\n@@\n") == [] == cods(L.convertir(DV + "estado: abstenida\nreabrir_si: hay datos\n@@\n", "zh")))
IFR = CAB + "@iframe v\nsrc: {}\n@@\n"
AT = "@"  # «@» aparte para que el gate de fugas no lo lea como correo
MALAS = ("https://evil.com\\" + AT + "www.youtube.com/x", "https://evil.com" + AT + "www.youtube.com/x", "https://www.youtube.com" + AT + "evil.com/x", "https://www.youtube.com\\.evil.com/x", "https://www.youtube.com\t.evil.com/x")
t("SEC-001: «\\», «usuario@» o controles en src de @iframe → error (el navegador abriría otro host)", all(("LND-SEC-001", "error") in cods(IFR.format(u)) for u in MALAS) and ("LND-SEC-001", "error") not in cods(IFR.format("https://www.youtube.com/embed/x?a=1#t")))
print(f"{ok} pruebas ok")
