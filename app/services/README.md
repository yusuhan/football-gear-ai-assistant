# services 模块

`services` 是智能客服业务核心。

## 当前服务

- `FootballGearAgent`：意图识别、工具路由、FAQ RAG 和回答生成。
- `ConversationService`：负责会话创建、消息落库、工具调用日志和 Agent 事件记录。
- `ConversationRepository`：访问 SQLite 会话、消息、工具日志和人工接管表。
- `HandoffPolicy`：判断低置信度、投诉、退款、人工请求等场景是否需要转人工。
- `ChannelAdapterService`：把淘宝/1688/企微等外部消息标准化为内部聊天请求。
- `ToolRouter`：封装 `check_inventory`、`search_products`、`get_size_recommendation`。
- `ProductRepository`：访问 SQLite 商品、库存和尺码数据。
- `FAQKnowledgeBase`：检索 FAQ，并返回可追溯 sources。
- `OperationsRepository`：负责运营账号认证、账号管理、密码变更、短期会话和审计日志持久化。
- `DemoDataService`：备份并重置运行数据，恢复固定商品数据与初始运营账号。

## 后续可扩展

- 将本地路由替换为 OpenAI function calling。
- 将 FAQ 检索替换为 ChromaDB 向量检索。
- 将 SQLite Repository 替换为 ERP、OMS 或 WMS API。
