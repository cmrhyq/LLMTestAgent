"""
报告生成模块

生成多格式测试报告：
- Excel报告：详细结果清单
- Markdown报告：简洁文本版
- HTML报告：可视化版，含图表
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from jinja2 import Template
import matplotlib
matplotlib.use('Agg')  # 非GUI后端
import matplotlib.pyplot as plt

from ..core.models import TestResult, TestSummary
from ..core.config import get_config, AppConfig
from .excel_exporter import ExcelExporter
from src.core.logging import get_logger

logger = get_logger(__name__)


# HTML报告模板
HTML_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API自动化测试报告</title>
    <style>
        :root {
            --primary-color: #2563eb;
            --success-color: #10b981;
            --danger-color: #ef4444;
            --warning-color: #f59e0b;
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-color: #1e293b;
            --text-muted: #64748b;
            --border-color: #e2e8f0;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .header {
            text-align: center;
            margin-bottom: 2rem;
            padding: 2rem;
            background: linear-gradient(135deg, var(--primary-color), #1d4ed8);
            color: white;
            border-radius: 1rem;
            box-shadow: 0 10px 40px rgba(37, 99, 235, 0.3);
        }
        
        .header h1 {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        
        .header .subtitle {
            opacity: 0.9;
            font-size: 1rem;
        }
        
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: var(--card-bg);
            border-radius: 1rem;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
        }
        
        .card-title {
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .card-value {
            font-size: 2rem;
            font-weight: 700;
        }
        
        .card-value.success { color: var(--success-color); }
        .card-value.danger { color: var(--danger-color); }
        .card-value.warning { color: var(--warning-color); }
        .card-value.primary { color: var(--primary-color); }
        
        .charts-section {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .chart-card {
            background: var(--card-bg);
            border-radius: 1rem;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }
        
        .chart-card h3 {
            margin-bottom: 1rem;
            color: var(--text-color);
        }
        
        .chart-card img {
            width: 100%;
            height: auto;
        }
        
        .results-section {
            background: var(--card-bg);
            border-radius: 1rem;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }
        
        .results-section h2 {
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid var(--border-color);
        }
        
        .interface-group {
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            margin-bottom: 1rem;
            overflow: hidden;
            background: #fff;
        }
        
        .interface-group summary {
            cursor: pointer;
            list-style: none;
            padding: 0.85rem 1rem;
            background: #eef2ff;
            border-bottom: 1px solid var(--border-color);
            font-weight: 600;
            color: #1e3a8a;
        }
        
        .interface-group summary::-webkit-details-marker {
            display: none;
        }
        
        .interface-group summary::before {
            content: "▶";
            display: inline-block;
            margin-right: 0.5rem;
            transition: transform 0.2s ease;
        }
        
        .interface-group[open] summary::before {
            transform: rotate(90deg);
        }
        
        .results-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .results-table th,
        .results-table td {
            padding: 1rem;
            text-align: left;
            vertical-align: top;
            border-bottom: 1px solid var(--border-color);
        }
        
        .json-block {
            max-width: 420px;
            max-height: 220px;
            overflow: auto;
            margin: 0;
            padding: 0.5rem;
            background: #f1f5f9;
            border-radius: 0.5rem;
            font-family: Consolas, 'Courier New', monospace;
            font-size: 0.75rem;
            white-space: pre-wrap;
            word-break: break-word;
        }
        
        .results-table th {
            background: var(--bg-color);
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }
        
        .results-table tr:hover {
            background: var(--bg-color);
        }
        
        .case-list {
            padding: 0.75rem;
        }
        
        .case-item {
            border: 1px solid var(--border-color);
            border-radius: 0.6rem;
            margin-bottom: 0.75rem;
            overflow: hidden;
            background: #ffffff;
        }
        
        .case-item summary {
            cursor: pointer;
            list-style: none;
            padding: 0.7rem 0.9rem;
            background: #f8fafc;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            gap: 0.75rem;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .case-item summary::-webkit-details-marker {
            display: none;
        }
        
        .case-item summary::before {
            content: "▶";
            display: inline-block;
            margin-right: 0.35rem;
            transition: transform 0.2s ease;
            color: #475569;
        }
        
        .case-item[open] summary::before {
            transform: rotate(90deg);
        }
        
        .case-meta {
            font-size: 0.82rem;
            color: #475569;
        }
        
        .case-content {
            padding: 0.75rem 0.9rem 0.9rem;
        }
        
        .kv-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .kv-table th,
        .kv-table td {
            padding: 0.65rem;
            border: 1px solid var(--border-color);
            vertical-align: top;
            text-align: left;
        }
        
        .kv-table th {
            width: 140px;
            background: #f8fafc;
            color: #334155;
            font-size: 0.8rem;
        }
        
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-badge.passed {
            background: #d1fae5;
            color: #065f46;
        }
        
        .status-badge.failed {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .status-badge.skipped {
            background: #fef3c7;
            color: #92400e;
        }
        
        .status-badge.error {
            background: #fce7f3;
            color: #9d174d;
        }
        
        .failure-reasons {
            background: var(--card-bg);
            border-radius: 1rem;
            padding: 1.5rem;
            margin-top: 2rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }
        
        .failure-reasons h2 {
            margin-bottom: 1rem;
            color: var(--danger-color);
        }
        
        .failure-item {
            display: flex;
            justify-content: space-between;
            padding: 0.75rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        .failure-item:last-child {
            border-bottom: none;
        }
        
        .failure-reason {
            flex: 1;
            font-family: monospace;
            font-size: 0.875rem;
        }
        
        .failure-count {
            font-weight: 600;
            color: var(--danger-color);
        }
        
        .footer {
            text-align: center;
            margin-top: 2rem;
            padding: 1rem;
            color: var(--text-muted);
            font-size: 0.875rem;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .charts-section {
                grid-template-columns: 1fr;
            }
            
            .results-table {
                display: block;
                overflow-x: auto;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 API自动化测试报告</h1>
            <p class="subtitle">生成时间: {{ generated_at }}</p>
        </div>
        
        <div class="summary-cards">
            <div class="card">
                <div class="card-title">总用例数</div>
                <div class="card-value primary">{{ summary.total }}</div>
            </div>
            <div class="card">
                <div class="card-title">通过</div>
                <div class="card-value success">{{ summary.passed }}</div>
            </div>
            <div class="card">
                <div class="card-title">失败</div>
                <div class="card-value danger">{{ summary.failed }}</div>
            </div>
            <div class="card">
                <div class="card-title">跳过</div>
                <div class="card-value warning">{{ summary.skipped }}</div>
            </div>
            <div class="card">
                <div class="card-title">通过率</div>
                <div class="card-value {% if summary.pass_rate >= 80 %}success{% elif summary.pass_rate >= 60 %}warning{% else %}danger{% endif %}">
                    {{ "%.1f"|format(summary.pass_rate) }}%
                </div>
            </div>
            <div class="card">
                <div class="card-title">平均耗时</div>
                <div class="card-value primary">{{ "%.2f"|format(summary.avg_response_time) }}ms</div>
            </div>
        </div>
        
        {% if include_charts %}
        <div class="charts-section">
            <div class="chart-card">
                <h3>📊 测试结果分布</h3>
                <img src="{{ pie_chart_path }}" alt="测试结果分布">
            </div>
            <div class="chart-card">
                <h3>⏱️ 响应时间分布</h3>
                <img src="{{ bar_chart_path }}" alt="响应时间分布">
            </div>
        </div>
        {% endif %}
        
        {% if summary.failure_reasons %}
        <div class="failure-reasons">
            <h2>❌ 失败原因统计 (Top 5)</h2>
            {% for reason, count in (summary.failure_reasons.items()|list)[:5] %}
            <div class="failure-item">
                <span class="failure-reason">{{ reason }}</span>
                <span class="failure-count">{{ count }}次</span>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <div class="results-section">
            <h2>📋 测试详情</h2>
            {% for group in grouped_results %}
            <details class="interface-group" {% if loop.first %}open{% endif %}>
                <summary>
                    接口: {{ group.request_url }}
                    <span style="color:#475569;font-weight:500;">(共{{ group.count }}条)</span>
                </summary>
                <div class="case-list">
                    {% for result in group.results %}
                    <details class="case-item">
                        <summary>
                            <strong>{{ result.case_id }}</strong>
                            <span>{{ result.case_name }}</span>
                            <span class="status-badge {{ result.status.value }}">{{ result.status.value }}</span>
                            <span class="case-meta">响应码: {{ result.response_status_code or '-' }}</span>
                            <span class="case-meta">耗时: {{ "%.2f"|format(result.response_time) if result.response_time else '-' }} ms</span>
                        </summary>
                        <div class="case-content">
                            <table class="kv-table">
                                <tbody>
                                    <tr>
                                        <th>请求方法</th>
                                        <td>{{ result.request_method or '-' }}</td>
                                    </tr>
                                    <tr>
                                        <th>请求地址</th>
                                        <td>{{ result.request_url or '-' }}</td>
                                    </tr>
                                    <tr>
                                        <th>请求头</th>
                                        <td><pre class="json-block">{{ format_json(result.request_headers) }}</pre></td>
                                    </tr>
                                    <tr>
                                        <th>请求数据</th>
                                        <td><pre class="json-block">{{ format_json(result.request_body) }}</pre></td>
                                    </tr>
                                    <tr>
                                        <th>响应码</th>
                                        <td>{{ result.response_status_code or '-' }}</td>
                                    </tr>
                                    <tr>
                                        <th>响应头</th>
                                        <td><pre class="json-block">{{ format_json(result.response_headers) }}</pre></td>
                                    </tr>
                                    <tr>
                                        <th>响应数据</th>
                                        <td><pre class="json-block">{{ format_json(result.response_body) }}</pre></td>
                                    </tr>
                                    <tr>
                                        <th>错误信息</th>
                                        <td>{{ result.error_message[:300] if result.error_message else '-' }}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </details>
                    {% endfor %}
                </div>
            </details>
            {% endfor %}
        </div>
        
        <div class="footer">
            <p>由 LLM API自动化测试工具 生成 | 执行时长: {{ "%.2f"|format(summary.total_duration) }}秒</p>
        </div>
    </div>
</body>
</html>
"""


class ReportGenerator:
    """
    报告生成器
    
    生成多格式测试报告。
    
    Attributes:
        config: 应用配置
    """
    
    def __init__(self, config: Optional[AppConfig] = None):
        """
        初始化报告生成器
        
        Args:
            config: 应用配置
        """
        self.config = config or get_config()
    
    def generate(
        self,
        results: List[TestResult],
        output_dir: Optional[str] = None
    ) -> Dict[str, str]:
        """
        生成测试报告
        
        Args:
            results: 测试结果列表
            output_dir: 输出目录
            
        Returns:
            Dict[str, str]: 报告路径字典 {格式: 路径}
        """
        if output_dir is None:
            output_dir = self.config.output.reports_dir
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 统一结果顺序，保证每次报告输出稳定（先按接口，再按用例）
        ordered_results = sorted(
            results,
            key=lambda r: (
                r.request_url or "",
                r.case_id or "",
            ),
        )
        
        # 生成摘要
        summary = TestSummary.from_results(ordered_results)
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        report_paths = {}
        formats = self.config.output.report.formats
        
        # 生成Excel报告
        if "excel" in formats:
            excel_path = self._generate_excel_report(ordered_results, output_path, timestamp)
            report_paths["excel"] = excel_path
        
        # 生成HTML报告
        if "html" in formats:
            html_path = self._generate_html_report(ordered_results, summary, output_path, timestamp)
            report_paths["html"] = html_path
        
        logger.info(f"报告生成完成: {report_paths}")
        return report_paths
    
    def _generate_excel_report(
        self,
        results: List[TestResult],
        output_path: Path,
        timestamp: str
    ) -> str:
        """
        生成Excel报告
        
        Args:
            results: 测试结果列表
            output_path: 输出目录
            timestamp: 时间戳
            
        Returns:
            str: Excel文件路径
        """
        exporter = ExcelExporter(self.config)
        excel_file = str(output_path / f"test_report_{timestamp}.xlsx")
        return exporter.export_test_results(results, excel_file)

    def _generate_html_report(
        self,
        results: List[TestResult],
        summary: TestSummary,
        output_path: Path,
        timestamp: str
    ) -> str:
        """
        生成HTML报告
        
        Args:
            results: 测试结果列表
            summary: 测试摘要
            output_path: 输出目录
            timestamp: 时间戳
            
        Returns:
            str: HTML文件路径
        """
        include_charts = self.config.output.report.include_charts
        pie_chart_path = ""
        bar_chart_path = ""
        
        # 生成图表
        if include_charts:
            pie_chart_path = self._generate_pie_chart(summary, output_path, timestamp)
            bar_chart_path = self._generate_bar_chart(results, output_path, timestamp)
        
        template = Template(HTML_REPORT_TEMPLATE)
        content = template.render(
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            summary=summary,
            results=results,
            grouped_results=self._group_results_by_interface(results),
            include_charts=include_charts,
            pie_chart_path=Path(pie_chart_path).name if pie_chart_path else "",
            bar_chart_path=Path(bar_chart_path).name if bar_chart_path else "",
            format_json=self._format_json_for_report,
        )
        
        html_file = output_path / f"test_report_{timestamp}.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"HTML报告已生成: {html_file}")
        return str(html_file)

    @staticmethod
    def _format_json_for_report(data: Any) -> str:
        """格式化报告中的JSON文本展示。"""
        if data is None:
            return "{}"
        if isinstance(data, str):
            return data
        try:
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            return str(data)
    
    @staticmethod
    def _group_results_by_interface(results: List[TestResult]) -> List[Dict[str, Any]]:
        """按请求地址分组测试结果，供HTML折叠展示使用。"""
        grouped: Dict[str, List[TestResult]] = {}
        for result in results:
            request_url = result.request_url or "-"
            grouped.setdefault(request_url, []).append(result)
        
        return [
            {
                "request_url": request_url,
                "count": len(group_results),
                "results": group_results,
            }
            for request_url, group_results in grouped.items()
        ]
    
    def _generate_pie_chart(
        self,
        summary: TestSummary,
        output_path: Path,
        timestamp: str
    ) -> str:
        """
        生成饼图
        
        Args:
            summary: 测试摘要
            output_path: 输出目录
            timestamp: 时间戳
            
        Returns:
            str: 图片路径
        """
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        labels = []
        sizes = []
        colors = []
        
        if summary.passed > 0:
            labels.append(f'通过 ({summary.passed})')
            sizes.append(summary.passed)
            colors.append('#10b981')
        
        if summary.failed > 0:
            labels.append(f'失败 ({summary.failed})')
            sizes.append(summary.failed)
            colors.append('#ef4444')
        
        if summary.skipped > 0:
            labels.append(f'跳过 ({summary.skipped})')
            sizes.append(summary.skipped)
            colors.append('#f59e0b')
        
        if summary.error > 0:
            labels.append(f'错误 ({summary.error})')
            sizes.append(summary.error)
            colors.append('#ec4899')
        
        if not sizes:
            sizes = [1]
            labels = ['无数据']
            colors = ['#94a3b8']
        
        fig, ax = plt.subplots(figsize=(8, 6))
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            pctdistance=0.75,
        )
        
        # 设置字体大小
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title('Test Results Distribution', fontsize=14, fontweight='bold', pad=20)
        
        # 保存图片
        chart_file = output_path / f"pie_chart_{timestamp}.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(chart_file)
    
    def _generate_bar_chart(
        self,
        results: List[TestResult],
        output_path: Path,
        timestamp: str
    ) -> str:
        """
        生成柱状图
        
        Args:
            results: 测试结果列表
            output_path: 输出目录
            timestamp: 时间戳
            
        Returns:
            str: 图片路径
        """
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 按响应时间分组
        time_ranges = {
            '0-100ms': 0,
            '100-500ms': 0,
            '500-1000ms': 0,
            '1000-3000ms': 0,
            '>3000ms': 0,
        }
        
        for result in results:
            if result.response_time <= 0:
                continue
            
            if result.response_time <= 100:
                time_ranges['0-100ms'] += 1
            elif result.response_time <= 500:
                time_ranges['100-500ms'] += 1
            elif result.response_time <= 1000:
                time_ranges['500-1000ms'] += 1
            elif result.response_time <= 3000:
                time_ranges['1000-3000ms'] += 1
            else:
                time_ranges['>3000ms'] += 1
        
        labels = list(time_ranges.keys())
        values = list(time_ranges.values())
        colors = ['#10b981', '#22c55e', '#f59e0b', '#f97316', '#ef4444']
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(labels, values, color=colors, edgecolor='white', linewidth=1.5)
        
        # 添加数值标签
        for bar, value in zip(bars, values):
            if value > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.5,
                    str(value),
                    ha='center',
                    va='bottom',
                    fontsize=10,
                    fontweight='bold'
                )
        
        ax.set_xlabel('Response Time Range', fontsize=12)
        ax.set_ylabel('Count', fontsize=12)
        ax.set_title('Response Time Distribution', fontsize=14, fontweight='bold', pad=20)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # 保存图片
        chart_file = output_path / f"bar_chart_{timestamp}.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(chart_file)


def generate_report(
    results: List[TestResult],
    output_dir: Optional[str] = None,
    config: Optional[AppConfig] = None
) -> Dict[str, str]:
    """
    生成报告的便捷函数
    
    Args:
        results: 测试结果列表
        output_dir: 输出目录
        config: 应用配置
        
    Returns:
        Dict[str, str]: 报告路径字典
    """
    generator = ReportGenerator(config)
    return generator.generate(results, output_dir)
