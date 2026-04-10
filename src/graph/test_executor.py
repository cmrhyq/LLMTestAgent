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
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import requests
from requests import Response
from requests.exceptions import RequestException, Timeout, ConnectionError
from jsonpath_ng import parse as jsonpath_parse

from src.core.cache.data_cache import DataCache
from src.core.models import (
    TestCase,
    TestResult,
    TestStatus,
    AssertRule,
    AssertOperator,
)
from src.core.config import get_config, AppConfig
from src.core.logging import get_logger, log_execution_time
from src.utils.http.request import HttpRequest

logger = get_logger(__name__)


class TestExecutor:
    """
    测试执行器

    执行测试用例并收集结果。

    Attributes:
        config: 应用配置
        # context: 执行上下文
        session: requests会话
    """

    def __init__(self, config: Optional[AppConfig] = None):
        """
        初始化测试执行器

        Args:
            config: 应用配置
        """
        self.cache = DataCache.get_instance()
        self.config = config or get_config()

    @log_execution_time(name="executor_test_case", level="info")
    def execute(self, domain: str, cases: list[TestCase]) -> List[TestResult]:
        """
        执行测试用例

        Args:
            domain: 被测网站域名
            cases: 测试用例列表

        Returns:
            List[TestResult]: 测试结果列表
        """
        if not cases:
            return []

        results: List[TestResult] = []
        for case in cases:
            case_result = TestResult(
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
                    url, headers, body = self._replace_dynamic_params(case)

                    # 记录请求信息
                    case_result.request_url = url
                    case_result.request_method = case.method.value
                    case_result.request_headers = headers
                    case_result.request_body = body

                    # 发送请求
                    start_time = time.time()
                    response = self._send_request(domain, url, case.method.value, headers, body)
                    end_time = time.time()

                    # 记录响应信息
                    case_result.response_time = (end_time - start_time) * 1000  # 转为毫秒
                    case_result.response_status_code = response.status_code
                    case_result.response_headers = dict(response.headers)

                    try:
                        case_result.response_body = response.json()
                    except json.JSONDecodeError:
                        case_result.response_body = response.text

                    # 存储参数到缓存
                    if case.cache_rules and case_result.response_body:
                        self._cache_response_params(case.cache_rules, case_result.response_body)

                    # 执行断言
                    assert_results = self._execute_assertions(case, case_result)
                    case_result.assert_results = assert_results

                    # 判断结果
                    all_passed = all(ar.get("passed", False) for ar in assert_results)
                    case_result.status = TestStatus.PASSED if all_passed else TestStatus.FAILED

                    if not all_passed:
                        failed_assertions = [ar for ar in assert_results if not ar.get("passed", False)]
                        case_result.error_message = f"断言失败: {failed_assertions}"

                    break  # 执行成功，退出重试循环

                except Timeout as e:
                    retry_count += 1
                    case_result.retry_count = retry_count
                    if retry_count <= max_retries:
                        logger.warning(f"用例[{case.case_id}]超时，重试{retry_count}/{max_retries}")
                        time.sleep(retry_interval)
                        continue
                    case_result.status = TestStatus.ERROR
                    case_result.error_message = f"请求超时: {str(e)}"
                    break

                except ConnectionError as e:
                    retry_count += 1
                    case_result.retry_count = retry_count
                    if retry_count <= max_retries:
                        logger.warning(f"用例[{case.case_id}]连接错误，重试{retry_count}/{max_retries}")
                        time.sleep(retry_interval)
                        continue
                    case_result.status = TestStatus.ERROR
                    case_result.error_message = f"连接错误: {str(e)}"
                    break

                except RequestException as e:
                    case_result.status = TestStatus.ERROR
                    case_result.error_message = f"请求异常: {str(e)}"
                    break

                except Exception as e:
                    case_result.status = TestStatus.ERROR
                    case_result.error_message = f"执行异常: {str(e)}"
                    logger.exception(f"用例[{case.case_id}]执行异常")
                    break

            case_result.finished_at = datetime.now()
            results.append(case_result)

        return results

    def _send_request(
        self,
        domain: str,
        url: str,
        method: str,
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]]
    ) -> Response | None:
        """
        发送HTTP请求

        Args:
            url: 请求地址
            method: 请求方法
            headers: 请求头
            body: 请求体

        Returns:
            requests.Response: 响应对象
        """
        method = method.upper()
        url = url

        # 处理查询参数
        params = None

        http_client = HttpRequest(
            base_url=domain,
            connect_timeout=self.config.execution.connect_timeout,
            read_timeout=self.config.execution.read_timeout
        )

        # 发送请求
        if method == "GET":
            response = http_client.get(url, headers=headers, params=params)
        elif method == "POST":
            response = http_client.post(url, headers=headers, json=body, params=params)
        elif method == "PUT":
            response = http_client.put(url, headers=headers, json=body, params=params)
        elif method == "DELETE":
            response = http_client.delete(url, headers=headers, json=body, params=params)
        elif method == "PATCH":
            response = http_client.patch(url, headers=headers, json=body, params=params)
        else:
            response = None
            logger.error(f"{url}使用了不受支持的请求方法：{method}")

        return response

    def _replace_dynamic_params(
        self, case: TestCase
    ) -> tuple[str, dict[str, str], dict[str, Any] | None]:
        """
        替换动态参数

        支持的占位符：
        - {{timestamp}} - 当前时间戳
        - {{uuid}} - 随机UUID
        - {{random_str:N}} - N位随机字符串
        - {{random_int:MIN:MAX}} - MIN到MAX的随机整数
        - {{cache:CACHE_KEY}} - 依赖接口返回值

        Args:
            case: 测试用例

        Returns:
            Tuple[Dict[str, str], Optional[Dict[str, Any]]]: 替换后的请求头和请求体
        """
        url = case.url
        headers = case.headers.copy()
        body = case.body.copy() if case.body else None

        # 处理API URL的占位符
        url = self._replace_placeholder(url)

        # 替换请求头中的占位符
        for key, value in headers.items():
            if isinstance(value, str):
                headers[key] = self._replace_placeholder(value)

        # 替换请求体中的占位符
        if body:
            body = self._replace_in_dict(body)

        return url, headers, body

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

        # {{cache:CACHE_KEY}}
        cache_pattern = r"\{\{cache:([^}]+)\}\}"
        for match in re.finditer(cache_pattern, value):
            cache_key = match.group(1)
            dep_value = self.cache.get(cache_key)
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
        elif rule.path.startswith("$"):
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

    def _cache_response_params(self, cache_rules: dict, response: dict[str, Any]):
        """
        存储需要缓存的参数到全局缓存

        Args:
            cache_rules: 缓存规则字典
            response: 响应

        Returns:
            None
        """
        try:
            for index, rule in cache_rules.items():
                expr = jsonpath_parse(rule)
                matches = expr.find(response)
                self.cache.set(index, matches[0].value)
                logger.info(f"从规则{rule}获取到数据 {index}: {matches[0].value}，已缓存")
        except Exception as e:
            logger.error(f"缓存响应参数失败：{e}")


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
