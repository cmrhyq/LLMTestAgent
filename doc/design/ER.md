# ⛧ 数据库实体关系图 — LLMTestAgent ⛧

---

> *「数据之间的纽带，如同命运的丝线——不可见，却牵动万物。」*

---

## 一、实体关系总览

![ER 实体关系图](images/er-diagram.svg)

<details>
<summary>PlantUML 源码（点击展开）</summary>

```plantuml
@startuml er-diagram
entity "project" as project {
  * id : Integer <<PK>>
  --
  * name : Text <<UNIQUE>>
  * base_url : Text
  description : Text
  * status : Integer
  * created_at : Text
  * updated_at : Text
}

entity "environment" as environment {
  * id : Integer <<PK>>
  --
  * project_id : Integer <<FK>>
  * name : Text
  * base_url : Text
  description : Text
  variables : Text (JSON)
  * is_default : Integer
  * status : Integer
}

entity "endpoint" as endpoint {
  * id : Integer <<PK>>
  --
  * project_id : Integer <<FK>>
  * operation_id : Text
  * name : Text
  * path : Text
  * method : Text
  ...
}

entity "test_run" as test_run {
  * id : Integer <<PK>>
  --
  project_id : Integer <<FK>>
  environment_id : Integer <<FK>>
  * status : Text
  * trigger_type : Text
  ...
}

entity "test_case" as test_case {
  * id : Integer <<PK>>
  --
  * run_id : Integer <<FK>>
  endpoint_id : Integer <<FK>>
  * case_id : Text
  * case_name : Text
  ...
}

entity "test_result" as test_result {
  * id : Integer <<PK>>
  --
  * run_id : Integer <<FK>>
  * test_case_id : Integer <<FK>>
  * status : Text
  ...
}

entity "test_summary" as test_summary {
  * id : Integer <<PK>>
  --
  * run_id : Integer <<FK, UNIQUE>>
  * total : Integer
  * pass_rate : Float
  ...
}

entity "report" as report {
  * id : Integer <<PK>>
  --
  * run_id : Integer <<FK>>
  * format : Text
  * file_path : Text
}

project ||--o{ environment : "CASCADE"
project ||--o{ endpoint : "CASCADE"
project ||--o{ test_run : "SET NULL"
environment ||--o{ test_run : "SET NULL"
test_run ||--o{ test_case : "CASCADE"
test_run ||--o{ test_result : "CASCADE"
test_run ||--|| test_summary : "CASCADE (1:1)"
test_run ||--o{ report : "CASCADE"
endpoint ||--o{ test_case : "SET NULL"
test_case ||--o{ test_result : "CASCADE"
@enduml
```

</details>

---

## 二、关系详解

> *「万物相连，因果相循。一表之变，牵动全局。」*

| 主表 | 关系 | 从表 | 外键 | 删除策略 |
|------|:----:|------|------|----------|
| `project` | 1 : N | `environment` | `environment.project_id` | CASCADE |
| `project` | 1 : N | `endpoint` | `endpoint.project_id` | CASCADE |
| `project` | 1 : N | `test_run` | `test_run.project_id` | SET NULL |
| `environment` | 1 : N | `test_run` | `test_run.environment_id` | SET NULL |
| `test_run` | 1 : N | `test_case` | `test_case.run_id` | CASCADE |
| `test_run` | 1 : N | `test_result` | `test_result.run_id` | CASCADE |
| `test_run` | 1 : 1 | `test_summary` | `test_summary.run_id` (UNIQUE) | CASCADE |
| `test_run` | 1 : N | `report` | `report.run_id` | CASCADE |
| `endpoint` | 1 : N | `test_case` | `test_case.endpoint_id` | SET NULL |
| `test_case` | 1 : N | `test_result` | `test_result.test_case_id` | CASCADE |

---

## 三、关系拓扑图

![关系拓扑图](images/er-topology.svg)

<details>
<summary>PlantUML 源码（点击展开）</summary>

```plantuml
@startuml er-topology
package "Core" {
  [project] as P
  [test_run] as TR
}

package "Resources" {
  [environment] as ENV
  [endpoint] as EP
}

package "Results" {
  [test_case] as TC
  [test_result] as TRES
  [test_summary] as TS
  [report] as RPT
}

P -down-> ENV : "1:N CASCADE"
P -down-> EP : "1:N CASCADE"
P -right-> TR : "1:N SET NULL"
ENV -right-> TR : "1:N SET NULL"
TR -down-> TC : "1:N CASCADE"
TR -down-> TRES : "1:N CASCADE"
TR -down-> TS : "1:1 CASCADE"
TR -down-> RPT : "1:N CASCADE"
EP -down-> TC : "1:N SET NULL"
TC -right-> TRES : "1:N CASCADE"
@enduml
```

</details>

---

## 四、设计要点

> *「约束即秩序，索引即速度，级联即纪律。」*

### 删除策略

- **CASCADE** — 父记录删除时，子记录一同清除。用于强依赖关系（如 TestRun 删除时清除其所有用例和结果）。
- **SET NULL** — 父记录删除时，子记录外键置空。用于弱引用关系（如项目删除后 TestRun 保留但断开关联）。

### 唯一约束

- `project.name` — 项目名全局唯一
- `(endpoint.project_id, endpoint.path, endpoint.method)` — 同一项目下接口路径+方法唯一
- `test_summary.run_id` — 每次测试运行仅有一条汇总记录

---

*📎 相关文档：[系统流程图](SystemFlowchart.md) · [数据库设计](DatabaseDesign.md)*
