"""LangGraph 工作流状态定义。

使用 TypedDict + Annotated reducer 模式，符合 LangGraph 2026 规范。
"""

from typing import Any, Dict, List

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """统一工作流状态。

    继承 MessagesState 自动包含 messages 字段（带 add_messages reducer）。
    包含所有节点需要的业务数据字段。
    """

    raw_input: str
    api_doc_file_path: str
    user_intent: str
    test_mode: str
    selected_endpoints: List[Dict[str, Any]]
    test_results: List[Dict[str, Any]]
    test_summary: Dict[str, Any]
    run_id: int
    test_cases_count: int
    test_results_summary: Dict[str, Any]
    report_path: str
    error_message: str
