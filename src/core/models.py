"""
数据模型模块

定义API测试相关的Pydantic数据模型，包括：
- APIInfo: API信息
- TestCase: 测试用例
- TestResult: 测试结果
- Dependency: 依赖关系
- AssertRule: 断言规则
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import re
import hashlib
import json


class HttpMethod(str, Enum):
    """HTTP请求方法"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class Priority(str, Enum):
    """用例优先级"""
    P0 = "P0"  # 冒烟用例
    P1 = "P1"  # 核心用例
    P2 = "P2"  # 全量用例


class TestStatus(str, Enum):
    """测试状态"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    PASSED = "passed"        # 通过
    FAILED = "failed"        # 失败
    SKIPPED = "skipped"      # 跳过
    ERROR = "error"          # 错误


class ScenarioType(str, Enum):
    """场景类型"""
    NORMAL = "normal"                    # 正常场景
    PARAM_MISSING = "param_missing"      # 参数缺失
    PARAM_TYPE_ERROR = "param_type_error"  # 参数类型错误
    BOUNDARY_VALUE = "boundary_value"    # 边界值
    PERMISSION_ERROR = "permission_error"  # 权限异常
    CUSTOM = "custom"                    # 自定义


class AssertOperator(str, Enum):
    """断言运算符"""
    EQ = "=="           # 等于
    NE = "!="           # 不等于
    GT = ">"            # 大于
    LT = "<"            # 小于
    GE = ">="           # 大于等于
    LE = "<="           # 小于等于
    CONTAINS = "contains"        # 包含
    NOT_CONTAINS = "not_contains"  # 不包含
    MATCHES = "matches"          # 正则匹配
    EXISTS = "exists"            # 存在
    NOT_EXISTS = "not_exists"    # 不存在


class AssertRule(BaseModel):
    """
    断言规则
    
    Attributes:
        path: JSONPath表达式或特殊字段（如response_time）
        operator: 断言运算符
        expected: 期望值
        raw_expression: 原始表达式
    """
    path: str = Field(..., description="JSONPath表达式")
    operator: AssertOperator = Field(..., description="断言运算符")
    expected: Any = Field(..., description="期望值")
    raw_expression: str = Field(default="", description="原始表达式")
    
    @classmethod
    def parse(cls, expression: str) -> "AssertRule":
        """
        解析断言表达式
        
        Args:
            expression: 断言表达式，如 "$.code == 200"
            
        Returns:
            AssertRule: 断言规则对象
        """
        expression = expression.strip()
        
        # 定义运算符映射（按长度降序排列，避免匹配问题）
        operators = [
            ("not_contains", AssertOperator.NOT_CONTAINS),
            ("not_exists", AssertOperator.NOT_EXISTS),
            ("contains", AssertOperator.CONTAINS),
            ("matches", AssertOperator.MATCHES),
            ("exists", AssertOperator.EXISTS),
            (">=", AssertOperator.GE),
            ("<=", AssertOperator.LE),
            ("!=", AssertOperator.NE),
            ("==", AssertOperator.EQ),
            (">", AssertOperator.GT),
            ("<", AssertOperator.LT),
        ]
        
        for op_str, op_enum in operators:
            if f" {op_str} " in expression:
                parts = expression.split(f" {op_str} ", 1)
                path = parts[0].strip()
                expected_str = parts[1].strip()
                
                # 解析期望值
                expected = cls._parse_expected_value(expected_str)
                
                return cls(
                    path=path,
                    operator=op_enum,
                    expected=expected,
                    raw_expression=expression
                )
        
        raise ValueError(f"无法解析断言表达式: {expression}")
    
    @staticmethod
    def _parse_expected_value(value_str: str) -> Any:
        """解析期望值字符串"""
        value_str = value_str.strip()
        
        # null
        if value_str.lower() == "null" or value_str.lower() == "none":
            return None
        
        # 布尔值
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False
        
        # 数字
        try:
            if "." in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass
        
        # 字符串（去除引号）
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]
        
        return value_str


class Dependency(BaseModel):
    """
    依赖关系
    
    Attributes:
        source_api_id: 依赖的API/用例ID
        source_path: 从依赖接口响应中提取值的JSONPath
        target_param: 目标参数位置（如 headers.Authorization, body.token）
    """
    source_api_id: str = Field(..., description="依赖的API/用例ID")
    source_path: str = Field(..., description="JSONPath表达式")
    target_param: str = Field(..., description="目标参数位置")
    
    @field_validator("source_path")
    @classmethod
    def validate_jsonpath(cls, v: str) -> str:
        """验证JSONPath格式"""
        if not v.startswith("$."):
            raise ValueError(f"JSONPath必须以$.开头: {v}")
        return v
    
    @field_validator("target_param")
    @classmethod
    def validate_target_param(cls, v: str) -> str:
        """验证目标参数格式"""
        valid_prefixes = ["headers.", "body.", "query.", "path."]
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"目标参数必须以 {valid_prefixes} 之一开头: {v}")
        return v


class APIInfo(BaseModel):
    """
    API信息
    
    Attributes:
        name: API名称
        api_url: API地址
        method: 请求方法
        headers: 请求头
        body: 请求体
        query_params: 查询参数
        assert_rules: 断言规则列表
        dependencies: 依赖关系
        priority: 优先级
        description: 描述
        tags: 标签
    """
    name: str = Field(..., description="API名称")
    api_url: str = Field(..., description="API地址")
    method: HttpMethod = Field(..., description="请求方法")
    headers: Dict[str, str] = Field(default_factory=dict, description="请求头")
    body: Optional[Dict[str, Any]] = Field(default=None, description="请求体")
    query_params: Optional[Dict[str, Any]] = Field(default=None, description="查询参数")
    assert_rules: List[str] = Field(default_factory=list, description="断言规则列表")
    dependencies: Dict[str, Dict[str, str]] = Field(default_factory=dict, description="依赖关系")
    priority: Priority = Field(default=Priority.P1, description="优先级")
    description: str = Field(default="", description="描述")
    tags: List[str] = Field(default_factory=list, description="标签")
    
    @field_validator("api_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """验证URL格式"""
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"API地址必须以http://或https://开头: {v}")
        return v
    
    @property
    def api_id(self) -> str:
        """生成API唯一ID"""
        return self.name.replace(" ", "_").lower()
    
    def get_parsed_assert_rules(self) -> List[AssertRule]:
        """获取解析后的断言规则"""
        rules = []
        for rule_str in self.assert_rules:
            try:
                rules.append(AssertRule.parse(rule_str))
            except ValueError as e:
                # 记录解析失败的规则，但不中断
                pass
        return rules
    
    def get_parsed_dependencies(self) -> List[Dependency]:
        """获取解析后的依赖关系"""
        deps = []
        for api_id, dep_info in self.dependencies.items():
            deps.append(Dependency(
                source_api_id=api_id,
                source_path=dep_info.get("source_path", ""),
                target_param=dep_info.get("target_param", "")
            ))
        return deps


class TestCase(BaseModel):
    """
    测试用例
    
    Attributes:
        case_id: 用例ID
        case_name: 用例名称
        api_info: API信息
        scenario_type: 场景类型
        priority: 优先级
        headers: 请求头（可能被修改）
        body: 请求体（可能被修改）
        assert_rules: 断言规则
        dependencies: 依赖关系
        expected_result: 预期结果
        description: 描述
        created_at: 创建时间
    """
    case_id: str = Field(..., description="用例ID")
    case_name: str = Field(..., description="用例名称")
    api_url: str = Field(..., description="API地址")
    method: HttpMethod = Field(..., description="请求方法")
    scenario_type: ScenarioType = Field(default=ScenarioType.NORMAL, description="场景类型")
    priority: Priority = Field(default=Priority.P1, description="优先级")
    headers: Dict[str, str] = Field(default_factory=dict, description="请求头")
    body: Optional[Dict[str, Any]] = Field(default=None, description="请求体")
    query_params: Optional[Dict[str, Any]] = Field(default=None, description="查询参数")
    assert_rules: List[str] = Field(default_factory=list, description="断言规则")
    dependencies: Dict[str, Dict[str, str]] = Field(default_factory=dict, description="依赖关系")
    expected_result: str = Field(default="成功", description="预期结果")
    description: str = Field(default="", description="描述")
    remark: str = Field(default="", description="备注")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    @classmethod
    def from_api_info(
        cls,
        api_info: APIInfo,
        scenario_type: ScenarioType = ScenarioType.NORMAL,
        case_suffix: str = "001",
        modified_headers: Optional[Dict[str, str]] = None,
        modified_body: Optional[Dict[str, Any]] = None,
        expected_result: str = "成功",
        description: str = "",
    ) -> "TestCase":
        """
        从API信息创建测试用例
        
        Args:
            api_info: API信息
            scenario_type: 场景类型
            case_suffix: 用例后缀
            modified_headers: 修改后的请求头
            modified_body: 修改后的请求体
            expected_result: 预期结果
            description: 描述
            
        Returns:
            TestCase: 测试用例
        """
        case_id = f"{api_info.api_id}_{scenario_type.value}_{case_suffix}"
        case_name = f"{api_info.name} - {scenario_type.value}"
        
        return cls(
            case_id=case_id,
            case_name=case_name,
            api_url=api_info.api_url,
            method=api_info.method,
            scenario_type=scenario_type,
            priority=api_info.priority,
            headers=modified_headers or api_info.headers.copy(),
            body=modified_body if modified_body is not None else (api_info.body.copy() if api_info.body else None),
            query_params=api_info.query_params.copy() if api_info.query_params else None,
            assert_rules=api_info.assert_rules.copy(),
            dependencies=api_info.dependencies.copy(),
            expected_result=expected_result,
            description=description or api_info.description,
        )
    
    def get_unique_hash(self) -> str:
        """生成用例唯一哈希（用于去重）"""
        content = f"{self.api_url}|{self.method}|{json.dumps(self.body, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()[:8]


class TestResult(BaseModel):
    """
    测试结果
    
    Attributes:
        case_id: 用例ID
        case_name: 用例名称
        status: 测试状态
        request_url: 实际请求URL
        request_method: 请求方法
        request_headers: 请求头
        request_body: 请求体
        response_status_code: 响应状态码
        response_headers: 响应头
        response_body: 响应体
        response_time: 响应时间（毫秒）
        assert_results: 断言结果列表
        error_message: 错误信息
        started_at: 开始时间
        finished_at: 结束时间
    """
    case_id: str = Field(..., description="用例ID")
    case_name: str = Field(..., description="用例名称")
    status: TestStatus = Field(default=TestStatus.PENDING, description="测试状态")
    request_url: str = Field(default="", description="实际请求URL")
    request_method: str = Field(default="", description="请求方法")
    request_headers: Dict[str, str] = Field(default_factory=dict, description="请求头")
    request_body: Optional[Dict[str, Any]] = Field(default=None, description="请求体")
    response_status_code: Optional[int] = Field(default=None, description="响应状态码")
    response_headers: Dict[str, str] = Field(default_factory=dict, description="响应头")
    response_body: Optional[Any] = Field(default=None, description="响应体")
    response_time: float = Field(default=0.0, description="响应时间（毫秒）")
    assert_results: List[Dict[str, Any]] = Field(default_factory=list, description="断言结果")
    error_message: str = Field(default="", description="错误信息")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    finished_at: Optional[datetime] = Field(default=None, description="结束时间")
    retry_count: int = Field(default=0, description="重试次数")
    
    @property
    def duration(self) -> float:
        """计算执行时长（秒）"""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return 0.0
    
    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.status == TestStatus.PASSED


class ValidationResult(BaseModel):
    """
    校验结果
    
    Attributes:
        is_valid: 是否有效
        errors: 错误列表
        warnings: 警告列表
    """
    is_valid: bool = Field(default=True, description="是否有效")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    
    def add_error(self, message: str) -> None:
        """添加错误"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        """添加警告"""
        self.warnings.append(message)


class TestSummary(BaseModel):
    """
    测试摘要
    
    Attributes:
        total: 总用例数
        passed: 通过数
        failed: 失败数
        skipped: 跳过数
        error: 错误数
        pass_rate: 通过率
        avg_response_time: 平均响应时间
        min_response_time: 最小响应时间
        max_response_time: 最大响应时间
        p95_response_time: P95响应时间
        total_duration: 总执行时长
        started_at: 开始时间
        finished_at: 结束时间
    """
    total: int = Field(default=0, description="总用例数")
    passed: int = Field(default=0, description="通过数")
    failed: int = Field(default=0, description="失败数")
    skipped: int = Field(default=0, description="跳过数")
    error: int = Field(default=0, description="错误数")
    pass_rate: float = Field(default=0.0, description="通过率")
    avg_response_time: float = Field(default=0.0, description="平均响应时间（毫秒）")
    min_response_time: float = Field(default=0.0, description="最小响应时间（毫秒）")
    max_response_time: float = Field(default=0.0, description="最大响应时间（毫秒）")
    p95_response_time: float = Field(default=0.0, description="P95响应时间（毫秒）")
    total_duration: float = Field(default=0.0, description="总执行时长（秒）")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    finished_at: Optional[datetime] = Field(default=None, description="结束时间")
    failure_reasons: Dict[str, int] = Field(default_factory=dict, description="失败原因统计")
    
    @classmethod
    def from_results(cls, results: List[TestResult]) -> "TestSummary":
        """
        从测试结果列表生成摘要
        
        Args:
            results: 测试结果列表
            
        Returns:
            TestSummary: 测试摘要
        """
        if not results:
            return cls()
        
        total = len(results)
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        error = sum(1 for r in results if r.status == TestStatus.ERROR)
        
        # 计算通过率
        executed = total - skipped
        pass_rate = (passed / executed * 100) if executed > 0 else 0.0
        
        # 计算响应时间统计
        response_times = [r.response_time for r in results if r.response_time > 0]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            # P95
            sorted_times = sorted(response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p95_response_time = sorted_times[min(p95_index, len(sorted_times) - 1)]
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = 0.0
        
        # 统计失败原因
        failure_reasons: Dict[str, int] = {}
        for r in results:
            if r.status in (TestStatus.FAILED, TestStatus.ERROR) and r.error_message:
                reason = r.error_message[:50]  # 截取前50个字符
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        
        # 计算总时长
        start_times = [r.started_at for r in results if r.started_at]
        end_times = [r.finished_at for r in results if r.finished_at]
        started_at = min(start_times) if start_times else None
        finished_at = max(end_times) if end_times else None
        total_duration = (finished_at - started_at).total_seconds() if started_at and finished_at else 0.0
        
        return cls(
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            error=error,
            pass_rate=round(pass_rate, 2),
            avg_response_time=round(avg_response_time, 2),
            min_response_time=round(min_response_time, 2),
            max_response_time=round(max_response_time, 2),
            p95_response_time=round(p95_response_time, 2),
            total_duration=round(total_duration, 2),
            started_at=started_at,
            finished_at=finished_at,
            failure_reasons=failure_reasons,
        )


class WorkflowState(BaseModel):
    """
    工作流状态
    
    用于LangGraph StateGraph的状态管理
    """
    # 输入
    raw_input: Dict[str, Any] = Field(default_factory=dict, description="原始输入")
    
    # 解析结果
    api_infos: List[APIInfo] = Field(default_factory=list, description="API信息列表")
    validation_result: Optional[ValidationResult] = Field(default=None, description="校验结果")
    
    # 用例
    test_cases: List[TestCase] = Field(default_factory=list, description="测试用例列表")
    
    # 执行
    execution_context: Dict[str, Any] = Field(default_factory=dict, description="执行上下文")
    test_results: List[TestResult] = Field(default_factory=list, description="测试结果列表")
    
    # 报告
    test_summary: Optional[TestSummary] = Field(default=None, description="测试摘要")
    report_paths: Dict[str, str] = Field(default_factory=dict, description="报告路径")
    
    # 工作流控制
    current_node: str = Field(default="", description="当前节点")
    error_message: str = Field(default="", description="错误信息")
    retry_count: int = Field(default=0, description="重试次数")
    
    class Config:
        arbitrary_types_allowed = True
