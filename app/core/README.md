# core 模块

`core` 模块保存全局配置、安全校验、知识库文件路径、检索阈值和运行环境。

当前 MVP 使用 Pydantic `BaseModel` 读取环境变量，避免引入过重的配置框架。

## 运营认证与授权

- 账号密码使用 PBKDF2 哈希保存，不存储明文密码。
- 登录后发放随机短期会话令牌，数据库仅存储 SHA-256 令牌哈希。
- 请求使用 `Authorization: Bearer <session_token>`。
- `support` 可查看和处理工单，`admin` 额外可查看审计日志。
- 非本地环境禁止使用默认密码。
