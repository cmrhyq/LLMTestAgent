"""
输入解析模块

负责解析和校验用户输入的API信息，包括：
- JSON格式解析
- 必填字段校验
- JSONPath语法校验
- 依赖关系闭环检测
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from src.data.enum.models import (
    APIInfo,
    HttpMethod,
    Priority,
    ValidationResult,
    AssertRule,
)
from src.core.logging import get_logger

logger = get_logger(__name__)


class InputParser:
    """
    输入解析器
    
    负责解析用户输入的API信息，并进行校验。
    
    Attributes:
        raw_input: 原始输入数据
        api_infos: 解析后的API信息列表
        validation_result: 校验结果
    """
    
    def __init__(self):
        """初始化输入解析器"""
        self.raw_input: Dict[str, Any] = {}
        self.domain: str = ""
        self.api_infos: List[APIInfo] = []
        self.validation_result: ValidationResult = ValidationResult()
    
    def parse(self, input_data: Dict[str, Any] | str | Path) -> tuple[str, list[APIInfo], ValidationResult]:
        """
        解析输入数据
        
        Args:
            input_data: 输入数据，可以是字典、JSON字符串或文件路径
            
        Returns:
            Tuple[List[APIInfo], ValidationResult]: API信息列表和校验结果
        """
        # 重置状态
        self.domain = ""
        self.api_infos = []
        self.validation_result = ValidationResult()
        
        # 加载输入数据
        try:
            self.raw_input = self._load_input(input_data)
        except Exception as e:
            self.validation_result.add_error(f"加载输入数据失败: {str(e)}")
            return self.domain, self.api_infos, self.validation_result

        self.domain = self.raw_input.get("domain", "")
        if self.domain == "":
            self.validation_result.add_error("输入数据中缺少apis字段或为空")
            return self.domain, self.api_infos, self.validation_result
        
        # 解析API列表
        apis_data = self.raw_input.get("apis", [])
        if not apis_data:
            self.validation_result.add_error("输入数据中缺少apis字段或为空")
            return self.domain, self.api_infos, self.validation_result
        
        # 解析每个API
        for idx, api_data in enumerate(apis_data):
            try:
                api_info = self._parse_api(api_data, idx)
                if api_info:
                    self.api_infos.append(api_info)
            except Exception as e:
                self.validation_result.add_error(f"解析API[{idx}]失败: {str(e)}")
        
        logger.info(f"解析完成: {len(self.api_infos)}个API, 校验结果: {self.validation_result.is_valid}")
        return self.domain, self.api_infos, self.validation_result
    
    def _load_input(self, input_data: Dict[str, Any] | str | Path) -> Dict[str, Any]:
        """
        加载输入数据
        
        Args:
            input_data: 输入数据
            
        Returns:
            Dict[str, Any]: 解析后的字典
        """
        if isinstance(input_data, dict):
            return input_data
        
        if isinstance(input_data, Path) or (isinstance(input_data, str) and Path(input_data).exists()):
            path = Path(input_data)
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        if isinstance(input_data, str):
            return json.loads(input_data)
        
        raise ValueError(f"不支持的输入类型: {type(input_data)}")
    
    def _parse_api(self, api_data: Dict[str, Any], index: int) -> Optional[APIInfo]:
        """
        解析单个API信息
        
        Args:
            api_data: API数据
            index: API索引
            
        Returns:
            Optional[APIInfo]: API信息对象
        """
        # 校验必填字段
        required_fields = ["url", "method"]
        for field in required_fields:
            if field not in api_data or not api_data[field]:
                self.validation_result.add_error(f"API[{index}]缺少必填字段: {field}")
                return None
        
        # 生成名称（如果未提供）
        name = api_data.get("name", f"API_{index + 1}")
        
        # 解析请求方法
        try:
            method = HttpMethod(api_data["method"].upper())
        except ValueError:
            self.validation_result.add_error(
                f"API[{index}]请求方法无效: {api_data['method']}, "
                f"支持的方法: {[m.value for m in HttpMethod]}"
            )
            return None
        
        # 解析优先级
        priority_str = api_data.get("priority", "P1")
        try:
            priority = Priority(priority_str)
        except ValueError:
            self.validation_result.add_warning(
                f"API[{index}]优先级无效: {priority_str}, 使用默认值P1"
            )
            priority = Priority.P1

        # 参数缓存规则
        cache_rules = api_data.get("cache_rules")
        
        # 校验断言规则
        assert_rules = api_data.get("assert_rules", [])
        validated_rules = self._validate_assert_rules(assert_rules, index)
        
        # 创建API信息对象
        try:
            api_info = APIInfo(
                name=name,
                url=api_data["url"],
                method=method,
                headers=api_data.get("headers", {}),
                body=api_data.get("body"),
                params=api_data.get("params"),
                cache_rules=cache_rules,
                assert_rules=validated_rules,
                priority=priority,
                description=api_data.get("description", ""),
                tags=api_data.get("tags", []),
            )
            return api_info
        except Exception as e:
            self.validation_result.add_error(f"API[{index}]创建失败: {str(e)}")
            return None
    
    def _validate_assert_rules(self, rules: List[str], api_index: int) -> List[str]:
        """
        校验断言规则
        
        Args:
            rules: 断言规则列表
            api_index: API索引
            
        Returns:
            List[str]: 有效的断言规则列表
        """
        valid_rules = []
        
        for rule in rules:
            try:
                # 尝试解析断言规则
                AssertRule.parse(rule)
                valid_rules.append(rule)
            except ValueError as e:
                self.validation_result.add_warning(
                    f"API[{api_index}]断言规则无效: {rule}, 错误: {str(e)}"
                )
        
        return valid_rules

def parse_input(input_data: Dict[str, Any] | str | Path) -> Tuple[List[APIInfo], ValidationResult]:
    """
    解析输入数据的便捷函数
    
    Args:
        input_data: 输入数据
        
    Returns:
        Tuple[List[APIInfo], ValidationResult]: API信息列表和校验结果
    """
    parser = InputParser()
    return parser.parse(input_data)
