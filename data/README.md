# data 模块

`data` 模块保存 Football Gear AI Assistant 的演示数据。

## 数据文件

- `products.json`：足球鞋、球衣、球袜、护腿板、足球、守门员装备和其他护具。
- `inventory.json`：商品尺码库存。
- `size_guide.json`：脚长到推荐尺码映射。
- `faq.json`：至少 20 条售后、发货、尺码和政策 FAQ。

FastAPI 启动时会把结构化数据导入 SQLite，FAQ 则由 RAG 检索服务直接加载。
