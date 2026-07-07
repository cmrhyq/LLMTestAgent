# ADR-001: Project 工作空间、Ask/Plan 对话模式与 Chroma 语义检索

| 属性 | 值 |
|------|-----|
| **状态** | Proposed |
| **日期** | 2026-07-07 |
| **决策者** | LLMTestAgent 团队 |
| **关联** | `doc/SystemFlowchart.md`, `backend/src/core/chroma/`, `frontend/src/pages/run/` |

---

## 1. 背景与上下文（Context）

### 1.1 项目原始设计

LLMTestAgent 的核心流程为：

1. 用户提供 `api_doc_file_path` 与自然语言指令；
2. 意图识别为 `parse_openapi` 时，解析 OpenAPI 文档并写入 SQLite（Project + Environment + Endpoint）；
3. 意图识别为 `run_test` 时，基于**已入库**的项目与接口数据，通过 Agent 挑选接口、生成用例、执行测试并生成报告。

`api_doc_file_path` 的设计目的是**支持解析入库**，而非在每次测试时重新读取文件。

### 1.2 当前实现与产品设想之间的差距

| 领域 | 设计意图 | 当前状态 |
|------|----------|----------|
| 文档导入 | 上传 → 解析 → 入库 | 前端 `upload` 仅存文件；`parse` 为独立 API；三者未统一 |
| 测试执行 | 基于已入库项目测「xxx 项目用户相关接口」 | 后端 Agent + DB Tools 具备能力，但缺少显式「当前工作空间」 |
| Ask / Plan | 两种对话模式 | 前端 UI 已实现，`mode` 未传后端，无对应逻辑 |
| 向量检索 | 语义检索增强问答与选接口 | `ChromaManager` 已实现，未接入业务，无 Embeddings 配置 |
| 项目上下文 | 操作应绑定某一 Project | 对话/运行 API 无 `project_id`；`api_doc_path` 在 chat 中被忽略 |

### 1.3 新的产品方向

引入类似 **Codex 工作空间** 的机制：

- **每个 Project = 一个工作空间**；
- 工作空间内可 **解析上传 OpenAPI**，也可 **手动编写/编辑接口**；
- 在同一工作空间内支持三种交互模式：
  - **Ask**：回答测试相关问题，不执行 HTTP；
  - **Plan**：生成测试计划，用户确认后执行；
  - **Run**：直接触发测试工作流（现有能力）。

### 1.4 驱动本 ADR 的问题

1. Chroma 应存储哪些数据？哪些代码需要修改？
2. Ask / Plan 应如何与现有 LangGraph 工作流共存？
3. `api_doc_file_path` 与 `project_id` 的职责如何划分？
4. 实施优先级如何排序？

---

## 2. 决策（Decision）

### 2.1 架构原则

| # | 原则 | 说明 |
|---|------|------|
| P1 | **SQLite 为 Source of Truth** | Project、Endpoint、TestCase、TestResult 等权威数据存于 SQLite |
| P2 | **Chroma 为语义检索层** | 仅作向量索引与相似度检索，不替代关系型存储 |
| P3 | **Project 为工作空间边界** | 所有 Ask / Plan / Run / 导入操作必须绑定 `project_id` |
| P4 | **模式由 API 显式指定** | Ask / Plan / Run 由前端传 `conversation_mode`，不由意图 LLM 推断 |
| P5 | **文件路径仅用于导入** | `api_doc_file_path` 仅用于工作空间内「导入 OpenAPI」，不作为问答/测试的常规参数 |

### 2.2 数据存储决策

#### 存入 Chroma 的数据

| 优先级 | doc_type | 来源 | 写入时机 | 用途 |
|--------|----------|------|----------|------|
| P0 | `endpoint` | SQLite Endpoint | OpenAPI 解析入库 / 手动增删改后 | Ask RAG、Plan 选接口、Run 语义预筛 |
| P0 | `project` | SQLite Project | 项目创建/更新时 | 项目级问答（「有哪些模块」） |
| P1 | `test_case` | SQLite TestCase | 用例生成或 Run 完成后 | Plan few-shot、Ask 历史用例问答 |
| P1 | `test_summary` | TestResult 聚合 | Run 完成后 | Plan 覆盖失败点、Ask 解释失败原因 |
| P2 | `schema_chunk` | OpenAPI 大段 schema | 按需拆分 | 复杂嵌套结构问答 |

#### 不存入 Chroma 的数据

- 完整 HTTP 响应体、运行时 Cache 变量、用户凭证、全量 OpenAPI 原始文件、实时执行状态。

#### Collection 策略

- 采用 **单一 Collection**（如 `llmtestagent_knowledge`）+ **metadata 过滤**（`project_id`, `doc_type`）；
- 文档 ID 规范：`endpoint:{id}`、`project:{id}`、`test_case:{id}`；
- Endpoint 分块粒度：**一个 endpoint = 一条向量文档**。

### 2.3 对话模式决策

| 模式 | 入口 | 行为 | 是否执行 HTTP |
|------|------|------|---------------|
| **Ask** | `POST /projects/{id}/chat/stream` | 安全审计 → 检索 workspace 知识 → RAG 流式回答 | 否 |
| **Plan** | `POST /projects/{id}/plans`（generate） | 检索 → LLM 生成结构化测试计划 | 否 |
| **Plan** | `POST /projects/{id}/plans/execute`（confirm） | 将计划注入 `AgentState`，复用现有执行链路 | 是 |
| **Run** | `POST /projects/{id}/runs` | 现有 LangGraph 工作流，`project_id` 限定范围 | 是 |

意图识别（`parse_input_node`）继续负责 `run_test` vs `parse_openapi` 及 `single` vs `flow`；**不**将 Ask / Plan 纳入意图 LLM 分类，避免路由冲突。

### 2.4 `api_doc_file_path` 职责收窄

| 场景 | 使用 `api_doc_file_path` | 使用 `project_id` |
|------|--------------------------|-------------------|
| 工作空间内导入 OpenAPI | ✅ | ✅（目标 workspace） |
| Ask 问答 | ❌ | ✅ |
| Plan 生成/确认 | ❌ | ✅ |
| Run 测试 | ❌ | ✅ |
| CLI 一次性解析（兼容） | ✅ | 可选 |

### 2.5 工作空间内知识入口

同一 Project 支持两种 Endpoint 来源，均写入 SQLite 并同步 Chroma：

1. **OpenAPI 导入**：upload + parse 合并为 workspace 内单一动作，返回/更新 `project_id`；
2. **手动维护**：复用现有 Endpoint CRUD API，变更时触发 Chroma upsert/delete。

### 2.6 技术组件决策

| 组件 | 决策 |
|------|------|
| 向量库 | ChromaDB（沿用现有 `ChromaManager` + `langchain-chroma`） |
| Embedding | 新增独立配置，与 LLM Provider 同生态（如 OpenAI `text-embedding-3-small`） |
| 检索 | 新建 `KnowledgeIndexer` + `KnowledgeRetriever`，业务层不直接调用底层 CRUD |
| Agent Tools | 新增 `semantic_search_endpoints` 等 Chroma Tool，补充现有 `db_tools` |
| 降级 | Chroma 不可用时，Ask 回退 SQLite 结构化查询 + 明确提示 |

---

## 3. 目标架构（Target Architecture）

```
┌─────────────────────────────────────────────────────────────┐
│                    Project Workspace (project_id)              │
├─────────────────────────────────────────────────────────────┤
│  知识入口                                                     │
│    ├─ 导入 OpenAPI (api_doc_file_path → parse → SQLite)      │
│    └─ 手动编辑 Endpoint (CRUD → SQLite)                      │
│                          ↓ sync                               │
│                    Chroma Indexer (语义索引)                  │
├─────────────────────────────────────────────────────────────┤
│  交互模式                                                     │
│    ├─ Ask   → Retriever → RAG → LLM Stream                   │
│    ├─ Plan  → Retriever → Plan JSON → 用户确认 → Run         │
│    └─ Run   → LangGraph (select → generate → execute → report)│
└─────────────────────────────────────────────────────────────┘

SQLite = Source of Truth
Chroma = per-project 语义检索
DataCache = run-scoped 执行期变量（不变）
```

---

## 4. 实施阶段（Implementation Phases）

### Phase 0：工作空间闭环（必须先于 Chroma）

- [ ] 统一「导入 OpenAPI 到 workspace」API（upload + parse，返回 `project_id`）
- [ ] Ask / Plan / Run API 均要求 `project_id`
- [ ] 前端：从 project 详情或选择 project 后进入对话/运行页
- [ ] Run 工作流默认限定在当前 `project_id`，减少 LLM 猜项目名
- [ ] 修复 API 层与工作流层 `TestRun` 双 ID 问题，统一 `run_id` 归属

**验收**：在某一 project 内导入文档 → 自然语言测「用户相关接口」→ 查看 run 详情数据一致。

### Phase 1：Ask 模式

- [ ] `POST /projects/{id}/chat/stream`，基于 SQLite 组装上下文（可无 Chroma）
- [ ] 复用 `security_audit_node`
- [ ] 前端传递 `conversation_mode=ask`

**验收**：在工作空间内提问接口参数、测试策略，回答引用该 project 的 endpoint 信息。

### Phase 2：Plan 模式

- [ ] Plan 生成 API 返回结构化计划 JSON
- [ ] 确认后注入 `selected_endpoints`、`test_mode`，跳过或简化 `select_endpoints_agent`
- [ ] 前端展示计划卡片与确认按钮

**验收**：生成计划 → 确认 → 自动执行 → 出报告。

### Phase 3：Chroma 语义层

- [ ] Embeddings 配置与工厂
- [ ] `app.py` lifespan 初始化 Chroma
- [ ] `KnowledgeIndexer` 挂钩解析入库与 Endpoint CRUD
- [ ] Ask / Plan / `select_endpoints` 接入语义检索

**验收**：大项目（50+ 接口）下语义选「用户相关接口」准确，token 消耗可控。

### Phase 4：历史知识增强（可选）

- [ ] 索引 TestCase、TestSummary
- [ ] Plan / Ask 支持「上次怎么测的」「失败原因」类问题

---

## 5. 代码变更范围（Scope of Changes）

### 5.1 新增模块

```
backend/src/core/chroma/
  embeddings.py       # Embedding 工厂
  indexer.py          # 写入/更新/删除索引
  retriever.py        # 统一检索接口
  document_builder.py # Endpoint → 文本 + metadata

backend/src/graph/
  nodes/ask_rag_node.py
  nodes/plan_node.py
  tools/chroma_tools.py

backend/src/prompts/templates/
  ask_rag_system.yaml
  plan_system.yaml
```

### 5.2 修改模块

| 文件 | 变更 |
|------|------|
| `backend/app.py` | lifespan 初始化 Chroma；health check 增加 chroma 状态 |
| `backend/src/core/config.py` | 新增 `EmbeddingConfig` |
| `backend/src/graph/api_doc_storage.py` | 入库后触发索引 |
| `backend/src/graph/state.py` | 增加 `project_id`, `conversation_mode`, `test_plan`, `retrieved_context` |
| `backend/src/api/v1/chat.py` | 重构为 project-scoped Ask（或迁移至新路由） |
| `backend/src/api/v1/workflow.py` | 新增 project-scoped runs/plans；收窄 `api_doc_path` 用途 |
| `backend/src/graph/nodes/select_endpoints_node.py` | 增加语义检索 Tool |
| `backend/src/data/services/endpoint_service.py` | CRUD 后同步 Chroma |
| `frontend/src/pages/run/*.tsx` | 传 `project_id`、`conversation_mode`；按模式调不同 API |

### 5.3 保持不变

- LangGraph 执行链路（`generate_*` → `execute_*` → `generate_report`）
- `security_audit_node` 作为 Ask/Plan 入口前置
- `DataCache` 作为 run-scoped 执行期缓存
- SQLite 表结构（Endpoint 模型已满足需求，无需为 Chroma 改表）

---

## 6. 后果（Consequences）

### 6.1 正面影响

- 产品形态与 Codex 工作空间一致，用户心智清晰；
- Ask / Plan / Run 职责分明，避免「Ask 模式却触发测试」；
- Chroma 有明确数据来源与刷新策略，避免空索引；
- 大项目下语义选接口可显著降低 token 成本与错误率；
- `project_id` 贯穿全链路，支持多项目并行使用。

### 6.2 负面影响与缓解

| 风险 | 缓解措施 |
|------|----------|
| SQLite ↔ Chroma 数据不一致 | 以 SQLite 为准；写入钩子 + 更新/删除同步；提供 reindex API |
| Embedding 额外成本与依赖 | 配置化；可选 provider；Chroma 故障时降级 SQLite |
| 实施范围大 | 严格按 Phase 0→1→2→3 推进，Phase 0 不依赖 Chroma |
| 现有 API 破坏性变更 | 保留旧路由一段时间，标记 deprecated |
| 双 TestRun ID 历史问题 | Phase 0 必须修复，否则 Plan/Run 数据不可信 |

### 6.3 明确不做（Out of Scope）

- Chroma 作为唯一数据存储；
- 用意图 LLM 推断 Ask / Plan / Run；
- 在 Run 流程中每次传递 `api_doc_file_path` 重新解析；
- 本阶段实现完整 Codex 级代码编辑能力（仅 API 测试工作空间）。

---

## 7. 备选方案（Alternatives Considered）

### 7.1 每 Project 一个 Chroma Collection

- **优点**：物理隔离简单；
- **缺点**：Collection 数量随项目增长，运维复杂；
- **结论**：不采纳；采用单 Collection + metadata 过滤。

### 7.2 Ask 直接塞全量 Endpoints 给 LLM（无 Chroma）

- **优点**：实现快；
- **缺点**：大项目 context 溢出，成本高；
- **结论**：Phase 1 小项目可暂用；Phase 3 必须上 Chroma。

### 7.3 全局对话页，不绑定 Project

- **优点**：入口简单；
- **缺点**：多项目混淆，与 workspace 设想冲突；
- **结论**：不采纳。

### 7.4 将 Ask / Plan 纳入 `parse_input_node` 意图

- **优点**：少一个 API 参数；
- **缺点**：与 `run_test` / `parse_openapi` 冲突，路由复杂；
- **结论**：不采纳；由前端显式传 `conversation_mode`。

---

## 8. 待决事项（Open Questions）

> 可执行验证任务见：[001-risks-validation-todo.md](./001-risks-validation-todo.md)

1. OpenAPI 重复导入同一 project：覆盖 vs 合并 vs 新建 version？
2. Plan 确认前是否允许用户编辑计划中的 endpoints 列表？
3. Embedding 模型是否与 LLM 强绑定（如 Bedrock LLM + Bedrock Embedding）？
4. 是否需要 workspace 级对话历史持久化（当前 chat 无 session）？
5. 手动 Endpoint 与 OpenAPI 导入冲突（同 path+method）的处理策略？

---

## 9. 参考（References）

- 现有工作流：`backend/src/workflow.py`
- OpenAPI 入库：`backend/src/graph/api_doc_storage.py`
- Chroma 连接：`backend/src/core/chroma/connection.py`
- 流式对话：`backend/src/api/v1/chat.py`
- 前端模式 UI：`frontend/src/pages/run/workflow-run.tsx`, `security-chat.tsx`
- 系统流程图：`doc/SystemFlowchart.md`

---

## 10. 修订记录（Revision History）

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| 0.1 | 2026-07-07 | — | 初稿：整合 Chroma 评估、工作空间模型、Ask/Plan 设想与实施路线 |
