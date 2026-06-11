# scripts 模块

该目录保存本地启动、数据重置、本地冒烟和公网部署验收脚本。

## start-local.sh

一条命令启动 FastAPI 和 Next.js：

```bash
./scripts/start-local.sh
```

脚本会：

- 创建缺失的 Python 虚拟环境并安装后端依赖。
- 安装缺失的前端依赖。
- 启动 `127.0.0.1:8000` 和 `127.0.0.1:3000`。
- 自动运行 `smoke_test.py --wait`。
- 按 `Ctrl+C` 时同时停止前后端进程。

## smoke_test.py

对运行中的系统验证：

- 前端可访问。
- `/health` 正常。
- 库存 Tool Calling 正常。
- 管理员登录正常。
- 运营账号接口正常。

```bash
.venv/bin/python scripts/smoke_test.py
```

脚本主动绕过系统 HTTP 代理，避免 localhost 请求被代理拦截。

## reset_demo_data.py

重置会话、消息、工单、审计、在线会话和运营账号，并恢复固定商品种子数据与初始账号。默认先将当前数据库备份到 `data/backups/`：

```bash
.venv/bin/python scripts/reset_demo_data.py --yes
```

该命令会使现有运营登录令牌失效。仅在明确不需要备份时使用 `--no-backup`。

## validate_deployment.py

部署后检查前端、后端健康状态和 CORS：

```bash
.venv/bin/python scripts/validate_deployment.py \
  --backend https://your-api.onrender.com \
  --frontend https://your-app.vercel.app
```
