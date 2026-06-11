# app 模块

`app` 是 FastAPI 后端主目录。

## 分层职责

- `api`：HTTP 路由，暴露聊天、商品、库存和健康检查接口。
- `core`：环境变量和路径配置。
- `db`：SQLite 初始化和种子数据导入。
- `models`：Pydantic 请求/响应模型。
- `services`：Agent、Tool Router、FAQ RAG 和数据仓储。

面试讲解重点：API 层不写业务决策，Agent 层不直接写 SQL，工具和数据访问通过清晰边界解耦。
