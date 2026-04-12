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
from typing import List, Dict, Optional, Set

from ..core.models import (
    APIInfo,
    TestCase,
    Priority,
    ScenarioType,
)
from ..core.config import get_config, AppConfig
from src.core.llm.llm_client import get_llm_client, LLMClient
from src.core.logging import get_logger
from ..prompts import CASE_GENERATION_SYSTEM_PROMPT
from ..prompts.builders.case_builder import CasePromptBuilder
from ..prompts.formatters.case_formatter import format_scenario_types

logger = get_logger(__name__)


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
        self.case_prompt_builder = CasePromptBuilder()
    
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
                cases = self._generate_with_llm(api_info)
                all_cases.extend(cases)
                logger.info(f"为API[{api_info.name}]生成了{len(cases)}个测试用例")
            except Exception as e:
                logger.error(f"为API[{api_info.name}]生成用例失败: {str(e)}")
                raise RuntimeError(f"API[{api_info.name}]用例生成失败: {str(e)}") from e
        
        # 去重
        unique_cases = self._deduplicate_cases(all_cases)
        logger.info(f"用例生成完成，总计{len(unique_cases)}个用例（去重后）")
        
        return unique_cases

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
        scenario_types = format_scenario_types(scenarios)

        # 构建用户提示词
        user_prompt = self.case_prompt_builder.build_user_prompt(
            api_info={
                "name": api_info.name,
                "url": api_info.url,
                "method": api_info.method.value,
                "headers": api_info.headers,
                "body": api_info.body,
                "params": api_info.params,
                "assert_rules": api_info.assert_rules,
                "priority": api_info.priority.value,
                "description": api_info.description,
            },
            scenario_types=scenario_types,
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
                        url=api_info.url,
                        method=api_info.method,
                        scenario_type=scenario_type,
                        priority=priority,
                        headers=case_data["headers"],
                        body=case_data.get("body"),
                        cache_rules=api_info.cache_rules,
                        assert_rules=case_data["assert_rules"],
                        expected_result=case_data["expected_result"],
                        description=case_data.get("description", ""),
                        remark="LLM生成",
                    )
                    cases.append(case)
                except Exception as e:
                    logger.debug(f"Case Data: {case_data}")
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
        content = f"{api_info.url}|{api_info.method}|{json.dumps(api_info.body, sort_keys=True)}"
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
            if not case.case_id or not case.url:
                logger.warning(f"用例缺少必填字段: {case.case_id}")
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
