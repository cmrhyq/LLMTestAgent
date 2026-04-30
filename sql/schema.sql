-- ============================================================================
-- LLMTestAgent 数据库建表脚本 (SQLite)
-- ============================================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA encoding = 'UTF-8';

-- ============================================================================
-- 1. 项目表 (project)
--    管理多个被测服务，支持多项目隔离
-- ============================================================================
CREATE TABLE IF NOT EXISTS project
(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    base_url    TEXT    NOT NULL, -- 默认基础URL
    description TEXT             DEFAULT '',
    status   INTEGER NOT NULL DEFAULT 1, -- 1=启用，2=禁用，3=已删除
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime'))
);

CREATE INDEX idx_project_name    ON project(name);

-- ============================================================================
-- 2. 测试环境表 (environment)
--    记录执行时的运行环境信息，支持多环境对比
-- ============================================================================
CREATE TABLE IF NOT EXISTS environment
(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL,
    name        TEXT    NOT NULL,
    base_url    TEXT    NOT NULL,
    description TEXT             DEFAULT '',
    variables   TEXT             DEFAULT '{}', -- 环境变量 KV
    is_default  INTEGER NOT NULL DEFAULT 1, -- 1=默认，2=不默认
    status   INTEGER NOT NULL DEFAULT 1, -- 1=启用，2=禁用，3=已删除
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime'))
);

CREATE INDEX idx_env_project ON environment (project_id);

-- ============================================================================
-- 3. API 定义表 (endpoint)
--    持久化 API 接口定义，支持版本化和复用
-- ============================================================================
CREATE TABLE IF NOT EXISTS endpoint
(
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER NOT NULL,
    operation_id TEXT    NOT NULL, -- OpenAPI operationId
    name         TEXT    NOT NULL,
    path         TEXT    NOT NULL,
    method       TEXT    NOT NULL CHECK (method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS')),
    tags         TEXT             DEFAULT '[]',
    summary      TEXT             DEFAULT NULL,
    description  TEXT             DEFAULT NULL,
    params       TEXT             DEFAULT '{}',
    headers      TEXT             DEFAULT '{}',
    body         TEXT             DEFAULT '{}',
    status    INTEGER NOT NULL DEFAULT 1, -- 1=启用，2=禁用，3=已删除, 4=已废弃
    version      INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    updated_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (project_id) REFERENCES project (id) ON DELETE CASCADE
);

CREATE INDEX idx_endpoint_project ON endpoint (project_id);
CREATE INDEX idx_endpoint_operation_id ON endpoint (operation_id);
CREATE UNIQUE INDEX uq_project_path_method ON endpoint(project_id, path, method);

-- ============================================================================
-- 4. 执行批次表 (test_run)
--    每次 CLI 运行产生一个批次，关联输入文件、配置快照和执行环境
-- ============================================================================
CREATE TABLE IF NOT EXISTS test_run
(
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER,
    environment_id  INTEGER,
    name            TEXT             DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    trigger_type    TEXT    NOT NULL DEFAULT 'manual' CHECK (trigger_type IN ('manual', 'scheduled', 'ci')),
    input_file      TEXT             DEFAULT '',
    input_snapshot  TEXT             DEFAULT '{}',
    config_snapshot TEXT             DEFAULT '{}',
    llm_provider    TEXT             DEFAULT '',
    llm_model       TEXT             DEFAULT '',
    total_cases     INTEGER NOT NULL DEFAULT 0,
    passed_cases    INTEGER NOT NULL DEFAULT 0,
    failed_cases    INTEGER NOT NULL DEFAULT 0,
    skipped_cases   INTEGER NOT NULL DEFAULT 0,
    error_cases     INTEGER NOT NULL DEFAULT 0,
    pass_rate       REAL    NOT NULL DEFAULT 0.0,
    started_at      TEXT             DEFAULT NULL,
    finished_at     TEXT             DEFAULT NULL,
    total_duration  REAL    NOT NULL DEFAULT 0.0,
    error_message   TEXT             DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (project_id) REFERENCES project (id) ON DELETE SET NULL,
    FOREIGN KEY (environment_id) REFERENCES environment (id) ON DELETE SET NULL
);

CREATE INDEX idx_run_project ON test_run (project_id);
CREATE INDEX idx_run_env ON test_run (environment_id);

-- ============================================================================
-- 5. 测试用例表 (test_case)
--    对应 workflow.py -> TestCase
--    由 LLM 生成或手工创建的用例
-- ============================================================================
CREATE TABLE IF NOT EXISTS test_case
(
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL,
    endpoint_id     INTEGER,
    case_id         TEXT    NOT NULL,
    case_name       TEXT    NOT NULL,
    url             TEXT    NOT NULL,
    method          TEXT    NOT NULL CHECK (method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS')),
    scenario_type   TEXT    NOT NULL DEFAULT 'normal' CHECK (scenario_type IN (
                                                                               'normal', 'param_missing',
                                                                               'param_type_error',
                                                                               'boundary_value', 'permission_error',
                                                                               'custom'
        )),
    priority        TEXT    NOT NULL DEFAULT 'P1' CHECK (priority IN ('P0', 'P1', 'P2')),
    headers         TEXT             DEFAULT '{}',
    body            TEXT             DEFAULT NULL,
    params          TEXT             DEFAULT NULL,
    cache_rules     TEXT             DEFAULT NULL,
    assert_rules    TEXT             DEFAULT '[]',
    expected_result TEXT             DEFAULT '成功',
    description     TEXT             DEFAULT '',
    remark          TEXT             DEFAULT '',
    unique_hash     TEXT             DEFAULT '',
    generated_by    TEXT    NOT NULL DEFAULT 'llm' CHECK (generated_by IN ('llm', 'manual', 'import')),
    status       INTEGER NOT NULL DEFAULT 1, -- 1=启用，2=禁用，3=已删除, 4=已废弃
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (run_id) REFERENCES test_run (id) ON DELETE CASCADE,
    FOREIGN KEY (endpoint_id) REFERENCES endpoint (id) ON DELETE SET NULL
);

CREATE INDEX idx_case_run ON test_case (run_id);
CREATE INDEX idx_case_api ON test_case (endpoint_id);
CREATE INDEX idx_case_case_id ON test_case (case_id);

-- ============================================================================
-- 6. 测试结果表 (test_result)
--    对应 workflow.py -> TestResult
--    完整记录每条用例的执行请求/响应/状态
-- ============================================================================
CREATE TABLE IF NOT EXISTS test_result
(
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id               INTEGER NOT NULL,
    test_case_id         INTEGER NOT NULL,
    case_id              TEXT    NOT NULL,
    case_name            TEXT    NOT NULL,
    status               TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN (
                                                                              'pending', 'running', 'passed', 'failed',
                                                                              'skipped', 'error'
        )),
    request_url          TEXT             DEFAULT '',
    request_method       TEXT             DEFAULT '',
    request_headers      TEXT             DEFAULT '{}',
    request_body         TEXT             DEFAULT NULL,
    query_params         TEXT             DEFAULT NULL,
    response_status_code INTEGER          DEFAULT NULL,
    response_headers     TEXT             DEFAULT '{}',
    response_body        TEXT             DEFAULT NULL,
    response_time        REAL    NOT NULL DEFAULT 0.0,
    error_message        TEXT             DEFAULT '',
    retry_count          INTEGER NOT NULL DEFAULT 0,
    started_at           TEXT             DEFAULT NULL,
    finished_at          TEXT             DEFAULT NULL,
    created_at           TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (run_id) REFERENCES test_run (id) ON DELETE CASCADE,
    FOREIGN KEY (test_case_id) REFERENCES test_case (id) ON DELETE CASCADE
);

CREATE INDEX idx_result_run ON test_result (run_id);
CREATE INDEX idx_result_case ON test_result (test_case_id);

-- ============================================================================
-- 7. 测试摘要表 (test_summary)
--     对应 models.py -> TestSummary
--     每次执行批次聚合一条摘要记录
-- ============================================================================
CREATE TABLE IF NOT EXISTS test_summary (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              INTEGER NOT NULL UNIQUE,
    total               INTEGER NOT NULL DEFAULT 0,
    passed              INTEGER NOT NULL DEFAULT 0,
    failed              INTEGER NOT NULL DEFAULT 0,
    skipped             INTEGER NOT NULL DEFAULT 0,
    error               INTEGER NOT NULL DEFAULT 0,
    pass_rate           REAL    NOT NULL DEFAULT 0.0,
    avg_response_time   REAL    NOT NULL DEFAULT 0.0,
    min_response_time   REAL    NOT NULL DEFAULT 0.0,
    max_response_time   REAL    NOT NULL DEFAULT 0.0,
    p95_response_time   REAL    NOT NULL DEFAULT 0.0,
    total_duration      REAL    NOT NULL DEFAULT 0.0,
    failure_reasons     TEXT    DEFAULT '{}',
    started_at          TEXT    DEFAULT NULL,
    finished_at         TEXT    DEFAULT NULL,
    created_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (run_id) REFERENCES test_run(id) ON DELETE CASCADE
);

CREATE INDEX idx_summary_run       ON test_summary(run_id);
CREATE INDEX idx_summary_pass_rate ON test_summary(pass_rate);

-- ============================================================================
-- 8. 报告记录表 (report)
--     记录每次生成的报告文件路径与元信息
-- ============================================================================
CREATE TABLE IF NOT EXISTS report
(
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       INTEGER NOT NULL,
    format       TEXT    NOT NULL CHECK (format IN ('excel', 'html', 'markdown', 'json')),
    file_path    TEXT    NOT NULL,
    file_size    INTEGER          DEFAULT 0,
    generated_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (run_id) REFERENCES test_run (id) ON DELETE CASCADE
);

CREATE INDEX idx_report_run ON report (run_id);
CREATE INDEX idx_report_format ON report (format);

-- ============================================================================
-- 触发器：自动更新 updated_at 字段
-- ============================================================================
CREATE TRIGGER trg_project_updated
    AFTER UPDATE
    ON project
BEGIN
    UPDATE project
    SET updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_environment_updated
    AFTER UPDATE
    ON environment
BEGIN
    UPDATE environment
    SET updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_endpoint_updated
    AFTER UPDATE
    ON endpoint
BEGIN
    UPDATE endpoint
    SET updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_test_run_updated
    AFTER UPDATE
    ON test_run
BEGIN
    UPDATE test_run
    SET updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_test_case_updated
    AFTER UPDATE
    ON test_case
BEGIN
    UPDATE test_case
    SET updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')
    WHERE id = NEW.id;
END;

-- ============================================================================
-- 常用分析视图
-- ============================================================================

-- 视图: 每次执行的概览（关联项目、环境、摘要）
CREATE VIEW IF NOT EXISTS v_run_overview AS
SELECT tr.id      AS run_id,
       p.name     AS project_name,
       p.base_url AS project_base_url,
       e.name     AS environment_name,
       tr.status  AS run_status,
       tr.trigger_type,
       tr.llm_provider,
       tr.llm_model,
       tr.started_at,
       tr.finished_at,
       tr.created_at
FROM test_run tr
         LEFT JOIN project p ON tr.project_id = p.id
         LEFT JOIN environment e ON tr.environment_id = e.id;

-- 视图: 接口维度聚合（按 API URL 分组统计通过率）
CREATE VIEW IF NOT EXISTS v_api_pass_rate AS
SELECT tr.request_url,
       tr.request_method,
       COUNT(*)                                              AS total_executions,
       SUM(CASE WHEN tr.status = 'passed' THEN 1 ELSE 0 END) AS passed_count,
       SUM(CASE WHEN tr.status = 'failed' THEN 1 ELSE 0 END) AS failed_count,
       ROUND(
               SUM(CASE WHEN tr.status = 'passed' THEN 1.0 ELSE 0 END)
                   / NULLIF(COUNT(*), 0) * 100, 2
       )                                                     AS pass_rate,
       ROUND(AVG(tr.response_time), 2)                       AS avg_response_time,
       ROUND(MIN(tr.response_time), 2)                       AS min_response_time,
       ROUND(MAX(tr.response_time), 2)                       AS max_response_time
FROM test_result tr
WHERE tr.status IN ('passed', 'failed')
GROUP BY tr.request_url, tr.request_method;

-- 视图: 场景类型分布（统计各场景类型的测试覆盖情况）
CREATE VIEW IF NOT EXISTS v_scenario_distribution AS
SELECT tc.scenario_type,
       COUNT(*)                                              AS total_cases,
       SUM(CASE WHEN tr.status = 'passed' THEN 1 ELSE 0 END) AS passed,
       SUM(CASE WHEN tr.status = 'failed' THEN 1 ELSE 0 END) AS failed,
       SUM(CASE WHEN tr.status = 'error' THEN 1 ELSE 0 END)  AS errors,
       ROUND(
               SUM(CASE WHEN tr.status = 'passed' THEN 1.0 ELSE 0 END)
                   / NULLIF(SUM(CASE WHEN tr.status IN ('passed', 'failed') THEN 1 ELSE 0 END), 0) * 100, 2
       )                                                     AS pass_rate
FROM test_case tc
         LEFT JOIN test_result tr ON tr.test_case_id = tc.id
GROUP BY tc.scenario_type;

-- ============================================================================
-- 初始数据
-- ============================================================================
-- 初始化Project数据
INSERT INTO project (name, base_url, description, status)
VALUES ('HTTP Bin Project', 'https://httpbin.org', '', 1);

-- 初始化Environment数据
INSERT INTO environment (project_id, name, base_url, description, variables, is_default, status)
VALUES (1, 'httpbin dev', 'https://httpbin.org', 'dev env', '{"name": "alan"}', 1, 1);
INSERT INTO environment (project_id, name, base_url, description, variables, is_default, status)
VALUES (1, 'httpbin prod', 'https://httpbin.org', 'prod env', '{"name": "anna"}', 2, 1);