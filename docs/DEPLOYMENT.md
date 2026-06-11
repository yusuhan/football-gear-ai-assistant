# 公网部署指南

当前最简单的真实部署方案是：Render 托管 FastAPI 和持久化 SQLite，Vercel 托管 Next.js。

## 1. 部署后端到 Render

1. 将代码推送到 GitHub。
2. 在 Render 中选择 **New > Blueprint**，连接仓库根目录的 `render.yaml`。
3. 创建时填写 `BACKEND_CORS_ORIGIN`，值暂时填写计划使用的 Vercel 域名；获得正式域名后可再次修改。
4. Render 会生成 `ADMIN_PASSWORD` 和 `SUPPORT_PASSWORD`。在服务环境变量页面查看并安全保存它们。
5. 等待 `https://<render-domain>/health` 返回 `status: ok`。

`render.yaml` 使用 Starter 实例和 1 GB 持久磁盘。磁盘保存 SQLite 数据，但会关闭 Render 的零停机部署；业务增长后应迁移到 PostgreSQL。

## 2. 部署前端到 Vercel

1. 在 Vercel 导入同一个 GitHub 仓库。
2. 将 **Root Directory** 设置为 `frontend`。
3. 添加生产环境变量：

```text
NEXT_PUBLIC_API_BASE_URL=https://<render-domain>
```

4. 部署并记录 Vercel 正式域名。
5. 回到 Render，将 `BACKEND_CORS_ORIGIN` 精确设置为该 Vercel 域名，不要带末尾 `/`。
6. 重新部署 Render 后端。

多个允许域名可以使用英文逗号分隔，例如生产域名和自定义域名。

## 3. 公网验收

```bash
.venv/bin/python scripts/validate_deployment.py \
  --backend https://<render-domain> \
  --frontend https://<vercel-domain>
```

脚本检查后端健康状态、浏览器 CORS 响应和前端页面。随后人工验证：

- 在聊天页询问“Mercurial 16 Elite有43码吗”。
- 使用管理员账号进入 `/admin/handoffs`。
- 创建投诉工单并完成处理。
- 重新部署后端，确认历史工单仍然存在。

## 4. 生产注意事项

- 不要提交 `.env`、OpenAI Key 或运营账号密码。
- 如果启用 OpenAI，必须在 Render 单独设置 `OPENAI_API_KEY` 和 `USE_OPENAI=true`。
- SQLite 方案仅适合单实例 MVP；多实例或高并发前迁移到 PostgreSQL。
