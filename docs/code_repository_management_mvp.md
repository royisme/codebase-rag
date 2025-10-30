# 代码仓库管理 MVP 需求文档

**创建时间：2025-10-30T14:50:39.537Z**  
**文档状态：MVP 决策版（可执行）**

## 一、目标与范围
- **目标**：实现从“添加代码仓库”到“完成索引并可供前端选择”的完整闭环，支撑 RAG Console 以仓库为知识源进行代码问答。
- **范围（MVP）**：支持 GitHub/GitLab HTTPS Token 访问；仅 main 分支；手动触发索引；全量构建代码图谱；最小语言集 Python/TypeScript/JavaScript/Go；管理员可管理仓库，普通用户仅可选择“已索引”仓库。
- **不在范围（MVP 后续）**：多分支、Webhook 自动增量、SSH、跨仓库依赖、PR/Commit 粒度分析、定时同步、复杂权限到文件粒度。

## 二、用户与角色
- **管理员（admin）**：创建/编辑/删除仓库，验证连接，触发/重试/取消索引，查看任务与日志。
- **普通用户（user）**：在 RAG Console 选择“已索引”的仓库进行问答；不可见管理操作。

## 三、端到端流程（必须走通）
1. 管理员添加仓库（名称、URL、分支、认证方式与 Token、包含/排除规则、最大文件大小）。
2. 连接验证（即时校验凭据与可达性，返回分支列表可选用）。
3. 创建知识源（`type=code`），状态 `pending`。
4. 触发索引任务（`ParseJob` 入队）。
5. 流水线执行：Git 克隆/拉取 → 文件扫描 → Tree-sitter 解析 → Embedding → 写入 Neo4j → 标记完成。
6. 前端仓库状态变为 `indexed`，RAG Console 的 SourceSelector 可选择该仓库。

## 四、数据模型（基于现有 KnowledgeSource/ParseJob 扩展）
- **KnowledgeSource（新增/约定字段）**
  - `source_type`: `"code"`
  - `connection_config`: `{ repo_url, branch, auth_type(token|none), access_token(加密), include_patterns["*.py","*.ts","*.js","*.go"], exclude_patterns["node_modules/*","*.test.*"], max_file_size_kb: 500 }`
  - `source_metadata`: `{ last_commit_sha, total_files, total_functions, languages: {python: n,...}, graph_nodes, graph_edges, index_version }`
  - `is_active`, `last_synced_at` 保持使用
- **ParseJob（状态机与摘要）**
  - `status`: `pending|running|completed|failed|cancelled`
  - `job_config`: `{ stage: git_clone|file_scan|code_parse|embedding|graph_build, retry_count, max_retries, timeout_seconds }`
  - `result_summary`: `{ files_scanned, files_parsed, files_failed, functions_extracted, imports_extracted, nodes_created, edges_created, duration_seconds, errors: [{file,error}] }`

## 五、后端 API（MVP 必需）
- **仓库管理**
  - `POST /api/admin/sources`
    - 请求：`{ name, source_type:"code", connection_config{ repo_url, branch, auth_type, access_token?, include_patterns?, exclude_patterns?, max_file_size_kb? } }`
    - 响应：`{ id, status:"pending_validation" | "pending" }`
  - `POST /api/admin/sources/validate`
    - 请求：`{ repo_url, auth_type, access_token? }`
    - 响应：`{ valid: true|false, message?, accessible_branches?: ["main", "dev"] }`
  - `PATCH /api/admin/sources/{id}`
    - 可更新：`connection_config`、`is_active`；变更后可选触发一次索引
  - `DELETE /api/admin/sources/{id}`（软删除）
- **索引/任务**
  - `POST /api/admin/sources/{id}/index`
    - 请求：`{ force_full: boolean }`
    - 响应：`{ job_id, status:"queued" }`
  - `GET /api/admin/jobs?source_id=&status=&page=&pageSize=`
    - 响应：`{ items:[{ id, source_id, status, stage, progress_percentage, started_at, items_processed, total_items }], total, page, pageSize }`
  - `GET /api/admin/jobs/{job_id}`
    - 响应：`{ ...job, logs:[{ timestamp, level, message, stage }] }`
  - `POST /api/admin/jobs/{job_id}/cancel | /retry`
- **前端消费**
  - `GET /api/admin/sources?statuses=indexed&search=&page=&pageSize=`
    - 响应：`{ items:[{ id, name, source_type, source_metadata, last_synced_at }], total, page, pageSize }`

## 六、流水线与模块（服务层）
- **Git 同步（git_sync）**
  - `clone_or_pull(source)`: 使用 `depth=1` 浅克隆或增量拉取；缓存到本地目录 `/data/repos/{source.id}`
  - `changed_files(old,new)`: 返回增量文件列表（MVP 可不实现增量，仅全量）
- **文件扫描（file_scan）**
  - 遵循 include/exclude/max_file_size 过滤，识别语言
- **代码解析（code_parser）**
  - 使用 Tree-sitter（python/ts/js/go）提取函数/类/导入，记录所在文件与行号
- **向量化（embedding）**
  - 对函数体或代码片段生成向量（MVP 可直接复用现有 embedding 服务）
- **图构建（graph_builder）**
  - 将 `CodeFile`、`Function` 节点与 `DEFINED_IN/CALLS/IMPORTS` 关系写入 Neo4j；幂等 `MERGE`；设置唯一约束（`source_id+path` / `source_id+qualified_name`）
- **编排（indexing_pipeline）**
  - 按阶段更新 `ParseJob` 状态与进度；失败写错误与回滚标记；完成后回写 `KnowledgeSource.source_metadata` + `last_synced_at`

## 七、前端功能（MVP）
> 前端改动不在当前仓库范围，仅作占位说明。
- 管理端：仓库列表、添加仓库表单、任务详情。
- 普通用户端：SourceSelector 仅展示 `status=indexed` 的仓库，显示语言、最后更新时间与统计。

## 八、权限与安全
- **RBAC**：`/api/admin/*` 仅 `admin`；普通用户仅可读已索引仓库列表。
- **Token 安全**：`access_token` 必须加密存储（开发用占位，生产对接 KMS/Vault）。
- **审计**：对仓库 CRUD、索引触发、任务控制写审计事件（用户、资源、动作、结果）。
- **速率与配额**：限制并发索引数；单仓库索引互斥；文件大小上限与总量阈值。

## 九、错误处理与可观测性
- **任务失败策略**：最大重试 3 次（git 网络错误、解析超时可重试；配置错误不重试）。
- **指标**：索引时延、成功率、解析文件数、节点/边增量；日志按阶段结构化记录。
- **用户提示**：前端在失败时展示错误摘要与重试入口。

## 十、配置项（默认值）
- `repo_root`: `/data/repos`
- `git_depth`: `1`
- `include_patterns`: `["*.py","*.ts","*.js","*.go"]`
- `exclude_patterns`: `["node_modules/*","*.test.*"]`
- `max_file_size_kb`: `500`
- `max_concurrent_indexing`: `2`
- `job_timeout_seconds`: `900`

## 十一、验收标准（Definition of Done）
- 管理员可成功添加并验证一个私有/公共仓库（HTTPS Token/None）。
- 触发索引后，`ParseJob` 阶段与进度可见，失败可重试，运行可取消。
- 索引完成后，Neo4j 中可查询到 `CodeFile`/`Function` 节点与关系；前端状态显示 `indexed`。
- 普通用户在 RAG Console 可选择该仓库，发起查询并返回包含代码片段的答案。
- 关键审计与错误日志可查；并发与互斥机制生效。
