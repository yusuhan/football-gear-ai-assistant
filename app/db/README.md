# db 模块

`db` 模块负责 SQLite 初始化和种子数据导入。

MVP 使用 SQLite 是为了本地可运行和可部署简单；真实业务中可以平滑迁移到 PostgreSQL 或云数据库，因为上层只通过 repository 访问数据。

## 当前表

- `products`、`inventory`、`size_guide`：商品、库存和尺码工具数据。
- `conversations`、`messages`：持久化会话和消息历史。
- `channel_conversations`：维护外部渠道会话 ID 到内部 `conversation_id` 的映射。
- `tool_call_logs`：记录每次工具调用的参数和结果。
- `agent_events`：记录 Agent 路由、RAG 来源等结构化事件。
- `handoff_tickets`：人工接管工单，支持创建、领取、解决和处理备注。
- `operations_users`：运营账号、PBKDF2 密码哈希和角色。
- `operations_sessions`：短期登录会话，只保存令牌哈希和过期时间。
- `audit_logs`：记录登录、退出和工单更新等敏感操作。

内置账号只在数据库首次创建时作为 bootstrap 数据写入。后续密码修改由账号管理接口持久化，服务重启不会覆盖。
