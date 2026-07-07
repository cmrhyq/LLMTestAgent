# ADR-001 风险验证与待决事项 Todo List

> 关联文档：[001-project-workspace-ask-plan-chroma.md](./001-project-workspace-ask-plan-chroma.md)
> 状态：Open
> 更新：2026-07-07

本文档汇总 ADR-001 方案中**尚未验证或尚未拍板**的事项，按优先级排列。
每项需在 Phase 0 开工前或对应 Phase 启动前完成决策/验证。

---

## P0 — Phase 0 开工前必须拍板

### 1. OpenAPI 重复导入策略

- [ ] **明确同一 Project 内重复导入 OpenAPI 的行为**
  - 选项 A：全量覆盖（同 `path+method` 更新，其余删除）
  - 选项 B：增量合并（仅新增/更新，不删除旧接口）
  - 选项 C：版本化（保留历史版本，当前激活一个）
- [ ] **明确手动 Endpoint 与导入冲突时的优先级**
  - 例如：同 `path+method`，手动编辑 vs 文档导入，谁覆盖谁？
- [ ] **确定 Chroma 同步策略**
  - 覆盖/删除时如何清理旧向量（`endpoint:{id}` 变化场景）
- [ ] **产出**：在 ADR-001 或新 ADR 中写入最终决策，并更新 `api_doc_storage` 设计说明

**不拍板的风险**：workspace 闭环 API、Chroma 文档 ID、Ask/Plan 上下文范围全部可能返工。

---

### 2. 验证双 TestRun ID 问题

- [ ] **端到端复现**：调用 `POST /workflows/run/test` → 等待完成 → 对比两个 ID
  - API 层返回的 `run_id`（`workflow.py` 创建）
  - 工作流内 `generate_*_cases_node` 创建的 `run_id`
- [ ] **检查前端跳转的 `/runs/{id}` 是否包含真实 TestCase / TestResult**
- [ ] **检查 API 层 `TestRun` 创建时缺少 `project_id` 是否导致 DB 异常**
- [ ] **若问题成立，确定修复方案**
  - 方案 A：API 只创建占位 run，工作流内复用同一 `run_id`
  - 方案 B：取消 API 预创建，由工作流创建后回写
- [ ] **产出**：问题确认记录 + 修复任务纳入 Phase 0

**不验证的风险**：Run/Plan 执行结果与 UI 展示可能长期不一致。

---

## P1 — Phase 0 / Phase 1 启动前需定稿

### 3. Embedding Provider 选型与切换规则

- [ ] **决定 Embedding 是否与 LLM Provider 绑定**
  - 绑定：体验一致，换 LLM 需 reindex
  - 解耦：固定一个 Embedding（如 OpenAI），LLM 可随意切换
- [ ] **评估各 Provider 的 Embedding 可用性与成本**
  - OpenAI `text-embedding-3-small`
  - Bedrock Titan / Cohere Embed
  - 智谱 / 千问（若有使用计划）
- [ ] **定义换 Embedding 模型时的 reindex 流程**
- [ ] **产出**：`EmbeddingConfig` 设计稿 + 写入 ADR 或 ADR-002

**不定稿的风险**：Phase 3 上 Chroma 后索引与查询可能不兼容，或合规/成本踩坑。

---

### 4. Plan 模式交互与计划 Schema

- [ ] **确认 Plan 是「只确认」还是「可编辑后确认」**
- [ ] **定义测试计划 JSON 最小字段集**
  - 建议字段：`test_mode`, `endpoints[]`, `scenarios[]`, `priority`, `environment_id?`, `rationale`
- [ ] **确认 Plan 执行失败时的回退策略**
  - 计划注入 `selected_endpoints` 后是否允许 Agent 二次校验？
- [ ] **设计前端 Plan 确认 UI 线框（计划卡片 + 编辑 + 执行按钮）**
- [ ] **产出**：Plan API 请求/响应草案 + 前端交互说明

**不定稿的风险**：Phase 2 前后端联调反复改接口；计划选错接口在执行阶段才暴露。

---

## P2 — Phase 1 / Phase 3 前需验证的假设

### 5. Phase 1「无 Chroma、仅 SQLite」的适用边界

- [ ] **统计典型 Project 的 Endpoint 数量分布**（小/中/大）
- [ ] **抽样 3～5 个复杂 Endpoint**，估算拼进 prompt 的 token 量
- [ ] **定义 Phase 1 的明确上限**
  - 例如：Endpoint ≤ 20 且单接口 JSON < 2KB 时可用 SQLite-only
- [ ] **定义超出上限时的产品行为**（提示用户等待 Chroma / 仅回答摘要）
- [ ] **产出**：Phase 1 Ask 降级策略文档

**不验证的风险**：Ask 在大项目上 context 溢出或回答质量差，误以为 Ask 模式「不可用」。

---

### 6. Agent + 语义 Tool 是否比现状更可靠

- [ ] **收集 10～20 条真实用户测试指令**（或团队自拟代表样本）
- [ ] **对比基线**：仅 `get_project_endpoints` 全量 vs 语义 top-k + LLM
- [ ] **定义成功指标**
  - 接口召回率（该选的选到了吗）
  - 误选率
  - 平均 token / 延迟
- [ ] **决定 Phase 3 是否采用「语义预筛 + Agent 精选」或「确定性检索 + 轻量 LLM」**
- [ ] **产出**：小规模评测记录（表格即可）

**不验证的风险**：加了 Chroma Tool 后 Agent 行为仍不可控，投入产出比不明。

---

## P3 — 产品化过程中逐步澄清

### 7. Workspace 是否需对话历史持久化

- [ ] **确认 Ask/Plan 是否需要跨会话记忆**（同 project 内）
- [ ] **若需要，决定存储位置**（SQLite 新表 vs 仅前端 session）
- [ ] **产出**：需求结论（要 / 不要 / 二期）

---

### 8. `security_audit_node` 对 Ask 的性价比

- [ ] **测量单次 Ask 增加的安全审计延迟与 token 成本**
- [ ] **评估 workspace 内 Ask 是否可降级为规则过滤 + 轻量审计**
- [ ] **产出**：Ask 入口审计策略（保持 / 简化 / 可配置）

---

### 9. 前端入口统一

- [ ] **梳理当前三个入口的职责重叠**
  - `workflow-run.tsx`
  - `security-chat.tsx`
  - `project-detail.tsx`
- [ ] **决定目标形态**：是否以 `projects/:id` 为唯一工作空间入口
- [ ] **产出**：前端路由与页面合并方案

---

## 建议执行顺序（总览）

```
Week 0（拍板）
  ├─ #1 OpenAPI 重复导入策略
  ├─ #2 双 TestRun ID 验证
  └─ #3 Embedding 选型

Week 1（设计）
  ├─ #4 Plan 模式 Schema + UI
  └─ #9 前端入口统一方案

Phase 1 前（验证）
  ├─ #5 SQLite-only Ask 边界
  └─ #8 安全审计性价比

Phase 3 前（验证）
  └─ #6 Agent + 语义 Tool 评测

按需
  └─ #7 对话历史持久化
```

---

## 完成定义（Definition of Done）

- [ ] P0 两项均有书面决策或验证结论
- [ ] P1 两项均有 API/配置草案
- [ ] P2 两项均有实测数据或明确「接受风险」的记录
- [ ] 结论已回写 ADR-001 或衍生 ADR（002、003…）
- [ ] 相关结论已同步到 Phase 0 任务拆分（Issue / 看板）

---

## 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 0.1 | 2026-07-07 | 初稿：汇总 ADR-001 方案中的不确定项与验证任务 |
