# PROJECT_PROGRESS

## 2026-06-09 至 2026-06-10

### 已完成

- 将项目定位重构为 Football Gear AI Assistant。
- 完成 FastAPI 后端骨架：`/health`、`/chat`、`/chat/stream`、`/products`、`/inventory`。
- 完成 SQLite 初始化和种子数据导入。
- 完成 8 个商品、19 条库存、9 条尺码、20 条 FAQ 数据。
- 完成 Agent 本地路由：商品推荐、库存查询、尺码推荐、FAQ RAG。
- 保留 OpenAI SDK function calling 开关：`USE_OPENAI=true`。
- 完成 Next.js/Tailwind 聊天前端源码。
- 完成 README、API 文档、架构图、面试讲解文档。
- 完成 Dockerfile、Render 后端配置、Vercel 前端配置模板。
- 安装 npm 11.16.0 到 `~/.local/bin/npm` 和 `~/.local/bin/npx`。
- 将前端 Next.js 升级到 16.2.7，并生成 `frontend/package-lock.json`。
- 回头检查并精简代码：Agent 本地路由改为表驱动，商品/位置识别改为别名表，SQLite seed 函数合并，前端移除不必要的 memo。
- 开始真实项目化第一步：新增 conversations、messages、tool_call_logs、handoff_tickets、agent_events 表。
- `/chat` 和 `/chat/stream` 已接入持久化会话，返回或透出 `conversation_id`。
- 新增 `/conversations/{conversation_id}/messages` 查询会话消息历史。
- 新增人工接管机制：`HandoffPolicy` 会对投诉、退款、人工请求、fallback 和低置信度创建 `handoff_tickets`。
- 新增 `/handoff-tickets` 查询人工接管工单，`/health` 返回 `open_handoffs`。
- 完成人工接管代码审查：同一会话复用已有 open 工单，前端 `ChatResponse` 类型补齐 `needs_handoff` 和 `handoff`。
- 新增渠道适配层：`POST /channels/{channel}/messages` 支持外部用户/会话 ID 映射到内部 `conversation_id`，并新增 `channel_conversations` 表。
- 新增人工工单工作流：`PATCH /handoff-tickets/{ticket_id}` 支持 `open`、`in_progress`、`resolved`，并记录处理人、处理备注和解决时间。
- 新增 handoff guard：会话存在 open/in_progress 工单时暂停 AI 自动回复，工单 resolved 后恢复 AI。
- 完成运营后台第一步：新增 `/admin/handoffs` 工单页面，可筛选工单、查看会话上下文、标记处理中、填写处理备注并关闭工单。
- 完成运营账号系统：内置 `admin`、`support` 两种角色，密码使用 PBKDF2 哈希保存。
- 登录后发放短期随机会话令牌，数据库只保存令牌哈希；退出后立即撤销会话。
- 完成 RBAC：客服可处理工单，管理员额外可查看 `/admin/audit-logs`。
- 完成操作审计：登录、退出和工单状态更新写入 `audit_logs`。
- 工单处理人由后端登录身份确定，前端传入的处理人字段不会被信任。
- 非本地环境禁止使用默认运营密码，避免部署时遗留开发凭据。
- 完成运营账号管理：管理员可创建、启停、调整角色和重置其他账号密码。
- 完成密码生命周期：账号可修改自己的密码，管理员重置密码会撤销目标账号全部会话。
- 完成在线会话管理：管理员查看和撤销全部会话，客服仅管理自己的会话。
- 增加安全约束：禁止移除自己的管理员权限，禁止移除最后一个有效管理员。
- API 测试改为每条用例使用独立临时 SQLite 数据库，不再污染开发数据。
- 完成一键启动：`./scripts/start-local.sh` 自动准备依赖、启动前后端并运行冒烟测试。
- 新增 `compose.yaml`、前端 Dockerfile、容器健康检查和 SQLite named volume。
- 新增无第三方依赖的 `scripts/smoke_test.py`，覆盖前端、健康检查、聊天、登录和运营接口。
- 新增安全的演示数据重置能力：默认备份 SQLite，清理运行数据并恢复固定商品与初始运营账号。
- 完成生产部署配置加固：Render 持久磁盘、健康检查、生产 CORS 和 Vercel 环境变量外置。
- 新增公网部署指南与 `validate_deployment.py`，可自动检查健康状态、CORS 和前端可达性。
- 将生产数据层迁移为 PostgreSQL：新增 SQLite/PostgreSQL 适配器，Render 改用 Free 实例，Neon 保存持久数据。
- 修复 Render 2026 默认 Python 3.14 与锁定依赖不兼容的问题，生产运行时固定为 Python 3.11.11。
- 修复 psycopg 批量种子写入：PostgreSQL `executemany` 改由 cursor 执行，并增加适配层回归测试。
- 公网验收脚本超时调整为 90 秒，以覆盖 Render Free 实例冷启动场景。
- 修复生产对话误路由：增加鞋楦宽度筛选、球衣尺码澄清，并移除中文单字 RAG 误匹配。

### 本地验证

- `.venv/bin/python -m unittest discover -s tests`：35 个测试通过。
- 后端依赖已安装在 `.venv`。
- FastAPI 已启动并通过 curl 验证：
  - `/health`
  - `/chat` 商品推荐
  - `/chat` 库存查询
  - `/chat` 尺码推荐
  - `/chat` FAQ RAG
  - `/chat/stream` 流式文本输出
- `cd frontend && npm run build`：通过；新增 `/admin/handoffs` 后再次通过。
- 浏览器打开 `http://localhost:3000`：通过。
- 前端发送 “Mercurial 16 Elite有43码吗”：成功返回 “当前库存 12 双”。
- 浏览器打开 `http://localhost:3000/admin/handoffs`：通过，已验证工单列表、处理中、已解决和处理备注落库。
- 运营认证浏览器验证通过：错误令牌被拒绝、正确令牌进入后台、退出后返回登录页。
- RBAC 浏览器验证通过：`support` 不显示审计入口，`admin` 可查看登录和工单操作记录。
- 账号与会话管理浏览器验证通过：新账号可在后台显示，管理员可查看当前及其他在线会话。
- 从停止状态运行 `./scripts/start-local.sh`：前后端启动成功，自动冒烟测试通过。
- 演示数据重置在独立临时数据库中验证通过，未自动清空当前开发数据库。
- 公网验收脚本已对本地前后端验证通过：健康检查、CORS 和前端访问均正常。
- Render Free 后端与 Neon PostgreSQL 已部署上线，健康检查、库存和尺码工具调用验证通过。
- Vercel Free 前端已部署上线，生产 CORS 和前端 HTTP 访问验证通过。

### 当前限制

- 当前 shell 的 `http_proxy` 会拦截 localhost，请求本地后端时使用：`NO_PROXY=127.0.0.1,localhost`。
- 启动和冒烟脚本已内置 localhost 代理绕过，不需要用户手动设置 `NO_PROXY`。
- 当前 Mac 未安装 Docker，因此 Compose 已完成格式检查，但未在本机实际构建镜像。
- 前端脚本使用 `next dev --webpack` 和 `next build --webpack`，当前构建稳定通过。
- `npm audit --omit=dev` 仍提示 Next 内部 PostCSS 依赖有 2 个 moderate 漏洞；npm 自动修复方案会降级 Next 到旧版本，暂不执行 `--force`。
- PostgreSQL 兼容层已通过本地适配测试，仍需连接实际 Neon 数据库完成集成验收。

### 下一步

- 在公网聊天页面完成人工点击验收，并验证 `/admin/handoffs` 登录与工单闭环。
- 根据真实渠道需求接入淘宝、1688 或企业微信消息回调。
