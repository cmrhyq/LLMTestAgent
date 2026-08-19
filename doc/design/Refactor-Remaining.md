# LLMTestAgent 剩余重构清单

> 版本：v1.0（2026-08-19）
> 对应代码：阶段 0 / 阶段 1 已落地之后的仓库现状
> 定位：只记录 **尚未改动** 的重构项。已完成工作见文末「已完成对照」。
> 与其他文档关系：当前实现总览见 [Architecture.md](./Architecture.md)；产品演进见 [ADR-001](../adr/ADR_001_project-workspace-ask-plan-chroma.md)。

---

## 〇、怎么读这份文档

- **阶段 0（修 bug）和阶段 1（消重复）已完成**，不要再按旧计划重做那两段。
- 下文从 **阶段 2** 起，每一项都给出：目标、当前代码证据、建议改法、验收方式。
- 行号会随后续提交漂移，以文件路径和符号名为准。
- 原则不变：小步提交、先契约后拆分、每阶段绿灯再进入下一阶段。

### 依赖关系

```
阶段2(分层契约) ──┬──→ 阶段3(工作流结构化)
                  └──→ 阶段4(核心层拆分) ──→ 阶段6(枚举与收尾)
阶段5(前端) 可与 2/3/4 并行
```

阶段 2 是关键路径：3、4 都假设「Service 是业务入口、Repository 只做存取」。

---

## 阶段 1 遗留：已抽出、尚未被调用方吃掉

阶段 1 已经把工具造好了，但部分调用方仍走旧路径。这些 **不算新功能**，建议在阶段 2 顺手切过去，避免基础设施闲置。

| 已有能力 | 现状 | 建议 |
|----------|------|------|
| `BaseRepository.paginate / update_fields / exists`（`backend/src/data/repositories/base.py`） | API 路由仍 `get_all(limit=1000)` + 内存 filter/slice，更新仍手写 `setattr` | 阶段 2.5 / 2.7 改为走这些方法 |
| `RunScopedRepositoryMixin.get_by_run / count_by_run` | `TestCase` / `TestResult` / `Report` 已继承；Graph 节点仍直接 new Repository | 阶段 2.6 改为走 Service |
| `src.utils.db_bootstrap.ensure_db` | `graph/tools/db_tools.py` 仍有一份 `_ensure_db_initialized()`（约 18–30 行） | 删除本地副本，改 import |
| `src.utils.json_utils.safe_json_loads` | `generate_report_node._format_json` 仍本地 `json.loads` | 改为共用解析 |
| `graph/nodes/utils.py`、`utils/llm_utils.py` | 仅 re-export，节点仍从 `graph.nodes.utils` 导入 | 阶段 3 节点改直连 `utils.*` 后可删 shim |
| 前端 `lib/format.ts` | `format-relative-time.ts` 仍独立文件；`report-view.tsx` 统计卡片仍内联 `toFixed(1) + "ms"/"s"` | 阶段 5 收口 |
| 前端 `PaginatedResponse<T>` | 后端已有；`frontend/src/lib/types.ts` 仍手写 6 份 list 类型 | 阶段 5.6 |

---

## 阶段 2：确立分层契约（3–5 天）

> 核心目标：**Service 成为唯一业务入口**；Repository 只做 SQL；API / Graph / Tools 禁止直接 new Repository。

### 现状判断

当前 Service 层几乎是「一行转发」：

- `ProjectService` 只有 `create_project` → `repo.find_or_create`（`backend/src/data/services/project_service.py`）
- `TestCaseService` / `TestResultService` / `ReportService` / `TestRunService` 同样只包一层 Repository
- **没有** `TestSummaryService`（`test_summary_repository.create_or_update` 仍把 upsert 业务放在 DAO）
- API 路由直接操作 Repository，例如：
  - `api/v1/project.py`、`environment.py`、`endpoint.py`、`conversation.py`、`test_run.py`、`report.py`
- Graph 节点直接操作 Repository，例如：
  - `generate_single_cases_node.py` / `generate_flow_cases_node.py`（一次打开 4 个 repo）
  - `execute_single_tests_node.py` / `execute_flow_tests_node.py`
  - `generate_report_node.py`
- `graph/tools/db_tools.py` 绕过 Repository，裸写 `select(Project)` / `select(Endpoint)`

### 2.1 新建 `BaseService`

**新建** `backend/src/data/services/base_service.py`

建议形态：

```python
class BaseService(Generic[TModel, TCreate, TUpdate]):
    def get(self, id: int) -> TModel | None: ...
    def get_or_raise(self, id: int) -> TModel: ...  # 抛业务异常，不抛 HTTPException
    def list(self, page, page_size, *filters) -> tuple[list[TModel], int]: ...
    def create(self, data: TCreate) -> TModel: ...
    def update(self, id: int, data: TUpdate) -> TModel: ...
    def delete(self, id: int) -> None: ...
```

约束：

- Service **不** `commit()`，事务仍由 `get_db` / `get_session` 上下文管理。
- 404/409 用业务异常（见 4.6），路由层再转 HTTP。阶段 2 若 4.6 未做，可暂在 Service 抛 `ValueError`/`LookupError`，路由捕获；但不要在 Service 里 `raise HTTPException`。

### 2.2 透传 Service 改为继承

把现有「纯转发」Service 收成 `BaseService` 子类，去掉样板：

| 文件 | 现状 | 改后应承担的业务 |
|------|------|------------------|
| `project_service.py` | 仅 `create_project` | 列表筛选、重名 409、级联删除、字段更新 |
| `environment_service.py` | 透传 | 按 `project_id` 列表、默认环境规则、更新 |
| `endpoint_service.py` | 透传 | 查重、JSON 字段序列化、按项目分页 |
| `test_run_service.py` | `update_status` 仍转 repo | 状态机 + 时间戳策略（从 repo 上移） |
| `test_case_service.py` | 透传 | 按 run 查询、启用态过滤 |
| `test_result_service.py` | 透传 | 按 run / status 查询 |
| `report_service.py` | 透传 | 按 run 查询、下载路径校验 |
| `conversation_service.py` | 已有部分业务 | 补列表分页、更新、删除；消息查询 |

同步更新 `data/services/__init__.py`。

### 2.3 把误放在 Repository 的业务上移

| 当前位置 | 问题 | 目标 |
|----------|------|------|
| `ProjectRepository.find_or_create` | 「找不到就创建」是业务决策 | `ProjectService.find_or_create`；Repository 只留 `get_by_name` + `add` |
| `EnvironmentRepository.find_or_create` | 同上 | `EnvironmentService` |
| `TestSummaryRepository.create_or_update`（约 35 字段赋值） | upsert + 统计写入是业务 | **新建** `TestSummaryService.create_or_update` |
| `TestRunRepository.update_status` | `running` 写 `started_at`、终态写 `finished_at`，且时间格式与 `local_now()` 不一致 | 策略放到 `TestRunService.update_status`；repo 只 `update_fields` |
| `ProjectRepository.delete_cascade` | 可保留在 repo（ORM 级联加载），但「是否允许删」由 Service 决定 | Service 调 `delete_cascade`，路由不再直接碰 repo |

### 2.4 Repository 瘦身规则

完成后 Repository 只允许：

- CRUD / 条件查询 / 分页 / exists
- 不写 if-status-then-timestamp
- 不 `commit()`
- 不拼业务校验（重名、默认环境互斥等）

阶段 2 结束时用 grep 验收：

```text
backend/src/api        不应出现 from src.data.repositories
backend/src/graph/nodes 不应出现 from src.data.repositories
backend/src/graph/tools  不应出现 sqlalchemy.select / 直接 Session 查表
```

允许 Repository 出现的位置：`data/services/*`、`data/repositories/*`、测试。

### 2.5 API 路由全部改走 Service

每个路由现在都是「new repo → 内存过滤 / setattr / HTTPException」。逐文件改造：

#### `api/v1/project.py`

| 端点 | 当前问题 | 改后 |
|------|----------|------|
| `POST /` | 路由里查重 + `Project(**body.model_dump())` | `ProjectService.create`（重名抛冲突） |
| `GET /` | `get_all(1000)` + 内存 keyword/status + slice | `ProjectService.list(...)` → SQL `paginate` |
| `GET /{id}` | repo.get_by_id + 404 | Service.get_or_raise |
| `PUT /{id}` | 手写 setattr | `Service.update` → `repo.update_fields` |
| `DELETE /{id}` | 直接 `delete_cascade` | Service.delete |

#### `api/v1/environment.py` / `endpoint.py`

模式相同。`endpoint.py` 更新时对 JSON 字段 `json.dumps`（约 103 行），这是序列化规则，必须进 `EndpointService.update`，不要留在路由。

`endpoint.py:36` 仍有 **内联 import** `EndpointService`，阶段 2 一并改为文件顶部导入（项目规则禁止函数体内 import，循环依赖除外）。

#### `api/v1/conversation.py`

已混用 `ConversationService` 与裸 `ConversationRepository` / `MessageRepository`。统一只依赖 Service。

#### `api/v1/test_run.py`

`GET /` 同样 `get_all(1000)` 内存分页（约 102 行）。改为 `TestRunService.list(project_id, status, page, page_size)`。

#### `api/v1/report.py`

同时 new 三个 Repository（report / test_run / test_result）。详情组装（报告 + 批次 + 结果）是业务，放 `ReportService.get_detail`。

#### `api/v1/chat.py`（部分）

已用 `ConversationService`，但仍直接 `MessageRepository`（约 101 行）。阶段 2 先把落库改走 Service；完整拆分（审计+流式）留给 4.1。

### 2.6 Graph 节点 / Tools 改走 Service

| 文件 | 当前 | 改后节点只做 |
|------|------|----------------|
| `generate_single_cases_node.py`（~227 行） | 打开 4 个 repo；创建 TestRun；逐条 add TestCase | 调 `TestRunService.create_running_run` + `CaseGenerationService.persist_cases` |
| `generate_flow_cases_node.py`（~180 行） | 与 single 前 80 行几乎相同 | 共用上述 Service；节点只换 PromptBuilder |
| `execute_single_tests_node.py` | TestCaseRepository + TestRunRepository.update_status | `TestCaseService.get_active_cases_by_run` + `TestRunService` |
| `execute_flow_tests_node.py` | 同上 | 同上 |
| `generate_report_node.py`（~336 行） | 三个 repo + 内联 HTML | 阶段 2 先改数据访问；HTML 外置放到 3.6 |
| `parse_openapi_node.py` | 若仍碰 repo，改为 Endpoint/Project Service | 编排解析器 + Service.bulk_upsert |
| `graph/tools/db_tools.py` | 裸 SQLAlchemy + 本地 `_ensure_db_initialized` | `ProjectService.search` / `EndpointService.list_active`；`ensure_db` 用 `utils.db_bootstrap` |

节点里不要 `TestCase(...)` 再 `repo.add`。构造 ORM 对象属于 Service。

### 2.7 内存分页下推 SQL

当前反模式（全部在路由层）：

| 文件 | 调用 |
|------|------|
| `project.py:41` | `get_all(limit=1000)` |
| `environment.py:41` | `get_all(limit=1000)` |
| `endpoint.py:58` | `get_all(limit=5000)` |
| `test_run.py:102` | `get_all(limit=1000)` |
| `report.py:111` | `get_all(limit=1000)` |

改法：Service 把 keyword/status/`project_id` 编成 SQL filter，调 `BaseRepository.paginate(page, page_size, *filters)`。keyword 用 `ilike`/`contains`，不要先拉全表。

`get_all(1000)` 作为内部调试方法可保留，但 **禁止** 出现在 API 热路径。

### 阶段 2 验收

- 全量 API 冒烟：项目/环境/接口 CRUD、会话、测试运行列表、报告详情。
- grep 规则见 2.4。
- 列表超过 20 条时分页 `total` 仍正确（证明不再用当前页 length）。
- 更新项目/接口后字段持久化（证明 `update_fields` 被用上）。

---

## 阶段 3：工作流层结构化（3–5 天）

> 依赖阶段 2。目标：State 类型化、路由表化、节点变薄、消除 single/flow 复制。

### 3.1 重构 `graph/state.py`

当前 `AgentState`（`backend/src/graph/state.py`）：

```text
current_step, raw_input, api_doc_file_path, user_intent, test_mode,
selected_endpoints: list[dict], endpoint_count,
test_results: list[dict],      # 死字段：节点已不往这里写执行结果
test_summary: dict,            # 死字段：与 test_results_summary 重复
run_id, test_cases_count, test_results_summary, report_path, error_message
```

问题：

1. `selected_endpoints` 是 `list[dict[str, Any]]`，调用方靠字符串键（`project_id` / `endpoint_id`）。
2. `task_complexity_node` 返回 `selected_model` / `complexity_level`，**State 未声明**。
3. `security_audit_node` 返回的审计结果未进入 State 类型。
4. `current_step` 身兼「下一跳节点名」和「运行状态」（含 `"error"`）。

建议拆分：

| 字段 | 类型 | 说明 |
|------|------|------|
| `next_node` | 枚举/Literal | 仅路由用 |
| `run_status` | `TestStatus` 或独立枚举 | pending/running/completed/failed |
| `SelectedEndpoint` | `TypedDict` | `endpoint_id`, `project_id`, `path`, `method`, … |
| `test_results_summary` | `TypedDict` | total/passed/failed/skipped/error |
| `complexity_level` / `selected_model` | 可选 str | 若节点接入图才保留 |
| 删除 | `test_results`, `test_summary` | 确认无读写后删，并改 `workflow.py` 初始 state |

同步改 `workflow.py` 初始字典，避免漏字段。

### 3.2 魔法字符串枚举化

新建 `graph/constants.py`，或复用 `data/enum/workflow.py` 并补工作流专用枚举：

| 散落点 | 字面量 | 应收拢为 |
|--------|--------|----------|
| `route.py:23-25` | `"parse_openapi"` / `"run_test"` | `UserIntent` |
| `route.py:38-40` | `"flow"` / `"single"` | `TestMode` |
| `parse_input_node.py` `_VALID_TEST_MODES` | `("single", "flow")` | 同一枚举 |
| 各节点 `current_step: "error"` | `"error"` | `next_node=ERROR` |
| `execute_*` `update_status(..., "running")` | `"running"` 等 | `TestStatus` |
| `workflow.py` `add_node("generate_single_cases", ...)` | 节点名字符串 | `NodeName` 枚举，build_graph 引用枚举值 |

`Project.status == 1` 这类数据状态放到阶段 6 与 `DataStatus` 对齐，阶段 3 先解决工作流字符串。

### 3.3 路由注册表化

当前 `route.py` 是 if/else，`workflow.py` 手写全部 `add_edge`。

建议：

```python
INTENT_ROUTES = {
    UserIntent.PARSE_OPENAPI: NodeName.PARSE_OPENAPI_DOC,
    UserIntent.RUN_TEST: NodeName.SELECT_ENDPOINTS,
}

TEST_MODE_ROUTES = {
    TestMode.SINGLE: (NodeName.GENERATE_SINGLE_CASES, NodeName.EXECUTE_SINGLE_TESTS),
    TestMode.FLOW: (NodeName.GENERATE_FLOW_CASES, NodeName.EXECUTE_FLOW_TESTS),
}
```

`build_graph()` 从注册表生成条件边。新增一种 intent / test_mode 时只改表，不改一长串 if。

### 3.4 抽 `BaseCaseGenerationNode` + `finalize_test_run()`

`generate_single_cases_node` 与 `generate_flow_cases_node` 重复约 80%：

- 读 `selected_endpoints`、空列表走 error
- `ensure_db`、按 `project_id` 取项目、`get_active_by_ids`
- 创建 `TestRun(name=LLM测试-{timestamp}, status=running, ...)`
- 调 LLM → `parse_llm_json_response` → 构造 `TestCase` → `add_many`

差异只有：PromptBuilder、是否按接口循环、case_id 规则。

建议：

1. `CaseGenerationService.create_run_and_persist(cases)` 承接 ORM/DB。
2. 节点模板方法：`validate_state` → `load_endpoints` → `invoke_llm` → `persist`。
3. `finalize_test_run()` 供 execute 节点写 statistics / finished_at（single 与 flow 的收尾也重复）。

### 3.5 节点瘦身

节点目标行数：编排 < 80 行。下沉方向：

| 逻辑 | 目标模块 |
|------|----------|
| LLM 调用 + JSON 解析 | 已有 `json_utils`；再抽 `CaseGenerationService.generate_for_endpoints` |
| HTML 报告渲染 | 3.6 `ReportRenderer` |
| 写 `reports/` 目录 + DB 记录 | `ReportStorage` / `ReportService.save` |
| HTTP 执行 + 断言 | 已在 `TestExecutor`，保持；节点只循环调用 |

### 3.6 `generate_report_node` 内联 HTML 外置

`generate_report_node.py`（~336 行）后半是字符串拼接 HTML：`_esc` / `_status_badge` / `_method_badge` / `_detail_block` / `_result_details` 以及整页 CSS。

改法：

- 新建 `backend/src/graph/report/templates/report.html.j2`（或 `backend/src/prompts/templates/` 旁独立 `report/`）
- Python 只准备 context dict，Jinja2 渲染
- `_format_json` 改用 `safe_json_loads` + `json.dumps`

### 3.7 游离节点

| 节点 | 现状 | 决策（二选一，需在本阶段拍板） |
|------|------|--------------------------------|
| `task_complexity_node` | 导出在 `graph/nodes/__init__.py`，**未**加入 `build_graph()`；写入未声明的 `complexity_level` / `selected_model` | A. 接到 parse_input 之后，按复杂度换模型；B. 从 exports 移除，标为实验代码 |
| `security_audit_node` | 不在测试工作流图里，由 `api/v1/chat.py` 作为前置守卫调用 | 保持「API 前置守卫」，不要塞进 `build_graph`；文档/命名标明不是图节点 |
| `start_node` / `end_node` / `error_node` | 在图中 | 保留；error 与 `next_node` 枚举对齐 |

### 阶段 3 验收

- 跑通 **single** 与 **flow** 两条链路（解析 → 选接口 → 生成 → 执行 → 报告）。
- `AgentState` 无未声明字段；无死字段。
- 新增 test_mode 只需改注册表（可用单测断言映射完整性）。

---

## 阶段 4：核心层与超长文件拆分（3–4 天）

> 可与阶段 3 部分并行，但 4.1/4.2 依赖阶段 2 的 Service。

当前超长文件（行数，含空行）：

| 行数 | 文件 |
|------|------|
| ~723 | `backend/src/utils/parser/openapi_parser.py` |
| ~457 | `backend/src/utils/http/request.py` |
| ~417 | `backend/src/core/llm/llm_client.py` |
| ~336 | `generate_report_node.py`（阶段 3.6 处理） |
| ~212 | `backend/src/core/config.py` |
| `chat.py` / `workflow.py` | 路由里塞满业务 |

### 4.1 `chat.py` → `ChatStreamService`

`api/v1/chat.py` 同时做：审计调用、拦截文案、系统 prompt、流式 SSE、会话创建、消息落库、`X-Conversation-Id`。

拆分：

| 内容 | 去向 |
|------|------|
| `_SECURITY_RISK_MESSAGE` / `_NON_TESTING_MESSAGE` / `_AUDIT_ERROR_MESSAGE` / `_ASSISTANT_SYSTEM_PROMPT` | `prompts/templates/`（yaml 或 md） |
| 审计 + 分流 + 落库 + 流式 | `data/services/chat_stream_service.py`（或 `src/chat/`） |
| 路由 | 只负责校验 body、返回 `StreamingResponse` |
| `MessageRepository` 直访 | 改为 ConversationService / MessageService |
| `get_db_manager().get_session()` | 与其它 API 一样走 `Depends(get_db)`，避免两套会话入口 |

现有测试 `tests/api/v1/test_chat_stream.py`、`tests/graph/node/test_security_audit_node.py` 必须跟着改 mock 路径。

### 4.2 `api/v1/workflow.py` 下沉

- OpenAPI 上传 / 解析编排 → `OpenAPIUploadService` / `WorkflowService`
- 内联 `from src.workflow import TestWorkflow`（约 82 行）改为顶部 import
- 去掉未使用的 `Depends(get_db)`（若仍存在）
- 路由保持薄：收文件、调 Service、返回 schema

### 4.3 拆 `config.py`

`backend/src/core/config.py`（~212 行）已含 LLM / DB / Server 等多个模型。建议按域拆文件：

```text
core/config/
  __init__.py      # get_config / load_config
  app.py           # AppConfig 聚合
  llm.py           # provider 子配置 + Literal["openai","bedrock","zhipu","qwen","deepseek"]
  database.py
  server.py        # CORS、端口；snowflake worker 配置收进来
```

注意：阶段 0 已删除 `case_generation`，**不要**再加回该配置块。场景类型已写死在 `single_case_user.yaml`。

### 4.4 拆超长实现文件

**OpenAPI parser**（`openapi_parser.py` ~723）→

- `loader.py`：读文件 / URL / yaml-json
- `schema.py`：`$ref` 展开、schema 归一
- `endpoint.py`：path/method → Endpoint 字典
- 门面 `OpenAPIParser.parse()` 保持原入口，避免一次改光调用方

**HTTP request**（`http/request.py` ~457）→

- UA / 头构造
- 重试策略（独立可测）
- `HttpRequest` 只负责发请求

**LLM client**（`llm_client.py` ~417）→

- `providers/openai.py` 等工厂
- `llm_client.py` 只做统一 `chat` / `achat_stream` 接口
- 顶部 import 替换函数内 `import ChatOpenAI` 等（若仅为可选依赖，用 lazy 工厂模块而不是散落在方法里）

### 4.5 Prompt builder 合并

现有 builder：

- `base.py`
- `case_builder.py` / `flow_case_builder.py`
- `intent_builder.py`
- `select_endpoints_builder.py`
- `task_complexity_builder.py`
- `system_safety.py`

方向：一个参数化 `PromptBuilder(template_name, context)`，模板全走 Jinja2。single/flow 只换 yaml，不换 Python 类。`formatters/` 只保留纯数据格式化。

### 4.6 全局异常 + 业务错误

各路由重复：

```python
if x is None:
    raise HTTPException(status_code=404, detail="...不存在")
```

建议：

- `src/core/errors.py`：`NotFoundError` / `ConflictError` / `ValidationError`
- FastAPI `exception_handler` 映射到 404/409/422
- Service `get_or_raise` 抛 `NotFoundError`
- 路由不再手写 HTTPException（输入校验除外）

### 阶段 4 验收

- `pytest`（至少 chat stream、llm_utils、openapi 相关）
- `/chat/stream`、`/workflows/parse/openapi` 手工冒烟
- 单文件原则上 < 400 行（parser 拆完后门面除外）

---

## 阶段 5：前端结构整理（3–4 天，可与后端并行）

阶段 1 已完成：`query-keys.ts`、`create-crud-hooks.ts`、`format.ts`。下面是 **页面与类型** 层未做的部分。

### 5.1 目录拼写

`frontend/src/pages/poject/` → `pages/project/`

同步：

- `frontend/src/router.tsx` 约 25 行：`import("./pages/poject/project-detail.tsx")`
- 其它相对/绝对引用
- 保留 301 意义不大（SPA），直接改路径即可

### 5.2 拆 `project-detail.tsx`（~399 行）

建议结构：

```text
pages/project/project-detail.tsx          # 容器：读路由、拉数、Tab
hooks/use-project-detail-page.ts          # 三个 list query + 删除确认状态
pages/project/tabs/endpoints-tab.tsx
pages/project/tabs/environments-tab.tsx
pages/project/tabs/test-runs-tab.tsx
pages/project/columns.ts                  # DataTable Column 定义
```

列定义里的 `formatDate` / `formatDuration` 已在阶段 1 接入，拆文件时保持引用。

### 5.3 拆 `report-view.tsx`（~363 行）

已有内部组件雏形：`ResponseTimeStats`、`ExpandableRow`。提到独立文件：

- `components/report/response-time-stats.tsx`
- `components/report/test-results-table.tsx`
- `components/report/http-payload-panel.tsx`
- `lib/stats.ts`：avg/min/max/p95（现在写在组件里）

统计卡片上的 `toFixed(1)` + 单位 span 改为 `formatResponseTime` / `formatDuration`。

### 5.4 拆 `security-chat.tsx`（~341 行）

- `hooks/use-security-chat.ts`：流式、conversation_id、invalidate `queryKeys.conversations`
- `components/chat/`：输入框、消息列表、模式切换
- 排查 **render 期间 setState**（若仍存在于 overlay / pending user 逻辑）

`queryKeys` 已在阶段 1 接入本页，拆 hook 时继续用工厂，不要写回字符串。

### 5.5 统一共享组件

| 缺口 | 现状 | 建议 |
|------|------|------|
| 详情页 Skeleton | 各页手写 `Skeleton` | `DetailPageSkeleton` |
| Query 错误 | 不统一 | `QueryErrorState` |
| `StatusBadge` | 只吃 string：`completed/passed/failed/...` | 同时支持数值 `DataStatus`（1 启用 / 2 禁用）；dashboard 仍用自制 `Badge`+`STATUS_MAP` |
| 资源表单 | `create-project-dialog` / `endpoint-form-dialog` / `environment-form-dialog` 结构相似 | `ResourceFormDialog` 抽壳，字段 slot 化 |

### 5.6 `types.ts` 按领域拆 + 分页泛型

`frontend/src/lib/types.ts`（~198 行）集中了全部 DTO。建议：

```text
lib/types/common.ts      # PaginatedResponse<T>、Id
lib/types/project.ts
lib/types/endpoint.ts
lib/types/environment.ts
lib/types/test-run.ts
lib/types/report.ts
lib/types/conversation.ts
lib/types/index.ts
```

评估：后端 OpenAPI（`/docs`）→ `openapi-typescript` 生成，作为中长期单一来源。阶段 5 先手拆，不强上 codegen。

### 5.7 清理死代码

| 项 | 证据 |
|----|------|
| `frontend/src/App.tsx` | 占位欢迎页；真正入口是 `router.tsx` + `main.tsx`。README 仍写 `App.tsx` 为根组件 |
| `useParseOpenAPI` | 仅在 `hooks/use-workflows.ts` 定义，无页面引用（上传走 `useUploadOpenAPI`） |
| `useCreateConversation` | 仅导出，页面未用（会话由 `/chat/stream` 服务端创建） |
| `format-relative-time.ts` | 可并入 `format.ts` 或保持实现文件、只从 `format` 导出（`spaces-section` 已改从 `format` 导入） |

### 阶段 5 验收

- `npx tsc --noEmit` + `npm run build`
- 手动：Dashboard、项目详情三 Tab、运行详情、报告列表/详情、安全对话（新建会话 + 旧会话续聊）

---

## 阶段 6：枚举落地与收尾（1–2 天）

> 放在 2–4 之后，避免与分层改动抢同一批文件。

### 6.1 全后端替换魔法数字 / 字符串

枚举已在 `backend/src/data/enum/workflow.py`，但业务代码几乎不用。

**`DataStatus` 文档矛盾（必须先统一语义再替换）：**

| 位置 | 写法 |
|------|------|
| `DataStatus` | 1=启用，2=禁用，3=已删除，4=已废弃 |
| `ProjectBase.status` | 「1-启用, **0-禁用**」 |
| `EnvironmentBase` | 1 启用 / 2 禁用 / 3 已删除；`is_default` 还出现 1/2 与注释「1-是, 2-否」混用 |
| `ProjectRepository.get_active_projects` | `status == 1` |
| 前端 dashboard | `status === 1` 为启用 |

先定一套（建议以 `DataStatus` 为准：禁用=2，不用 0），改 schema 注释、ORM 默认值、前端比较，再把字面量换成枚举。

其它：

- `TestStatus` 替换 `"pending"` / `"running"` / `"completed"` …
- `HttpMethod` 替换 endpoint 的 method 字符串比较
- `ScenarioType` 与 yaml 里写死的五种场景对齐
- `AssertOperator` 与 `assertion_engine._OPERATORS_BY_LENGTH` 对齐

### 6.2 统一时间戳

已有 `local_now()`（`data/models/base.py`）：`YYYY-MM-DDTHH:MM:SS.mmm`

散落实现：

| 位置 | 格式 |
|------|------|
| `TestRunRepository.update_status` | 与 `local_now` 相同（复制粘贴） |
| `generate_single_cases_node` `started_at` | `datetime.now().isoformat()`（带微秒，格式不同） |
| `execute_*_node` `finished_at` | `isoformat()` |
| `generate_report_node` | `"%Y-%m-%d %H:%M:%S"`（给 HTML 展示，可保留，但生成时间入库应 `local_now`） |

规则：

- 入库字段一律 `local_now()`
- 所有 update 路径写 `updated_at`（当前不少 `update_fields` / setattr 路径会漏）
- Repository 不再自己 `strftime`

### 6.3 安全收尾

`graph/tools/fs_tools.py` 的 `run_command`（约 97 行）：

- 任意 Shell 命令，Windows 走 `powershell -Command`，Linux 走 `bash -c`
- 无命令白名单、无工作目录沙箱（只检查目录存在）
- 环境变量原样继承 `os.environ`

必须三选一，并在 ADR 或本文件记录决策：

1. **禁用**：从 `AVAILABLE_TOOLS` 拿掉，LLM 不可调用
2. **白名单**：只允许固定可执行文件 + 参数校验
3. **沙箱**：cwd 限制在项目 `workspace/`，禁止 `..`，清空危险环境变量

同文件 `read_file` / `list_directory` 建议限制在工作区根目录。

其它：

- 清掉剩余内联 import：`workflow.py` 路由、`llm_client` 方法内 import、`fs_tools.py:211` `from datetime import datetime`、`openapi_parser` 的 yaml/requests（可选依赖可放到模块级 try）
- `test_executor.py` 的 `TYPE_CHECKING` 下 import `DataCache` 可保留

### 6.4 测试、覆盖率、changelog

- 补：Service 单测、paginate SQL 过滤、jsonpath、BaseService 404
- 现有 `tests/utils/test_llm_utils.py` 在阶段 1 后仍从 `llm_utils` re-export 导入，阶段 3 删 shim 时改 import 到 `json_utils` / `db_bootstrap`
- 当前 venv 可能未装 pytest（阶段 1 校验时 `No module named pytest`），收尾需把测试依赖装回并纳入 CI
- 更新根目录 `CHANGELOG.md` 与 `doc/CHANGELOG.md`

### 阶段 6 验收

- 全库 `status == 1` / `"running"` 仅允许出现在枚举定义或显式 `.value`
- `run_command` 按选定策略不可再任意执行
- `pytest` 可运行且核心路径绿灯

---

## 建议推进顺序（剩余）

| 顺序 | 阶段 | 原因 |
|------|------|------|
| 1 | **阶段 2** | 不先把 API/节点改到 Service，后面拆 chat/workflow/节点都会反复改同一批调用 |
| 2 | 阶段 2 收尾时消化「阶段 1 遗留」表 | paginate、db_tools.ensure_db |
| 3 | **阶段 3 与阶段 5 并行** | 工作流与前端页面互不阻塞 |
| 4 | **阶段 4** | 超长文件拆分，依赖 Service 已稳定 |
| 5 | **阶段 6** | 枚举/时间/安全一次扫尾，避免和 2–4 冲突 |

单人估算：**约 2–3 周**（阶段 2 最重）。阶段 5 可另开前端并行。

---

## 已完成对照（不要重做）

### 阶段 0

- `case_generation` 配置删除后的场景链路清理（模板写死 5 种场景）
- `endpoint_count` 独立状态字段（不再把 int 写入 `selected_endpoints`）
- 耗时单位：`total_duration` 秒、`response_time` 毫秒，前后端对齐
- Dashboard 项目总数用 `projectsData.total`

### 阶段 1

- `utils/json_utils.py`、`utils/db_bootstrap.py`
- `graph/executor/jsonpath.py`
- `data/schemas/common.py`（`PaginatedResponse` / 批量请求 / validator）
- `RunScopedRepositoryMixin` + `paginate` / `update_fields` / `exists`
- 前端 `lib/query-keys.ts`、`lib/create-crud-hooks.ts`、`lib/format.ts`

---

## 明确不在本清单内的事项

下列是产品演进，不是代码整理，见 ADR-001，不要塞进阶段 2–6：

- Chroma 语义检索接入业务
- Plan 模式真正触发测试工作流
- `project_id` 贯穿对话与测试全链路
- Ask/Plan 后端分流
