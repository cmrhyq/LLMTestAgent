"""LangGraph 工作流状态定义。

使用 TypedDict + Annotated reducer 模式，符合 LangGraph 2026 规范。
"""

from typing import Any, Dict, List

from typing_extensions import TypedDict
from langgraph.graph import MessagesState


class TestGraphState(TypedDict, total=False):
    """测试工作流状态。

    只包含业务数据字段，工作流控制由 LangGraph 图结构自身管理。
    使用 total=False 允许节点返回部分状态更新。
    """

    raw_input: str
    api_doc_file_path: str
    user_intent: str
    selected_endpoints: List[Dict[str, Any]]
    test_results: List[Dict[str, Any]]
    test_summary: Dict[str, Any]
    report_path: str
    error_message: str


class AgentState(MessagesState):
    """带 messages 的 Agent 状态，用于 ToolNode 场景。

    继承 MessagesState 自动包含 messages 字段（带 add_messages reducer）。
    """

    raw_input: str
    user_intent: str
    selected_endpoints: List[Dict[str, Any]]
    error_message: str
