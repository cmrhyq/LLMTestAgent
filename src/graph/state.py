from typing import TypedDict, Dict, Any, List


class GraphState(TypedDict):
    """
    工作流状态类型定义

    用于LangGraph StateGraph的状态管理。
    """
    # 输入
    raw_input: Dict[str, Any]

    # 解析结果
    api_infos: List[Dict[str, Any]]
    validation_result: Dict[str, Any]

    # 用例
    test_cases: List[Dict[str, Any]]

    # 执行上下文
    execution_context: Dict[str, Any]

    # 结果
    test_results: List[Dict[str, Any]]
    test_summary: Dict[str, Any]

    # 报告
    report_paths: Dict[str, str]
    excel_path: str

    # 工作流控制
    current_node: str
    error_message: str
    retry_count: int
    should_continue: bool