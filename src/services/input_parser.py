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
from typing import Dict, Any, List, Optional, Set, Tuple
from loguru import logger

from ..core.models import (
    APIInfo,
    HttpMethod,
    Priority,
    ValidationResult,
    AssertRule,
    Dependency,
)


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
        self.api_infos: List[APIInfo] = []
        self.validation_result: ValidationResult = ValidationResult()
    
    def parse(self, input_data: Dict[str, Any] | str | Path) -> Tuple[List[APIInfo], ValidationResult]:
        """
        解析输入数据
        
        Args:
            input_data: 输入数据，可以是字典、JSON字符串或文件路径
            
        Returns:
            Tuple[List[APIInfo], ValidationResult]: API信息列表和校验结果
        """
        # 重置状态
        self.api_infos = []
        self.validation_result = ValidationResult()
        
        # 加载输入数据
        try:
            self.raw_input = self._load_input(input_data)
        except Exception as e:
            self.validation_result.add_error(f"加载输入数据失败: {str(e)}")
            return self.api_infos, self.validation_result
        
        # 解析API列表
        apis_data = self.raw_input.get("apis", [])
        if not apis_data:
            self.validation_result.add_error("输入数据中缺少apis字段或为空")
            return self.api_infos, self.validation_result
        
        # 解析每个API
        for idx, api_data in enumerate(apis_data):
            try:
                api_info = self._parse_api(api_data, idx)
                if api_info:
                    self.api_infos.append(api_info)
            except Exception as e:
                self.validation_result.add_error(f"解析API[{idx}]失败: {str(e)}")
        
        # 校验依赖关系
        if self.api_infos:
            self._validate_dependencies()
        
        logger.info(f"解析完成: {len(self.api_infos)}个API, 校验结果: {self.validation_result.is_valid}")
        return self.api_infos, self.validation_result
    
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
        required_fields = ["api_url", "method"]
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
        
        # 校验断言规则
        assert_rules = api_data.get("assert_rules", [])
        validated_rules = self._validate_assert_rules(assert_rules, index)
        
        # 校验依赖关系格式
        dependencies = api_data.get("dependencies", {})
        validated_deps = self._validate_dependency_format(dependencies, index)
        
        # 创建API信息对象
        try:
            api_info = APIInfo(
                name=name,
                api_url=api_data["api_url"],
                method=method,
                headers=api_data.get("headers", {}),
                body=api_data.get("body"),
                query_params=api_data.get("query_params"),
                assert_rules=validated_rules,
                dependencies=validated_deps,
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
    
    def _validate_dependency_format(
        self, dependencies: Dict[str, Dict[str, str]], api_index: int
    ) -> Dict[str, Dict[str, str]]:
        """
        校验依赖关系格式
        
        Args:
            dependencies: 依赖关系
            api_index: API索引
            
        Returns:
            Dict[str, Dict[str, str]]: 有效的依赖关系
        """
        valid_deps = {}
        
        for dep_id, dep_info in dependencies.items():
            if not isinstance(dep_info, dict):
                self.validation_result.add_warning(
                    f"API[{api_index}]依赖关系格式无效: {dep_id}"
                )
                continue
            
            source_path = dep_info.get("source_path", "")
            target_param = dep_info.get("target_param", "")
            
            # 校验source_path
            if not source_path.startswith("$."):
                self.validation_result.add_warning(
                    f"API[{api_index}]依赖{dep_id}的source_path必须以$.开头: {source_path}"
                )
                continue
            
            # 校验target_param
            valid_prefixes = ["headers.", "body.", "query.", "path."]
            if not any(target_param.startswith(prefix) for prefix in valid_prefixes):
                self.validation_result.add_warning(
                    f"API[{api_index}]依赖{dep_id}的target_param格式无效: {target_param}"
                )
                continue
            
            valid_deps[dep_id] = dep_info
        
        return valid_deps
    
    def _validate_dependencies(self) -> None:
        """
        校验依赖关系
        
        检测：
        1. 依赖的API是否存在
        2. 是否存在循环依赖
        """
        # 构建API ID映射
        api_id_map = {api.name: api for api in self.api_infos}
        api_id_map.update({api.api_id: api for api in self.api_infos})
        
        # 检查依赖是否存在
        for api in self.api_infos:
            for dep_id in api.dependencies.keys():
                if dep_id not in api_id_map:
                    self.validation_result.add_warning(
                        f"API[{api.name}]依赖的接口不存在: {dep_id}"
                    )
        
        # 检测循环依赖
        cycle = self._detect_dependency_cycle()
        if cycle:
            self.validation_result.add_error(
                f"检测到循环依赖: {' -> '.join(cycle)}"
            )
    
    def _detect_dependency_cycle(self) -> Optional[List[str]]:
        """
        检测依赖循环
        
        使用DFS检测有向图中的环
        
        Returns:
            Optional[List[str]]: 如果存在环，返回环中的节点列表
        """
        # 构建依赖图
        graph: Dict[str, Set[str]] = {}
        for api in self.api_infos:
            api_id = api.name
            graph[api_id] = set(api.dependencies.keys())
        
        # DFS检测环
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []
        
        def dfs(node: str) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    # 找到环
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
            
            path.pop()
            rec_stack.remove(node)
            return None
        
        for node in graph:
            if node not in visited:
                result = dfs(node)
                if result:
                    return result
        
        return None
    
    def get_execution_order(self) -> List[APIInfo]:
        """
        获取API执行顺序（拓扑排序）
        
        Returns:
            List[APIInfo]: 按依赖顺序排列的API列表
        """
        if not self.api_infos:
            return []
        
        # 构建API ID映射
        api_map = {api.name: api for api in self.api_infos}
        
        # 计算入度
        in_degree: Dict[str, int] = {api.name: 0 for api in self.api_infos}
        for api in self.api_infos:
            for dep_id in api.dependencies.keys():
                if dep_id in in_degree:
                    in_degree[api.name] += 1
        
        # 拓扑排序
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(api_map[current])
            
            # 更新入度
            for api in self.api_infos:
                if current in api.dependencies:
                    in_degree[api.name] -= 1
                    if in_degree[api.name] == 0:
                        queue.append(api.name)
        
        # 如果结果数量不等于API数量，说明存在环（理论上前面已经检测过）
        if len(result) != len(self.api_infos):
            logger.warning("拓扑排序失败，可能存在循环依赖")
            return self.api_infos
        
        return result


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
