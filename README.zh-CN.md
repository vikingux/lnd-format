# LANDDY `.lnd` · lnd-format

> 智能体与人，像操作系统一样自由。

一种纯文本知识格式，人和 AI 智能体都能读、写、引用和审阅。块以 `@类型 id` 开头，包含 `键: 值` 行和 Markdown 正文，以 `@@` 结束。保留字支持西班牙语、英语和中文（zh-CN 为暂定版本）。本仓库包含规范（[spec/SPEC.zh-CN.md](spec/SPEC.zh-CN.md)）、保留字表（[tools/keywords.json](tools/keywords.json)）、最小解析器（`tools/lnd_parse.py`）、验证器（`tools/lnd_check_v12.py`）、键名转换器（`tools/lnd_keys.py`）、测试（`tools/pruebas_v12.py`）和[示例](examples/)。版本 **0.9.2**，Apache-2.0 许可。

```sh
python3 tools/lnd_check_v12.py --estricto examples/zh-CN/hello.lnd
python3 tools/pruebas_v12.py
```

需要 Python 3，无其他依赖。许可：[Apache-2.0](LICENSE)。联系：[info@conocimiento.wiki](mailto:info@conocimiento.wiki)。
