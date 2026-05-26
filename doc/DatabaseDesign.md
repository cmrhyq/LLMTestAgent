<![CDATA[# ⛧ 数据库设计文档 — LLMTestAgent ⛧

---

> *「数据库乃系统之基石，表结构即逻辑之骨架。此文档详录每一列、每一约束，以供后来者参阅。」*

---

## 〇、概述

| 项目 | 说明 |
|------|------|
| **数据库引擎** | SQLite 3 |
| **ORM 框架** | SQLAlchemy 2.0 |
| **文件位置** | `db/LLMTest.db`（首次运行自动创建） |
| **ID 策略** | 全局雪花算法（`next_id` 生成器），非自增 |
| **时间格式** | `Text` 存储本地时间字符串（`local_now` 函数生成） |

---

## 一、project — 项目表

> *「万事之始，皆立于项目。一个项目，统辖其下所有接口与测试。」*

### 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | **PK**, 非自增 | 全局唯一 ID |
| `name` | Text | NOT NULL, **UNIQUE** | 项目名称 |
| `base_url` | Text | NOT NULL | 项目基础 URL |
| `description` | Text | default="" | 项目描述 |
| `status` | Integer | NOT NULL, default=1 | 状态（1=启用） |
| `created_at` | Text | NOT NULL | 创建时间 |
| `updated_at` | Text | NOT NULL | 更新时间 |

### 索引

| 索引名 | 字段 |
|--------|------|
| `idx_project_name` | `name` |

### 关系

- 1:N → `environment`（CASCADE 级联删除）
- 1:N → `endpoint`（CASCADE 级联删除）
- 1:N → `test_run`（SET NULL 置空）

---

## 二、environment — 环境表

> *「同一接口，在不同环境中呈现不同面貌——开发、测试、生产，各有各的真相。」*

### 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | **PK**, 非自增 | 全局唯一 ID |
| `project_id` | Integer | **FK** → `project.id`, NOT NULL | 所属项目 |
| `name` | Text | NOT NULL | 环境名称 |
| `base_url` | Text | NOT NULL | 环境基础 URL |
| `description` | Text | default="" | 环境描述 |
| `variables` | Text | default="{}" | 环境变量（JSON） |
| `is_default` | Integer | NOT NULL, default=1 | 是否默认环境 |
| `status` | Integer | NOT NULL, default=1 | 状态 |
| `created_at` | Text | NOT NULL | 创建时间 |
| `updated_at` | Text | NOT NULL | 更新时间 |

### 索引

| 索引名 | 字段 |
|--------|------|
| `idx_env_project` | `project_id` |

### 外键删除策略

| 外键 | 指向 | 策略 |
|------|------|------|
| `project_id` | `project.id` | CASCADE |

---

## 三、endpoint — 接口表

> *「接口者，系统与外界沟通之门户也。路径、方法、参数，缺一不可。」*

### 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | **PK**, 非自增 | 全局唯一 ID |
| `project_id` | Integer | **FK** → `project.id`, NOT NULL | 所属项目 |
| `operation_id` | Text | NOT NULL | OpenAPI operationId |
| `name` | Text | NOT NULL | 接口名称 |
| `path` | Text | NOT NULL | 请求路径 |
| `method` | Text | NOT NULL | HTTP 方法 |
| `tags` | Text | default="[]" | 标签（JSON 数组） |
| `summary` | Text | NULLABLE | 简要描述 |
| `description` | Text | default="" | 详细描述 |
| `params` | Text | NULLABLE | 路径/查询参数（JSON） |
| `headers` | Text | default="{}" | 请求头定义（JSON） |
| `body` | Text | NULLABLE | 请求体 Schema（JSON） |
| `responses` | Text | default="[]" | 响应定义（JSON 数组） |
| `security` | Text | default="[]" | 安全要求（JSON 数组） |
| `content_type` | Text | default="application/json" | 内容类型 |
| `deprecated` | Integer | NOT NULL, default=0 | 是否已废弃 |
| `status` | Integer | NOT NULL, default=1 | 状态 |
| `version` | Integer | NOT NULL, default=1 | 版本号 |
| `created_at` | Text | NOT NULL | 创建时间 |
| `updated_at` | Text | NOT NULL | 更新时间 |

### 约束

| 约束名 | 类型 | 规则 |
|--------|------|------|
| `ck_api_method` | CHECK | `method IN ('GET','POST','PUT','DELETE','PATCH','HEAD','OPTIONS')` |
| `uq_project_path_method` | UNIQUE | `(project_id, path, method)` |

### 索引

| 索引名 | 字段 |
|--------|------|
| `idx_endpoint_project` | `project_id` |
| `idx_endpoint_operation_id` | `operation_id` |

### 外键删除策略

| 外键 | 指向 | 策略 |
|------|------|------|
| `project_id` | `project.id` | CASCADE |

---

## 四、test_run — 测试运行表

> *「每一次测试运行，都是一场审判——代码在此接受检验，真相在此大白。」*

### 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | **PK**, 非自增 | 全局唯一 ID |
| `project_id` | Integer | **FK** → `project.id`, NULLABLE | 关联项目 |
| `environment_id` | Integer | **FK** → `environment.id`, NULLABLE | 关联环境 |
| `name` | Text | default="" | 运行名称 |
| `status` | Text | NOT NULL, default="pending" | 运行状态 |
| `trigger_type` | Text | NOT NULL, default="manual" | 触发方式 |
| `input_file` | Text | default="" | 输入文件路径 |
| `input_snapshot` | Text | default="{}" | 输入快照（JSON） |
| `config_snapshot` | Text | default="{}" | 配置快照（JSON） |
| `llm_provider` | Text | default="" | LLM 提供商 |
| `llm_model` | Text | default="" | LLM 模型名称 |
| `total_cases` | Integer | NOT NULL, default=0 | 用例总数 |
| `passed_cases` | Integer | NOT NULL, default=0 | 通过数 |
| `failed_cases` | Integer | NOT NULL, default=0 | 失败数 |
| `skipped_cases` | Integer | NOT NULL, default=0 | 跳过数 |
| `error_cases` | Integer | NOT NULL, default=0 | 错误数 |
| `pass_rate` | Float | NOT NULL, default=0.0 | 通过率 |
| `started_at` | Text | NULLABLE | 开始时间 |
| `finished_at` | Text | NULLABLE | 结束时间 |
| `total_duration` | Float | NOT NULL, default=0.0 | 总耗时（秒） |
| `error_message` | Text | default="" | 错误信息 |
| `created_at` | Text | NOT NULL | 创建时间 |
| `updated_at` | Text | NOT NULL | 更新时间 |

### 约束

| 约束名 | 类型 | 规则 |
|--------|------|------|
| `ck_run_status` | CHECK | `status IN ('pending','running','completed','failed','cancelled')` |
| `ck_run_trigger` | CHECK | `trigger_type IN ('manual','scheduled','ci')` |

### 索引

| 索引名 | 字段 |
|--------|------|
| `idx_run_project` | `project_id` |
| `idx_run_env` | `environment_id` |

### 外键删除策略

| 外键 | 指向 | 策略 |
|------|------|------|
| `project_id` | `project.id` | SET NULL |
| `environment_id` | `environment.id` | SET NULL |

---

## 五、test_case — 测试用例表

> *「用例乃测试之灵魂——每一条用例，都是对系统的一次质问。」*

### 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | **PK**, 非自增 | 全局唯一 ID |
| `run_id` | Integer | **FK** → `test_run.id`, NOT NULL | 所属测试运行 |
| `endpoint_id` | Integer | **FK** → `endpoint.id`, NULLABLE | 关联接口 |
| `case_id` | Text | NOT NULL | 用例业务 ID |
| `case_name` | Text | NOT NULL | 用例名称 |
| `url` | Text | NOT NULL | 请求 URL |
| `method` | Text | NOT NULL | HTTP 方法 |
| `scenario_type` | Text | NOT NULL, default="normal" | 场景类型 |
| `priority` | Text | NOT NULL, default="P1" | 优先级 |
| `headers` | Text | default="{}" | 请求头（JSON） |
| `body` | Text | NULLABLE | 请求体（JSON） |
| `params` | Text | NULLABLE | 查询参数（JSON） |
| `cache_rules` | Text | NULLABLE | 缓存规则（JSON） |
| `assert_rules` | Text | default="[]" | 断言规则（JSON 数组） |
| `expected_result` | Text | default="成功" | 预期结果描述 |
| `description` | Text | default="" | 用例描述 |
| `remark` | Text | default="" | 备注 |
| `unique_hash` | Text | default="" | 去重哈希 |
| `generated_by` | Text | NOT NULL, default="llm" | 生成方式 |
| `status` | Integer | NOT NULL, default=1 | 状态 |
| `created_at` | Text | NOT NULL | 创建时间 |
| `updated_at` | Text | NOT NULL | 更新时间 |

### 约束

| 约束名 | 类型 | 规则 |
|--------|------|------|
| `ck_case_method` | CHECK | `method IN ('GET','POST','PUT','DELETE','PATCH','HEAD','OPTIONS')` |
| `ck_case_scenario` | CHECK | `scenario_type IN ('normal','param_missing','param_type_error','boundary_value','permission_error','custom')` |
| `ck_case_priority` | CHECK | `priority IN ('P0','P1','P2')` |
| `ck_case_generated` | CHECK | `generated_by IN ('llm','manual','import')` |

### 索引

| 索引名 | 字段 |
|--------|------|
| `idx_case_run` | `run_id` |
| `idx_case_api` | `endpoint_id` |
| `idx_case_case_id` | `case_id` |

### 外键删除策略

| 外键 | 指向 | 策略 |
|------|------|------|
| `run_id` | `test_run.id` | CASCADE |
| `endpoint_id` | `endpoint.id` | SET NULL |

---

## 六、test_result — 测试结果表

> *「结果不会说谎——状态码、响应体、耗时，铁证如山。」*

### 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | **PK**, 非自增 | 全局唯一 ID |
| `run_id` | Integer | **FK** → `test_run.id`, NOT NULL | 所属测试运行 |
| `test_case_id` | Integer | **FK** → `test_case.id`, NOT NULL | 关联测试用例 |
| `case_id` | Text | NOT NULL | 用例业务 ID（冗余） |
| `case_name` | Text | NOT NULL | 用例名称（冗余） |
| `status` | Text | NOT NULL, default="pending" | 执行状态 |
| `request_url` | Text | default="" | 实际请求 URL |
| `request_method` | Text | default="" | 实际请求方法 |
| `request_headers` | Text | default="{}" | 实际请求头（JSON） |
| `request_body` | Text | NULLABLE | 实际请求体 |
| `query_params` | Text | NULLABLE | 实际查询参数 |
| `response_status_code` | Integer | NULLABLE | 响应状态码 |
| `response_headers` | Text | default="{}" | 响应头（JSON） |
| `response_body` | Text | NULLABLE | 响应体 |
| `response_time` | Float | NOT NULL, default=0.0 | 响应时间（秒） |
| `error_message` | Text | default="" | 错误信息 |
| `retry_count` | Integer | NOT NULL, default=0 | 重试次数 |
| `started_at` | Text | NULLABLE | 开始时间 |
| `finished_at` | Text | NULLABLE | 结束时间 |
| `created_at` | Text | NOT NULL | 创建时间 |

### 约束

| 约束名 | 类型 | 规则 |
|--------|------|------|
| `ck_result_status` | CHECK | `status IN ('pending','running','passed','failed','skipped','error')` |

### 索引

| 索引名 | 字段 |
|--------|------|
| `idx_result_run` | `run_id` |
| `idx_result_case` | `test_case_id` |

### 外键删除策略

| 外键 | 指向 | 策略 |
|------|------|------|
| `run_id` | `test_run.id` | CASCADE |
| `test_case_id` | `test_case.id` | CASCADE |

---

## 七、test_summary — 测试汇总表

> *「汇总者，统观全局之眼也。通过率、响应时间、失败原因——一览无余。」*

### 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | **PK**, 非自增 | 全局唯一 ID |
| `run_id` | Integer | **FK** → `test_run.id`, NOT NULL, **UNIQUE** | 关联测试运行（一对一） |
| `total` | Integer | NOT NULL, default=0 | 用例总数 |
| `passed` | Integer | NOT NULL, default=0 | 通过数 |
| `failed` | Integer | NOT NULL, default=0 | 失败数 |
| `skipped` | Integer | NOT NULL, default=0 | 跳过数 |
| `error` | Integer | NOT NULL, default=0 | 错误数 |
| `pass_rate` | Float | NOT NULL, default=0.0 | 通过率 |
| `avg_response_time` | Float | NOT NULL, default=0.0 | 平均响应时间 |
| `min_response_time` | Float | NOT NULL, default=0.0 | 最小响应时间 |
| `max_response_time` | Float | NOT NULL, default=0.0 | 最大响应时间 |
| `p95_response_time` | Float | NOT NULL, default=0.0 | P95 响应时间 |
| `total_duration` | Float | NOT NULL, default=0.0 | 总耗时 |
| `failure_reasons` | Text | default="{}" | 失败原因统计（JSON） |
| `started_at` | Text | NULLABLE | 开始时间 |
| `finished_at` | Text | NULLABLE | 结束时间 |
| `created_at` | Text | NOT NULL | 创建时间 |

### 索引

| 索引名 | 字段 |
|--------|------|
| `idx_summary_run` | `run_id` |
| `idx_summary_pass_rate` | `pass_rate` |

### 外键删除策略

| 外键 | 指向 | 策略 |
|------|------|------|
| `run_id` | `test_run.id` | CASCADE |

---

## 八、report — 报告表

> *「报告乃测试之终章——将混沌的数据，锻造为可读的真知。」*

### 字段定义

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | **PK**, 非自增 | 全局唯一 ID |
| `run_id` | Integer | **FK** → `test_run.id`, NOT NULL | 关联测试运行 |
| `format` | Text | NOT NULL | 报告格式 |
| `file_path` | Text | NOT NULL | 文件路径 |
| `file_size` | Integer | default=0 | 文件大小（字节） |
| `generated_at` | Text | NOT NULL | 生成时间 |

### 约束

| 约束名 | 类型 | 规则 |
|--------|------|------|
| `ck_report_format` | CHECK | `format IN ('excel','html','markdown','json')` |

### 索引

| 索引名 | 字段 |
|--------|------|
| `idx_report_run` | `run_id` |
| `idx_report_format` | `format` |

### 外键删除策略

| 外键 | 指向 | 策略 |
|------|------|------|
| `run_id` | `test_run.id` | CASCADE |

---

## 九、枚举值速查

> *「标准化的值域，是数据完整性的守护者。」*

### test_run.status

| 值 | 含义 |
|----|------|
| `pending` | 等待执行 |
| `running` | 执行中 |
| `completed` | 已完成 |
| `failed` | 执行失败 |
| `cancelled` | 已取消 |

### test_run.trigger_type

| 值 | 含义 |
|----|------|
| `manual` | 手动触发 |
| `scheduled` | 定时触发 |
| `ci` | CI/CD 触发 |

### test_case.scenario_type

| 值 | 含义 |
|----|------|
| `normal` | 正常场景 |
| `param_missing` | 参数缺失 |
| `param_type_error` | 参数类型错误 |
| `boundary_value` | 边界值 |
| `permission_error` | 权限错误 |
| `custom` | 自定义场景 |

### test_case.priority

| 值 | 含义 |
|----|------|
| `P0` | 最高优先级（冒烟测试） |
| `P1` | 高优先级（核心功能） |
| `P2` | 普通优先级（边缘场景） |

### test_case.generated_by

| 值 | 含义 |
|----|------|
| `llm` | LLM 自动生成 |
| `manual` | 人工编写 |
| `import` | 外部导入 |

### test_result.status

| 值 | 含义 |
|----|------|
| `pending` | 等待执行 |
| `running` | 执行中 |
| `passed` | 通过 |
| `failed` | 失败（断言不通过） |
| `skipped` | 跳过（依赖未满足） |
| `error` | 错误（执行异常） |

### report.format

| 值 | 含义 |
|----|------|
| `excel` | Excel 格式 |
| `html` | HTML 格式 |
| `markdown` | Markdown 格式 |
| `json` | JSON 格式 |

### endpoint.method / test_case.method

| 值 |
|----|
| `GET` |
| `POST` |
| `PUT` |
| `DELETE` |
| `PATCH` |
| `HEAD` |
| `OPTIONS` |

---

## 十、数据库重建

```bash
# Windows
del db\LLMTest.db

# macOS / Linux
rm db/LLMTest.db

# 重新运行程序即可自动重建所有表结构
python main.py "解析这份API文档并存储" --api-doc input/httpbin_service.json
```

---

> *「此文档终。数据库之道，尽在此间。」*

---

*📎 相关文档：[系统流程图](SystemFlowchart.md) · [ER 图](ER.md)*
]]>