# tests 模块

`tests` 模块用于本地验证 MVP 主链路。

当前覆盖：

- FAQ RAG 检索。
- Agent 工具路由。
- FastAPI、会话持久化、人工接管、RBAC 和运营后台接口。
- 演示数据库备份、运行数据清理和固定种子恢复。

运行：

```bash
.venv/bin/python -m unittest discover -s tests
```
