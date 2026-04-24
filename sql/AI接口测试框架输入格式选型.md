# AI接口测试框架输入格式选型

## 🧑‍💻 User

我正在使用python+ langchain + langgraph开发一个AI的API自动化测试框架，然后发现了一些问题：1.不知道如何选择输入，第一种是自己定义的一种格式的json文件，然后，第二种是OpenAPI格式的json/yaml文件，第三种是postman格式的json文件，帮我选择一下哪一个更好。这个框架不仅仅要做单接口的AI的API自动化测试，还要做流程化的AI的API自动化测试（也就是把接口串成流程，前面接口的响应数据后面一个接口需要用到，等等这一类）

---
## 🤖 Assistant

# AI API 自动化测试框架 - 输入格式选择建议

## 核心结论

**推荐方案：以 OpenAPI 3.x 为主，辅以自定义 DSL 描述流程编排**

即：**OpenAPI (接口定义) + 自定义 YAML/JSON (流程编排)** 的混合方案。

---

## 三种方案对比

| 维度 | 自定义 JSON | OpenAPI | Postman Collection |
|------|------------|---------|-------------------|
| **标准化程度** | ❌ 自造轮子 | ✅ 行业标准 | ⚠️ 半标准（Postman生态） |
| **生态工具链** | ❌ 无 | ✅ 极丰富（Swagger/Redoc/代码生成等） | ⚠️ 依赖Postman |
| **Schema 完整度** | 取决于设计 | ✅ 极完整（参数、类型、示例、约束） | ⚠️ 主要描述请求，schema 弱 |
| **AI 友好度** | 一般 | ✅ **最高**（LLM训练语料中大量存在） | 中等 |
| **流程编排支持** | 自己定 | ❌ 原生不支持 | ⚠️ 有但弱（pre/post script） |
| **团队接入成本** | 高 | ✅ 低（开发通常自带） | 中（要导出） |
| **参数提取/断言** | 自己设计 | ❌ 需扩展 | ✅ 有但JS脚本化 |

---

## 为什么选 OpenAPI？

### 1. AI 理解最友好
LLM（GPT-4、Claude）对 OpenAPI 规范有**极强的先验知识**，让 LangChain/LangGraph 生成测试用例、推理参数依赖时准确率最高。

### 2. 开发者零成本
大多数后端框架（FastAPI、Spring Boot、NestJS）可**自动生成** OpenAPI 文档，不用让团队重复维护。

### 3. 生态完整
- `openapi-spec-validator` 校验
- `prance` / `openapi-core` 解析
- 可直接生成 mock、客户端代码

### 4. Schema 信息最完整
有了完整的 request/response schema，AI 才能：
- 生成边界值、异常值用例
- 理解字段含义生成合理业务数据
- 在流程中正确提取/匹配字段

---

## 为什么不直接用 Postman？

- Postman Collection 的**响应 schema 很弱**（通常只有 example），AI 难以推断数据结构做流程串联
- 流程编排依赖 JS 脚本（`pm.environment.set(...)`），**AI 难以结构化理解和生成**
- 绑定 Postman 生态，不如 OpenAPI 通用

但可以**支持导入 Postman** → 转换为内部格式（作为兼容能力）。

---

## 推荐架构

```
┌──────────────────────────────────────────┐
│  输入层（多源支持，归一化）                  │
│  - OpenAPI 3.x (主推)                     │
│  - Postman Collection (可选导入)          │
│  - 自定义流程 DSL (YAML)  ←── 流程编排专用  │
└──────────────────────────────────────────┘
                  ↓ 归一化
┌──────────────────────────────────────────┐
│  内部统一模型 (Pydantic Models)            │
│  - APISpec: 接口定义                       │
│  - TestFlow: 流程定义                      │
│  - TestCase: 用例定义                      │
└──────────────────────────────────────────┘
                  ↓
         LangGraph Agent 执行
```

---

## 流程 DSL 设计建议（补充 OpenAPI 缺失的编排能力）

OpenAPI 不描述"流程"，所以需要一个轻量 DSL：

```yaml
# flow_login_and_create_order.yaml
flow_name: "登录并下单流程"
description: "用户登录后获取token，然后创建订单"

steps:
  - id: login
    ref: "POST /api/auth/login"        # 引用 OpenAPI 中的 operationId 或 path
    input:
      body:
        username: "test_user"
        password: "{{env.PASSWORD}}"
    extract:                            # 提取响应数据
      token: "$.data.access_token"
      user_id: "$.data.user.id"
    assert:
      - "$.code == 0"

  - id: create_order
    ref: "POST /api/orders"
    depends_on: [login]
    input:
      headers:
        Authorization: "Bearer {{login.token}}"   # 引用上一步
      body:
        user_id: "{{login.user_id}}"
        product_id: "P001"
    extract:
      order_id: "$.data.id"
    assert:
      - "$.code == 0"
      - "$.data.user_id == {{login.user_id}}"

  - id: query_order
    ref: "GET /api/orders/{order_id}"
    depends_on: [create_order]
    input:
      path:
        order_id: "{{create_order.order_id}}"
      headers:
        Authorization: "Bearer {{login.token}}"
```

**关键设计点：**
- `ref` 引用 OpenAPI 中的接口（复用定义，不重复）
- `extract` 用 JSONPath 提取字段
- `{{step_id.field}}` 模板变量做上下文传递
- `depends_on` 构建 DAG → 天然映射到 **LangGraph 的节点依赖**

---

## LangGraph 落地建议

1. **每个 step = 一个 Node**
2. **flow 的 DAG = LangGraph 的 StateGraph**
3. **State 中保存各步骤的 extract 结果**，供后续节点渲染模板
4. **AI Agent 的角色：**
   - 从 OpenAPI 自动推荐/生成流程
   - 为每个 step 生成测试数据
   - 失败时智能分析定位
   - 自动补全缺失的字段依赖关系

---

## 实施路线建议

| 阶段 | 目标 |
|------|------|
| **P0** | 支持 OpenAPI 3.x 解析 + 单接口测试 |
| **P1** | 设计流程 DSL + LangGraph 编排执行 |
| **P2** | AI 自动根据 OpenAPI 推荐流程 & 生成用例 |
| **P3** | 支持 Postman 导入（转为内部格式） |
| **P4** | AI 失败诊断、自愈、回放 |

---

## 总结一句话

> **用 OpenAPI 做"静态接口字典"，用自定义 DSL 做"动态流程剧本"，两者互补，AI 双双可读。**

如果你需要，我可以帮你设计具体的 Pydantic 数据模型，或画出 LangGraph 的 StateGraph 结构，告诉我下一步想深入哪块。

---
## 🧑‍💻 User

那这套框架的话，需要把输入的OpenAPI格式的文件解析后存储到数据库里去呢

---
## 🤖 Assistant

# OpenAPI 解析后是否入库？—— 分层决策

## 核心结论

**需要入库，但不是"把 OpenAPI 原样塞进去"，而是解析归一化后，按用途分层存储。**

关键判断：**你的框架是"一次性脚本工具"还是"可持续运营的测试平台"？**

- 一次性工具 → 内存/文件缓存即可
- 测试平台（有用户、有历史、有流程复用）→ **必须入库**

从你的描述（流程编排、AI 辅助）看，**强烈建议入库**。

---

## 为什么需要入库？

| 场景 | 不入库的痛点 | 入库后的收益 |
|------|------------|------------|
| 流程编排引用接口 | 每次加载 OpenAPI 全文件，无法精准引用 | 通过 API ID 直接关联 |
| OpenAPI 版本迭代 | 接口变更无感知 | 可做版本 diff，告警流程失效 |
| AI 检索相关接口 | 每次全量喂给 LLM，token 爆炸 | 向量检索 Top-K，精准投喂 |
| 执行历史追溯 | 无法复盘 | 用例、流程、执行记录可查询 |
| 多人协作 | 文件管理混乱 | 统一数据源 |
| 流程复用 | 无法跨项目引用 | 接口/流程资产沉淀 |

---

## 推荐存储架构（分层）

```
┌─────────────────────────────────────────────────┐
│ 1. 原始文件存储 (对象存储 / 文件系统)              │
│    - 保留 OpenAPI 原文件 (审计、回溯)              │
├─────────────────────────────────────────────────┤
│ 2. 结构化数据库 (PostgreSQL / MySQL)              │
│    - Project / APISpec / Endpoint / Schema       │
│    - TestFlow / TestCase / ExecutionRecord       │
├─────────────────────────────────────────────────┤
│ 3. 向量数据库 (Chroma / Qdrant / pgvector)        │
│    - Endpoint 的语义向量 (供 AI 检索)              │
├─────────────────────────────────────────────────┤
│ 4. 缓存 (Redis, 可选)                             │
│    - 热点接口定义、执行中的流程上下文               │
└─────────────────────────────────────────────────┘
```

对于中小规模项目，**PostgreSQL + pgvector 一个库搞定**（推荐起步方案）。

---

## 核心数据模型设计

### 1. 项目与 Spec 版本管理

```python
# Project: 被测项目
class Project:
    id: UUID
    name: str                    # "订单服务"
    base_url: str
    created_at: datetime

# APISpec: 一份 OpenAPI 文件的导入记录（支持版本）
class APISpec:
    id: UUID
    project_id: UUID
    version: str                 # "v1.2.0"
    source_type: str             # "openapi" | "postman"
    raw_content: JSON            # 原始 OpenAPI 完整内容
    file_hash: str               # 去重、判断是否变更
    imported_at: datetime
    is_active: bool              # 当前激活版本
```

### 2. 接口（核心表）

```python
# Endpoint: 单个接口（OpenAPI 中的一个 operation）
class Endpoint:
    id: UUID
    spec_id: UUID
    project_id: UUID
    
    # 标识信息
    operation_id: str            # OpenAPI 的 operationId
    method: str                  # GET/POST...
    path: str                    # /api/users/{id}
    tags: list[str]              # 分组
    summary: str
    description: str
    
    # 结构化请求定义
    path_params: JSON            # [{name, type, required, ...}]
    query_params: JSON
    headers: JSON
    request_body_schema: JSON    # JSON Schema
    request_body_example: JSON
    
    # 响应定义
    responses: JSON              # {200: {schema, example}, 400: {...}}
    
    # AI 相关
    embedding: vector(1536)      # pgvector 字段
    ai_tags: list[str]           # AI 打的业务标签，如"认证""支付"
    
    # 依赖提示 (AI 预分析)
    likely_depends_on: list[UUID]  # 可能依赖的接口（如需要先登录）
    produces_fields: list[str]     # 响应中可被后续接口引用的字段
    consumes_fields: list[str]     # 请求中需要从上游获取的字段
    
    created_at: datetime
    updated_at: datetime
```

### 3. 流程与用例

```python
class TestFlow:
    id: UUID
    project_id: UUID
    name: str                    # "登录并下单"
    description: str
    dsl_content: JSON            # 流程 DSL（见上轮回复）
    steps: list[FlowStep]        # 或拆表
    created_by: str
    
class FlowStep:
    id: UUID
    flow_id: UUID
    endpoint_id: UUID            # ← 关联到 Endpoint
    order: int
    input_template: JSON
    extract_rules: JSON
    assertions: JSON
    depends_on: list[UUID]

class TestCase:
    id: UUID
    endpoint_id: UUID | None     # 单接口用例
    flow_id: UUID | None         # 流程用例
    name: str
    case_type: str               # "normal" | "boundary" | "error" | "ai_generated"
    input_data: JSON
    expected: JSON
    generated_by_ai: bool

class ExecutionRecord:
    id: UUID
    case_id: UUID
    status: str                  # passed/failed/error
    request: JSON
    response: JSON
    duration_ms: int
    error_detail: JSON
    executed_at: datetime
```

---

## 关键设计点

### ① 保留原文 + 结构化并存
- `APISpec.raw_content` 存原 OpenAPI → 审计、回滚
- `Endpoint` 表存解析后的扁平数据 → 高效查询

### ② 用 `file_hash` 做幂等
导入时先算 hash，相同则跳过或提示；不同则做 diff 更新。

### ③ Endpoint 的向量化（AI 核心）
```python
# 索引文本拼接
text = f"{method} {path}\n{summary}\n{description}\ntags: {tags}"
embedding = embed(text)
```
这是 **LangChain Retriever** 的数据源，让 AI 能"搜到"相关接口。

### ④ Spec 变更检测
重新导入 OpenAPI 时：
- 新增接口 → 新增 Endpoint
- 已删除接口 → 标记 `deprecated`，通知受影响的 Flow
- Schema 变更 → diff 并告警（流程可能失效）

### ⑤ $ref 要解开
OpenAPI 的 `components.schemas` 用 `$ref` 相互引用，建议用 `prance` 或 `openapi-spec-validator` **dereference** 后存储，避免查询时反复跳转。

```python
from prance import ResolvingParser
parser = ResolvingParser('api.yaml')
resolved_spec = parser.specification  # 所有 $ref 已展开
```

---

## 解析入库流程

```
OpenAPI 文件上传
     ↓
1. 校验 (openapi-spec-validator)
     ↓
2. 解析 + 解 $ref (prance)
     ↓
3. 计算 file_hash，判断是否变更
     ↓
4. 存 APISpec (原文)
     ↓
5. 遍历 paths × methods，拆分为 N 个 Endpoint 入库
     ↓
6. 对每个 Endpoint 生成 embedding → 向量库
     ↓
7. (可选) AI 预分析依赖关系、业务标签
     ↓
8. 与旧版本 diff，触发告警 / 流程健康检查
```

---

## 技术选型建议

| 组件 | 推荐 | 理由 |
|------|------|------|
| 主库 | **PostgreSQL** | JSON 字段 + pgvector 一站式 |
| 向量检索 | **pgvector** 起步，Qdrant 升级 | 初期省一个组件 |
| ORM | **SQLModel** / SQLAlchemy 2.0 | 配合 Pydantic，和 LangChain 顺 |
| OpenAPI 解析 | **prance** + **openapi-spec-validator** | 社区成熟 |
| 迁移 | Alembic | Schema 迭代必备 |

---

## 最小化启动（MVP）

如果刚开始别想太多，先建 3 张表能跑起来：

```
projects
api_specs  (存原文)
endpoints  (解析后扁平表 + embedding)
```

流程、用例、执行记录等后续迭代加。

---

## 一句话总结

> **OpenAPI 是"输入协议"，数据库里的 Endpoint 表才是框架的"运行时真相"。入库不是可选项，是 AI + 流程化能力的地基。**

需要我帮你写出具体的 SQLModel 建模代码、或者 OpenAPI → Endpoint 的解析器实现吗？
