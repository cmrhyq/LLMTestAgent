-- ============================================================================
-- LLMTestAgent 数据库建表脚本 (SQLite)
--
-- 数据模型基于 src/core/models.py 中的 Pydantic 模型设计
-- 覆盖：项目/执行批次/API 定义/测试用例/测试结果/断言/摘要/缓存/环境/标签
-- ============================================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA encoding = 'UTF-8';

-- ============================================================================
-- 1. 项目表 (project)
--    管理多个被测服务，支持多项目隔离
-- ============================================================================
CREATE TABLE IF NOT EXISTS project (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    domain          TEXT    NOT NULL,
    description     TEXT    DEFAULT '',
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime'))
);

CREATE INDEX idx_project_name    ON project(name);
CREATE INDEX idx_project_active  ON project(is_active);

-- ============================================================================
-- 2. 测试环境表 (environment)
--    记录执行时的运行环境信息，支持多环境对比
-- ============================================================================
CREATE TABLE IF NOT EXISTS environment (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    base_url        TEXT    NOT NULL,
    description     TEXT    DEFAULT '',
    variables       TEXT    DEFAULT '{}',
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime'))
);

CREATE INDEX idx_env_name   ON environment(name);
CREATE INDEX idx_env_active ON environment(is_active);

-- ============================================================================
-- 3. API 定义表 (api_info)
--    对应 models.py -> APIInfo
--    持久化 API 接口定义，支持版本化和复用
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_info (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL,
    api_id          TEXT    NOT NULL,
    name            TEXT    NOT NULL,
    url             TEXT    NOT NULL,
    method          TEXT    NOT NULL CHECK (method IN ('GET','POST','PUT','DELETE','PATCH','HEAD','OPTIONS')),
    headers         TEXT    DEFAULT '{}',
    body            TEXT    DEFAULT NULL,
    params          TEXT    DEFAULT NULL,
    cache_rules     TEXT    DEFAULT NULL,
    assert_rules    TEXT    DEFAULT '[]',
    priority        TEXT    NOT NULL DEFAULT 'P1' CHECK (priority IN ('P0','P1','P2')),
    description     TEXT    DEFAULT '',
    tags            TEXT    DEFAULT '[]',
    is_active       INTEGER NOT NULL DEFAULT 1,
    version         INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
);

CREATE INDEX idx_api_project    ON api_info(project_id);
CREATE INDEX idx_api_api_id     ON api_info(api_id);
CREATE INDEX idx_api_method     ON api_info(method);
CREATE INDEX idx_api_priority   ON api_info(priority);
CREATE INDEX idx_api_active     ON api_info(is_active);
CREATE UNIQUE INDEX uk_api_project_apiid_version ON api_info(project_id, api_id, version);

-- ============================================================================
-- 4. API 依赖关系表 (api_dependency)
--    对应 models.py -> Dependency
--    记录接口之间的数据依赖关系
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_dependency (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    api_info_id     INTEGER NOT NULL,
    source_api_id   TEXT    NOT NULL,
    source_path     TEXT    NOT NULL,
    target_param    TEXT    NOT NULL,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (api_info_id) REFERENCES api_info(id) ON DELETE CASCADE
);

CREATE INDEX idx_dep_api_info   ON api_dependency(api_info_id);
CREATE INDEX idx_dep_source     ON api_dependency(source_api_id);

-- ============================================================================
-- 5. 标签表 (tag)  +  API-标签关联表 (api_tag)
--    支持通过标签对 API 进行分类和筛选
-- ============================================================================
CREATE TABLE IF NOT EXISTS tag (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    color           TEXT    DEFAULT '#6366f1',
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS api_tag (
    api_info_id     INTEGER NOT NULL,
    tag_id          INTEGER NOT NULL,
    PRIMARY KEY (api_info_id, tag_id),
    FOREIGN KEY (api_info_id) REFERENCES api_info(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id)      REFERENCES tag(id)      ON DELETE CASCADE
);

-- ============================================================================
-- 6. 执行批次表 (test_run)
--    每次 CLI 运行产生一个批次，关联输入文件、配置快照和执行环境
-- ============================================================================
CREATE TABLE IF NOT EXISTS test_run (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT    NOT NULL UNIQUE,
    project_id      INTEGER,
    environment_id  INTEGER,
    name            TEXT    DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','completed','failed','cancelled')),
    trigger_type    TEXT    NOT NULL DEFAULT 'manual' CHECK (trigger_type IN ('manual','scheduled','ci')),
    input_file      TEXT    DEFAULT '',
    input_snapshot  TEXT    DEFAULT '{}',
    config_snapshot TEXT    DEFAULT '{}',
    llm_provider    TEXT    DEFAULT '',
    llm_model       TEXT    DEFAULT '',
    total_cases     INTEGER NOT NULL DEFAULT 0,
    passed_cases    INTEGER NOT NULL DEFAULT 0,
    failed_cases    INTEGER NOT NULL DEFAULT 0,
    skipped_cases   INTEGER NOT NULL DEFAULT 0,
    error_cases     INTEGER NOT NULL DEFAULT 0,
    pass_rate       REAL    NOT NULL DEFAULT 0.0,
    started_at      TEXT    DEFAULT NULL,
    finished_at     TEXT    DEFAULT NULL,
    total_duration  REAL    NOT NULL DEFAULT 0.0,
    error_message   TEXT    DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (project_id)     REFERENCES project(id)     ON DELETE SET NULL,
    FOREIGN KEY (environment_id) REFERENCES environment(id) ON DELETE SET NULL
);

CREATE INDEX idx_run_project     ON test_run(project_id);
CREATE INDEX idx_run_env         ON test_run(environment_id);
CREATE INDEX idx_run_status      ON test_run(status);
CREATE INDEX idx_run_trigger     ON test_run(trigger_type);
CREATE INDEX idx_run_started     ON test_run(started_at);
CREATE INDEX idx_run_created     ON test_run(created_at);

-- ============================================================================
-- 7. 测试用例表 (test_case)
--    对应 models.py -> TestCase
--    由 LLM 生成或手工创建的用例
-- ============================================================================
CREATE TABLE IF NOT EXISTS test_case (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL,
    api_info_id     INTEGER,
    case_id         TEXT    NOT NULL,
    case_name       TEXT    NOT NULL,
    url             TEXT    NOT NULL,
    method          TEXT    NOT NULL CHECK (method IN ('GET','POST','PUT','DELETE','PATCH','HEAD','OPTIONS')),
    scenario_type   TEXT    NOT NULL DEFAULT 'normal' CHECK (scenario_type IN (
                        'normal','param_missing','param_type_error',
                        'boundary_value','permission_error','custom'
                    )),
    priority        TEXT    NOT NULL DEFAULT 'P1' CHECK (priority IN ('P0','P1','P2')),
    headers         TEXT    DEFAULT '{}',
    body            TEXT    DEFAULT NULL,
    params          TEXT    DEFAULT NULL,
    cache_rules     TEXT    DEFAULT NULL,
    assert_rules    TEXT    DEFAULT '[]',
    expected_result TEXT    DEFAULT '成功',
    description     TEXT    DEFAULT '',
    remark          TEXT    DEFAULT '',
    unique_hash     TEXT    DEFAULT '',
    generated_by    TEXT    NOT NULL DEFAULT 'llm' CHECK (generated_by IN ('llm','manual','import')),
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (run_id)      REFERENCES test_run(id) ON DELETE CASCADE,
    FOREIGN KEY (api_info_id) REFERENCES api_info(id) ON DELETE SET NULL
);

CREATE INDEX idx_case_run         ON test_case(run_id);
CREATE INDEX idx_case_api         ON test_case(api_info_id);
CREATE INDEX idx_case_case_id     ON test_case(case_id);
CREATE INDEX idx_case_scenario    ON test_case(scenario_type);
CREATE INDEX idx_case_priority    ON test_case(priority);
CREATE INDEX idx_case_hash        ON test_case(unique_hash);
CREATE INDEX idx_case_generated   ON test_case(generated_by);
CREATE INDEX idx_case_active      ON test_case(is_active);

-- ============================================================================
-- 8. 测试结果表 (test_result)
--    对应 models.py -> TestResult
--    完整记录每条用例的执行请求/响应/状态
-- ============================================================================
CREATE TABLE IF NOT EXISTS test_result (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id               INTEGER NOT NULL,
    test_case_id         INTEGER NOT NULL,
    case_id              TEXT    NOT NULL,
    case_name            TEXT    NOT NULL,
    status               TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN (
                             'pending','running','passed','failed','skipped','error'
                         )),
    request_url          TEXT    DEFAULT '',
    request_method       TEXT    DEFAULT '',
    request_headers      TEXT    DEFAULT '{}',
    request_body         TEXT    DEFAULT NULL,
    query_params         TEXT    DEFAULT NULL,
    response_status_code INTEGER DEFAULT NULL,
    response_headers     TEXT    DEFAULT '{}',
    response_body        TEXT    DEFAULT NULL,
    response_time        REAL   NOT NULL DEFAULT 0.0,
    error_message        TEXT    DEFAULT '',
    retry_count          INTEGER NOT NULL DEFAULT 0,
    started_at           TEXT    DEFAULT NULL,
    finished_at          TEXT    DEFAULT NULL,
    created_at           TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (run_id)      REFERENCES test_run(id)  ON DELETE CASCADE,
    FOREIGN KEY (test_case_id) REFERENCES test_case(id) ON DELETE CASCADE
);

CREATE INDEX idx_result_run        ON test_result(run_id);
CREATE INDEX idx_result_case       ON test_result(test_case_id);
CREATE INDEX idx_result_status     ON test_result(status);
CREATE INDEX idx_result_resp_code  ON test_result(response_status_code);
CREATE INDEX idx_result_resp_time  ON test_result(response_time);
CREATE INDEX idx_result_started    ON test_result(started_at);

-- ============================================================================
-- 9. 断言结果表 (assert_result)
--    对应 TestResult.assert_results 列表中的每一条断言
--    从 JSON 拆解为独立行，方便按断言维度聚合分析
-- ============================================================================
CREATE TABLE IF NOT EXISTS assert_result (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    test_result_id  INTEGER NOT NULL,
    rule_expression TEXT    NOT NULL,
    path            TEXT    DEFAULT '',
    operator        TEXT    DEFAULT '' CHECK (operator IN (
                        '==','!=','>','<','>=','<=',
                        'contains','not_contains','matches',
                        'exists','not_exists',''
                    )),
    expected_value  TEXT    DEFAULT NULL,
    actual_value    TEXT    DEFAULT NULL,
    passed          INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT    DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (test_result_id) REFERENCES test_result(id) ON DELETE CASCADE
);

CREATE INDEX idx_assert_result   ON assert_result(test_result_id);
CREATE INDEX idx_assert_passed   ON assert_result(passed);

-- ============================================================================
-- 10. 测试摘要表 (test_summary)
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
-- 11. 参数缓存表 (param_cache)
--     对应 DataCache 单例的持久化
--     记录接口间通过 cache_rules / {{cache:key}} 传递的参数值
-- ============================================================================
CREATE TABLE IF NOT EXISTS param_cache (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL,
    cache_key       TEXT    NOT NULL,
    cache_value     TEXT    DEFAULT NULL,
    source_api_id   TEXT    DEFAULT '',
    source_path     TEXT    DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (run_id) REFERENCES test_run(id) ON DELETE CASCADE
);

CREATE INDEX idx_cache_run  ON param_cache(run_id);
CREATE INDEX idx_cache_key  ON param_cache(cache_key);
CREATE UNIQUE INDEX uk_cache_run_key ON param_cache(run_id, cache_key);

-- ============================================================================
-- 12. 报告记录表 (report)
--     记录每次生成的报告文件路径与元信息
-- ============================================================================
CREATE TABLE IF NOT EXISTS report (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL,
    format          TEXT    NOT NULL CHECK (format IN ('excel','html','markdown','json')),
    file_path       TEXT    NOT NULL,
    file_size       INTEGER DEFAULT 0,
    generated_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (run_id) REFERENCES test_run(id) ON DELETE CASCADE
);

CREATE INDEX idx_report_run    ON report(run_id);
CREATE INDEX idx_report_format ON report(format);

-- ============================================================================
-- 13. LLM 调用日志表 (llm_invocation_log)
--     记录每次 LLM 调用的详情，用于成本分析、质量回溯和 Prompt 调优
-- ============================================================================
CREATE TABLE IF NOT EXISTS llm_invocation_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL,
    provider        TEXT    NOT NULL,
    model           TEXT    NOT NULL,
    purpose         TEXT    NOT NULL DEFAULT 'case_generation' CHECK (purpose IN (
                        'case_generation','report_analysis','validation','other'
                    )),
    prompt_tokens   INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens    INTEGER DEFAULT 0,
    latency_ms      REAL    DEFAULT 0.0,
    system_prompt   TEXT    DEFAULT '',
    user_prompt     TEXT    DEFAULT '',
    raw_response    TEXT    DEFAULT '',
    is_success      INTEGER NOT NULL DEFAULT 1,
    error_message   TEXT    DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (run_id) REFERENCES test_run(id) ON DELETE CASCADE
);

CREATE INDEX idx_llm_run      ON llm_invocation_log(run_id);
CREATE INDEX idx_llm_provider  ON llm_invocation_log(provider);
CREATE INDEX idx_llm_purpose   ON llm_invocation_log(purpose);
CREATE INDEX idx_llm_success   ON llm_invocation_log(is_success);
CREATE INDEX idx_llm_created   ON llm_invocation_log(created_at);

-- ============================================================================
-- 14. 执行日志表 (execution_log)
--     记录工作流各节点的执行日志，辅助排查问题
-- ============================================================================
CREATE TABLE IF NOT EXISTS execution_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL,
    node_name       TEXT    NOT NULL,
    level           TEXT    NOT NULL DEFAULT 'INFO' CHECK (level IN ('DEBUG','INFO','WARNING','ERROR')),
    message         TEXT    NOT NULL,
    extra_data      TEXT    DEFAULT '{}',
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
    FOREIGN KEY (run_id) REFERENCES test_run(id) ON DELETE CASCADE
);

CREATE INDEX idx_execlog_run    ON execution_log(run_id);
CREATE INDEX idx_execlog_node   ON execution_log(node_name);
CREATE INDEX idx_execlog_level  ON execution_log(level);
CREATE INDEX idx_execlog_created ON execution_log(created_at);

-- ============================================================================
-- 触发器：自动更新 updated_at 字段
-- ============================================================================
CREATE TRIGGER trg_project_updated AFTER UPDATE ON project
BEGIN
    UPDATE project SET updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_environment_updated AFTER UPDATE ON environment
BEGIN
    UPDATE environment SET updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_api_info_updated AFTER UPDATE ON api_info
BEGIN
    UPDATE api_info SET updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_test_run_updated AFTER UPDATE ON test_run
BEGIN
    UPDATE test_run SET updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_test_case_updated AFTER UPDATE ON test_case
BEGIN
    UPDATE test_case SET updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')
    WHERE id = NEW.id;
END;

-- ============================================================================
-- 常用分析视图
-- ============================================================================

-- 视图: 每次执行的概览（关联项目、环境、摘要）
CREATE VIEW IF NOT EXISTS v_run_overview AS
SELECT
    tr.id           AS run_id,
    tr.run_id       AS run_code,
    p.name          AS project_name,
    p.domain        AS project_domain,
    e.name          AS environment_name,
    tr.status       AS run_status,
    tr.trigger_type,
    tr.llm_provider,
    tr.llm_model,
    ts.total,
    ts.passed,
    ts.failed,
    ts.skipped,
    ts.error,
    ts.pass_rate,
    ts.avg_response_time,
    ts.p95_response_time,
    ts.total_duration,
    tr.started_at,
    tr.finished_at,
    tr.created_at
FROM test_run tr
LEFT JOIN project     p  ON tr.project_id     = p.id
LEFT JOIN environment e  ON tr.environment_id  = e.id
LEFT JOIN test_summary ts ON ts.run_id         = tr.id;

-- 视图: 接口维度聚合（按 API URL 分组统计通过率）
CREATE VIEW IF NOT EXISTS v_api_pass_rate AS
SELECT
    tr.request_url,
    tr.request_method,
    COUNT(*)                                             AS total_executions,
    SUM(CASE WHEN tr.status = 'passed' THEN 1 ELSE 0 END)  AS passed_count,
    SUM(CASE WHEN tr.status = 'failed' THEN 1 ELSE 0 END)  AS failed_count,
    ROUND(
        SUM(CASE WHEN tr.status = 'passed' THEN 1.0 ELSE 0 END)
        / NULLIF(COUNT(*), 0) * 100, 2
    )                                                    AS pass_rate,
    ROUND(AVG(tr.response_time), 2)                      AS avg_response_time,
    ROUND(MIN(tr.response_time), 2)                      AS min_response_time,
    ROUND(MAX(tr.response_time), 2)                      AS max_response_time
FROM test_result tr
WHERE tr.status IN ('passed','failed')
GROUP BY tr.request_url, tr.request_method;

-- 视图: 场景类型分布（统计各场景类型的测试覆盖情况）
CREATE VIEW IF NOT EXISTS v_scenario_distribution AS
SELECT
    tc.scenario_type,
    COUNT(*)                                                AS total_cases,
    SUM(CASE WHEN tr.status = 'passed' THEN 1 ELSE 0 END)  AS passed,
    SUM(CASE WHEN tr.status = 'failed' THEN 1 ELSE 0 END)  AS failed,
    SUM(CASE WHEN tr.status = 'error'  THEN 1 ELSE 0 END)  AS errors,
    ROUND(
        SUM(CASE WHEN tr.status = 'passed' THEN 1.0 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN tr.status IN ('passed','failed') THEN 1 ELSE 0 END), 0) * 100, 2
    )                                                       AS pass_rate
FROM test_case tc
LEFT JOIN test_result tr ON tr.test_case_id = tc.id
GROUP BY tc.scenario_type;

-- 视图: 失败断言排行（找出最常失败的断言规则）
CREATE VIEW IF NOT EXISTS v_top_failed_assertions AS
SELECT
    ar.rule_expression,
    COUNT(*)                                                 AS total_checks,
    SUM(CASE WHEN ar.passed = 0 THEN 1 ELSE 0 END)          AS fail_count,
    ROUND(
        SUM(CASE WHEN ar.passed = 0 THEN 1.0 ELSE 0 END)
        / NULLIF(COUNT(*), 0) * 100, 2
    )                                                        AS fail_rate
FROM assert_result ar
GROUP BY ar.rule_expression
HAVING fail_count > 0
ORDER BY fail_count DESC;

-- 视图: LLM 使用量统计
CREATE VIEW IF NOT EXISTS v_llm_usage_stats AS
SELECT
    provider,
    model,
    purpose,
    COUNT(*)                          AS invocation_count,
    SUM(total_tokens)                 AS total_tokens_used,
    ROUND(AVG(latency_ms), 2)        AS avg_latency_ms,
    SUM(CASE WHEN is_success = 0 THEN 1 ELSE 0 END) AS failure_count
FROM llm_invocation_log
GROUP BY provider, model, purpose;
