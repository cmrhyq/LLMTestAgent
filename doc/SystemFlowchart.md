# ⛧ 系统流程图 — LLMTestAgent ⛧

---

> *「以大模型之智，驭测试之道。自然语言为钥，开启自动化测试的黑暗华章。」*

---

## 一、总览

本文描述 **LLMTestAgent** 系统的完整工作流程——从用户输入自然语言指令开始，经由意图识别分流至「文档解析」或「测试执行」两条主线，最终汇聚于结果输出。

---

## 二、系统主流程

![系统流程图](images/system-flowchart.svg)

<details>
<summary>PlantUML 源码（点击展开）</summary>

```plantuml
@startuml system-flowchart
start
:User Input (Natural Language Instruction + OpenAPI Doc);
:Intent Recognition (LLM Classification);

if (Intent?) then (parse_openapi)
  :Parse OpenAPI Document (JSON / YAML);
  :Feature Extraction (LLM Analysis);
  :Persist to Database (Project + Endpoints);
else (run_test)
  :Parse Input (Extract test mode & scope);
  :Select Endpoints Agent (LLM + Tool Calling Loop);

  partition "Agent Tool Loop" {
    :search_project(name);
    :get_project_endpoints(project_id);
    :Parse Selected Endpoints;
  }

  if (Test Mode?) then (single)
    :Generate Single Cases (Per-endpoint LLM generation);
  else (flow)
    :Generate Flow Cases (Cross-endpoint orchestration);
  endif

  partition "Test Execution" {
    :CacheResolver.inject();
    :HTTP Request (with retry);
    :AssertionEngine.evaluate_all();
    :CacheResolver.extract();
    :Write TestResult to DB;
  }

  :Generate HTML Report;
endif
stop
@enduml
```

</details>

---

## 三、节点详解

> *「每一节点，皆为齿轮；每一流转，皆为命运。」*

| 序号 | 节点 | 职责描述 |
|:----:|------|----------|
| 1 | **输入测试内容** | 用户通过 CLI 或 Web API 输入自然语言指令，可附带 OpenAPI 文档路径 |
| 2 | **意图识别** | LLM 解析指令，分类为 `run_test`（执行测试）或 `parse_openapi`（解析文档） |
| 3 | **解析文档** | 读取 OpenAPI 3.x 文件（JSON/YAML），提取项目、接口元数据 |
| 4 | **数据特征识别** | 调用 LLM 对接口进行语义理解与结构化分析 |
| 5 | **数据存储** | 将解析结果持久化至 SQLite 数据库 |
| 6 | **解析输入** | 提取用户指令中的测试模式（single/flow）与目标范围 |
| 7 | **获取数据** | 从数据库中查询已存储的项目与接口信息 |
| 8 | **Query Tool** | LangGraph Agent Tool — 执行数据库模糊搜索与接口列表获取 |
| 9 | **AI 选择接口** | LLM Agent 根据用户意图自主挑选目标接口集合 |
| 10 | **生成测试代码** | LLM 基于接口元数据生成覆盖多场景的测试用例 |
| 11 | **执行测试代码** | HTTP 客户端发送请求，断言引擎校验响应 |
| 12 | **分析测试结果** | 统计通过率、响应时间、失败原因等指标 |
| 13 | **生成测试报告** | 输出双层折叠式 HTML 可视化报告 |

---

## 四、分支路由详情

### 意图路由

| 输入 | 条件 | 输出节点 |
|------|------|----------|
| `parse_input` | `intent = parse_openapi` | `parse_openapi_doc` |
| `parse_input` | `intent = run_test` | `select_endpoints` |

### 测试模式路由

| 输入 | 条件 | 输出节点 |
|------|------|----------|
| `parse_result` | `mode = single` | `generate_single_cases` |
| `parse_result` | `mode = flow` | `generate_flow_cases` |

---

## 五、Agent Tool-Calling 循环

> *「智能体与工具之间的对话，如同巫师与魔典的低语。」*

| 步骤 | 行为 | 说明 |
|:----:|------|------|
| 1 | Agent 推理 | LLM 根据上下文决定是否调用工具 |
| 2 | 发出 tool_calls | 调用 `search_project` 或 `get_project_endpoints` |
| 3 | Tools 执行 | 执行数据库查询并返回结果 |
| 4 | 循环判断 | 若 LLM 仍需信息 → 回到步骤 1；否则 → 进入 parse_result |

---

## 六、执行引擎管线

| 阶段 | 模块 | 说明 |
|:----:|------|------|
| 1 | 反序列化 TestCase | 将 JSON 字段解析为 Python 对象 |
| 2 | CacheResolver.inject() | 从 DataCache 注入动态参数 |
| 3 | HttpRequest | 发送 HTTP 请求（支持重试） |
| 4 | AssertionEngine.evaluate_all() | 执行所有断言规则 |
| 5 | CacheResolver.extract() | 从响应中提取值存入 DataCache |
| 6 | 写入 TestResult | 结果持久化至数据库 |

---

> *「流程之末，报告铸成，真相大白于天下。」*

---

*📎 相关文档：[ER 图](ER.md) · [数据库设计](DatabaseDesign.md)*
