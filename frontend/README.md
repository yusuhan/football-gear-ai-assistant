# frontend 模块

`frontend` 是 Next.js 聊天界面，用于演示 Football Gear AI Assistant。

## 功能

- ChatGPT 风格聊天页。
- 默认调用后端 `/chat/stream` 做流式输出。
- 流式失败时可改用普通 `/chat` 接口。
- `/admin/handoffs` 提供最小运营后台，可查看转人工工单、会话上下文，并将工单标记为处理中或已解决。
- 运营后台使用用户名和密码登录，服务端发放短期会话令牌，浏览器仅在当前标签页保存会话。
- `support` 可处理工单，`admin` 额外可查看审计日志。
- 管理员可管理运营账号和全部在线会话；客服可管理自己的密码和会话。

## 本地运行

当前项目已安装 npm，并生成 `package-lock.json`。

```bash
cd frontend
npm install
npm run dev
```

默认后端地址为 `http://127.0.0.1:8000`，可通过 `.env.local` 覆盖：

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

本地账号：

```text
admin / local-admin-change-me
support / local-support-change-me
```

默认密码只用于本地开发，部署前必须替换。

## 验证记录

- `npm run build` 已通过。
- `dev` 和 `build` 脚本使用 Webpack，当前环境构建稳定通过。
- 已用浏览器验证聊天页面可访问，并成功调用后端库存查询。
- 已新增人工接管工单后台页面，后续验证以 `npm run build` 和浏览器访问 `/admin/handoffs` 为准。
