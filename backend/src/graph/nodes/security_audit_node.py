"""
用户输入安全审计节点

审计用户的输入，判断用户的prompt是否涉及安全问题以及是否不是API测试的内容
"""

from graph import AgentState


def security_audit_node(state: AgentState) -> dict:
    pass
