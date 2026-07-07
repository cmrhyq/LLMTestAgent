# 设计变更日志（Design Changelog）

本文件记录 **LLMTestAgent 架构与产品设计** 的变更历史，面向 ADR、流程图、数据模型、API 契约等产品/技术设计文档。

> 代码与依赖发布变更见项目根目录 [`CHANGELOG.md`](../CHANGELOG.md)。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
设计状态标签：`Proposed`（提议中）· `Accepted`（已采纳）· `Implemented`（已实现）· `Superseded`（已取代）

---

## [Unreleased]

### Proposed

- **ADR-001**：引入 Project 工作空间模型（每个 Project = 一个 Codex 式 workspace）
  - 文档：[adr/ADR_001_project-workspace-ask-plan-chroma.md](./adr/ADR_001_project-workspace-ask-plan-chroma.md)
  - 状态：`Proposed`
- **对话模式 Ask / Plan / Run**：三种 `conversation_mode`，由 API 显式指定，不纳入意图 LLM 分类
  - Ask：RAG 问答，不执行 HTTP
  - Plan：生成测试计划 → 用户确认 → 执行
  - Run：现有 LangGraph 测试工作流
- **Chroma 语义检索层**：SQLite 为 Source of Truth，Chroma 仅作 per-project 向量索引
  - Collection 策略：单 Collection + `project_id` / `doc_type` metadata 过滤
  - 索引优先级：endpoint（P0）→ test_case / test_summary（P1）
- **API 边界调整（拟议）**：
  - `api_doc_file_path` 收窄为「工作空间内导入 OpenAPI」专用
  - Ask / Plan / Run 改为 `project_id` 驱动
  - 新增拟议路由：`/projects/{id}/chat/stream`、`/projects/{id}/plans`、`/projects/{id}/runs`
- **实施分阶段路线**：Phase 0（工作空间闭环）→ Phase 1（Ask）→ Phase 2（Plan）→ Phase 3（Chroma）→ Phase 4（历史知识）
- **风险验证清单**：ADR-001 待决事项与验证任务
  - 文档：[adr/ADR_001_risks-validation-todo.md](./adr/ADR_001_risks-validation-todo.md)

### Changed（设计层面，待实现）

- `doc/` 目录结构重组：
  - 设计文档迁入 `doc/design/`（系统流程图、数据库设计、ER 图）
  - 架构决策记录迁入 `doc/adr/`
  - 图示资源集中于 `doc/images/`

### Open Questions

以下事项已在 ADR-001 中标记为待决，变更落地前需拍板：

| # | 事项 | 阻塞阶段 |
|---|------|----------|
| 1 | 同一 Project 重复导入 OpenAPI：覆盖 / 合并 / 版本化 | Phase 0 |
| 2 | 手动 Endpoint 与导入文档冲突时的优先级 | Phase 0 |
| 3 | Embedding Provider 是否与 LLM Provider 绑定 | Phase 3 |
| 4 | Plan 模式：仅确认 vs 可编辑后确认 | Phase 2 |
| 5 | Ask 对话历史是否跨会话持久化 | 待定 |

---

## [0.2.0] - 2026-07-07

### Added

- 新增 **ADR-001**：Project 工作空间、Ask/Plan 对话模式与 Chroma 语义检索（`Proposed`）
- 新增 **ADR-001 风险验证 Todo List**：汇总方案中不确定项与验证任务
- 新增本文件 `doc/CHANGELOG.md`（设计变更日志）

### Documented（现状分析写入 ADR）

- 记录当前实现与产品设想之间的差距：
  - 前端 `upload` / `parse` / `run` 三条路径未统一
  - Ask / Plan 仅前端 UI 占位，后端未实现
  - `ChromaManager` 已实现但未接入业务，缺少 Embeddings 配置
  - `api_doc_path` 在 chat 接口中被忽略
  - 缺少显式 `project_id` 作为工作空间锚点
- 识别待验证技术风险：API 层与工作流层 `TestRun` 双 ID 问题

---

## [0.1.0] - 2026-06-15

### Added

- **Monorepo 产品设计**：前后端分离，`backend/`（FastAPI + LangGraph）+ `frontend/`（React 19）
- **系统主流程设计**（[design/SystemFlowchart.md](./design/SystemFlowchart.md)）：
  - 意图识别分流：`parse_openapi` | `run_test`
  - 测试模式：`single`（单接口）| `flow`（业务流程）
  - Agent Tool Loop：`search_project` → `get_project_endpoints` → LLM 选接口
  - 执行链路：生成用例 → HTTP 执行 + 断言 → HTML 报告
- **数据库设计**（[design/DatabaseDesign.md](./design/DatabaseDesign.md)）：
  - SQLite 3 + SQLAlchemy 2.0
  - 核心实体：Project、Environment、Endpoint、TestRun、TestCase、TestResult、Report
  - Project 作为接口与测试运行的顶层容器
- **ER 拓扑图**（[design/ER.md](./design/ER.md) + `images/`）
- **流式对话设计**（安全审计 + API 测试问答）：
  - `POST /api/v1/chat/stream`
  - 前置 `security_audit_node` 拦截非测试内容与安全风险
- **ChromaDB 连接层设计**（`ChromaManager`，配置项 `ChromaConfig`）：
  - HttpClient 单例、Collection/文档 CRUD、LangChain VectorStore 集成
  - 状态：基础设施就绪，**未定义业务索引与检索策略**

### Changed

- 移除 CLI 入口设计，统一为 FastAPI REST API 触发工作流
- CORS 改为环境变量配置，适配前端开发服务器

### Deprecated（设计意图，尚未完全收敛）

- `api_doc_file_path` 原设计仅服务于 `parse_openapi` 分支；前端引入后职责边界模糊，待 ADR-001 收窄

---

## [0.0.1] - 2026-05-28

### Added

- **初始架构设想**：
  - 自然语言驱动 API 自动化测试
  - LangGraph 有状态工作流编排
  - OpenAPI 解析入库 → 基于 DB 的接口挑选与用例生成
  - 多 LLM Provider 支持（OpenAI、Bedrock、智谱、千问）
- **Prompt 模板体系**：意图分类、接口挑选、单接口/流程用例生成、安全审计
- **测试执行设计**：`CacheResolver` 步骤间变量传递、`AssertionEngine` 断言评估

---

## 变更类型说明

| 类型 | 含义 |
|------|------|
| **Added** | 新增设计、文档、ADR、API 契约 |
| **Changed** | 已有设计发生变更 |
| **Deprecated** | 计划废弃但尚未移除的设计 |
| **Removed** | 已从设计中移除 |
| **Proposed** | 提议中、未采纳（`Unreleased` 区） |
| **Implemented** | 设计已落地到代码（需在对应版本注明） |
| **Documented** | 对现状的梳理记录，不一定是新设计 |

---

## 与其他文档的关系

```
doc/
├── CHANGELOG.md          ← 本文件（设计变更日志）
├── adr/                  ← 架构决策记录（ADR）
│   ├── ADR_001_*.md
│   └── ...
└── design/               ← 详细设计文档
    ├── SystemFlowchart.md
    ├── DatabaseDesign.md
    └── ER.md

CHANGELOG.md（根目录）    ← 代码发布变更日志
```

新增 ADR 或重大设计变更时，请同步更新本文件 `Unreleased` 区，采纳后归入版本号条目。

---

## 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 0.1 | 2026-07-08 | 初稿：建立设计变更日志，回溯至初始架构，记录 ADR-001 |
