# API 文档

## 基础信息

- 本地地址：`http://127.0.0.1:8000`
- Swagger：`/docs`
- 数据格式：JSON

## 运营接口认证

运营账号使用用户名和密码登录，服务端返回短期会话令牌。后续请求携带：

```text
Authorization: Bearer <access_token>
```

本地账号：`admin / local-admin-change-me`、`support / local-support-change-me`。部署前必须替换默认密码。

## POST /admin/auth/login

创建运营会话。

```json
{
  "username": "admin",
  "password": "local-admin-change-me"
}
```

响应包含 `access_token`、`expires_at` 和当前账号的 `username`、`role`。

## POST /admin/auth/logout

撤销当前会话令牌，需要 Bearer Token。

## GET /admin/audit-logs

返回登录、退出和工单更新记录，仅 `admin` 角色可访问。`support` 访问时返回 `403`。

## POST /admin/auth/change-password

当前账号修改自己的密码。成功后保留当前会话，撤销该账号的其他会话。

```json
{
  "current_password": "old-password",
  "new_password": "new-password"
}
```

## GET /admin/users

管理员查询全部运营账号。

## POST /admin/users

管理员创建 `admin` 或 `support` 账号。

```json
{
  "username": "support_02",
  "password": "initial-password",
  "role": "support"
}
```

## PATCH /admin/users/{user_id}

管理员调整角色或启停账号。系统禁止管理员移除自己的权限，也禁止移除最后一个有效管理员。

## POST /admin/users/{user_id}/reset-password

管理员重置其他账号密码，并撤销目标账号全部在线会话。

## GET /admin/sessions

管理员返回全部有效会话；客服只返回自己的有效会话。

## DELETE /admin/sessions/{session_id}

管理员可撤销任意会话；客服只能撤销自己的会话。

## GET /health

健康检查和演示数据加载状态。

### 响应示例

```json
{
  "status": "ok",
  "products": 8,
  "inventory_rows": 19,
  "faq_articles": 20,
  "conversations": 3,
  "open_handoffs": 1
}
```

## POST /chat

主聊天接口。

### 请求示例

```json
{
  "message": "Mercurial 16 Elite有43码吗"
}
```

如果是已有会话，继续传：

```json
{
  "conversation_id": "conv_...",
  "message": "那42码呢"
}
```

### 响应示例

```json
{
  "conversation_id": "conv_...",
  "answer": "Nike Mercurial 16 Elite 43码有货，当前库存 12 双。",
  "intent": "inventory_check",
  "confidence": 0.92,
  "route": "tool",
  "tool_calls": [
    {
      "name": "check_inventory",
      "arguments": {
        "product_name": "Mercurial",
        "size": 43
      },
      "result": {
        "available": true,
        "product_id": "P001",
        "product_name": "Nike Mercurial 16 Elite",
        "size": 43,
        "stock": 12
      }
    }
  ],
  "sources": [],
  "needs_handoff": false,
  "handoff": null
}
```

## POST /chat/stream

聊天流式输出接口，返回 `text/plain` 分块文本，用于前端逐字/逐段展示。

响应 Header 会包含：

```text
X-Conversation-Id: conv_...
```

## POST /api/v1/chat

`/chat` 的版本化别名，方便后续兼容。

## POST /channels/{channel}/messages

渠道适配入口，用于淘宝、1688、企微、独立站等外部消息源。外部系统只需要传自己的用户 ID 和会话 ID，服务会映射到内部 `conversation_id`。

### 请求示例

```json
{
  "external_user_id": "buyer_001",
  "external_conversation_id": "taobao_thread_001",
  "message": "多久发货",
  "metadata": {
    "shop_id": "demo_shop"
  }
}
```

### 响应示例

```json
{
  "channel": "taobao",
  "external_conversation_id": "taobao_thread_001",
  "conversation_id": "conv_...",
  "answer": "现货商品通常在付款后 24 小时内发货；大促期间可能延长到 48 小时。",
  "needs_handoff": false,
  "handoff": null
}
```

## GET /products

获取商品列表。

## GET /inventory

获取库存列表。

## GET /conversations/{conversation_id}/messages

获取一个会话的持久化消息历史。

需要 `admin` 或 `support` 会话令牌。

### 响应示例

```json
[
  {
    "id": "msg_...",
    "conversation_id": "conv_...",
    "role": "user",
    "content": "多久发货",
    "created_at": "2026-06-09T..."
  },
  {
    "id": "msg_...",
    "conversation_id": "conv_...",
    "role": "assistant",
    "content": "现货商品通常在付款后 24 小时内发货；大促期间可能延长到 48 小时。",
    "intent": "faq",
    "route": "rag",
    "confidence": 0.95,
    "created_at": "2026-06-09T..."
  }
]
```

## GET /handoff-tickets

查询人工接管工单，默认只返回 `open` 状态。

需要 `admin` 或 `support` 会话令牌。

### 响应示例

```json
[
  {
    "id": "handoff_...",
    "conversation_id": "conv_...",
    "reason": "sensitive_keyword:投诉",
    "status": "open",
    "created_at": "2026-06-09T...",
    "updated_at": "2026-06-09T..."
  }
]
```

## PATCH /handoff-tickets/{ticket_id}

人工客服更新工单状态。支持状态：`open`、`in_progress`、`resolved`。

需要 `admin` 或 `support` 会话令牌。`assigned_to` 由后端根据当前登录账号填写。

### 请求示例

```json
{
  "status": "resolved",
  "resolution_note": "已人工联系用户处理"
}
```

### 转人工后的聊天行为

如果一个会话存在 `open` 或 `in_progress` 工单，后续 `/chat` 不再调用 Agent，而是返回：

```json
{
  "intent": "human_handoff",
  "route": "handoff",
  "needs_handoff": true,
  "answer": "这次会话已经转接人工客服，我已记录你的补充消息，请等待人工继续处理。"
}
```

当工单更新为 `resolved` 后，同一个 `conversation_id` 会恢复 AI 自动回复。

### 响应示例

```json
{
  "id": "handoff_...",
  "conversation_id": "conv_...",
  "reason": "sensitive_keyword:投诉",
  "status": "resolved",
  "assigned_to": "agent_001",
  "resolution_note": "已人工联系用户处理",
  "resolved_at": "2026-06-09T...",
  "created_at": "2026-06-09T...",
  "updated_at": "2026-06-09T..."
}
```

## 典型演示命令

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"推荐800元以内足球鞋"}'
```

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"脚长27厘米穿什么码"}'
```

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"多久发货"}'
```
