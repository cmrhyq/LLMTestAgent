"""TestWorkflow 流式输出方法测试。

覆盖 stream() / astream() / astream_events() 的事件序列、
include_updates 参数与异常处理。使用 FakeGraph 替代真实编译图，
不触发 LLM 调用。
"""

from typing import Any

from src.data.enum.workflow import TestStatus
from src.workflow import TestWorkflow

# 阻止 pytest 收集从 src 导入的 Test 前缀类（TestWorkflow / TestStatus）
TestWorkflow.__test__ = False  # type: ignore[attr-defined]
TestStatus.__test__ = False  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Fake 图：模拟 langgraph 的 stream / astream / astream_events
# ---------------------------------------------------------------------------


def _chunk(content: str) -> Any:
    """构造带 .content 属性的假 AIMessageChunk。"""
    return type("FakeChunk", (), {"content": content})()


class FakeGraph:
    """按预置序列产出 (mode, chunk) 的假编译图。"""

    def __init__(
        self,
        chunks: list[tuple[str, Any]] | None = None,
        events: list[dict] | None = None,
        *,
        raise_on_call: bool = False,
    ) -> None:
        self._chunks = chunks or []
        self._events = events or []
        self._raise = raise_on_call

    def stream(self, state: dict, **kwargs: Any):
        if self._raise:
            raise RuntimeError("graph boom")
        yield from self._chunks

    async def astream(self, state: dict, **kwargs: Any):
        if self._raise:
            raise RuntimeError("graph boom")
        for chunk in self._chunks:
            yield chunk

    async def astream_events(self, state: dict, **kwargs: Any):
        if self._raise:
            raise RuntimeError("graph boom")
        for event in self._events:
            yield event


def _make_workflow(graph: FakeGraph) -> TestWorkflow:
    """构造绕过 __init__ 的 TestWorkflow 实例（避免 build_graph/加载配置）。"""
    wf = TestWorkflow.__new__(TestWorkflow)
    wf.config = None
    wf.graph = graph
    return wf


NODE_CHUNKS = [
    ("updates", {"parse_input": {"user_intent": "run_test"}}),
    ("updates", {"generate_report": {"report_path": "/tmp/report.md"}}),
    ("values", {"run_status": TestStatus.COMPLETED.value, "report_path": "/tmp/report.md"}),
]

FINAL_STATE = {"run_status": TestStatus.COMPLETED.value, "report_path": "/tmp/report.md"}


# ---------------------------------------------------------------------------
# stream() 同步生成器
# ---------------------------------------------------------------------------


class TestStream:
    def test_stream_yields_node_and_final_events(self):
        wf = _make_workflow(FakeGraph(NODE_CHUNKS))
        events = list(wf.stream("测试登录接口"))

        types = [e["type"] for e in events]
        assert types == ["start", "node", "node", "final"]

        assert events[0]["raw_input"] == "测试登录接口"
        assert events[1]["node"] == "parse_input"
        assert "user_intent" in events[1]["update"]
        assert events[2]["node"] == "generate_report"
        assert events[3]["state"] == FINAL_STATE

    def test_stream_include_updates_false(self):
        wf = _make_workflow(FakeGraph(NODE_CHUNKS))
        events = list(wf.stream("测试登录接口", include_updates=False))

        node_events = [e for e in events if e["type"] == "node"]
        assert node_events
        assert all("update" not in e for e in node_events)

    def test_stream_yields_error_event(self):
        wf = _make_workflow(FakeGraph(raise_on_call=True))
        events = list(wf.stream("测试登录接口"))

        assert events[-1]["type"] == "error"
        assert "boom" in events[-1]["message"]
        assert events[-1]["state"]["run_status"] == TestStatus.FAILED.value
        assert events[-1]["state"]["error_message"] == "graph boom"

    def test_stream_final_falls_back_to_initial_state(self):
        # 图无任何输出时 final 事件携带初始状态
        wf = _make_workflow(FakeGraph([]))
        events = list(wf.stream("测试登录接口"))

        assert events[-1]["type"] == "final"
        assert events[-1]["state"]["raw_input"] == "测试登录接口"
        assert events[-1]["state"]["run_status"] == TestStatus.PENDING.value


# ---------------------------------------------------------------------------
# astream() 异步生成器
# ---------------------------------------------------------------------------


class TestAStream:
    async def test_astream_yields_node_and_final_events(self):
        wf = _make_workflow(FakeGraph(NODE_CHUNKS))
        events = [e async for e in wf.astream("测试登录接口")]

        types = [e["type"] for e in events]
        assert types == ["start", "node", "node", "final"]

        assert events[1]["node"] == "parse_input"
        assert events[3]["state"] == FINAL_STATE

    async def test_astream_include_updates_false(self):
        wf = _make_workflow(FakeGraph(NODE_CHUNKS))
        events = [e async for e in wf.astream("测试登录接口", include_updates=False)]

        node_events = [e for e in events if e["type"] == "node"]
        assert all("update" not in e for e in node_events)

    async def test_astream_yields_error_event(self):
        wf = _make_workflow(FakeGraph(raise_on_call=True))
        events = [e async for e in wf.astream("测试登录接口")]

        assert events[-1]["type"] == "error"
        assert events[-1]["message"] == "graph boom"
        assert events[-1]["state"]["run_status"] == TestStatus.FAILED.value


# ---------------------------------------------------------------------------
# astream_events() 事件级（token 流）
# ---------------------------------------------------------------------------


class TestAStreamEvents:
    EVENTS = [
        {"event": "on_chat_model_start", "name": "ChatModel", "data": {}},
        {
            "event": "on_chat_model_stream",
            "name": "ChatModel",
            "data": {"chunk": _chunk("正在")},
            "metadata": {"langgraph_node": "parse_input"},
        },
        {
            "event": "on_chat_model_stream",
            "name": "ChatModel",
            "data": {"chunk": _chunk("生成用例")},
            "metadata": {"langgraph_node": "generate_single_cases"},
        },
        # 无文本的 chunk 应被跳过
        {
            "event": "on_chat_model_stream",
            "name": "ChatModel",
            "data": {"chunk": _chunk("")},
            "metadata": {"langgraph_node": "generate_single_cases"},
        },
        {
            "event": "on_chain_end",
            "name": "LangGraph",
            "data": {"output": {"run_status": TestStatus.COMPLETED.value}},
        },
    ]

    async def test_astream_events_yields_tokens_and_final(self):
        wf = _make_workflow(FakeGraph(events=self.EVENTS))
        events = [e async for e in wf.astream_events("测试登录接口")]

        types = [e["type"] for e in events]
        assert types == ["start", "token", "token", "final"]

        assert events[1]["content"] == "正在"
        assert events[1]["node"] == "parse_input"
        assert events[2]["content"] == "生成用例"
        assert events[2]["node"] == "generate_single_cases"
        assert events[3]["state"] == {"run_status": TestStatus.COMPLETED.value}

    async def test_astream_events_without_llm_events(self):
        # 无 token 事件时（如纯执行节点），也应正常产出 start/final
        wf = _make_workflow(FakeGraph(events=[{"event": "on_chain_end", "name": "LangGraph", "data": {}}]))
        events = [e async for e in wf.astream_events("测试登录接口")]

        assert events[0]["type"] == "start"
        assert events[-1]["type"] == "final"
        # 顶层 on_chain_end 无 output 时回退到初始状态
        assert events[-1]["state"]["run_status"] == TestStatus.PENDING.value

    async def test_astream_events_yields_error_event(self):
        wf = _make_workflow(FakeGraph(raise_on_call=True))
        events = [e async for e in wf.astream_events("测试登录接口")]

        assert events[-1]["type"] == "error"
        assert events[-1]["message"] == "graph boom"
