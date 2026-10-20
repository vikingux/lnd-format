# LANDDY `.lnd` · lnd-format

> Agentic y human, somos libres como un OS.

Un formato de texto plano para conocimiento que personas y agentes de IA pueden leer, escribir, citar y revisar. Un bloque abre con `@tipo id`, lleva líneas `clave: valor` y un cuerpo en Markdown, y cierra con `@@`. Las palabras reservadas funcionan en español, inglés y chino. Aquí están la spec ([spec/SPEC.es.md](spec/SPEC.es.md)), la tabla de palabras reservadas ([tools/keywords.json](tools/keywords.json)), un parser mínimo (`tools/lnd_parse.py`), el validador (`tools/lnd_check_v12.py`), el convertidor de claves (`tools/lnd_keys.py`), las pruebas (`tools/pruebas_v12.py`) y [ejemplos](examples/). Versión **0.9.2**, Apache-2.0.

```sh
python3 tools/lnd_check_v12.py --estricto examples/es/hello.lnd
python3 tools/pruebas_v12.py
```

Python 3, sin dependencias. Para ver un `.lnd` en el navegador: [conocimiento.wiki](https://github.com/vikingux/conocimiento-wiki). Licencia: [Apache-2.0](LICENSE). Contacto: [info@conocimiento.wiki](mailto:info@conocimiento.wiki).
