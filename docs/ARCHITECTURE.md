# 架构图

## MVP 架构

```mermaid
flowchart LR
    User["用户"] --> Frontend["Next.js 聊天界面"]
    Channel["淘宝 / 1688 / 企微 / CRM"] --> Adapter["Channel Adapter /channels/{channel}/messages"]
    Frontend --> API["FastAPI /chat"]
    Ops["运营后台 admin / support"] --> Auth["Operations Auth + RBAC"]
    Auth --> API
    Auth --> Audit["SQLite sessions / audit_logs"]
    Auth --> Users["Account Management / Password Policy"]
    Adapter --> API
    API --> Conversation["ConversationService 持久化会话"]
    Conversation --> Agent["FootballGearAgent"]
    Agent --> Router["Intent Router"]
    Router --> ToolRouter["Tool Router"]
    ToolRouter --> ProductTool["search_products"]
    ToolRouter --> InventoryTool["check_inventory"]
    ToolRouter --> SizeTool["get_size_recommendation"]
    ProductTool --> SQLite["SQLite products / inventory / size_guide"]
    InventoryTool --> SQLite
    SizeTool --> SQLite
    Router --> RAG["FAQ RAG Retriever"]
    RAG --> FAQ["data/faq.json"]
    Conversation --> Handoff["HandoffPolicy 人工接管规则"]
    Conversation --> Store["SQLite conversations / channel_conversations / messages / tool_call_logs / handoff_tickets / agent_events"]
    Agent --> Response["answer + conversation_id + route + tool_calls + sources"]
```

## Tool Calling 流程

```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent
    participant T as ToolRouter
    participant DB as SQLite
    U->>A: Mercurial 16 Elite有43码吗
    A->>A: 识别为 inventory_check
    A->>T: check_inventory(product_name="Mercurial", size=43)
    T->>DB: 查询库存
    DB-->>T: stock=12
    T-->>A: 工具结果
    A-->>U: 43码有货，库存12双
```

## RAG 流程

```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent
    participant R as FAQKnowledgeBase
    participant F as faq.json
    U->>A: 多久发货
    A->>R: search("多久发货")
    R->>F: 本地 FAQ 检索
    F-->>R: FAQ001
    R-->>A: answer + score
    A-->>U: 现货商品通常在付款后24小时内发货
```

## 设计取舍

- **OpenAI SDK 可选**：有 Key 时可启用 function calling；无 Key 时本地路由仍能展示 Agent 架构。
- **SQLite 优先**：比真实 ERP 简单，适合 MVP 和面试演示。
- **本地 FAQ 检索优先**：实现 RAG 闭环，后续可替换成 ChromaDB。
- **返回 tool_calls 和 sources**：便于解释 Agent 为什么这么回答。
- **ConversationService 独立**：Agent 保持无状态，真实渠道接入时由外层服务负责会话、消息和审计日志。
- **HandoffPolicy 独立**：投诉、退款、明确人工请求和订单异常会创建人工接管工单；普通 fallback 先澄清，不制造无效工单。
- **Handoff workflow 完整**：人工客服可以将工单更新为处理中或已解决，并记录处理人和备注。
- **Handoff guard**：会话转人工后暂停业务自动回复，避免 AI 和人工同时处理订单；身份和能力说明等安全元问题仍由 AI 自助回答。
- **Channel Adapter 独立**：淘宝/1688/企微只负责把外部用户和会话 ID 标准化，内部 Agent 不绑定任何渠道。
- **运营身份独立**：密码哈希、短期会话、角色校验和审计日志不进入 Agent 层，避免业务问答与后台权限耦合。
- **会话可撤销**：密码修改、管理员重置和账号停用都会主动撤销相关会话，降低凭据泄露后的风险。

## 可扩展方向

```mermaid
flowchart TB
    Agent["Agent"] --> OpenAI["OpenAI Function Calling"]
    Agent --> HybridRAG["ChromaDB + BM25 Hybrid RAG"]
    Agent --> ERP["ERP / OMS / WMS"]
    Agent --> Ticket["Human Handoff / Ticket"]
    Agent --> Eval["Answer Quality Eval"]
    Agent --> Logs["Tracing / Metrics / Guardrails"]
```
