"""
测试执行模块

执行测试用例，支持：
- 依赖拓扑排序执行
- 并行执行（无依赖用例）
- 动态参数替换
- 异常处理和重试
- 断言校验
- 全量日志记录
"""

import re
import time
import json
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JsonPathParserError

from ..core.models import (
    TestCase,
    TestResult,
    TestStatus,
    AssertRule,
    AssertOperator,
)
from ..core.config import get_config, AppConfig


class ExecutionContext:
    """
    执行上下文
    
    存储执行过程中的依赖接口返回值和其他上下文信息。
    
    Attributes:
        responses: 已执行用例的响应数据 {case_id: response_body}
        results: 已执行用例的结果 {case_id: TestResult}
        variables: 自定义变量
    """
    
    def __init__(self):
        """初始化执行上下文"""
        self.responses: Dict[str, Any] = {}
        self.results: Dict[str, TestResult] = {}
        self.variables: Dict[str, Any] = {}
    
    def set_response(self, case_id: str, response: Any) -> None:
        """存储响应数据"""
        self.responses[case_id] = response
    
    def get_response(self, case_id: str) -> Optional[Any]:
        """获取响应数据"""
        return self.responses.get(case_id)
    
    def set_result(self, case_id: str, result: TestResult) -> None:
        """存储执行结果"""
        self.results[case_id] = result
    
    def get_result(self, case_id: str) -> Optional[TestResult]:
        """获取执行结果"""
        return self.results.get(case_id)
    
    def extract_value(self, case_id: str, jsonpath: str) -> Optional[Any]:
        """
        从响应中提取值
        
        Args:
            case_id: 用例ID
            jsonpath: JSONPath表达式
            
        Returns:
            提取的值，如果未找到返回None
        """
        response = self.get_response(case_id)
        if response is None:
            return None
        
        try:
            expr = jsonpath_parse(jsonpath)
            matches = expr.find(response)
            if matches:
                return matches[0].value
        except JsonPathParserError as e:
            logger.warning(f"JSONPath解析失败: {jsonpath}, 错误: {e}")
        
        return None


class TestExecutor:
    """
    测试执行器
    
    执行测试用例并收集结果。
    
    Attributes:
        config: 应用配置
        context: 执行上下文
        session: requests会话
    """
    
    def __init__(self, config: Optional[AppConfig] = None):
        """
        初始化测试执行器
        
        Args:
            config: 应用配置
        """
        self.config = config or get_config()
        self.context = ExecutionContext()
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self) -> None:
        """配置requests会话"""
        # 设置默认超时
        self.session.timeout = (
            self.config.execution.connect_timeout,
            self.config.execution.read_timeout
        )
    
    def execute(self, cases: List[TestCase]) -> List[TestResult]:
        """
        执行测试用例
        
        Args:
            cases: 测试用例列表
            
        Returns:
            List[TestResult]: 测试结果列表
        """
        if not cases:
            return []
        
        # 重置上下文
        self.context = ExecutionContext()
        
        # 拓扑排序
        sorted_cases = self._topological_sort(cases)
        # 固定输出顺序，避免并发执行导致结果顺序抖动
        case_order = {case.case_id: index for index, case in enumerate(sorted_cases)}
        
        # 分组：有依赖和无依赖
        independent_cases = [c for c in sorted_cases if not c.dependencies]
        dependent_cases = [c for c in sorted_cases if c.dependencies]
        
        results: List[TestResult] = []
        
        # 并行执行无依赖用例
        if independent_cases and self.config.execution.concurrency.enabled:
            logger.info(f"并行执行{len(independent_cases)}个无依赖用例")
            independent_results = self._execute_parallel(independent_cases)
            results.extend(independent_results)
        elif independent_cases:
            for case in independent_cases:
                result = self._execute_single(case)
                results.append(result)
        
        # 串行执行有依赖用例
        for case in dependent_cases:
            # 检查依赖是否满足
            if not self._check_dependencies(case):
                result = TestResult(
                    case_id=case.case_id,
                    case_name=case.case_name,
                    status=TestStatus.SKIPPED,
                    error_message="依赖接口执行失败，跳过执行",
                    started_at=datetime.now(),
                    finished_at=datetime.now(),
                )
                results.append(result)
                self.context.set_result(case.case_id, result)
                logger.warning(f"用例[{case.case_id}]因依赖失败被跳过")
                continue
            
            result = self._execute_single(case)
            results.append(result)
        
        # 并发执行时 future 完成顺序不稳定，统一按用例拓扑顺序输出
        results.sort(key=lambda result: case_order.get(result.case_id, len(case_order)))
        
        logger.info(f"测试执行完成: {len(results)}个用例")
        return results
    
    def _execute_parallel(self, cases: List[TestCase]) -> List[TestResult]:
        """
        并行执行用例
        
        Args:
            cases: 测试用例列表
            
        Returns:
            List[TestResult]: 测试结果列表
        """
        results: List[TestResult] = []
        max_workers = self.config.execution.concurrency.max_workers
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_case = {
                executor.submit(self._execute_single, case): case 
                for case in cases
            }
            
            for future in as_completed(future_to_case):
                case = future_to_case[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"用例[{case.case_id}]执行异常: {str(e)}")
                    result = TestResult(
                        case_id=case.case_id,
                        case_name=case.case_name,
                        status=TestStatus.ERROR,
                        error_message=str(e),
                        started_at=datetime.now(),
                        finished_at=datetime.now(),
                    )
                    results.append(result)
        
        return results
    
    def _execute_single(self, case: TestCase) -> TestResult:
        """
        执行单个用例
        
        Args:
            case: 测试用例
            
        Returns:
            TestResult: 测试结果
        """
        result = TestResult(
            case_id=case.case_id,
            case_name=case.case_name,
            status=TestStatus.RUNNING,
            started_at=datetime.now(),
        )
        
        retry_count = 0
        max_retries = self.config.execution.retry.max_retries
        retry_interval = self.config.execution.retry.retry_interval
        
        while True:
            try:
                # 替换动态参数
                headers, body = self._replace_dynamic_params(case)
                
                # 记录请求信息
                result.request_url = case.api_url
                result.request_method = case.method.value
                result.request_headers = headers
                result.request_body = body
                
                # 发送请求
                start_time = time.time()
                response = self._send_request(case, headers, body)
                end_time = time.time()
                
                # 记录响应信息
                result.response_time = (end_time - start_time) * 1000  # 转为毫秒
                result.response_status_code = response.status_code
                result.response_headers = dict(response.headers)
                
                try:
                    result.response_body = response.json()
                except json.JSONDecodeError:
                    result.response_body = response.text
                
                # 存储响应到上下文
                self.context.set_response(case.case_id, result.response_body)
                
                # 执行断言
                assert_results = self._execute_assertions(case, result)
                result.assert_results = assert_results
                
                # 判断结果
                all_passed = all(ar.get("passed", False) for ar in assert_results)
                result.status = TestStatus.PASSED if all_passed else TestStatus.FAILED
                
                if not all_passed:
                    failed_assertions = [ar for ar in assert_results if not ar.get("passed", False)]
                    result.error_message = f"断言失败: {failed_assertions}"
                
                break  # 执行成功，退出重试循环
                
            except Timeout as e:
                retry_count += 1
                result.retry_count = retry_count
                if retry_count <= max_retries:
                    logger.warning(f"用例[{case.case_id}]超时，重试{retry_count}/{max_retries}")
                    time.sleep(retry_interval)
                    continue
                result.status = TestStatus.ERROR
                result.error_message = f"请求超时: {str(e)}"
                break
                
            except ConnectionError as e:
                retry_count += 1
                result.retry_count = retry_count
                if retry_count <= max_retries:
                    logger.warning(f"用例[{case.case_id}]连接错误，重试{retry_count}/{max_retries}")
                    time.sleep(retry_interval)
                    continue
                result.status = TestStatus.ERROR
                result.error_message = f"连接错误: {str(e)}"
                break
                
            except RequestException as e:
                result.status = TestStatus.ERROR
                result.error_message = f"请求异常: {str(e)}"
                break
                
            except Exception as e:
                result.status = TestStatus.ERROR
                result.error_message = f"执行异常: {str(e)}"
                logger.exception(f"用例[{case.case_id}]执行异常")
                break
        
        result.finished_at = datetime.now()
        self.context.set_result(case.case_id, result)
        
        # 记录日志
        self._log_execution(case, result)
        
        return result
    
    def _send_request(
        self, 
        case: TestCase, 
        headers: Dict[str, str], 
        body: Optional[Dict[str, Any]]
    ) -> requests.Response:
        """
        发送HTTP请求
        
        Args:
            case: 测试用例
            headers: 请求头
            body: 请求体
            
        Returns:
            requests.Response: 响应对象
        """
        method = case.method.value.upper()
        url = case.api_url
        
        # 处理查询参数
        params = case.query_params
        
        # 设置超时
        timeout = (
            self.config.execution.connect_timeout,
            self.config.execution.read_timeout
        )
        
        # 发送请求
        if method == "GET":
            response = self.session.get(url, headers=headers, params=params, timeout=timeout)
        elif method == "POST":
            response = self.session.post(url, headers=headers, json=body, params=params, timeout=timeout)
        elif method == "PUT":
            response = self.session.put(url, headers=headers, json=body, params=params, timeout=timeout)
        elif method == "DELETE":
            response = self.session.delete(url, headers=headers, json=body, params=params, timeout=timeout)
        elif method == "PATCH":
            response = self.session.patch(url, headers=headers, json=body, params=params, timeout=timeout)
        else:
            response = self.session.request(method, url, headers=headers, json=body, params=params, timeout=timeout)
        
        return response
    
    def _replace_dynamic_params(
        self, case: TestCase
    ) -> Tuple[Dict[str, str], Optional[Dict[str, Any]]]:
        """
        替换动态参数
        
        支持的占位符：
        - {{timestamp}} - 当前时间戳
        - {{uuid}} - 随机UUID
        - {{random_str:N}} - N位随机字符串
        - {{random_int:MIN:MAX}} - MIN到MAX的随机整数
        - {{dep:API_ID:JSONPATH}} - 依赖接口返回值
        
        Args:
            case: 测试用例
            
        Returns:
            Tuple[Dict[str, str], Optional[Dict[str, Any]]]: 替换后的请求头和请求体
        """
        headers = case.headers.copy()
        body = case.body.copy() if case.body else None
        
        # 替换请求头中的占位符
        for key, value in headers.items():
            if isinstance(value, str):
                headers[key] = self._replace_placeholder(value)
        
        # 替换请求体中的占位符
        if body:
            body = self._replace_in_dict(body)
        
        # 处理依赖关系
        for dep_id, dep_info in case.dependencies.items():
            source_path = dep_info.get("source_path", "")
            target_param = dep_info.get("target_param", "")
            
            # 从上下文提取依赖值
            dep_value = self.context.extract_value(dep_id, source_path)
            
            if dep_value is not None:
                # 注入到目标参数
                if target_param.startswith("headers."):
                    header_key = target_param[8:]
                    headers[header_key] = str(dep_value)
                elif target_param.startswith("body."):
                    body_key = target_param[5:]
                    if body:
                        body[body_key] = dep_value
        
        return headers, body
    
    def _replace_placeholder(self, value: str) -> str:
        """
        替换字符串中的占位符
        
        Args:
            value: 原始字符串
            
        Returns:
            str: 替换后的字符串
        """
        import random
        import string
        
        # {{timestamp}}
        value = value.replace("{{timestamp}}", str(int(time.time() * 1000)))
        
        # {{uuid}}
        value = value.replace("{{uuid}}", str(uuid.uuid4()))
        
        # {{random_str:N}}
        random_str_pattern = r"\{\{random_str:(\d+)\}\}"
        for match in re.finditer(random_str_pattern, value):
            length = int(match.group(1))
            random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
            value = value.replace(match.group(0), random_str)
        
        # {{random_int:MIN:MAX}}
        random_int_pattern = r"\{\{random_int:(\d+):(\d+)\}\}"
        for match in re.finditer(random_int_pattern, value):
            min_val = int(match.group(1))
            max_val = int(match.group(2))
            random_int = random.randint(min_val, max_val)
            value = value.replace(match.group(0), str(random_int))
        
        # {{dep:API_ID:JSONPATH}}
        dep_pattern = r"\{\{dep:([^:]+):([^}]+)\}\}"
        for match in re.finditer(dep_pattern, value):
            api_id = match.group(1)
            jsonpath = match.group(2)
            dep_value = self.context.extract_value(api_id, jsonpath)
            if dep_value is not None:
                value = value.replace(match.group(0), str(dep_value))
        
        return value
    
    def _replace_in_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归替换字典中的占位符
        
        Args:
            data: 原始字典
            
        Returns:
            Dict[str, Any]: 替换后的字典
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self._replace_placeholder(value)
            elif isinstance(value, dict):
                result[key] = self._replace_in_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._replace_placeholder(item) if isinstance(item, str)
                    else self._replace_in_dict(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result
    
    def _execute_assertions(
        self, case: TestCase, result: TestResult
    ) -> List[Dict[str, Any]]:
        """
        执行断言校验
        
        Args:
            case: 测试用例
            result: 测试结果
            
        Returns:
            List[Dict[str, Any]]: 断言结果列表
        """
        assert_results = []
        
        for rule_str in case.assert_rules:
            try:
                rule = AssertRule.parse(rule_str)
                passed, actual_value = self._check_assertion(rule, result)
                
                assert_results.append({
                    "rule": rule_str,
                    "passed": passed,
                    "expected": rule.expected,
                    "actual": actual_value,
                })
            except Exception as e:
                assert_results.append({
                    "rule": rule_str,
                    "passed": False,
                    "error": str(e),
                })
        
        return assert_results
    
    def _check_assertion(
        self, rule: AssertRule, result: TestResult
    ) -> Tuple[bool, Any]:
        """
        检查单个断言
        
        Args:
            rule: 断言规则
            result: 测试结果
            
        Returns:
            Tuple[bool, Any]: (是否通过, 实际值)
        """
        # 获取实际值
        if rule.path == "response_time":
            actual_value = result.response_time
        elif rule.path == "status_code":
            actual_value = result.response_status_code
        elif rule.path.startswith("$."):
            try:
                expr = jsonpath_parse(rule.path)
                matches = expr.find(result.response_body)
                actual_value = matches[0].value if matches else None
            except Exception:
                actual_value = None
        else:
            actual_value = None
        
        # 执行比较
        expected = rule.expected
        operator = rule.operator
        
        if operator == AssertOperator.EQ:
            passed = actual_value == expected
        elif operator == AssertOperator.NE:
            passed = actual_value != expected
        elif operator == AssertOperator.GT:
            passed = actual_value is not None and actual_value > expected
        elif operator == AssertOperator.LT:
            passed = actual_value is not None and actual_value < expected
        elif operator == AssertOperator.GE:
            passed = actual_value is not None and actual_value >= expected
        elif operator == AssertOperator.LE:
            passed = actual_value is not None and actual_value <= expected
        elif operator == AssertOperator.CONTAINS:
            passed = actual_value is not None and str(expected) in str(actual_value)
        elif operator == AssertOperator.NOT_CONTAINS:
            passed = actual_value is None or str(expected) not in str(actual_value)
        elif operator == AssertOperator.EXISTS:
            passed = actual_value is not None
        elif operator == AssertOperator.NOT_EXISTS:
            passed = actual_value is None
        elif operator == AssertOperator.MATCHES:
            passed = actual_value is not None and bool(re.match(str(expected), str(actual_value)))
        else:
            passed = False
        
        return passed, actual_value
    
    def _check_dependencies(self, case: TestCase) -> bool:
        """
        检查依赖是否满足
        
        Args:
            case: 测试用例
            
        Returns:
            bool: 依赖是否全部满足
        """
        for dep_id in case.dependencies.keys():
            dep_result = self.context.get_result(dep_id)
            if dep_result is None or dep_result.status != TestStatus.PASSED:
                return False
        return True
    
    def _topological_sort(self, cases: List[TestCase]) -> List[TestCase]:
        """
        拓扑排序
        
        Args:
            cases: 测试用例列表
            
        Returns:
            List[TestCase]: 排序后的用例列表
        """
        # 构建用例ID映射
        case_map = {case.case_id: case for case in cases}
        # 也用case_name作为映射（兼容依赖关系中使用name的情况）
        for case in cases:
            case_map[case.case_name] = case
        
        # 计算入度
        in_degree: Dict[str, int] = {case.case_id: 0 for case in cases}
        for case in cases:
            for dep_id in case.dependencies.keys():
                if dep_id in case_map:
                    in_degree[case.case_id] += 1
        
        # 拓扑排序
        queue = [case_id for case_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current_id = queue.pop(0)
            current_case = case_map.get(current_id)
            if current_case and current_case not in result:
                result.append(current_case)
            
            # 更新入度
            for case in cases:
                if current_id in case.dependencies or current_case.case_name in case.dependencies:
                    in_degree[case.case_id] -= 1
                    if in_degree[case.case_id] == 0 and case.case_id not in [c.case_id for c in result]:
                        queue.append(case.case_id)
        
        # 添加未排序的用例（可能存在循环依赖）
        for case in cases:
            if case not in result:
                result.append(case)
        
        return result
    
    def _log_execution(self, case: TestCase, result: TestResult) -> None:
        """
        记录执行日志
        
        Args:
            case: 测试用例
            result: 测试结果
        """
        status_emoji = {
            TestStatus.PASSED: "✅",
            TestStatus.FAILED: "❌",
            TestStatus.SKIPPED: "⏭️",
            TestStatus.ERROR: "💥",
        }
        
        emoji = status_emoji.get(result.status, "❓")
        logger.info(
            f"{emoji} [{result.case_id}] {result.case_name} - "
            f"状态: {result.status.value}, "
            f"耗时: {result.response_time:.2f}ms"
        )
        
        if result.error_message:
            logger.error(f"  错误: {result.error_message}")


def execute_tests(
    cases: List[TestCase],
    config: Optional[AppConfig] = None
) -> List[TestResult]:
    """
    执行测试的便捷函数
    
    Args:
        cases: 测试用例列表
        config: 应用配置
        
    Returns:
        List[TestResult]: 测试结果列表
    """
    executor = TestExecutor(config)
    return executor.execute(cases)
