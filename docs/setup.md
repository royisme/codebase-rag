# 后端开发环境搭建指南（SQLite MVP）

本文档说明如何为 “CIT Knowledge Graph Console” 在本地搭建后端开发环境。本阶段默认使用 **SQLite** 作为持久层，便于快速验证 RBAC、审计与知识源模块；如需对接 PostgreSQL，可参考文末的可选步骤。

## 1. 环境依赖

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)（推荐的包管理工具）
- SQLite 3（随操作系统自带即可）
- （可选）Neo4j 5.x，用于联调 GraphRAG 能力

## 2. 克隆仓库并安装依赖

```bash
git clone <repo>
cd <repo>/backend
uv sync
```

`uv sync` 会根据 `pyproject.toml` 与 `uv.lock` 安装所需依赖，包括 FastAPI、SQLAlchemy、Alembic、Casbin 等组件。

## 3. 配置环境变量

复制默认配置并按需修改：

```bash
cp env.example .env
```

关键字段说明：

- `DB_PATH`：SQLite 数据库存储路径，默认 `data/knowledge.db`。
- `DB_ECHO`：是否打印 SQL 调试日志（`true` / `false`）。
- `DEBUG`：设为 `true` 后可通过 `http://localhost:8123/docs` 访问 Swagger UI。
- `AUTH_*`：默认管理员账号与 JWT 秘钥，首次启动后请立即更换。

若 `.env` 中存在旧版本的 `DB_HOST`、`DB_PORT` 等字段，可保留但不会在 SQLite 模式下生效。

## 4. 初始化数据库

SQLite 模式下无需额外服务，首次运行 Alembic 会自动创建数据库文件与表结构：

```bash
uv run alembic upgrade head
```

如需重置数据库，可删除 `data/knowledge.db` 后重新执行迁移命令。

## 5. 启动后端服务

```bash
uv run server
```

- 接口默认监听 `http://0.0.0.0:8123`，可通过 `.env` 中的 `HOST`、`PORT` 调整。
- 若 `DEBUG=true`，可访问：
  - `http://localhost:8123/docs`（Swagger UI）
  - `http://localhost:8123/redoc`（Redoc 文档）
- 日志默认写入 `app.log`，可以通过 `LOG_LEVEL` 修改等级。

## 6. 验证运行状态

1. **健康检查**

   ```bash
   curl http://localhost:8123/api/v1/health
   ```

2. **数据库文件**

   启动成功后将在 `backend/data/knowledge.db` 下生成 SQLite 文件。

3. **默认管理员**

   首次运行会打印默认管理员凭据，可使用 `/api/v1/auth/login` 获取访问令牌。

4. **注册流程说明**

   - `/api/v1/auth/register` 接口现在支持 `company`、`department` 字段，用于存储企业名称与部门信息，仅在响应中展示，不参与权限判断。
   - 注册成功后接口返回 `UserRead` 对象，其中 `company`、`department` 若未填写将为 `null`。
   - **注册不会自动返回访问令牌**：前端需在注册成功后调用 `/api/v1/auth/login`（或 `/api/v1/auth/jwt/login`）获取 token。

## 7.（可选）切换到 PostgreSQL

若需要联调更接近生产的环境：

1. 在 `.env` 中改写 `DB_DRIVER_ASYNC=postgresql+asyncpg`、`DB_DRIVER_SYNC=postgresql+psycopg`，并配置 `DB_HOST`、`DB_USER` 等字段。
2. 启动 PostgreSQL 实例（Docker 示例）：

   ```bash
   docker run --name cit-postgres \
     -e POSTGRES_USER=cit_admin \
     -e POSTGRES_PASSWORD=changeme \
     -e POSTGRES_DB=cit_knowledge \
     -p 5432:5432 \
     -d postgres:15
   ```

3. 重新执行 `uv run alembic upgrade head` 即可初始化表结构。

## 8. 常见问题

- **Casbin Adapter 尝试连接失败**：确认当前模式是否仍引用 PostgreSQL DSN，必要时清空 `.env` 中的老变量。
- **无法生成 Swagger**：请检查 `DEBUG` 是否设为 `true`，生产环境默认关闭在线文档。
- **GraphRAG 查询超时**：可调整 `GRAPHRAG_QUERY_TIMEOUT_SECONDS` 或使用更小的测试数据集。
- **GraphRAG 多轮上下文**：如需延长缓存有效期，可配置 `GRAPHRAG_QUERY_CACHE_TTL_SECONDS`；前端在继续追问时应附带上一轮响应的 `query_id`。

完成以上步骤后，即可基于 SQLite 数据库开展 RBAC、审计、知识源管理以及 GraphRAG 接口的开发与测试。
