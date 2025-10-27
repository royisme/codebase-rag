# CIT 知识图谱 GraphRAG 查询需求文档

## 1. 背景与目标
- 阶段目标：在 MVP 中提供「代码变更关联查询」的最小可用体验，帮助开发者快速理解某段代码或需求对应的文件、提交、参与者与证据。
- 现状：已有知识源 CRUD、基本 GraphRAG API，但返回内容以通用文本为主，尚未体现知识图谱关系，也缺少对 LLM 的结构化约束。
- 本文档旨在定义后端应实现的数据收集、提示词编排、响应结构以及前端展示契约，为后续任务拆分提供共同参考。

## 2. 主要用户场景
1. **定位功能变化**：用户询问“登录流程最近的改动在哪？”，系统需给出涉及的文件、提交、负责人，并附带证据片段。
2. **理解代码依赖**：用户询问“`UserService` 被哪些模块调用？”，系统需列出上游/下游模块，以及相关讨论或文档。
3. **评估影响范围**：用户询问“重构 `GraphRAG` 会影响谁？”，系统需输出相关的人、服务、测试套件。

## 3. 数据收集与上下文构建
实现 GraphRAG 查询时，后端必须在调用 LLM 前准备以下结构化信息：

| 模块 | 说明 | 结构示例 |
| --- | --- | --- |
| **Graph 数据** | 基于 Neo4j，按问题意图检索相关节点及关系：文件、函数、提交、模块、人员等 | `{ "files": [...], "commits": [...], "modules": [...], "people": [...] }` |
| **向量检索** | 从嵌入向量索引中检索最相关的代码片段、文档段落、提交说明 | `[{"id": "...", "text": "...", "source_type": "commit"}]` |
| **问题意图分类（可选）** | 判断问题偏向“变更历史 / 依赖 / 责任人”，用于选择 Cypher 模板或提示策略 | `"intent": "recent_changes"` |

### Neo4j 查询要求
- 至少覆盖以下关系：`FILE_CHANGED_IN_COMMIT`、`FILE_DEPENDS_ON_FILE`、`MODULE_OWNS_FILE`、`PERSON_AUTHORED_COMMIT`。
- 查询结果需附带关键属性：文件路径、最后提交时间、提交摘要、作者、模块描述等。
- 若未检索到结果，仍需将检索过程中的指标返回给 LLM（用于说明“暂无数据”）。

## 4. LLM 提示词与输出规格

### System Prompt（建议放置于 `prompts/system_graph_rag.txt`）
```
你是 CIT 代码知识图谱的技术顾问。必须基于提供的结构化图谱数据和证据回答，禁止杜撰。
输出 JSON，字段如下：
- summary: 对用户问题的简明回答（中文）
- related_entities: 数组，每项包含 {type, name, importance, detail, link}
- evidence: 数组，每项包含 {id, snippet, source_type, source_ref}
- next_actions: 建议用户下一步可调查的问题或操作
当证据不足时，summary 中需要明确说明「暂无足够信息」。
```

### User Prompt 模板（伪代码）
```jinja2
用户问题：
{{ user_question }}

检索意图：
{{ intent }}

图谱摘要（JSON）：
{{ graph_context_json }}

证据片段：
{% for item in evidence_snippets %}
[{{ item.id }}] {{ item.text }}
{% endfor %}

请基于以上内容回答，并使用 JSON 输出。
```

### LLM 输出校验
- 后端需在返回前进行 JSON Schema 校验（或至少验证字段存在），防止 LLM 输出非结构化文本导致前端渲染失败。
- 若解析失败，后端应返回 500 并写审计日志，便于排查。

## 5. API 响应契约
扩展 `/api/v1/knowledge/query` 的响应结构：
```json
{
  "answer": {
    "summary": "...",
    "related_entities": [
      {
        "type": "file|commit|module|person",
        "name": "...",
        "importance": "high|medium|low",
        "detail": "...",
        "link": "可选：跳转到代码/提交的 URL"
      }
    ],
    "evidence": [
      {
        "id": "...",
        "snippet": "...",
        "source_type": "commit|file|doc",
        "source_ref": "commit hash 或文件路径"
      }
    ],
    "next_actions": ["...", "..."]
  },
  "raw_messages": [...],             // 可选：保留 LLM 原始消息，便于调试
  "sources_queried": ["uuid", ...],  // 与现有字段兼容
  "processing_time_ms": 1234,
  "query_id": "..."
}
```

> 注：原有响应中的 `confidence_score` 可保留，但需要说明其计算方法（例如采用 LLM 返回的 score 或证据相似度均值）。

## 6. 前端展示建议（供 UI 参考）
- 基础布局：左侧为 Chat 时间轴（沿用 `@ai-sdk/react useChat` 模式），右侧为“知识卡片”面板。
- 右侧卡片按 `type` 分组（文件、提交、模块、人员），每张卡展示 `name`、`detail`、`importance`，并提供跳转链接/继续追问按钮。
- `evidence` 可在摘要中以引用标注，如 `[E1]`，鼠标悬停显示具体 snippet。
- `next_actions` 直接渲染成快捷操作按钮（点击后自动带着上下文提问）。

## 7. 验收标准
1. 针对上述典型用户问题，后端能返回结构化 JSON，前端能渲染出聊天 + 卡片视图。
2. 如果图谱/向量检索无结果，summary 中要明确提示，同时 evidence 为空。
3. 至少新增 2 个集成测试：使用伪造的图谱数据模拟 LLM 调用（可 mock），验证 JSON 字段完整性。
4. 运行 `uv run pytest -q` 全部通过，GraphRAG 查询接口在 README/文档中同步更新调用示例。
5. 记录 LLM 调用失败、JSON 解析失败等情况到审计日志或错误追踪，便于后续运维。

## 8. 多轮查询最小形态
- 请求体可携带 `context_query_id`，命中缓存时服务端会将上一轮的摘要、关联实体、建议操作拼装进当次提示语，增强回答连贯性。
- 查询成功会生成新的 `query_id` 并写入缓存（默认 10 分钟，可通过 `GRAPHRAG_QUERY_CACHE_TTL_SECONDS` 调整），前端应使用该 ID 继续追问。
- 暴露 `GET /api/v1/knowledge/query/{query_id}` 以获取缓存结果，便于演示或分享。

## 9. 后续扩展（非 MVP）
- 支持“多轮追问”时引用上一轮的相关实体，形成上下文记忆。
- 结合 CI/CD 信息，将提交链接到流水线状态或测试覆盖率。
- 提供“知识更新提醒”，告知当前回答基于的知识源更新时间。

---
本文档是后续 OpenSpec 变更、任务拆分以及 Claude 执行的基础，请在开始开发前确保阅读并保持一致。***
