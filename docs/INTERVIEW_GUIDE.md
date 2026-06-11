# 面试讲解文档

## 一句话介绍

Football Gear AI Assistant 是一个足球用品零售智能客服 MVP。它能通过 Agent 判断用户意图，调用商品、库存、尺码工具，并通过 FAQ RAG 回答售后和物流问题。

## 演示顺序

1. 打开前端聊天页，展示 ChatGPT 风格入口。
2. 输入“推荐800元以内足球鞋”，展示 `search_products` 工具调用。
3. 输入“Mercurial 16 Elite有43码吗”，展示 `check_inventory` 工具调用。
4. 输入“脚长27厘米穿什么码”，展示 `get_size_recommendation` 工具调用。
5. 输入“多久发货”，展示 FAQ RAG 命中。
6. 输入投诉请求，展示 AI 暂停回复并创建人工接管工单。
7. 使用 `support` 登录运营后台，领取并解决工单。
8. 使用 `admin` 登录，展示该操作已经写入审计日志。
9. 展示账号管理和在线会话撤销，说明权限系统与 Agent 业务层解耦。

## 架构讲法

我把系统拆成四层：

- API 层：FastAPI 接收请求，做参数校验，不写业务逻辑。
- Agent 层：负责意图识别、路由决策和最终回答组织。
- Tool 层：把真实业务能力封装成函数，如查库存、搜商品、查尺码。
- Data/RAG 层：SQLite 保存结构化商品数据，FAQ 检索提供非结构化知识问答。
- Operations 层：独立处理账号认证、角色授权、人工工单和审计日志。

## 关键亮点

- **Tool Calling 可解释**：响应中返回实际调用的工具名、参数和结果。
- **RAG 可追溯**：FAQ 问答返回命中的知识来源。
- **演示稳定**：没有 OpenAI Key 或额度时仍可本地跑通。
- **可扩展**：OpenAI function calling、ChromaDB、ERP、工单系统都保留了接口边界。
- **真实运营闭环**：支持 Agent 转人工、客服处理、管理员审计，处理人由后端身份决定。
- **身份生命周期完整**：支持账号创建、停用、密码修改、管理员重置和会话撤销。

## Prompt 设计

系统提示词的核心约束：

```text
You are a football gear retail support agent.
Use tools for inventory, product recommendations and size advice.
For shipping, return and policy questions, answer from FAQ retrieval context.
```

讲解重点不是把 Prompt 写得很长，而是让 LLM 明确什么时候该用工具，什么时候该用知识库。

## 为什么默认不用真实 OpenAI 调用

面试演示最怕外部依赖不稳定。API Key、组织、项目、模型权限、免费额度、预算上限、RPM/TPM 都可能导致“有额度但接口不可用”。所以默认使用本地路由，保证核心链路可演示；设置 `USE_OPENAI=true` 后可以启用 OpenAI SDK。

## 为什么先不用真正 ERP

MVP 目标是展示 AI 系统如何解决真实业务问题，不是复刻完整零售系统。SQLite 模拟产品、库存和尺码已经足够表达 Tool Calling；真实上线时把 Repository 换成 ERP/OMS/WMS API 即可。

## 为什么 RAG 先用本地检索

FAQ 只有 20 条，本地 lexical retriever 足够展示 RAG 闭环。后续替换成 ChromaDB 时，只需要保持 `FAQKnowledgeBase.search(query)` 的输出结构不变，Agent 不需要重写。

## 可以被追问的点

- 如何做多轮对话：加入 session store，保存用户位置、预算、尺码偏好。
- 如何做评估：准备 FAQ golden set，统计命中率、工具选择准确率和人工接管率。
- 如何做安全：工具参数校验、库存结果只读、敏感操作必须人工确认。
- 如何部署：后端 Render/Railway，前端 Vercel，环境变量控制 API 地址和 OpenAI 开关。
- 如何观测：记录 request_id、route、tool_calls、latency、confidence。
