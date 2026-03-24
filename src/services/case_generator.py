"""
测试用例生成模块

基于LangChain调用LLM，结合预设规则生成测试用例。

功能：
- 生成正常场景用例
- 生成参数缺失场景用例
- 生成参数类型错误场景用例
- 生成边界值场景用例
- 生成权限异常场景用例
- 用例参数化处理
- 用例去重
"""

import json
import hashlib
from typing import List, Dict, Any, Optional, Set

from ..core.models import (
    APIInfo,
    TestCase,
    Priority,
    ScenarioType,
)
from ..core.config import get_config, AppConfig
from .llm_client import get_llm_client, LLMClient
from src.core.logging import get_logger

logger = get_logger(__name__)


# 用例生成的系统提示词
CASE_GENERATION_SYSTEM_PROMPT = """你是一个专业的API测试用例生成专家。你的任务是根据提供的API信息，生成全面的测试用例。

请遵循以下规则：
1. 生成的用例必须覆盖正常场景、异常场景和边界值场景
2. 每个用例必须包含完整的请求信息和断言规则
3. 用例必须具有明确的预期结果
4. 输出必须是有效的JSON格式
5. 警告：不准使用类似"Bearer " + "a".repeat(10000)的东西

用例场景类型：
- normal: 正常场景，使用有效参数
- param_missing: 参数缺失，移除必填参数
- param_type_error: 参数类型错误，如字符串改为数字
- boundary_value: 边界值，如空字符串、极值
- permission_error: 权限异常，如无token或无效token

输出格式：
```json
{
  "test_cases": [
    {
      "case_name": "用例名称",
      "scenario_type": "场景类型",
      "priority": "P0/P1/P2",
      "headers": {},
      "body": {},
      "assert_rules": ["断言规则"],
      "expected_result": "预期结果",
      "description": "用例描述"
    }
  ]
}
```
"""

CASE_GENERATION_USER_PROMPT_TEMPLATE = """请为以下API生成测试用例：

API名称: {name}
API地址: {api_url}
请求方法: {method}
请求头: {headers}
请求体: {body}
现有断言规则: {assert_rules}
优先级: {priority}
描述: {description}

请生成以下类型的测试用例：
{scenario_types}

要求：
1. 正常场景用例优先级为P0
2. 参数缺失和权限异常用例优先级为P1
3. 参数类型错误和边界值用例优先级为P2
4. 每种场景类型至少生成1个用例
5. 对于请求体中的每个必填字段，生成一个参数缺失用例
6. 输出有效的JSON格式
"""


class CaseGenerator:
    """
    测试用例生成器
    
    基于LLM和规则引擎生成测试用例。
    
    Attributes:
        config: 应用配置
        llm_client: LLM客户端
        cache: 用例缓存
    """
    
    def __init__(self, config: Optional[AppConfig] = None, llm_client: Optional[LLMClient] = None):
        """
        初始化用例生成器
        
        Args:
            config: 应用配置
            llm_client: LLM客户端
        """
        self.config = config or get_config()
        self.llm_client = llm_client or get_llm_client()
        self.cache: Dict[str, List[TestCase]] = {}
    
    def generate(self, api_infos: List[APIInfo]) -> List[TestCase]:
        """
        为API列表生成测试用例
        
        Args:
            api_infos: API信息列表
            
        Returns:
            List[TestCase]: 测试用例列表
        """
        all_cases: List[TestCase] = []
        
        for api_info in api_infos:
            try:
                cases = self.generate_for_api(api_info)
                all_cases.extend(cases)
                logger.info(f"为API[{api_info.name}]生成了{len(cases)}个测试用例")
            except Exception as e:
                logger.error(f"为API[{api_info.name}]生成用例失败: {str(e)}")
                raise RuntimeError(f"API[{api_info.name}]用例生成失败: {str(e)}") from e
        
        # 去重
        unique_cases = self._deduplicate_cases(all_cases)
        logger.info(f"用例生成完成，总计{len(unique_cases)}个用例（去重后）")
        
        return unique_cases
    
    def generate_for_api(self, api_info: APIInfo) -> List[TestCase]:
        """
        为单个API生成测试用例
        
        Args:
            api_info: API信息
            
        Returns:
            List[TestCase]: 测试用例列表
        """
        # 检查缓存
        cache_key = self._get_cache_key(api_info)
        if self.config.case_generation.enable_cache and cache_key in self.cache:
            logger.debug(f"从缓存获取API[{api_info.name}]的测试用例")
            return self.cache[cache_key]
        
        # 仅允许LLM生成，移除规则兜底/模拟生成逻辑
        cases = self._generate_with_llm(api_info)
        if not cases:
            raise ValueError(f"API[{api_info.name}]未生成任何有效用例")
        
        # 缓存结果
        if self.config.case_generation.enable_cache:
            self.cache[cache_key] = cases
        
        return cases
    
    def _generate_with_llm(self, api_info: APIInfo) -> List[TestCase]:
        """
        使用LLM生成补充用例
        
        Args:
            api_info: API信息
            
        Returns:
            List[TestCase]: 测试用例列表
        """
        # 构建场景类型列表
        scenarios = self.config.case_generation.scenarios
        scenario_types = []
        if scenarios.normal:
            scenario_types.append("- 正常场景 (normal)")
        if scenarios.param_missing:
            scenario_types.append("- 参数缺失场景 (param_missing)")
        if scenarios.param_type_error:
            scenario_types.append("- 参数类型错误场景 (param_type_error)")
        if scenarios.boundary_value:
            scenario_types.append("- 边界值场景 (boundary_value)")
        if scenarios.permission_error:
            scenario_types.append("- 权限异常场景 (permission_error)")
        
        # 构建用户提示词
        user_prompt = CASE_GENERATION_USER_PROMPT_TEMPLATE.format(
            name=api_info.name,
            api_url=api_info.api_url,
            method=api_info.method.value,
            headers=json.dumps(api_info.headers, ensure_ascii=False, indent=2),
            body=json.dumps(api_info.body, ensure_ascii=False, indent=2) if api_info.body else "无",
            assert_rules=json.dumps(api_info.assert_rules, ensure_ascii=False),
            priority=api_info.priority.value,
            description=api_info.description or "无",
            scenario_types="\n".join(scenario_types),
        )
        
        # 调用LLM
        messages = [
            {"role": "system", "content": CASE_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        
        try:
            response = self.llm_client.chat(messages)
            cases = self._parse_llm_response(response, api_info)
            if not cases:
                raise ValueError(f"API[{api_info.name}]的LLM响应未产出有效用例")
            return cases
        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            raise RuntimeError(f"LLM调用失败: {str(e)}") from e
    
    def _parse_llm_response(self, response: str, api_info: APIInfo) -> List[TestCase]:
        """
        解析LLM响应
        
        Args:
            response: LLM响应内容
            api_info: API信息
            
        Returns:
            List[TestCase]: 测试用例列表
        """
        cases: List[TestCase] = []
        
        try:
            # 去除多余符号和空格
            response = response.replace("```json", "").strip()
            response = response.replace("```", "").strip()

            # 提取JSON部分
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("LLM响应中未找到有效JSON")

            # print(response)
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            test_cases_data = data.get("test_cases", [])
            
            for idx, case_data in enumerate(test_cases_data, 1):
                try:
                    # 解析场景类型
                    scenario_type_str = case_data.get("scenario_type", "custom")
                    try:
                        scenario_type = ScenarioType(scenario_type_str)
                    except ValueError:
                        scenario_type = ScenarioType.CUSTOM
                    
                    # 解析优先级
                    priority_str = case_data.get("priority", "P1")
                    try:
                        priority = Priority(priority_str)
                    except ValueError:
                        priority = Priority.P1
                    
                    case = TestCase(
                        case_id=f"{api_info.api_id}_llm_{idx:03d}",
                        case_name=case_data["case_name"],
                        api_url=api_info.api_url,
                        method=api_info.method,
                        scenario_type=scenario_type,
                        priority=priority,
                        headers=case_data["headers"],
                        body=case_data.get("body"),
                        assert_rules=case_data["assert_rules"],
                        dependencies=api_info.dependencies,
                        expected_result=case_data["expected_result"],
                        description=case_data.get("description", ""),
                        remark="LLM生成",
                    )
                    cases.append(case)
                except Exception as e:
                    logger.warning(f"解析LLM生成的用例失败: {str(e)}")
                    continue
        
        except json.JSONDecodeError as e:
            raise ValueError(f"解析LLM响应JSON失败: {str(e)}") from e
        
        return cases
    
    def _deduplicate_cases(self, cases: List[TestCase]) -> List[TestCase]:
        """
        用例去重
        
        按「API地址 + 请求方法 + 请求体MD5」去重
        
        Args:
            cases: 测试用例列表
            
        Returns:
            List[TestCase]: 去重后的用例列表
        """
        seen_hashes: Set[str] = set()
        unique_cases: List[TestCase] = []
        
        for case in cases:
            case_hash = case.get_unique_hash()
            if case_hash not in seen_hashes:
                seen_hashes.add(case_hash)
                unique_cases.append(case)
            else:
                logger.debug(f"去重: 移除重复用例 {case.case_id}")
        
        return unique_cases
    
    def _get_cache_key(self, api_info: APIInfo) -> str:
        """
        生成缓存键
        
        Args:
            api_info: API信息
            
        Returns:
            str: 缓存键
        """
        content = f"{api_info.api_url}|{api_info.method}|{json.dumps(api_info.body, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def validate_cases(self, cases: List[TestCase]) -> List[TestCase]:
        """
        校验用例
        
        检查用例的合法性，修正或过滤无效用例。
        
        Args:
            cases: 测试用例列表
            
        Returns:
            List[TestCase]: 校验后的用例列表
        """
        valid_cases: List[TestCase] = []
        
        for case in cases:
            # 校验必填字段
            if not case.case_id or not case.api_url:
                logger.warning(f"用例缺少必填字段: {case.case_id}")
                continue
            
            # 校验URL格式
            if not case.api_url.startswith(("http://", "https://")):
                logger.warning(f"用例URL格式无效: {case.api_url}")
                continue
            
            # 校验断言规则
            valid_rules = []
            for rule in case.assert_rules:
                try:
                    from ..core.models import AssertRule
                    AssertRule.parse(rule)
                    valid_rules.append(rule)
                except ValueError:
                    logger.warning(f"用例[{case.case_id}]断言规则无效: {rule}")
            case.assert_rules = valid_rules
            
            valid_cases.append(case)
        
        logger.info(f"用例校验完成: {len(valid_cases)}/{len(cases)}个有效")
        return valid_cases


def generate_test_cases(api_infos: List[APIInfo], config: Optional[AppConfig] = None) -> List[TestCase]:
    """
    生成测试用例的便捷函数
    
    Args:
        api_infos: API信息列表
        config: 应用配置
        
    Returns:
        List[TestCase]: 测试用例列表
    """
    generator = CaseGenerator(config)
    cases = generator.generate(api_infos)
    return generator.validate_cases(cases)
