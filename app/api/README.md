# api 模块

`api` 模块负责 HTTP 接口和请求/响应绑定。

## 当前接口

- `GET /health`：健康检查和数据加载状态。
- `POST /chat`：主聊天接口。
- `POST /chat/stream`：流式文本输出接口。
- `POST /api/v1/chat`：版本化聊天接口。
- `GET /products`：商品列表。
- `GET /inventory`：库存列表。
- `POST /admin/auth/login`：使用运营账号密码创建会话。
- `POST /admin/auth/logout`：撤销当前运营会话。
- `GET /admin/audit-logs`：管理员查询操作审计日志。
- `POST /admin/auth/change-password`：当前账号修改密码并撤销其他会话。
- `GET/POST/PATCH /admin/users`：管理员查询、创建和更新运营账号。
- `POST /admin/users/{user_id}/reset-password`：管理员重置其他账号密码。
- `GET /admin/sessions`：管理员查看全部会话，客服查看自己的会话。
- `DELETE /admin/sessions/{session_id}`：撤销有权限管理的会话。
- `GET /conversations/{conversation_id}/messages`：运营账号查询会话记录。
- `GET /handoff-tickets`：运营账号查询人工工单。
- `PATCH /handoff-tickets/{ticket_id}`：运营账号处理人工工单。

API 层只调用 Agent 或 Repository，不负责工具选择和回答生成。
