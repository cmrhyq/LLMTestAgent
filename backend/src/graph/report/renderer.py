"""HTML 报告渲染器。

使用 Jinja2 模板渲染离线 HTML 测试报告，
替代 generate_report_node 中内联的字符串拼接 HTML。
"""

import json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import escape

from src.utils.json_utils import safe_json_loads

_TEMPLATE_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _pretty_json(raw: str | None) -> str:
    """Pretty-print 一段 JSON；解析失败时原样返回。"""
    if not raw:
        return ""
    parsed = safe_json_loads(raw, None)
    if parsed is None:
        return raw
    return json.dumps(parsed, ensure_ascii=False, indent=2)


def _status_badge(status: str | None) -> str:
    """状态徽章 HTML。"""
    css_class = {
        "passed": "badge-passed",
        "failed": "badge-failed",
        "error": "badge-error",
        "skipped": "badge-skipped",
        "pending": "badge-pending",
        "running": "badge-running",
    }.get(status or "", "badge-pending")
    return f'<span class="badge {css_class}">{escape(status or "")}</span>'


def _method_badge(method: str | None) -> str:
    """HTTP 方法徽章 HTML。"""
    method_text = (method or "").upper()
    css_class = {
        "GET": "method-get",
        "POST": "method-post",
        "PUT": "method-put",
        "PATCH": "method-patch",
        "DELETE": "method-delete",
    }.get(method_text, "method-default")
    return f'<span class="method-badge {css_class}">{escape(method_text or "N/A")}</span>'


_env.filters["pretty_json"] = _pretty_json
_env.filters["status_badge"] = _status_badge
_env.filters["method_badge"] = _method_badge


def _compute_stats(results) -> dict | None:
    """计算响应耗时统计（avg/min/max/p95，单位毫秒）。"""
    times = [r.response_time for r in results if r.response_time and r.response_time > 0]
    if not times:
        return None
    sorted_times = sorted(times)
    p95_idx = min(int(len(sorted_times) * 0.95), len(sorted_times) - 1)
    return {
        "avg": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
        "p95": sorted_times[p95_idx],
    }


def render_report(test_run, results) -> str:
    """渲染 HTML 测试报告。"""
    total = test_run.total_cases or len(results)
    failed_results = [r for r in results if r.status in ("failed", "error")]
    template = _env.get_template("report.html.j2")
    return template.render(
        test_run=test_run,
        results=results,
        failed_results=failed_results,
        total=total,
        stats=_compute_stats(results),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
