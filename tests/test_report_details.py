import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.core.config import AppConfig
from src.data.enum.models import TestResult, TestStatus
from src.graph.report_generator import ReportGenerator


class ReportDetailsTest(unittest.TestCase):
    def test_markdown_contains_request_and_response_fields(self) -> None:
        config = AppConfig()
        config.output.report.formats = ["markdown"]
        config.output.report.include_charts = False

        result = TestResult(
            case_id="case_001",
            case_name="查询用户",
            status=TestStatus.PASSED,
            request_method="POST",
            request_url="https://example.test/api/user/query",
            request_headers={"Content-Type": "application/json"},
            request_body={"userId": 1001},
            response_status_code=200,
            response_headers={"x-trace-id": "trace-001"},
            response_body={"code": 0, "msg": "ok"},
            response_time=123.45,
            started_at=datetime.now(),
            finished_at=datetime.now(),
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            generator = ReportGenerator(config)
            report_paths = generator.generate([result], tmp_dir)

            markdown_path = Path(report_paths["markdown"])
            content = markdown_path.read_text(encoding="utf-8")

        self.assertIn("请求方法: POST", content)
        self.assertIn("请求地址: https://example.test/api/user/query", content)
        self.assertIn("\"Content-Type\": \"application/json\"", content)
        self.assertIn("\"userId\": 1001", content)
        self.assertIn("\"x-trace-id\": \"trace-001\"", content)
        self.assertIn("\"code\": 0", content)
    
    def test_html_groups_by_request_url_with_details(self) -> None:
        config = AppConfig()
        config.output.report.formats = ["html"]
        config.output.report.include_charts = False

        results = [
            TestResult(
                case_id="case_a_001",
                case_name="接口A-用例1",
                status=TestStatus.PASSED,
                request_method="GET",
                request_url="https://example.test/api/a",
                request_headers={"Accept": "application/json"},
                response_status_code=200,
                response_headers={"x-trace-id": "a-1"},
                response_body={"ok": True},
                response_time=10.0,
                started_at=datetime.now(),
                finished_at=datetime.now(),
            ),
            TestResult(
                case_id="case_a_002",
                case_name="接口A-用例2",
                status=TestStatus.FAILED,
                request_method="POST",
                request_url="https://example.test/api/a",
                request_headers={"Content-Type": "application/json"},
                request_body={"name": "foo"},
                response_status_code=400,
                response_headers={"x-trace-id": "a-2"},
                response_body={"error": "bad request"},
                response_time=12.0,
                started_at=datetime.now(),
                finished_at=datetime.now(),
            ),
            TestResult(
                case_id="case_b_001",
                case_name="接口B-用例1",
                status=TestStatus.PASSED,
                request_method="GET",
                request_url="https://example.test/api/b",
                request_headers={"Accept": "application/json"},
                response_status_code=200,
                response_headers={"x-trace-id": "b-1"},
                response_body={"ok": True},
                response_time=20.0,
                started_at=datetime.now(),
                finished_at=datetime.now(),
            ),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            generator = ReportGenerator(config)
            report_paths = generator.generate(results, tmp_dir)
            html_path = Path(report_paths["html"])
            content = html_path.read_text(encoding="utf-8")

        self.assertIn("class=\"interface-group\"", content)
        self.assertIn("接口: https://example.test/api/a", content)
        self.assertIn("接口: https://example.test/api/b", content)
        self.assertIn("(共2条)", content)
        self.assertIn("(共1条)", content)
        self.assertIn("\"Content-Type\": \"application/json\"", content)
        self.assertIn("\"error\": \"bad request\"", content)


if __name__ == "__main__":
    unittest.main()
