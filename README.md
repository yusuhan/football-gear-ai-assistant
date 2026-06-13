# Football Gear AI Assistant

足球用品零售 AI 客服系统。当前版本已经具备 Agent、Tool Calling、FAQ RAG、FastAPI、数据库持久化、前端聊天界面和运营后台，可继续扩展到淘宝/1688/企微/CRM 等真实客服渠道。

## 项目目标

用户可以在聊天窗口咨询：

- 商品推荐：如“推荐800元以内足球鞋”
- 库存查询：如“Mercurial 16 Elite有43码吗”
- 尺码推荐：如“脚长27厘米穿什么码”
- FAQ 问答：如“多久发货”“支持退货吗”

## 技术栈

- 后端：Python 3.11、FastAPI、Pydantic
- Agent：OpenAI SDK 可选，默认本地规则路由保证演示稳定
- Tool Calling：`check_inventory`、`search_products`、`get_size_recommendation`
- 数据库：本地 SQLite / 生产 PostgreSQL
- RAG：本地 FAQ 检索，保留 ChromaDB 替换边界
- 前端：Next.js、Tailwind、shadcn/ui 风格组件
- 部署：Render/Railway 后端，Vercel 前端

## 真实项目化能力

- 每次聊天会自动创建或复用 `conversation_id`。
- 用户消息、AI 回复、工具调用和 Agent 事件会写入 SQLite。
- 支持查询会话历史：`GET /conversations/{conversation_id}/messages`。
- 投诉、退款、人工请求、fallback 和低置信度会自动创建人工接管工单。
- 支持查询人工队列：`GET /handoff-tickets`。
- 支持人工处理工单：`PATCH /handoff-tickets/{ticket_id}`。
- 会话存在 open/in_progress 工单时，后续消息只进入人工队列，不再触发 AI 自动回复；工单 resolved 后恢复 AI。
- 支持渠道适配入口：`POST /channels/{channel}/messages`，可模拟淘宝/1688/企微等外部消息源。
- 运营后台支持 `admin` 和 `support` 两种角色、短期会话令牌与操作审计日志。
- 管理员可创建、启停和调整运营账号，重置其他账号密码，并管理全部在线会话。
- 所有运营账号均可修改自己的密码和撤销自己的其他会话。

## 目录结构

```text
.
├── app                  # FastAPI 后端
│   ├── api              # HTTP 路由
│   ├── core             # 配置
│   ├── db               # SQLite/PostgreSQL 连接与初始化
│   ├── models           # Pydantic 模型
│   └── services         # Agent、Tool Router、RAG、Repository
├── data                 # 商品、库存、尺码、FAQ 种子数据
├── docs                 # API、架构图、面试讲解
├── frontend             # Next.js 聊天页面
├── scripts              # 一键启动和冒烟测试
├── tests                # 后端验证用例
├── compose.yaml         # 前后端 Docker Compose 编排
├── Dockerfile
├── render.yaml
└── PROJECT_PROGRESS.md
```

## 一键启动

当前 Mac 或普通开发环境：

```bash
./scripts/start-local.sh
```

脚本会自动准备缺失依赖、启动前后端并运行冒烟测试。按 `Ctrl+C` 可同时停止两项服务。

安装 Docker 的机器也可以运行：

```bash
docker compose up --build
```

Docker Compose 包含：

- FastAPI 后端健康检查。
- Next.js 前端健康检查和后端启动依赖。
- SQLite named volume 持久化。
- 本地账号和 OpenAI 配置的环境变量入口。

停止服务：

```bash
docker compose down
```

清空 Docker 本地数据库时使用：

```bash
docker compose down -v
```

## 后端快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

访问：

- 健康检查：http://127.0.0.1:8000/health
- Swagger：http://127.0.0.1:8000/docs

## 前端快速开始

项目已在本机安装 npm。首次运行或重新安装依赖：

```bash
cd frontend
npm install
npm run dev
```

默认后端地址：`http://127.0.0.1:8000`

运营后台地址：`http://localhost:3000/admin/handoffs`

本地账号：

- 管理员：`admin` / `local-admin-change-me`
- 客服：`support` / `local-support-change-me`

部署时必须设置 `ADMIN_PASSWORD` 和 `SUPPORT_PASSWORD`；非本地环境使用默认密码时，服务会拒绝启动。

## 示例请求

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Mercurial 16 Elite有43码吗"}'
```

## 本地验证

```bash
.venv/bin/python -m unittest discover -s tests
```

当前已验证：32 个后端测试通过。

前端验证：

```bash
cd frontend
npm run build
```

当前已验证：前端生产构建通过，浏览器可打开 `http://localhost:3000` 并成功调用后端。

整套系统冒烟验证：

```bash
.venv/bin/python scripts/smoke_test.py
```

重置演示数据（默认先备份数据库）：

```bash
.venv/bin/python scripts/reset_demo_data.py --yes
```

重置会清空会话、工单、审计、在线登录和临时运营账号，然后恢复固定商品数据以及 `admin`、`support` 初始账号。

## OpenAI Function Calling

默认 `USE_OPENAI=false`，Agent 使用本地确定性路由，避免 API Key 或额度问题影响演示。

如需启用 OpenAI SDK：

```bash
export OPENAI_API_KEY=sk-...
export USE_OPENAI=true
export OPENAI_MODEL=gpt-4.1-mini
uvicorn app.main:app --reload
```

如果平台提示“明明有额度但没额度”，常见原因是 API Key 属于错误组织/项目、免费额度过期、项目预算上限、模型权限、RPM/TPM 限流或环境变量被旧 Key 覆盖。本项目默认不依赖外部额度。

## 文档

- [API 文档](docs/API.md)
- [架构图](docs/ARCHITECTURE.md)
- [面试讲解文档](docs/INTERVIEW_GUIDE.md)
- [公网部署指南](docs/DEPLOYMENT.md)

## 公网环境

- 前端：https://football-gear-ai-assistant.vercel.app
- 后端：https://football-gear-ai-assistant-api.onrender.com
- API 文档：https://football-gear-ai-assistant-api.onrender.com/docs

生产环境使用 Vercel Free、Render Free 和 Neon Free。Render 免费实例休眠后，首次请求可能需要等待约 50 秒。
